from fastapi import APIRouter

from ..auth import AdminUser
from ..schemas import DashboardSummary


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(user: AdminUser) -> DashboardSummary:
    return DashboardSummary(
        center_count=223,
        active_clients=158_792,
        counseling_sessions=236_101,
        ai_report_minutes=4.21,
        satisfaction=4.41,
        training_completion_rate=70.1,
    )
