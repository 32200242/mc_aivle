from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.account_recovery import get_recovery_center, list_recovery_centers


client = TestClient(app)


def test_recovery_centers_are_synthetic_sorted_and_bounded() -> None:
    response = client.get("/api/v1/auth/recovery/centers")

    assert response.status_code == 200
    body = response.json()
    assert body["synthetic"] is True
    assert len(body["centers"]) == 244
    assert body["centers"] == sorted(
        body["centers"],
        key=lambda center: (center["region_name"], center["center_name"], center["center_id"]),
    )
    assert set(body["centers"][0]) == {"center_id", "center_name", "region_name"}
    display_labels = {
        (center["region_name"], center["center_name"])
        for center in body["centers"]
    }
    assert len(display_labels) == len(body["centers"])


def test_recovery_counselors_returns_only_selected_center_public_fields() -> None:
    center = next(item for item in list_recovery_centers() if item["center_id"] == "CTR-SEO-001")
    expected = get_recovery_center(center["center_id"])
    assert expected is not None

    response = client.get(
        "/api/v1/auth/recovery/counselors",
        params={"center_id": center["center_id"].lower()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["synthetic"] is True
    assert body["center_id"] == center["center_id"]
    assert body["center_name"] == center["center_name"]
    assert body["region_name"] == center["region_name"]
    assert body["counselors"] == expected["counselors"]
    assert body["counselors"]
    assert all(
        set(counselor) == {"counselor_id", "counselor_name"}
        for counselor in body["counselors"]
    )
    assert all(counselor["counselor_name"].endswith(" 상담사") for counselor in body["counselors"])
    assert body["counselors"] == sorted(
        body["counselors"],
        key=lambda counselor: (counselor["counselor_name"], counselor["counselor_id"]),
    )


def test_recovery_counselors_rejects_unknown_or_malformed_center() -> None:
    missing = client.get(
        "/api/v1/auth/recovery/counselors",
        params={"center_id": "CTR-SEO-999"},
    )
    malformed = client.get(
        "/api/v1/auth/recovery/counselors",
        params={"center_id": "SEO"},
    )

    assert missing.status_code == 404
    assert missing.json()["detail"] == "해당 센터를 찾을 수 없습니다."
    assert malformed.status_code == 422


def test_recovery_endpoints_require_no_auth_but_do_not_disclose_login_secrets() -> None:
    centers = client.get("/api/v1/auth/recovery/centers").json()["centers"]
    response = client.get(
        "/api/v1/auth/recovery/counselors",
        params={"center_id": centers[0]["center_id"]},
    )

    assert response.status_code == 200
    serialized = response.text.lower()
    assert "password" not in serialized
    assert "access_token" not in serialized
    assert "auth_secret" not in serialized
