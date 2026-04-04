import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.chef_service import ChefService


MOCK_RECIPE_JSON = """
{
  "dish_name": "Bamboo Shoots Stir-fry with Beef",
  "tags": ["Low Carb", "High Protein"],
  "description": "A savory high-protein dish with crisp textures.",
  "steps": ["Slice beef", "Stir fry bamboo shoots", "Combine and serve"],
  "chef_tips": "Do not overcook the beef."
}
"""


def test_generate_recipe_success():
    """Service should parse valid model JSON and build a recipe card."""

    async def _run():
        with patch("backend.core.config.settings.OPENAI_API_KEY", "test-key"):
            service = ChefService()

            mock_create = AsyncMock()
            mock_create.return_value.choices = [
                MagicMock(message=MagicMock(content=MOCK_RECIPE_JSON))
            ]
            service.client.chat.completions.create = mock_create

            ingredients = [
                {"name": "Bamboo Shoots", "grams": 100},
                {"name": "Beef", "grams": 50},
            ]
            result = await service.generate_recipe_card(ingredients)

            assert result is not None
            assert "Bamboo Shoots" in result["dish_name"]
            assert len(result["steps"]) == 3

            call_kwargs = mock_create.call_args[1]
            user_content = call_kwargs["messages"][1]["content"]
            assert "Bamboo Shoots" in user_content
            assert "Beef" in user_content

    asyncio.run(_run())


def test_generate_recipe_no_api_key():
    """Missing key should trigger deterministic local fallback recipe."""

    async def _run():
        with patch("backend.core.config.settings.OPENAI_API_KEY", None):
            service = ChefService()
            assert service.client is None

            result = await service.generate_recipe_card([])
            assert result is not None
            assert "dish_name" in result
            assert isinstance(result.get("steps"), list)

    asyncio.run(_run())


def test_generate_recipe_api_failure():
    """Provider failure should degrade to local fallback recipe."""

    async def _run():
        with patch("backend.core.config.settings.OPENAI_API_KEY", "test-key"):
            service = ChefService()

            mock_create = AsyncMock(side_effect=Exception("API Down"))
            service.client.chat.completions.create = mock_create

            result = await service.generate_recipe_card([{"name": "Beef", "grams": 100}])
            assert result is not None
            assert "dish_name" in result
            assert len(result.get("steps", [])) > 0

    asyncio.run(_run())


def test_generate_recipe_markdown_strip():
    """Service should strip markdown fences before json.loads."""
    markdown_json = "```json\n" + MOCK_RECIPE_JSON.strip() + "\n```"

    async def _run():
        with patch("backend.core.config.settings.OPENAI_API_KEY", "test-key"):
            service = ChefService()
            mock_create = AsyncMock()
            mock_create.return_value.choices = [
                MagicMock(message=MagicMock(content=markdown_json))
            ]
            service.client.chat.completions.create = mock_create

            result = await service.generate_recipe_card([{"name": "Beef", "grams": 100}])
            assert result is not None
            assert result["dish_name"] == "Bamboo Shoots Stir-fry with Beef"

    asyncio.run(_run())
