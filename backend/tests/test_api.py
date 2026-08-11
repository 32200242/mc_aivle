import asyncio
import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.routers import training
from backend.app.services import ai, avatar, copilot, linked_data, llm, ocr, records, session_workflow, stt, training_progress, tts
from backend.app.services.ai import extract_json_object, score_counselor_utterance
from backend.app.services.ocr import _page_review, clean_form_boilerplate
from backend.app.questionnaire import calculate_assessments, questionnaire_items
from backend.app.schemas import CopilotRequest, RecordGenerateRequest
from backend.app.synthetic_cases import build_case_analysis_context, get_client_case, get_session


client = TestClient(app)


@pytest.fixture(autouse=True)
def force_mock_provider(monkeypatch, tmp_path):
    mock_settings = SimpleNamespace(ai_provider="mock")
    monkeypatch.setattr(ai, "settings", mock_settings)
    monkeypatch.setattr(copilot, "settings", mock_settings)
    monkeypatch.setattr(llm, "settings", mock_settings)
    monkeypatch.setattr(ocr, "settings", SimpleNamespace(
        ocr_provider="paddleocr_vl_http",
        internal_ocr_url="",
        internal_ocr_api_key="",
        internal_llm_base_url="",
        internal_llm_api_key="",
        ocr_health_timeout=1,
        ocr_request_timeout=1,
        ocr_remote_batch_size=4,
        paddle_ocr_model_id="PaddlePaddle/PaddleOCR-VL-1.6",
    ))
    monkeypatch.setattr(records, "settings", mock_settings)
    monkeypatch.setattr(stt, "settings", SimpleNamespace(stt_provider="browser", internal_stt_url=""))
    monkeypatch.setattr(tts, "settings", SimpleNamespace(internal_tts_url=""))
    monkeypatch.setattr(avatar, "settings", SimpleNamespace(
        avatar_provider="static_2d",
        longcat_avatar_base_url="",
        longcat_avatar_api_key="",
        longcat_avatar_request_timeout=1800,
    ))
    monkeypatch.setattr(session_workflow, "STATE_PATH", tmp_path / "session_workflow.json")
    monkeypatch.setattr(linked_data, "STATE_PATH", tmp_path / "linked_session_events.json")
    monkeypatch.setattr(training_progress, "STATE_PATH", tmp_path / "training_progress.json")


def sample_records(session_number: int, client_id: str = "client-004") -> dict:
    case = get_client_case(client_id)
    assert case is not None
    session = get_session(case, session_number)
    official = records.official_record_fields(case, session, "윤주연 상담사") if session is not None else {}
    return {
        "provider": "mock",
        "model": "test",
        "initial_intake": {
            **official,
            "내담자 호소문제(주제)": "관계 갈등과 의사소통 어려움을 보고함",
            "상담목표(내담자와 합의된 목표)": "갈등 상황에서 감정을 안전하게 표현함",
            "상담계획": "갈등 장면을 확인하고 감정 표현을 단계적으로 연습함",
            "상담내용": "갈등 장면과 상호작용 양상을 확인함",
            "가계도": "내담자와 배우자, 자녀 1명으로 구성됨",
        },
        "session_record": {
            **official,
            "상담주제 1순위": "관계 갈등과 의사소통",
            "당회기 상담목표": "갈등 장면의 반응을 구체적으로 확인함",
            "상담내용(상담개입)": f"{session_number}회기에서 갈등 장면과 반응을 확인함",
            "다음 회기 계획": "감정 표현 연습 결과를 점검함",
        },
        "soap": {"S": "", "O": "", "A": "", "P": ""},
        "uncertain_items": [],
        "source_summary": {},
    }


def login(username: str = "counselor") -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": "demo"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_health() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_removed_trainer_account_cannot_login() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "trainer", "password": "demo"},
    )
    assert response.status_code == 401


def test_llm_output_tokens_are_clamped_to_server_limit(monkeypatch) -> None:
    monkeypatch.setattr(llm, "settings", SimpleNamespace(llm_max_output_tokens=1600))
    assert llm._clamp_max_tokens(1800) == 1600
    assert llm._clamp_max_tokens(950) == 950


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
    assert '"nonverbal_cues": []' in response.text

    avatar_status = client.get("/api/v1/avatar/status", headers=headers)
    assert avatar_status.status_code == 200
    assert avatar_status.json()["provider"] == "static_2d"


def test_training_reference_score_rewards_complete_reflection_not_keyword_fragments() -> None:
    fragment = score_counselor_utterance("마음 이해 느껴지. 어떤 구체적으로?")
    reflective = score_counselor_utterance("많이 답답하고 힘드셨겠어요. 그 순간 어떤 마음이 가장 크게 느껴졌나요?")
    judgmental = score_counselor_utterance("왜 그랬나요? 그냥 참으세요.")

    assert reflective["total"] > fragment["total"]
    assert reflective["empathy"] > fragment["empathy"]
    assert judgmental["nonjudgment"] < reflective["nonjudgment"]


def test_training_completion_is_linked_to_admin_dashboard() -> None:
    counselor_headers = {"Authorization": f"Bearer {login()}"}
    admin_headers = {"Authorization": f"Bearer {login('admin')}"}
    before = client.get("/api/v1/admin/dashboard?days=90", headers=admin_headers).json()
    session = client.post("/api/v1/training/sessions", headers=counselor_headers, json={}).json()
    for message in (
        "왜 그냥 말씀하지 않으셨나요?",
        "그때 어떤 일이 있었는지 말씀해 주실래요?",
        "많이 답답하고 힘드셨겠어요. 그 순간 어떤 마음이 가장 크게 느껴졌나요?",
    ):
        turn = client.post(
            f"/api/v1/training/sessions/{session['id']}/turns/stream",
            headers=counselor_headers,
            json={"counselor_message": message},
        )
        assert turn.status_code == 200

    completed = client.post(
        f"/api/v1/training/sessions/{session['id']}/complete",
        headers=counselor_headers,
        json={"elapsed_seconds": 420, "turn_count": 4},
    )
    assert completed.status_code == 200
    completion = completed.json()
    assert completion["session"]["status"] == "completed"
    assert completion["completed"] is True
    assert completion["turn_count"] == 3
    assert completion["score_change"] > 0

    dashboard = client.get("/api/v1/admin/dashboard?days=90", headers=admin_headers).json()
    assert dashboard["training_completion_rate"] == before["training_completion_rate"]
    assert dashboard["practice"]["completed_sessions"] == 1
    assert dashboard["practice"]["average_score_change"] == completion["score_change"]
    assert "첫·마지막 발화" in dashboard["methodology"]["practice"]

    repeated = client.post(
        f"/api/v1/training/sessions/{session['id']}/complete",
        headers=counselor_headers,
        json={"elapsed_seconds": 430, "turn_count": 5},
    )
    assert repeated.status_code == 200
    assert training_progress.progress_summary()["completed"] == 1


def test_admin_cannot_use_counselor_feature_apis() -> None:
    headers = {"Authorization": f"Bearer {login('admin')}"}
    responses = [
        client.post("/api/v1/training/sessions", headers=headers, json={}),
        client.get("/api/v1/clients/page?page=1&page_size=10", headers=headers),
        client.get("/api/v1/ai/status", headers=headers),
        client.get("/api/v1/documents/ocr/status", headers=headers),
        client.get("/api/v1/speech/status", headers=headers),
        client.get("/api/v1/avatar/status", headers=headers),
    ]
    assert all(response.status_code == 403 for response in responses)


def test_male_training_persona_is_selected() -> None:
    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    session = client.post(
        "/api/v1/training/sessions",
        headers=headers,
        json={"persona_id": "kim-minseok", "scenario_id": "couple-conflict-01"},
    )
    assert session.status_code == 200
    body = session.json()
    assert body["persona_id"] == "kim-minseok"
    assert body["persona_gender"] == "male"
    assert body["persona_name"] == "김민석 (가명)"
    encoded, mime_type = avatar._source_image("kim-minseok", "anxious")
    assert len(encoded) > 1000
    assert mime_type == "image/png"


def test_avatar_failure_does_not_expose_infrastructure_details(monkeypatch) -> None:
    monkeypatch.setattr(avatar, "settings", SimpleNamespace(
        avatar_provider="longcat_http",
        longcat_avatar_base_url="https://avatar.example",
        longcat_avatar_api_key="",
        longcat_avatar_request_timeout=1800,
    ))

    render_call = {}

    async def fail_render(*args, **kwargs):
        render_call["cache_key"] = args[-1]
        raise RuntimeError("CUDA out of memory at secret-gpu-host")

    monkeypatch.setattr(training, "render_avatar", fail_render)
    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    session = client.post(
        "/api/v1/training/sessions",
        headers=headers,
        json={"persona_id": "lee-jieun", "scenario_id": "couple-conflict-01"},
    ).json()

    response = client.post(
        f"/api/v1/training/sessions/{session['id']}/turns/stream",
        headers=headers,
        json={"counselor_message": ai.DEFAULT_DEMO_QUESTION},
    )

    assert response.status_code == 200
    assert training.AVATAR_FALLBACK_MESSAGE in response.text
    assert render_call["cache_key"].endswith(f"-{training.AVATAR_SYNC_CACHE_VERSION}")
    assert "CUDA" not in response.text
    assert "secret-gpu-host" not in response.text


def test_male_voice_and_emotion_are_bounded() -> None:
    result = asyncio.run(tts.prepare_tts(
        "turn-male",
        "요즘 마음이 조금 답답합니다.",
        "kim-minseok",
        "angry",
        0.99,
    ))
    assert result["gender"] == "male"
    assert result["voice"] == "김민석 음성"
    assert result["emotion"] == "angry"
    assert result["emotion_intensity"] == 0.78


def test_demo_first_question_is_fixed_and_prewarmable() -> None:
    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    session = client.post(
        "/api/v1/training/sessions",
        headers=headers,
        json={"persona_id": "lee-jieun", "scenario_id": "couple-conflict-01"},
    ).json()
    prewarm = client.post(
        f"/api/v1/training/sessions/{session['id']}/demo/prewarm",
        headers=headers,
    )
    assert prewarm.status_code == 200
    assert prewarm.json()["ready"] is True
    response = client.post(
        f"/api/v1/training/sessions/{session['id']}/turns/stream",
        headers=headers,
        json={"counselor_message": ai.DEFAULT_DEMO_QUESTION},
    )
    assert response.status_code == 200
    assert "제 마음은 전혀 전달되지 않은 것 같아서" in response.text
    assert '"emotion": "hurt"' in response.text


def test_male_demo_first_question_uses_restrained_anger() -> None:
    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    session = client.post(
        "/api/v1/training/sessions",
        headers=headers,
        json={"persona_id": "kim-minseok", "scenario_id": "couple-conflict-01"},
    ).json()
    response = client.post(
        f"/api/v1/training/sessions/{session['id']}/turns/stream",
        headers=headers,
        json={"counselor_message": ai.DEFAULT_DEMO_QUESTION},
    )
    assert response.status_code == 200
    assert "계속 몰아붙인다는 느낌이 들면 화가 나요" in response.text
    assert '"emotion": "angry"' in response.text
    assert '"emotion_intensity": 0.67' in response.text


def test_admin_role_is_enforced() -> None:
    counselor_headers = {"Authorization": f"Bearer {login('counselor')}"}
    assert client.get("/api/v1/admin/dashboard", headers=counselor_headers).status_code == 403
    admin_headers = {"Authorization": f"Bearer {login('admin')}"}
    response = client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["center_count"] == 244
    assert body["counselor_count"] == 1724
    assert len(body["regions"]) == 17
    assert body["trend"]
    assert body["forecast"]
    assert body["service_targets"]["family_counseling_users"] == 304699
    assert body["service_targets"]["family_counseling_satisfaction"] == 93.0

    seoul = client.get(
        "/api/v1/admin/dashboard?region_id=SEO&days=30", headers=admin_headers
    )
    assert seoul.status_code == 200
    assert seoul.json()["scope"]["type"] == "region"
    assert all(center["region_id"] == "SEO" for center in seoul.json()["centers"])


def test_counselor_id_login_and_case_assignment_are_linked() -> None:
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "CNS-SEO-00001", "password": "demo"},
    )
    assert login_response.status_code == 200
    body = login_response.json()
    assert body["user"]["id"] == "CNS-SEO-00001"
    assert body["user"]["name"].endswith("상담사")
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    assigned = client.get("/api/v1/clients", headers=headers)
    assert assigned.status_code == 200
    assigned_ids = {item["id"] for item in assigned.json()}
    assert len(assigned_ids) == 14
    assert {
        "client-001", "client-002", "client-003", "client-004"
    }.issubset(assigned_ids)

    first_page = client.get("/api/v1/clients/page?page=1&page_size=10", headers=headers)
    assert first_page.status_code == 200
    assert first_page.json()["total"] == 14
    assert first_page.json()["pages"] == 2
    assert len(first_page.json()["items"]) == 10
    detailed = client.get(f"/api/v1/clients/{first_page.json()['items'][0]['id']}", headers=headers)
    assert detailed.status_code == 200
    assert len(detailed.json()["questionnaire_responses"]) == 74
    assert len(detailed.json()["assessments"]) == 8

    other_headers = {"Authorization": f"Bearer {login('CNS-SEO-00002')}"}
    assert len(client.get("/api/v1/clients", headers=other_headers).json()) == 14
    assert client.get("/api/v1/clients/client-001", headers=other_headers).status_code == 404


def test_hwang_session_completion_advances_to_the_next_session() -> None:
    headers = {"Authorization": f"Bearer {login('CNS-SEO-00001')}"}
    submitted = sample_records(2, "client-00013")
    submitted["session_record"]["상담일자"] = "2026-08-11"
    finalized = client.post(
        "/api/v1/documents/workflow/client-00013/sessions/2/finalize",
        headers=headers,
        json={
            "records": submitted,
            "include_soap": False,
            "soap_source_label": "",
            "service_date": "2026-08-11",
        },
    )
    assert finalized.status_code == 200, finalized.text
    assert finalized.json()["next_session_number"] == 3

    detailed = client.get("/api/v1/clients/client-00013", headers=headers).json()
    assert detailed["session_count"] == 2
    assert detailed["current_session_number"] == 3


def test_finalized_session_updates_client_progress_and_admin_participant_total() -> None:
    counselor_headers = {"Authorization": f"Bearer {login('CNS-SEO-00001')}"}
    admin_headers = {"Authorization": f"Bearer {login('admin')}"}
    before = client.get("/api/v1/admin/dashboard?days=365", headers=admin_headers).json()
    case = get_client_case("client-004")
    assert case is not None
    assert case.current_session_number == 1
    assert all(not session.client_report for session in case.sessions)
    participant_count = len(case.sessions[0].participants)
    submitted_records = sample_records(1)
    submitted_records["initial_intake"]["상담일자"] = "2026-08-07"

    finalized = client.post(
        "/api/v1/documents/workflow/client-004/sessions/1/finalize",
        headers=counselor_headers,
        json={
            "records": submitted_records,
            "include_soap": False,
            "soap_source_label": "",
            "service_date": "2026-08-07",
        },
    )
    assert finalized.status_code == 200
    assert finalized.json()["sessions"][0]["status"] == "completed"
    saved_generation = session_workflow._load()["clients"]["client-004"]["completed"]["1"]["generation"]
    assert saved_generation == {
        "provider": "mock", "model": "test", "mode": "model", "fallback_reason": None,
    }

    progress = client.get("/api/v1/clients", headers=counselor_headers).json()
    client_row = next(item for item in progress if item["id"] == "client-004")
    assert client_row["session_count"] == 1
    detailed = client.get("/api/v1/clients/client-004", headers=counselor_headers).json()
    assert detailed["current_session_number"] == 2
    assert detailed["sessions"][0]["client_report"] == ""
    assert detailed["sessions"][0]["official_record"]["record_label"] == "초기상담기록지"
    assert detailed["sessions"][0]["official_record"]["fields"]["내담자 호소문제(주제)"] == "관계 갈등과 의사소통 어려움을 보고함"
    assert detailed["sessions"][1]["client_report"] == ""

    after = client.get("/api/v1/admin/dashboard?days=365", headers=admin_headers).json()
    assert after["counseling_sessions"] == before["counseling_sessions"] + participant_count
    assert linked_data.list_session_events()[0]["date"] == "2026-08-07"
    repeated = client.post(
        "/api/v1/documents/workflow/client-004/sessions/1/finalize",
        headers=counselor_headers,
        json={"records": submitted_records, "include_soap": False, "soap_source_label": "", "service_date": "2026-08-07"},
    )
    assert repeated.status_code == 200
    assert len(linked_data.list_session_events()) == 1

    changed_records = json.loads(json.dumps(submitted_records))
    changed_records["initial_intake"]["상담내용"] = "확정 후 변경된 내용"
    changed = client.post(
        "/api/v1/documents/workflow/client-004/sessions/1/finalize",
        headers=counselor_headers,
        json={"records": changed_records, "include_soap": False, "soap_source_label": ""},
    )
    assert changed.status_code == 409


def test_finalization_rejects_missing_fields_and_unknown_session() -> None:
    headers = {"Authorization": f"Bearer {login('CNS-SEO-00001')}"}
    incomplete = sample_records(1)
    incomplete["initial_intake"]["상담내용"] = "확인 필요"
    missing = client.post(
        "/api/v1/documents/workflow/client-004/sessions/1/finalize",
        headers=headers,
        json={"records": incomplete, "include_soap": False, "soap_source_label": ""},
    )
    assert missing.status_code == 409
    assert "상담내용" in missing.json()["detail"]

    for required_field in ("상담계획", "가계도"):
        incomplete_initial = sample_records(1)
        incomplete_initial["initial_intake"][required_field] = ""
        rejected = client.post(
            "/api/v1/documents/workflow/client-004/sessions/1/finalize",
            headers=headers,
            json={"records": incomplete_initial, "include_soap": False, "soap_source_label": ""},
        )
        assert rejected.status_code == 409
        assert required_field in rejected.json()["detail"]

    incomplete_session = sample_records(4)
    incomplete_session["session_record"]["상담주제 1순위"] = ""
    rejected_session = client.post(
        "/api/v1/documents/workflow/client-001/sessions/4/finalize",
        headers=headers,
        json={"records": incomplete_session, "include_soap": False, "soap_source_label": ""},
    )
    assert rejected_session.status_code == 409
    assert "상담주제 1순위" in rejected_session.json()["detail"]

    unknown = client.post(
        "/api/v1/documents/workflow/client-004/sessions/99/finalize",
        headers=headers,
        json={"records": sample_records(99), "include_soap": False, "soap_source_label": ""},
    )
    assert unknown.status_code == 404


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda record: record.__setitem__("상담자", "다른 상담사"), "상담자 정보"),
        (lambda record: record.__setitem__("상담일자", "2026-01-01"), "실제 상담일"),
        (lambda record: record.__setitem__("상담방법", "화상상담"), "상담방법"),
        (lambda record: record.__setitem__("상담내용", "가" * 301), "300자 이내"),
        (lambda record: record.__setitem__("임의 항목", "허용되지 않음"), "없는 항목"),
    ],
)
def test_initial_record_contract_rejects_format_drift(mutate, message: str) -> None:
    case = get_client_case("client-004")
    assert case is not None
    session = get_session(case, 1)
    assert session is not None
    expected = records.official_record_fields(case, session, "윤주연 상담사")
    record = sample_records(1)["initial_intake"]
    mutate(record)

    with pytest.raises(ValueError, match=message):
        session_workflow._validate_official_record(
            record,
            session_number=1,
            service_date=session.date,
            expected=expected,
        )


def test_session_record_contract_rejects_wrong_session_and_time_order() -> None:
    case = get_client_case("client-001")
    assert case is not None
    session = get_session(case, 4)
    assert session is not None
    expected = records.official_record_fields(case, session, "윤주연 상담사")
    record = sample_records(4, "client-001")["session_record"]
    record["상담회기"] = "3"

    with pytest.raises(ValueError, match="현재 작성 중인 회기"):
        session_workflow._validate_official_record(
            record,
            session_number=4,
            service_date=session.date,
            expected=expected,
        )

    record["상담회기"] = "4"
    record["상담시작시각"] = "15:00"
    record["상담종료시각"] = "14:00"
    with pytest.raises(ValueError, match="종료시각"):
        session_workflow._validate_official_record(
            record,
            session_number=4,
            service_date=session.date,
            expected=expected,
        )


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
    assert body["generation_mode"] == "mock"
    assert body["core_issues"]
    assert body["soap_draft"] == {}


def test_copilot_can_analyze_loaded_synthetic_case_without_manual_transcript() -> None:
    headers = {"Authorization": f"Bearer {login('counselor')}"}
    case_response = client.get("/api/v1/clients/client-001", headers=headers)
    assert case_response.status_code == 200
    case = case_response.json()
    assert case["synthetic"] is True
    assert case["case_code"] == "FC-2026-001"
    assert len(case["assessments"]) == 8
    assert len(case["sessions"]) == 4

    workflow = client.get("/api/v1/documents/workflow/client-001", headers=headers).json()
    assert workflow["next_session_number"] == 4
    assert [item["status"] for item in workflow["sessions"]] == [
        "completed",
        "completed",
        "completed",
        "ready",
    ]

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
    assert body["soap_draft"] == {}
    assert body["analysis_mode"] == "cumulative"
    assert len(body["module_analyses"]) == 4
    assert all(module["evidence"] for module in body["module_analyses"])

    source_case = get_client_case("client-001")
    assert source_case is not None
    first_context = build_case_analysis_context(source_case, get_session(source_case, 1))
    assert "1회기 시작 전 사전문진 분석" in first_context
    assert "상담 대화, 상담사 관찰, 회기 기록, SOAP 및 사후 정보는 사용하지 않음" in first_context
    assert source_case.presenting_problem not in first_context
    assert source_case.sessions[0].client_report not in first_context

    first_response = client.post(
        "/api/v1/copilot/analyze-case",
        headers=headers,
        json={"client_id": "client-001", "session_number": 1},
    )
    assert first_response.status_code == 200
    first_body = first_response.json()
    assert first_body["analysis_mode"] == "pre_intake"
    assert first_body["source_scope"] == ["사전문진"]
    assert all(module["evidence_level"] == "사전문진 기반" for module in first_body["module_analyses"])
    safety_module = next(module for module in first_body["module_analyses"] if module["id"] == "safety_priority")
    assert not any("FSTRESS_38 원응답" in item for item in safety_module["evidence"])
    assert any("관계 해체 고려" in item for item in safety_module["evidence"])
    assert first_body["soap_draft"] == {}

    second_context = build_case_analysis_context(source_case, get_session(source_case, 2))
    assert "확정된 이전 회기 기록: 1건" in second_context
    assert source_case.sessions[0].client_report in second_context
    assert source_case.sessions[1].client_report not in second_context


@pytest.mark.parametrize(
    ("client_id", "expected_ready", "expected_statuses"),
    [
        ("client-001", 4, ["completed", "completed", "completed", "ready"]),
        ("client-002", 3, ["completed", "completed", "ready", "locked"]),
        ("client-003", 2, ["completed", "ready", "locked", "locked"]),
        ("client-004", 1, ["ready", "locked", "locked", "locked"]),
    ],
)
def test_existing_case_workflow_opens_its_current_session(
    client_id: str,
    expected_ready: int,
    expected_statuses: list[str],
) -> None:
    headers = {"Authorization": f"Bearer {login('counselor')}"}
    response = client.get(f"/api/v1/documents/workflow/{client_id}", headers=headers)
    assert response.status_code == 200
    workflow = response.json()
    assert workflow["next_session_number"] == expected_ready
    assert [item["status"] for item in workflow["sessions"]] == expected_statuses
    assert workflow["sessions"][expected_ready - 1]["required_record_label"] == (
        "초기상담기록지" if expected_ready == 1 else "상담기록지"
    )


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
    assert result.nonverbal_cues == []


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
            "record_type": "initial_intake",
            "include_soap": True,
            "transcript": "내담자: 남편과 대화하면 또 싸울까 봐 불안해요.",
            "session_goal": "감정 표현과 관계 회복",
            "counselor_note": "시선 회피가 관찰됨",
            "ocr_text": "수기 기록: 최근 대화 감소",
            "ocr_reviewed": True,
            "ocr_review_note": "원본 대조 완료",
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


def test_soap_cleanup_keeps_only_section_content() -> None:
    raw_text = """\
\"SOAP\" 일지
S: Summary (요약)
• 내담자의 관점에서 무엇을 이야기했고 행했는지
• 상담주제들
• 보고된 증상들
S: 지난주 배우자와 두 차례 대화했다고 보고함.
O: Observatoin (관찰)
• 말
• 정서
• 행동
• 관찰된 증상들
O: 대화 중 눈물을 보였고 후반부에는 짧게 답변함.
A: Assessment (평가)
• 내담자 평가
• 주호소문제
• 지난 회기 이후로의 변화
• 사용한 개입
A: 보호 요인이 확인되며 현재 위험은 낮은 것으로 판단됨.
P: Plan (계획)
• 상담목표를 달성하기 위한 계획
• 이후의 방향
• 과제
• 다음 회기 일정
P: 다음 상담에서 호흡 이완을 점검하기로 함.
"""
    clean_text, form_type = clean_form_boilerplate(raw_text)

    assert form_type == "SOAP 일지"
    assert clean_text.splitlines() == [
        "S: 지난주 배우자와 두 차례 대화했다고 보고함.",
        "O: 대화 중 눈물을 보였고 후반부에는 짧게 답변함.",
        "A: 보호 요인이 확인되며 현재 위험은 낮은 것으로 판단됨.",
        "P: 다음 상담에서 호흡 이완을 점검하기로 함.",
    ]
    assert "Summary" not in clean_text
    assert "상담주제들" not in clean_text


def test_ocr_text_requires_human_review_before_record_generation() -> None:
    headers = {"Authorization": f"Bearer {login('counselor')}"}
    response = client.post(
        "/api/v1/documents/records/generate",
        headers=headers,
        json={
            "record_type": "session_record",
            "transcript": "상담 대화 원문",
            "ocr_text": "위기 상황은 없었고 현재 안전하다고 표현함.",
            "ocr_reviewed": False,
        },
    )
    assert response.status_code == 409
    assert "원본과 대조" in response.json()["detail"]


def test_ocr_review_flags_risk_phrase_and_variant_omission() -> None:
    reasons, risk_terms, omission_suspected = _page_review(
        "현재 안전하다고 표현함.",
        "위기 상황은 없었고 현재 안전하다고 표현함.",
        "SOAP 일지",
    )
    assert "안전" in risk_terms
    assert omission_suspected is True
    assert any("원본·강화본" in reason for reason in reasons)
    assert any("S 필드" in reason for reason in reasons)


def test_ocr_http_endpoint_reuses_existing_colab_base_url(monkeypatch) -> None:
    monkeypatch.setattr(ocr, "settings", SimpleNamespace(
        internal_ocr_url="",
        internal_llm_base_url="https://demo.ngrok-free.dev/v1",
    ))
    assert ocr._ocr_endpoint() == "https://demo.ngrok-free.dev/v1/ocr"


def test_remote_ocr_reader_batches_four_images_per_request(monkeypatch) -> None:
    calls: list[int] = []

    class FakeImage:
        def convert(self, mode: str):
            assert mode == "RGB"
            return self

        def save(self, buffer, **kwargs):
            buffer.write(b"synthetic-image")

    class FakeResponse:
        def __init__(self, body: dict):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(self.body).encode("utf-8")

    def fake_urlopen(request, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        calls.append(len(payload["images"]))
        return FakeResponse({"texts": [f"문장 {index}" for index in range(len(payload["images"]))]})

    monkeypatch.setattr(ocr, "settings", SimpleNamespace(
        internal_ocr_url="https://demo.ngrok-free.dev/v1/ocr",
        internal_ocr_api_key="key",
        internal_llm_base_url="",
        internal_llm_api_key="",
        ocr_remote_batch_size=4,
        ocr_request_timeout=300,
    ))
    monkeypatch.setattr(ocr.urllib.request, "urlopen", fake_urlopen)
    texts = ocr._PaddleOCRVLHTTPReader().read_many([FakeImage() for _ in range(5)])
    assert calls == [4, 1]
    assert len(texts) == 5


def test_official_record_forms_use_linked_case_and_session_data() -> None:
    headers = {"Authorization": f"Bearer {login('counselor')}"}
    case = get_client_case("client-001")
    assert case is not None
    first_session = get_session(case, 1)
    fourth_session = get_session(case, 4)
    initial_response = client.post(
        "/api/v1/documents/records/generate",
        headers=headers,
        json={
            "record_type": "initial_intake",
            "client_id": "client-001",
            "session_number": 1,
            "transcript": "첫 회기에서 주호소와 반복 갈등 장면을 확인함.",
            "session_goal": "주호소와 반복 갈등 장면 파악",
        },
    )
    assert initial_response.status_code == 200
    initial = initial_response.json()["initial_intake"]
    assert initial["사례번호"] == case.case_code
    assert initial["상담자"]
    assert initial["상담일자"] == first_session.date
    assert initial["상담방법"] == "면접상담"
    assert initial["상담유형"] == "부부상담"
    assert initial["내담자1 성명"] == case.name
    assert initial["내담자1 관계"] == "본인"
    assert initial["내담자1 성별"] == "여"
    assert initial["가계도"]

    scheduled_case = get_client_case("client-004")
    assert scheduled_case is not None
    scheduled_session = get_session(scheduled_case, scheduled_case.current_session_number)
    scheduled = records.official_record_fields(scheduled_case, scheduled_session, "상담사")
    expected_start = datetime.fromisoformat(str(scheduled_case.next_session_at))
    assert scheduled["상담시작시각"] == expected_start.strftime("%H:%M")
    assert scheduled["상담종료시각"] == (expected_start + timedelta(minutes=50)).strftime("%H:%M")

    session_response = client.post(
        "/api/v1/documents/records/generate",
        headers=headers,
        json={
            "record_type": "session_record",
            "client_id": "client-001",
            "session_number": 4,
            "transcript": "역할 분담을 구체적으로 합의함.",
            "session_goal": "복구 대화와 역할 협상 강화",
        },
    )
    assert session_response.status_code == 200
    session = session_response.json()["session_record"]
    assert session["상담회기"] == "4"
    assert session["상담일자"] == fourth_session.date
    assert session["내담자"] == ", ".join(fourth_session.participants)
    assert session["상담방법"] == "면접상담"
    assert "현재 회기 데이터" in session_response.json()["source_summary"]


def test_record_prompt_contains_linked_case_context_for_llm() -> None:
    case = get_client_case("client-001")
    assert case is not None
    session = get_session(case, 4)
    messages = records._record_messages(
        RecordGenerateRequest(
            record_type="session_record",
            client_id=case.id,
            session_number=session.number,
            transcript="역할 분담 합의를 점검함.",
            session_goal=session.goal,
        ),
        case=case,
        session=session,
        counselor_name="김상담 상담사",
    )
    prompt_context = json.loads(messages[1]["content"])["사례관리·현재회기 데이터"]
    assert prompt_context["사례번호"] == case.case_code
    assert prompt_context["내담자"]["성명"] == case.name
    assert prompt_context["현재회기"]["회기"] == 4
    assert prompt_context["현재회기"]["개입"] == session.interventions


def test_record_normalization_keeps_linkage_fields_structured_and_allows_empty_uncertainty() -> None:
    case = get_client_case("client-001")
    assert case is not None
    session = get_session(case, 3)
    request = RecordGenerateRequest(
        record_type="session_record",
        client_id=case.id,
        session_number=session.number,
        session_goal=session.goal,
    )
    fallback = records._fallback_records(
        request,
        "midm_local",
        "test-model",
        "fallback",
        case=case,
        session=session,
        counselor_name="김상담 상담사",
    )
    model_record = {
        "접수 연계기관": "가족센터 홈페이지 자가 신청",
        "상담주제 1순위": "취약 감정과 관계 욕구 표현",
        "상담주제 2순위": "",
        "상담주제 3순위": "",
        "당회기 상담목표": session.goal,
        "상담내용(상담개입)": "감정 명료화와 I-메시지 리허설을 실시함.",
        "다음 회기 계획": session.next_plan,
        "연계기관": "가족센터",
    }

    assert records._missing_record_fields(
        {"session_record": model_record, "uncertain_items": []}, request,
    ) == []
    normalized = records._normalize_records(
        {"session_record": model_record, "uncertain_items": []}, fallback, request,
    )

    assert normalized.session_record["접수 연계기관"] == ""
    assert normalized.session_record["연계기관"] == ""
    assert normalized.uncertain_items == []


def test_record_linkage_uses_only_explicit_institutional_referral() -> None:
    self_referred = get_client_case("client-001")
    institution_referred = get_client_case("client-004")
    assert self_referred is not None
    assert institution_referred is not None

    assert records._intake_referral_institution(self_referred) == ""
    assert records._intake_referral_institution(institution_referred) == "지역 복지관"


def test_record_normalization_removes_no_uncertainty_placeholders() -> None:
    case = get_client_case("client-002")
    assert case is not None
    session = get_session(case, 2)
    request = RecordGenerateRequest(
        record_type="session_record",
        client_id=case.id,
        session_number=session.number,
        session_goal=session.goal,
    )
    fallback = records._fallback_records(
        request, "midm_local", "test-model", "fallback",
        case=case, session=session, counselor_name="김상담 상담사",
    )
    model_record = {
        "상담주제 1순위": "역할 기대 불일치",
        "상담주제 2순위": "",
        "상담주제 3순위": "",
        "당회기 상담목표": session.goal,
        "상담내용(상담개입)": "역할 카드를 분류하고 상대 관점을 재진술함.",
        "다음 회기 계획": session.next_plan,
    }

    normalized = records._normalize_records(
        {"session_record": model_record, "uncertain_items": ["확인 필요 사항 없음"]},
        fallback,
        request,
    )
    assert normalized.uncertain_items == []


def test_record_fallback_narratives_respect_official_length() -> None:
    case = get_client_case("client-001")
    assert case is not None
    session = get_session(case, 3)
    request = RecordGenerateRequest(
        record_type="session_record",
        client_id=case.id,
        session_number=session.number,
        transcript="긴 상담 내용 " * 200,
        counselor_note="긴 상담사 메모 " * 200,
        session_goal=session.goal,
    )
    fallback = records._fallback_records(
        request, "mock", "deterministic-demo", "mock",
        case=case, session=session, counselor_name="김상담 상담사",
    )

    assert all(
        len(fallback.session_record[field]) <= 300
        for field in records.SESSION_FIELDS
    )


def test_bfi10_emotional_stability_scoring_direction_and_dimensions() -> None:
    neutral = {item["item_id"]: 3 for item in questionnaire_items()}
    stable = {**neutral, "BFI10_04": 5, "BFI10_09": 1}
    unstable = {**neutral, "BFI10_04": 1, "BFI10_09": 5}

    stable_scores = {item["code"]: item for item in calculate_assessments(stable)}
    unstable_scores = {item["code"]: item for item in calculate_assessments(unstable)}

    assert "BFI10" not in stable_scores
    assert stable_scores["BFI10-ES"]["score"] == 5
    assert unstable_scores["BFI10-ES"]["score"] == 1
    assert stable_scores["BFI10-ES"]["severity"] == "참고용"


def test_official_family_questionnaire_scoring_is_exposed_without_invented_risk_levels() -> None:
    responses = {item["item_id"]: item["scale_max"] for item in questionnaire_items()}
    scores = {item["code"]: item for item in calculate_assessments(responses)}

    assert scores["FRPS"]["score"] == 90
    assert scores["FRPS"]["max_score"] == 90
    assert scores["FRPS"]["severity"] == "확인 기준 이상"
    assert "54점" in scores["FRPS"]["interpretation"]
    assert scores["FSTRESS"]["score"] == 225
    assert scores["FSTRESS"]["max_score"] == 225
    assert scores["FSTRESS"]["severity"] == "생활사건 45건 경험"
    assert scores["DIVORCE"]["severity"] == "현재 실제 선택지로 고려 중"


def test_family_stress_separates_event_frequency_from_burden() -> None:
    responses = {item["item_id"]: item["scale_min"] for item in questionnaire_items()}
    responses.update({"FSTRESS_07": 4, "FSTRESS_18": 2, "FSTRESS_38": 1})
    scores = {item["code"]: item for item in calculate_assessments(responses)}

    assert scores["FSTRESS"]["score"] == 7
    assert scores["FSTRESS"]["severity"] == "생활사건 3건 경험"
    assert "3/45건" in scores["FSTRESS"]["interpretation"]


def test_model_parse_failure_is_identified_in_api_metadata(monkeypatch) -> None:
    monkeypatch.setattr(copilot, "settings", SimpleNamespace(ai_provider="midm"))

    async def invalid_completion(*args, **kwargs):
        return "구조화되지 않은 응답"

    monkeypatch.setattr(copilot, "chat_completion", invalid_completion)
    result = asyncio.run(copilot.analyze_copilot(CopilotRequest(
        transcript="가족 갈등 상황에서 불안과 긴장이 반복되어 대화를 이어가기 어렵습니다.",
    )))

    assert result.generation_mode == "fallback"
    assert result.fallback_reason


def test_copilot_semantically_empty_json_uses_fallback(monkeypatch) -> None:
    monkeypatch.setattr(copilot, "settings", SimpleNamespace(ai_provider="midm"))

    async def empty_completion(*args, **kwargs):
        return '{"summary":"","core_issues":[],"soap_draft":{}}'

    monkeypatch.setattr(copilot, "chat_completion", empty_completion)
    result = asyncio.run(copilot.analyze_copilot(CopilotRequest(
        transcript="가족 갈등 상황에서 불안과 긴장이 반복되어 대화를 이어가기 어렵습니다.",
    )))

    assert result.generation_mode == "fallback"
    assert "필수 분석 구조" in (result.fallback_reason or "")


def test_record_parse_failure_is_identified_in_api_metadata(monkeypatch) -> None:
    monkeypatch.setattr(records, "settings", SimpleNamespace(ai_provider="midm"))

    async def invalid_completion(*args, **kwargs):
        return "구조화되지 않은 응답"

    monkeypatch.setattr(records, "chat_completion", invalid_completion)
    result = asyncio.run(records.generate_records(RecordGenerateRequest(
        transcript="이번 회기에서 갈등 장면과 서로의 반응을 구체적으로 확인했습니다.",
    )))

    assert result.generation_mode == "fallback"
    assert result.fallback_reason


def test_record_semantically_incomplete_json_uses_fallback(monkeypatch) -> None:
    monkeypatch.setattr(records, "settings", SimpleNamespace(ai_provider="midm"))

    async def incomplete_completion(*args, **kwargs):
        return '{"initial_intake":{},"session_record":{},"soap":{}}'

    monkeypatch.setattr(records, "chat_completion", incomplete_completion)
    result = asyncio.run(records.generate_records(RecordGenerateRequest(
        transcript="이번 회기에서 갈등 장면과 서로의 반응을 구체적으로 확인했습니다.",
    )))

    assert result.generation_mode == "fallback"
    assert "필수 기록 항목" in (result.fallback_reason or "")


def test_session_outbox_survives_event_store_failure(monkeypatch) -> None:
    headers = {"Authorization": f"Bearer {login('CNS-SEO-00001')}"}
    original = linked_data.record_session_completion

    def fail_delivery(**kwargs):
        raise OSError("event store unavailable")

    monkeypatch.setattr(linked_data, "record_session_completion", fail_delivery)
    submitted_records = sample_records(1)
    response = client.post(
        "/api/v1/documents/workflow/client-004/sessions/1/finalize",
        headers=headers,
        json={"records": submitted_records, "include_soap": False, "soap_source_label": ""},
    )
    assert response.status_code == 200
    assert response.json()["sessions"][0]["status"] == "completed"
    assert linked_data.list_session_events() == []

    monkeypatch.setattr(linked_data, "record_session_completion", original)
    assert session_workflow.dispatch_pending_completion_events() == 1
    assert len(linked_data.list_session_events()) == 1

    repeated = client.post(
        "/api/v1/documents/workflow/client-004/sessions/1/finalize",
        headers=headers,
        json={"records": submitted_records, "include_soap": False, "soap_source_label": ""},
    )
    assert repeated.status_code == 200
    assert len(linked_data.list_session_events()) == 1
