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
import os
import random
from pathlib import Path
from typing import List, Dict, Union, Optional
from openai import AsyncOpenAI
from backend.core.config import settings

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
            print(f"⚠️ Warning: Nutrition DB not found at {self.db_path}")
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
        
        print(f"✅ Loaded {len(self.food_items)} food items.")

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
            return self._fallback_plan()

        system_prompt = (
            "你是一名营养师。请从提供的候选食材列表中，仅挑选 2-3 种最合适的来制作一道菜（例如：只选一种最好的豆浆 + 芋头）。"
            "必须清洗数据：将英文翻译为中文，将份量转换为标准的 '克(g)' 或 '毫升(ml)'，去除 'undetermined' 等无意义字符。"
            "重新计算热量：根据你设定的份量（例如 250ml 豆浆），重新估算热量，不要直接照搬数据库的每100g热量。"
            "Output Format：强制要求 LLM 返回 纯 JSON 格式（不要 Markdown），结构如下："
            "{"
            '  "total_calories": 350,'
            '  "protein_ratio": 20,'
            '  "fat_ratio": 30,'
            '  "carbs_ratio": 50,'
            '  "ingredients": ['
            '    {"name": "无糖豆浆", "portion": "250ml", "calories": 130},'
            '    {"name": "鲜芋头", "portion": "100g", "calories": 110}'
            '  ],'
            '  "dish_name": "菜名",'  # Added to match expectations
            '  "steps": ["步骤1...", "步骤2..."]'
            "}"
        )
        
        user_prompt = (
            f"目标热量: {target_calories} (仅参考，作为单餐)\n"
            f"健康限制: {', '.join(restrictions)}\n"
            f"候选食材列表:\n{cand_str}"
        )

        try:
            print("🚀 Calling LLM for Meal Selection...")
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
                    "protein_g": 0, # Simplify
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
                    "dish_name": data.get("dish_name", "健康简餐"),
                    "steps": data.get("steps", []),
                    "description": "由 AI 精选食材生成的美味方案。",
                    "tags": ["AI甄选", "健康"],
                    "chef_tips": "请根据个人口味适当调整调料。",
                    "ingredient_translation": [] # Frontend uses this for Translation, but name is already CN
                },
                "warnings": restrictions # Ensure warnings field exists
            }

        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return self._fallback_plan()

    def _fallback_plan(self):
        return {
            "status": "success",
            "actual_calories": 0,
            "foods": [],
            "recipe_suggestion": None,
            "message": "服务繁忙，请稍后重试"
        }

if __name__ == "__main__":
    import asyncio
    async def test():
        opt = DietOptimizer()
        res = await opt.generate_daily_plan(2000)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    asyncio.run(test())
