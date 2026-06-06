from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.models import User
from backend.services.demo_behavior_scenarios import (
    BehaviorScenarioRepository,
    DemoScenarioArtifactError,
)


router = APIRouter()
_scenario_repository = BehaviorScenarioRepository()


@router.get("/behavior-scenarios")
async def list_behavior_scenarios(current_user: User = Depends(get_current_user)):
    try:
        return {
            "status": "success",
            "scenarios": _scenario_repository.list_scenarios(),
        }
    except DemoScenarioArtifactError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/behavior-scenarios/{scenario_id}")
async def get_behavior_scenario(
    scenario_id: str,
    current_user: User = Depends(get_current_user),
):
    try:
        scenario = _scenario_repository.get_scenario(scenario_id)
    except DemoScenarioArtifactError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Behavior scenario not found: {scenario_id}")
    return {
        "status": "success",
        "scenario": scenario,
    }
