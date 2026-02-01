import json
import logging
from typing import List, Dict, Optional, Any
from openai import AsyncOpenAI
from backend.core.config import settings
from backend.core.cache import CacheManager  # Task 109: Redis Cache

# Initialize Logger
logger = logging.getLogger(__name__)

class ChefService:
    def __init__(self):
        """
        Initialize ChefService with explicit Kimi Support.
        """
        print(f"DEBUG: Initializing ChefService...")
        print(f"DEBUG: Base URL: {settings.OPENAI_BASE_URL}")
        
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL or "https://api.moonshot.cn/v1"
        self.model = settings.OPENAI_MODEL or "moonshot-v1-8k"
        
        if not self.api_key:
            print("❌ Error: OPENAI_API_KEY is missing in settings.")
            self.client = None
        else:
            print(f"✅ Chef Service initialized with Key: {self.api_key[:4]}***")
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

    async def generate_recipe_card(
        self, 
        ingredients: List[Dict[str, Any]], 
        cuisine: str = "Asian",
        user_id: Optional[str] = None,  # Task 109: 用于缓存 Key
        force_refresh: bool = False  # Task 111: 强制刷新
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a recipe card from a list of ingredients.
        Task 109: 添加 Redis 缓存支持
        Task 111: 支持 force_refresh 强制刷新
        """
        # Task 109: 生成缓存 Key
        ingredient_names = sorted([item.get("name", "") for item in ingredients])
        cache_key = CacheManager.generate_key(
            "diet_plan",
            user_id or "anonymous",
            cuisine,
            *ingredient_names
        )
        
        # Task 111: 只有不强制刷新时才查缓存
        if not force_refresh:
            cached_result = await CacheManager.get(cache_key)
            if cached_result:
                print(f"⚡ Cache Hit: Diet Plan for user={user_id}")
                logger.info(f"⚡ Cache Hit: Diet Plan [{cache_key[:20]}...]")
                return cached_result
        else:
            print(f"🔄 Force Refresh: Bypassing cache for recipe generation")
        
        if not self.client:
            print("⚠️ Client not initialized (No Key), using fallback.")
            return self._get_fallback_recipe(ingredients)

        # 1. Format Ingredients
        ing_str_list = []
        for item in ingredients:
            name = item.get("name", "Unknown")
            desc = item.get("amount_desc", "quantity unknown")
            ing_str_list.append(f"- {name}: {desc}")
        
        ingredients_text = "\n".join(ing_str_list)

        # 2. System Prompt
        system_prompt = (
            "你是一位精通营养学的米其林大厨。"
            "数据处理指令（关键）："
            "我将提供一个候选食材数据库列表（Retrieval Context）。"
            "请注意：这些只是备选食材，不是必须全部使用的食材！"
            "你必须从中挑选最合适、最精简的 1-3 种食材来完成菜品。"
            "严禁在一个菜谱中重复使用同类食材（例如：不要同时使用 3 种不同的豆浆，只选最健康的一种）。"
            "份量控制："
            "生成的份量必须符合单人一餐的合理摄入量（通常总热量在 400-800kcal 之间）。"
            "如果总热量超过 1000kcal，请自动减少食材用量。"
            "Output MUST be valid JSON."
        )

        # 3. User Prompt
        user_prompt = (
            f"这里有一份由营养算法生成的候选食材清单（Retrieval Context）：\n{ingredients_text}\n\n"
            "请按照以下步骤思考并输出 JSON：\n"
            "Step 1 [筛选与清洗]: \n"
            "- 识别清单中的重复/同类项（如多个 'Soy milk' 或 'Beef'）。\n"
            "- 从中挑选 1 个最佳选项，忽略其他同类项。\n"
            "- 忽略水、盐等基础辅料。\n\n"
            "Step 2 [创意组合]:\n"
            "- 基于你筛选出的 1-3 种核心食材，设计一道美味的米其林级简餐。\n"
            "- 起一个吸引人的中文菜名。\n\n"
            "Step 3 [翻译与输出]:\n"
            "- 将你**最终选中**的食材翻译为中文，并估算合理的食用份量。\n"
            "- 必须为清单中的**每一个**被选中的食材生成映射项。\n\n"
            "请仅返回以下 JSON 格式：\n"
            "{\n"
            '  "dish_name": "菜名",\n'
            '  "tags": ["低卡", "高蛋白"],\n'
            '  "description": "一句话描述",\n'
            '  "steps": ["Step 1", "Step 2"],\n'
            '  "chef_tips": "贴士",\n'
            '  "ingredient_translation": [\n'
            '     { "original_name": "Chicken breast", "zh_name": "鸡胸肉", "zh_portion": "1块 (约150g)" }\n'
            '  ]\n'
            "}"
        )

        try:
            print("🚀 Sending request to Kimi API...")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                # Task 66: Removed temperature, response_format for Kimi k2.5 compatibility
            )
            
            content = response.choices[0].message.content
            print("✅ Kimi API Response received!")
            
            if not content:
                print("❌ API returned empty content.")
                return self._get_fallback_recipe(ingredients)
            
            # Clean up Markdown
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
                
            recipe_data = json.loads(content)
            
            # Task 109: 写入缓存 (TTL=24小时)
            await CacheManager.set(cache_key, recipe_data, ttl=3600*24)
            logger.info(f"📝 Cached Diet Plan [{cache_key[:20]}...] for 24h")
            
            return recipe_data

        except Exception as e:
            print(f"❌ Kimi API Error: {str(e)}")
            return self._get_fallback_recipe(ingredients)

    def _get_fallback_recipe(self, ingredients: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Provides a default recipe structure when AI fails."""
        translations = []
        for item in ingredients:
            name = item.get("name", "Unknown")
            desc = item.get("amount_desc", "")
            translations.append(self._basic_translate(name, desc))

        return {
            "dish_name": "营养均衡健康餐 (离线模式)",
            "tags": ["健康", "均衡"],
            "description": "由于AI服务连接失败，我们为您提供了基础食材清单。建议简单烹饪。",
            "steps": [
                "准备所有食材，清洗干净。",
                "将肉类做熟（煎、烤或煮）。",
                "将蔬菜焯水或炒熟。",
                "混合搭配，享受健康美味。"
            ],
            "chef_tips": "保持健康饮食，即便没有AI也能做出美味！",
            "ingredient_translation": translations
        }

    def _basic_translate(self, name: str, portion: str) -> Dict[str, str]:
        """Simple string replacement for fallback translation."""
        vocab = {
            "Chicken": "鸡肉", "Beef": "牛肉", "Pork": "猪肉", "Egg": "鸡蛋",
            "Milk": "牛奶", "Rice": "米饭", "Bread": "面包", "Apple": "苹果",
            "Banana": "香蕉", "Broccoli": "西兰花", "Carrot": "胡萝卜",
            "Spinach": "菠菜", "Tomato": "番茄", "Potato": "土豆",
            "Water": "水", "Oil": "油", "Salt": "盐",
            "cup": "杯", "tbsp": "勺", "tsp": "小勺", "slice": "片",
            "undetermined": "适量"
        }
        
        zh_name = name
        zh_portion = portion

        for en, zh in vocab.items():
            if en.lower() in name.lower():
                zh_name = zh_name.replace(en, zh).replace(en.lower(), zh)
            
            if en in portion or en.lower() in portion:
                zh_portion = zh_portion.replace(en, zh).replace(en.lower(), zh)

        return {
            "original_name": name,
            "zh_name": zh_name,
            "zh_portion": zh_portion
        }
