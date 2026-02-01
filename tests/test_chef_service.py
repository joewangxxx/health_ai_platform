import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from backend.services.chef_service import ChefService

# Mock response content
MOCK_RECIPE_JSON = """
{
  "dish_name": "Bamboo Shoots Stir-fry with Beef (竹笋炒牛肉)",
  "tags": ["Low Carb", "High Protein"],
  "description": "A savory high-protein dish with crisp textures.",
  "steps": ["Slice beef", "Stir fry bamboo shoots", "Combine and serve"],
  "chef_tips": "Don't overcook the beef."
}
"""

@pytest.mark.asyncio
async def test_generate_recipe_success():
    """Test successful recipe generation with mocked OpenAI"""
    
    # Mock settings to ensure API key exists
    with patch("backend.core.config.settings.OPENAI_API_KEY", "test-key"):
        service = ChefService()
        
        # Mock the client and create methods
        mock_create = AsyncMock()
        mock_create.return_value.choices = [
            MagicMock(message=MagicMock(content=MOCK_RECIPE_JSON))
        ]
        service.client.chat.completions.create = mock_create
        
        ingredients = [
            {"name": "Bamboo Shoots", "grams": 100},
            {"name": "Beef", "grams": 50}
        ]
        
        result = await service.generate_recipe_card(ingredients)
        
        assert result is not None
        assert result["dish_name"] == "Bamboo Shoots Stir-fry with Beef (竹笋炒牛肉)"
        assert len(result["steps"]) == 3
        
        # Verify prompt construction (optional check)
        call_kwargs = mock_create.call_args[1]
        user_content = call_kwargs["messages"][1]["content"]
        assert "Bamboo Shoots" in user_content
        assert "Beef" in user_content

@pytest.mark.asyncio
async def test_generate_recipe_no_api_key():
    """Test graceful fallback when API key is missing"""
    with patch("backend.core.config.settings.OPENAI_API_KEY", None):
        service = ChefService()
        assert service.client is None
        
        result = await service.generate_recipe_card([])
        assert result is None

@pytest.mark.asyncio
async def test_generate_recipe_api_failure():
    """Test handling of API errors"""
    with patch("backend.core.config.settings.OPENAI_API_KEY", "test-key"):
        service = ChefService()
        
        # Mock create to raise Exception
        mock_create = AsyncMock(side_effect=Exception("API Down"))
        service.client.chat.completions.create = mock_create
        
        ingredients = [{"name": "Beef", "grams": 100}]
        result = await service.generate_recipe_card(ingredients)
        
        assert result is None

@pytest.mark.asyncio
async def test_generate_recipe_markdown_strip():
    """Test stripping of markdown code blocks"""
    markdown_json = "```json\n" + MOCK_RECIPE_JSON.strip() + "\n```"
    
    with patch("backend.core.config.settings.OPENAI_API_KEY", "test-key"):
        service = ChefService()
        mock_create = AsyncMock()
        mock_create.return_value.choices = [
            MagicMock(message=MagicMock(content=markdown_json))
        ]
        service.client.chat.completions.create = mock_create
        
        result = await service.generate_recipe_card([{"name": "Beef", "grams": 100}])
        assert result is not None
        assert result["dish_name"] == "Bamboo Shoots Stir-fry with Beef (竹笋炒牛肉)"
