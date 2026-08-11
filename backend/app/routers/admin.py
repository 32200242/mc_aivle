from fastapi import APIRouter, HTTPException, Query

from ..auth import AdminUser
from ..schemas import DashboardSummary
from ..services.operational_data import build_dashboard


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(
    user: AdminUser,
    region_id: str | None = None,
    center_id: str | None = None,
    days: int = Query(default=90),
) -> DashboardSummary:
    if days not in {30, 90, 180, 365}:
        raise HTTPException(status_code=422, detail="조회 기간은 30, 90, 180, 365일 중 하나여야 합니다.")
    try:
        return DashboardSummary.model_validate(
            build_dashboard(region_id=region_id, center_id=center_id, days=days)
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc).strip("'")) from exc
