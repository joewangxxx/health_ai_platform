from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Union

class FoodItem(BaseModel):
    id: int
    name: str
    category: str
    servings: float
    amount_desc: str
    grams: float
    calories: float
    nutrients: Dict[str, float]

class IngredientTranslation(BaseModel):
    original_name: str
    zh_name: str
    zh_portion: str

class RecipeCard(BaseModel):
    dish_name: str
    tags: List[str] = []
    description: str
    steps: List[str]
    chef_tips: str
    ingredient_translation: List[IngredientTranslation] = []

class DietResponse(BaseModel):
    status: str
    target_calories: int
    actual_calories: float
    macros: Dict[str, float]
    macro_ratios: Dict[str, float]
    warnings: List[str]
    foods: List[FoodItem]
    recipe_suggestion: Optional[RecipeCard] = None

class DietRequest(BaseModel):
    target_calories: Optional[int] = Field(None, description="手动指定目标热量，若不填则自动计算")
    health_conditions: List[str] = Field(default=[], description="疾病标签，如 ['hypertension', 'diabetes']")
    cuisine_preference: Optional[str] = Field(None, description="预留字段：偏好菜系")
    force_refresh: bool = Field(False, description="Task 111: 强制刷新，忽略缓存重新生成")
