from fastapi import APIRouter, Depends

from app.core.dependencies import (
    CurrentUserDep,
    DashboardInsightServiceDep,
    DashboardServiceDep,
    get_current_user,
)
from app.schemas.dashboard_schema import (
    DashboardAnalyticsOut,
    DashboardInsightOut,
    DashboardStatsOut,
)
from app.schemas.response_schema import BaseResponse

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/stats",
    response_model=BaseResponse[DashboardStatsOut],
)
async def get_dashboard_stats(
    dashboard_service: DashboardServiceDep,
    current_user: CurrentUserDep,
):
    stats = dashboard_service.get_stats(current_user=current_user)
    return BaseResponse(data=stats)


@router.get(
    "/analytics",
    response_model=BaseResponse[DashboardAnalyticsOut],
)
async def get_dashboard_analytics(
    dashboard_service: DashboardServiceDep,
    current_user: CurrentUserDep,
):
    analytics = dashboard_service.get_analytics(current_user=current_user)
    return BaseResponse(data=analytics)


@router.get(
    "/insight",
    response_model=BaseResponse[DashboardInsightOut],
)
async def get_dashboard_insight(
    insight_service: DashboardInsightServiceDep,
    current_user: CurrentUserDep,
):
    insight = await insight_service.get_insight(current_user=current_user)
    return BaseResponse(data=insight)


@router.post(
    "/insight/refresh",
    response_model=BaseResponse[DashboardInsightOut],
)
async def refresh_dashboard_insight(
    insight_service: DashboardInsightServiceDep,
    current_user: CurrentUserDep,
):
    insight = await insight_service.get_insight(
        current_user=current_user,
        force_refresh=True,
    )
    return BaseResponse(data=insight)
