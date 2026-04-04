from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from sqlmodel import select
from backend.database import get_session
from backend.models import User, UserProfile
from backend.auth import get_current_user
from backend.schemas.nutrition import DietRequest
from backend.services.nutrition_service import DietOptimizer

router = APIRouter()


class _LazyDietOptimizerProxy:
    def __init__(self):
        self._optimizer: Optional[DietOptimizer] = None

    def _get_optimizer(self) -> DietOptimizer:
        if self._optimizer is None:
            self._optimizer = DietOptimizer()
        return self._optimizer

    async def generate_daily_plan(self, *args, **kwargs):
        return await self._get_optimizer().generate_daily_plan(*args, **kwargs)


optimizer = _LazyDietOptimizerProxy()

# --- New Logic: Validated Response Models ---
# Defined locally to match the new LLM-driven service output

class NutritionFoodItem(BaseModel):
    name: str # Simplified Name (CN)
    amount_desc: str # e.g. "250ml"
    calories: float
    protein: Optional[float] = 0
    fat: Optional[float] = 0
    carbs: Optional[float] = 0
    
    # Optional Legacy Fields (to prevent validation error if service returns them or defaults)
    id: Optional[int] = None
    category: Optional[str] = None
    servings: Optional[float] = None
    grams: Optional[float] = None
    nutrients: Optional[dict] = {}

class NutritionPlanResponse(BaseModel):
    status: str
    target_calories: Optional[int] = None
    actual_calories: float
    macros: Dict[str, float]
    macro_ratios: Dict[str, float]
    foods: List[NutritionFoodItem]
    recipe_suggestion: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = []
    message: Optional[str] = None

def calculate_tdee(profile: UserProfile) -> int:
    """
    Calculate TDEE based on Mifflin-St Jeor Equation.
    Default Activity Factor: 1.2 (Sedentary) for MVP safety.
    """
    if not profile.Weight or not profile.Height or not profile.Age or not profile.Gender:
        return None
        
    weight = profile.Weight # kg
    height = profile.Height # cm
    age = profile.Age
    
    # Mifflin-St Jeor
    bmr = 10 * weight + 6.25 * height - 5 * age
    
    if profile.Gender == 1: # Male
        bmr += 5
    else: # Female
        bmr -= 161
        
    tdee = bmr * 1.2 # Sedentary
    return int(tdee)

@router.post("/generate", response_model=NutritionPlanResponse)
async def generate_diet_plan(
    request: DietRequest,
    current_user: User = Depends(get_current_user),
    session = Depends(get_session)
):
    """
    Generate a personalized daily diet plan.
    - If target_calories is provided, use it.
    - Otherwise, calculate TDEE from user profile.
    - Uses 'Search-then-Filter' LLM Strategy.
    """
    target_calories = request.target_calories
    
    if not target_calories:
        # Fetch Profile
        statement = select(UserProfile).where(UserProfile.user_id == current_user.id)
        results = session.exec(statement)
        profile = results.first()
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户档案不存在，请先完善个人信息 (User Profile) 或在请求中指定 target_calories。"
            )
            
        calculated = calculate_tdee(profile)
        if not calculated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户档案缺失关键信息 (身高/体重/年龄/性别)，无法计算推荐热量。请完善信息或手动指定 target_calories。"
            )
        target_calories = calculated

    # Call Optimizer (Async LLM)
    try:
        plan = await optimizer.generate_daily_plan(
            target_calories=target_calories,
            restrictions=request.health_conditions
        )
        
        if plan.get("status") == "failed":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"无法生成食谱: {plan.get('message')}"
            )
            
        return plan
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization Error: {str(e)}"
        )
