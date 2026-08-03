import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import ai, copilot, llm, records, stt
from backend.app.services.ai import extract_json_object
from backend.app.services.ocr import clean_form_boilerplate
from backend.app.synthetic_cases import build_case_analysis_context, get_client_case, get_session


client = TestClient(app)


@pytest.fixture(autouse=True)
def force_mock_provider(monkeypatch):
    mock_settings = SimpleNamespace(ai_provider="mock")
    monkeypatch.setattr(ai, "settings", mock_settings)
    monkeypatch.setattr(copilot, "settings", mock_settings)
    monkeypatch.setattr(llm, "settings", mock_settings)
    monkeypatch.setattr(records, "settings", mock_settings)
    monkeypatch.setattr(stt, "settings", SimpleNamespace(stt_provider="browser", internal_stt_url=""))


def login(username: str = "counselor") -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": "demo"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_health() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_training_session_and_stream() -> None:
    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    session = client.post("/api/v1/training/sessions", headers=headers, json={}).json()
    response = client.post(
        f"/api/v1/training/sessions/{session['id']}/turns/stream",
        headers=headers,
        json={"counselor_message": "요즘 가장 힘든 순간이 언제인가요?"},
    )
    assert response.status_code == 200
    assert "event: turn.completed" in response.text
    assert "nonverbal_cues" in response.text


def test_admin_role_is_enforced() -> None:
    counselor_headers = {"Authorization": f"Bearer {login('counselor')}"}
    assert client.get("/api/v1/admin/dashboard", headers=counselor_headers).status_code == 403
    admin_headers = {"Authorization": f"Bearer {login('admin')}"}
    response = client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["center_count"] == 223


def test_copilot_api_returns_dynamic_contract() -> None:
    headers = {"Authorization": f"Bearer {login('counselor')}"}
    status = client.get("/api/v1/ai/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["provider"] == "mock"
    response = client.post(
        "/api/v1/copilot/analyze",
        headers=headers,
        json={
            "transcript": "상담사: 요즘 어떠세요? 내담자: 남편과 싸울까 봐 불안하고 말을 못 하겠어요.",
            "session_goal": "감정 표현과 관계 회복",
            "counselor_note": "시선 회피가 관찰됨",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock"
    assert body["core_issues"]
    assert set(body["soap_draft"]) == {"S", "O", "A", "P"}


def test_copilot_can_analyze_loaded_synthetic_case_without_manual_transcript() -> None:
    headers = {"Authorization": f"Bearer {login('counselor')}"}
    case_response = client.get("/api/v1/clients/client-001", headers=headers)
    assert case_response.status_code == 200
    case = case_response.json()
    assert case["synthetic"] is True
    assert case["case_code"] == "FC-2026-001"
    assert len(case["assessments"]) == 4
    assert len(case["sessions"]) == 4

    response = client.post(
        "/api/v1/copilot/analyze-case",
        headers=headers,
        json={"client_id": "client-001", "session_number": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source_type"] == "synthetic_case"
    assert body["client_id"] == "client-001"
    assert body["session_number"] == 3
    assert set(body["soap_draft"]) == {"S", "O", "A", "P"}

    source_case = get_client_case("client-001")
    assert source_case is not None
    first_context = build_case_analysis_context(source_case, get_session(source_case, 1))
    assert "완료된 이전 회기 기록: 0건" in first_context
    assert "완료된 이전 회기 없음" in first_context
    assert source_case.sessions[0].client_report not in first_context

    second_context = build_case_analysis_context(source_case, get_session(source_case, 2))
    assert "완료된 이전 회기 기록: 1건" in second_context
    assert source_case.sessions[0].client_report in second_context
    assert source_case.sessions[1].client_report not in second_context


def test_json_extraction_repairs_common_model_formats() -> None:
    fenced = "설명입니다.\n```json\n{\"response\": \"불안해요\", \"emotion\": \"anxious\",}\n```"
    assert extract_json_object(fenced)["response"] == "불안해요"
    python_mapping = "결과: {'response': '서운해요', 'emotion': 'hurt'}"
    assert extract_json_object(python_mapping)["emotion"] == "hurt"


def test_unstructured_midm_output_still_returns_training_turn(monkeypatch) -> None:
    async def fake_chat_completion(*args, **kwargs):
        return "내담자: 또 제 말을 듣지 않을까 봐 불안하고 긴장돼요."

    monkeypatch.setattr(ai, "settings", SimpleNamespace(ai_provider="internal_openai"))
    monkeypatch.setattr(ai, "chat_completion", fake_chat_completion)
    result = asyncio.run(ai.generate_turn(
        "그 순간 어떤 마음이 들었나요?",
        {"scenario_id": "couple-conflict-01", "difficulty": "intermediate", "goal": "감정반영"},
        [],
    ))
    assert "불안" in result.response
    assert result.emotion == "anxious"
    assert result.nonverbal_cues


def test_ocr_cleanup_records_and_report_flow() -> None:
    clean_text, form_type = clean_form_boilerplate("SOAP\nSubjective\n남편과 대화가 두려움\nObjective")
    assert form_type == "SOAP 일지"
    assert "남편과 대화가 두려움" in clean_text
    assert "Subjective" not in clean_text

    headers = {"Authorization": f"Bearer {login('counselor')}"}
    ocr_status = client.get("/api/v1/documents/ocr/status", headers=headers)
    assert ocr_status.status_code == 200
    speech_status = client.get("/api/v1/speech/status", headers=headers)
    assert speech_status.status_code == 200
    assert speech_status.json()["provider"] == "browser"

    record_response = client.post(
        "/api/v1/documents/records/generate",
        headers=headers,
        json={
            "transcript": "내담자: 남편과 대화하면 또 싸울까 봐 불안해요.",
            "session_goal": "감정 표현과 관계 회복",
            "counselor_note": "시선 회피가 관찰됨",
            "ocr_text": "수기 기록: 최근 대화 감소",
        },
    )
    assert record_response.status_code == 200
    record = record_response.json()
    assert set(record["soap"]) == {"S", "O", "A", "P"}
    assert record["initial_intake"]

    report_response = client.post(
        "/api/v1/documents/reports/generate",
        headers=headers,
        json={
            "records": record,
            "case_summary": "반복 갈등과 대화 회피",
            "session_change": "감정을 한 문장으로 표현함",
            "goal_status": "부분 달성",
            "next_date": "2026-08-10",
        },
    )
    assert report_response.status_code == 200
    assert "회기 요약" in report_response.json()["session_report"]
