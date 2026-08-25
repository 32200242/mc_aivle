from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone


SERVICE_TIME_ZONE = timezone(timedelta(hours=9), name="Asia/Seoul")


def service_today() -> date:
    """Return the calendar day the service should use for operational screens."""
    configured = os.getenv("SERVICE_DATE", "").strip()
    if configured:
        try:
            return date.fromisoformat(configured)
        except ValueError:
            pass
    return datetime.now(SERVICE_TIME_ZONE).date()


def project_iso_datetime(value: str | None, anchor: date) -> str | None:
    if not value:
        return value
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    return (parsed + timedelta(days=(service_today() - anchor).days)).isoformat()


def project_upcoming_iso_datetime(value: str | None, dataset_anchor: date) -> str | None:
    """Project fixed demo appointments from the service day onward."""
    return project_iso_datetime(value, dataset_anchor + timedelta(days=1))


def project_iso_date(value: str, anchor: date) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return value
    return (parsed + timedelta(days=(service_today() - anchor).days)).isoformat()
