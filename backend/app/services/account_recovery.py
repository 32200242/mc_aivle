from __future__ import annotations

from functools import lru_cache
from typing import Any

from .operational_data import REGION_SPECS, get_counselor_directory


REGION_NAMES = {str(spec[0]): str(spec[2]) for spec in REGION_SPECS}


@lru_cache(maxsize=1)
def _recovery_directory() -> dict[str, dict[str, Any]]:
    """Build the public-demo account directory from synthetic operational data only."""

    centers: dict[str, dict[str, Any]] = {}
    for item in get_counselor_directory():
        center_id = str(item["center_id"])
        center_name = str(item["center_name"])
        region_name = REGION_NAMES[str(item["region_id"])]
        center = centers.setdefault(
            center_id,
            {
                "center_id": center_id,
                "center_name": center_name,
                "region_name": region_name,
                "counselors": [],
            },
        )
        center["counselors"].append({
            "counselor_id": str(item["id"]),
            "counselor_name": f"{item['display_name']} 상담사",
        })

    for center in centers.values():
        center["counselors"].sort(
            key=lambda counselor: (counselor["counselor_name"], counselor["counselor_id"])
        )
    return centers


def list_recovery_centers() -> list[dict[str, str]]:
    centers = _recovery_directory().values()
    return sorted(
        (
            {
                "center_id": str(center["center_id"]),
                "center_name": str(center["center_name"]),
                "region_name": str(center["region_name"]),
            }
            for center in centers
        ),
        key=lambda center: (center["region_name"], center["center_name"], center["center_id"]),
    )


def get_recovery_center(center_id: str) -> dict[str, Any] | None:
    normalized = center_id.strip().upper()
    return _recovery_directory().get(normalized)
