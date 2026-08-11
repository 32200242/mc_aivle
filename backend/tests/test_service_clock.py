from __future__ import annotations

from datetime import date, datetime

from backend.app.schemas import UserView
from backend.app.services.client_repository import get_client_case, list_client_page
from backend.app.services.service_clock import (
    project_iso_date,
    project_iso_datetime,
    project_upcoming_iso_datetime,
    service_today,
)


def test_service_today_uses_seoul_service_date_override(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_DATE", "2026-08-11")
    assert service_today() == date(2026, 8, 11)


def test_fixture_schedule_moves_with_each_service_day(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_DATE", "2026-08-11")
    anchor = date(2026, 8, 10)
    assert project_iso_datetime("2026-08-11T09:30:00", anchor) == "2026-08-12T09:30:00"
    assert project_iso_date("2026-08-11", anchor) == "2026-08-12"


def test_upcoming_fixture_schedule_includes_service_day(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_DATE", "2026-08-11")
    anchor = date(2026, 8, 10)
    assert project_upcoming_iso_datetime("2026-08-11T09:30:00", anchor) == "2026-08-11T09:30:00"
    assert project_upcoming_iso_datetime("2026-08-12T13:00:00", anchor) == "2026-08-12T13:00:00"


def test_invalid_service_date_falls_back_without_crashing(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_DATE", "not-a-date")
    assert isinstance(service_today(), date)


def test_client_list_projects_next_appointments_from_service_day(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_DATE", "2026-08-11")
    user = UserView(
        id="CNS-SEO-00001",
        name="상담사",
        role="counselor",
        center_id="CENTER-001",
        center_name="가족센터",
    )
    result = list_client_page(user, page=1, page_size=50)
    regular_appointments = [
        datetime.fromisoformat(item.next_session_at)
        for item in result.items
        if item.next_session_at and item.id != "client-00013"
    ]
    prepared_appointment = next(item for item in result.items if item.id == "client-00013")
    assert regular_appointments
    assert min(item.date() for item in regular_appointments) == service_today()
    assert all(item.date() >= service_today() for item in regular_appointments)
    assert prepared_appointment.next_session_at == "2026-08-11T09:00:00"


def test_pending_first_session_is_shown_as_scheduled_not_in_progress(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_DATE", "2026-08-10")
    case = get_client_case("client-00007")
    assert case is not None
    assert case.session_count == 0
    assert case.next_session_at is not None
    expected_date = case.next_session_at[:10].replace("-", ".")
    assert case.counseling_period == f"{expected_date} 시작 예정"
