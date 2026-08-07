"""
api/routers/plan.py
----------------------
A thin HTTP wrapper over the existing ImprovementPlanService (pure,
rule-based 7-day plan generation - no model inference) and
PlanProgressService (per-user, per-ISO-week task checkmarks). Neither
service is reimplemented here, only sequenced and translated to
Pydantic, exactly like every other router in this package.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth.security import get_current_account
from api.dependencies.services import get_improvement_plan_service, get_history_storage_backend, get_plan_progress_service
from api.schemas.plan import PlanDayResponse, PlanGenerateRequest, PlanResponse, PlanTaskResponse, PlanTaskUpdateRequest
from services.account_service import Account
from services.improvement_plan_service import ImprovementPlanService
from services.plan_progress_service import PlanProgressService, current_week_key
from services.storage.base import StorageBackend

router = APIRouter(prefix="/plan", tags=["Weekly Plan"])


@router.post(
    "", response_model=PlanResponse,
    summary="Generate this week's rule-based 7-day improvement plan from a real prediction's outputs, with saved checkmarks merged in",
)
def generate_plan(
    payload: PlanGenerateRequest,
    account: Account = Depends(get_current_account),
    plan_service: ImprovementPlanService = Depends(get_improvement_plan_service),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> PlanResponse:
    plan = plan_service.generate(
        health_class=payload.health_class,
        wellness_score=payload.wellness_score,
        persona=payload.persona,
        user_data=payload.user_data,
    )
    progress_service = get_plan_progress_service(account, storage=storage)
    week_key = current_week_key()
    completed = progress_service.get_completed(week_key)

    return PlanResponse(
        week_key=week_key,
        intro=plan.intro,
        focus_areas=plan.focus_areas,
        days=[
            PlanDayResponse(
                day_number=day.day_number, day_label=day.day_label, theme=day.theme,
                icon=day.icon, tip=day.tip,
                tasks=[
                    PlanTaskResponse(task_index=i, text=task, completed=(day.day_number, i) in completed)
                    for i, task in enumerate(day.tasks)
                ],
            )
            for day in plan.days
        ],
    )


@router.put(
    "/tasks", response_model=dict,
    summary="Mark one plan task done/not-done for the authenticated user's current week",
)
def update_task(
    payload: PlanTaskUpdateRequest,
    account: Account = Depends(get_current_account),
    storage: StorageBackend | None = Depends(get_history_storage_backend),
) -> dict:
    progress_service: PlanProgressService = get_plan_progress_service(account, storage=storage)
    progress_service.set_completed(payload.day_number, payload.task_index, payload.completed)
    return {"ok": True}
