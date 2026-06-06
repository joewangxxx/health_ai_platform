"""
AI Nutrition Planning Service
==============================
Backend service for generating personalized daily meal plans using Linear Programming (PuLP).

Algorithm:
- Objective: Minimize deviation from target calories.
- Constraints: Macro balance, Disease-specific restrictions, Variety limits.
"""

"""
AI Nutrition Planning Service
==============================
Backend service for generating personalized daily meal plans using LLM-based Selection.

Strategy: "Search-then-Filter"
1. Search: Retrieve candidate ingredients from local DB (Top N).
2. Filter: Use LLM to select best 2-3 items and generate recipe.
"""

import json
import logging
import os
import random
from pathlib import Path
from typing import List, Dict, Union, Optional
from openai import AsyncOpenAI
from backend.core.config import settings

logger = logging.getLogger(__name__)

class DietOptimizer:
    def __init__(self, db_path: str = None):
        """
        Initialize DietOptimizer with nutrition database.
        """
        if not db_path:
            current_dir = Path(__file__).parent
            db_path = current_dir.parent / "data" / "nutrition_db.json"
        
        self.db_path = db_path
        self.food_items = []
        self._load_data()
        
        # Init OpenAI
        self.client = None
        if settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL or "https://api.moonshot.cn/v1"
            )

    def _load_data(self):
        """Load food data from JSON."""
        if not os.path.exists(self.db_path):
            logger.warning("Nutrition database not found at %s", self.db_path)
            self.food_items = []
            return

        with open(self.db_path, "r", encoding="utf-8") as f:
            all_items = json.load(f)
            
        self.food_items = []
        for item in all_items:
            nutrients = item.get("nutrients", {})
            cals = nutrients.get("calories", 0)
            if cals <= 0:
                continue
            
            food = {
                "id": item["id"],
                "name": item["name"],
                "category": item["category"],
                "calories": cals,
                "protein": nutrients.get("protein", 0),
                "fat": nutrients.get("fat", 0),
                "carbs": nutrients.get("carbs", 0),
                "portion_desc": item["portion"]["desc"],
                "portion_grams": item["portion"]["grams"]
            }
            self.food_items.append(food)
        
        logger.info("Nutrition database loaded with %s items", len(self.food_items))

    def _get_candidates(self, restrictions: List[str] = [], limit: int = 20) -> List[Dict]:
        """Simple heuristic search to get diverse candidates."""
        # Weighted random selection favoring common categories
        categories = ["Vegetables", "Fruits", "Poultry", "Beef", "Pork", "Dairy", "Grains"]
        candidates = []
        
        # Shuffle for randomness
        pool = list(self.food_items)
        random.shuffle(pool)
        
        # Pick items
        count = 0
        for item in pool:
            if count >= limit:
                break
            
            # Basic Filtering
            if "Baby" in item["category"]: continue
            if "Sweets" in item["category"]: continue
            
            # Add to candidates
            candidates.append(item)
            count += 1
            
        return candidates

    async def generate_daily_plan(self, target_calories: int, restrictions: List[str] = []) -> Dict:
        """
        Generate a meal plan using LLM "Search-then-Filter".
        This replaces the old PuLP optimization.
        """
        # 1. Search Candidates
        candidates = self._get_candidates(restrictions, limit=15)
        
        # Format for LLM
        cand_str = "\n".join([f"- {f['name']} ({f['category']})" for f in candidates])

        # 2. LLM Generation
        if not self.client:
            return self._fallback_plan(target_calories=target_calories, restrictions=restrictions)

        system_prompt = """
You are a nutrition planner. Select only 2-3 of the best candidate ingredients to build a single meal.

Rules:
1. Clean the data:
   - Translate ingredient names to Chinese when appropriate.
   - Normalize units to standard forms such as "g" or "ml".
   - Remove meaningless placeholders such as "undetermined".
2. Recalculate calories:
   - Re-estimate calories based on the portion you choose.
   - Do not blindly copy the database calories per 100g.
3. Output format:
   - Return JSON only.
   - Do not wrap the result in Markdown.

Required JSON shape:
{
  "total_calories": 350,
  "protein_ratio": 20,
  "fat_ratio": 30,
  "carbs_ratio": 50,
  "ingredients": [
    {"name": "unsweetened soy milk", "portion": "250ml", "calories": 130},
    {"name": "fresh potato", "portion": "100g", "calories": 110}
  ],
  "dish_name": "Dish name",
  "steps": ["Step 1...", "Step 2..."]
}
""".strip()

        user_prompt = (
            f"Target calories: {target_calories} (for one meal)\n"
            f"Restrictions: {', '.join(restrictions)}\n"
            f"Candidate ingredients:\n{cand_str}"
        )

        try:
            logger.info("Nutrition planner requesting LLM meal selection")
            # Task 86: Removed temperature, response_format for Kimi k2.5 compatibility
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # Map to DietResponse structure
            # DietResponse expects: actual_calories, foods, macros, recipe_suggestion
            
            foods = []
            for ing in data.get("ingredients", []):
                foods.append({
                    "name": ing["name"],
                    "amount_desc": ing["portion"],
                    "calories": ing["calories"],
                    # Fill dummy macros if missing, or LLM didn't provide individual macros
                    "protein": 0, "fat": 0, "carbs": 0
                })
            
            return {
                "status": "success",
                "target_calories": target_calories,
                "actual_calories": data.get("total_calories", 0),
                "macros": {
                    "protein_g": 0,
                    "fat_g": 0,
                    "carbs_g": 0,
                    "sodium_mg": 0
                },
                "macro_ratios": {
                    "protein": data.get("protein_ratio", 0) / 100.0,
                    "fat": data.get("fat_ratio", 0) / 100.0,
                    "carbs": data.get("carbs_ratio", 0) / 100.0
                },
                "foods": foods,
                "recipe_suggestion": {
                    "dish_name": data.get("dish_name", "Healthy meal"),
                    "steps": data.get("steps", []),
                    "description": "A healthy recipe generated from AI-selected ingredients.",
                    "tags": ["AI generated", "healthy"],
                    "chef_tips": "Adjust seasonings according to personal taste.",
                    "ingredient_translation": [] # Frontend uses this for Translation, but name is already CN
                },
                "warnings": restrictions # Ensure warnings field exists
            }

        except Exception as e:
            logger.warning("Nutrition planner LLM request failed: %s", e)
            return self._fallback_plan(target_calories=target_calories, restrictions=restrictions)

    def _fallback_plan(self, target_calories: int = 1800, restrictions: List[str] | None = None):
        restrictions = restrictions or []
        return {
            "status": "success",
            "target_calories": target_calories,
            "actual_calories": 1685.0,
            "macros": {
                "protein_g": 92.0,
                "fat_g": 48.0,
                "carbs_g": 205.0,
                "sodium_mg": 1180.0,
            },
            "macro_ratios": {
                "protein": 0.22,
                "fat": 0.26,
                "carbs": 0.52,
            },
            "foods": [
                {
                    "name": "燕麦希腊酸奶碗",
                    "amount_desc": "1 碗",
                    "calories": 390.0,
                    "protein": 24.0,
                    "fat": 9.0,
                    "carbs": 54.0,
                },
                {
                    "name": "鸡胸肉藜麦沙拉",
                    "amount_desc": "1 份",
                    "calories": 620.0,
                    "protein": 42.0,
                    "fat": 18.0,
                    "carbs": 68.0,
                },
                {
                    "name": "清蒸鳕鱼配杂蔬",
                    "amount_desc": "1 份",
                    "calories": 510.0,
                    "protein": 26.0,
                    "fat": 17.0,
                    "carbs": 55.0,
                },
                {
                    "name": "无糖豆浆与坚果",
                    "amount_desc": "1 份",
                    "calories": 165.0,
                    "protein": 10.0,
                    "fat": 4.0,
                    "carbs": 28.0,
                },
            ],
            "recipe_suggestion": {
                "dish_name": "低钠高纤维控糖演示餐",
                "description": "本地演示 fallback 方案，适合在外部 AI 服务不可用时继续展示营养模块。",
                "tags": ["本地演示", "低钠", "控糖", "高纤维"],
                "steps": [
                    "以燕麦和无糖酸奶作为早餐，搭配少量浆果提升膳食纤维。",
                    "午餐使用鸡胸肉、藜麦和深色蔬菜，减少精制碳水比例。",
                    "晚餐选择清蒸鱼和杂蔬，避免高盐酱料。",
                ],
                "chef_tips": "答辩演示时可说明该方案是 LLM 不可用时的本地安全降级结果，仍保持结构化营养输出。",
                "ingredient_translation": [],
            },
            "warnings": restrictions,
            "message": "外部营养生成服务不可用，已切换到本地演示 fallback 食谱。",
        }
if __name__ == "__main__":
    import asyncio
    async def test():
        opt = DietOptimizer()
        res = await opt.generate_daily_plan(2000)
        logger.info("Nutrition service smoke test result: %s", json.dumps(res, indent=2, ensure_ascii=False))
    asyncio.run(test())
