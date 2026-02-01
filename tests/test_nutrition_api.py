
import pytest
from unittest.mock import patch, AsyncMock
from sqlmodel import Session, select
from backend.models import User, UserProfile
from backend.auth import create_access_token

@pytest.fixture
def auth_header(session: Session):
    # Ensure test user exists
    user = session.exec(select(User).where(User.username == "test_nutrition_user")).first()
    if not user:
        user = User(username="test_nutrition_user", hashed_password="hashed_password")
        session.add(user)
        session.commit()
        session.refresh(user)
        
        # Profile for TDEE
        profile = UserProfile(
            user_id=user.id,
            Age=30,
            Gender=1, # Male
            Height=175.0,
            Weight=70.0
        )
        session.add(profile)
        session.commit()
        
    token = create_access_token(data={"sub": user.username})
    return {"Authorization": f"Bearer {token}"}

@patch("backend.api.nutrition.chef_service.generate_recipe_card", new_callable=AsyncMock)
def test_generate_plan_explicit_calories(mock_chef, client, auth_header):
    """Test generating plan with explicit target calories"""
    
    # Mock Recipe Return
    mock_chef.return_value = {
        "dish_name": "Mock Dish",
        "tags": ["Mock Tag"],
        "description": "Tasty mock dish",
        "steps": ["Step 1"],
        "chef_tips": "Mock Tip"
    }

    payload = {
        "target_calories": 2500,
        "health_conditions": ["hypertension"],
        "cuisine_preference": "Asian"
    }
    response = client.post("/nutrition/generate", json=payload, headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["target_calories"] == 2500
    assert len(data["foods"]) > 0
    # Check sodium limit (Hypertension < 1500 or 2400)
    assert data["macros"]["sodium_mg"] <= 1500
    
    # Check Recipe Integration
    assert "recipe_suggestion" in data
    if data.get("recipe_suggestion"): # It might be None if Logic failed, but we mocked it to return something
        assert data["recipe_suggestion"]["dish_name"] == "Mock Dish"
    
    # Verify Mock was called
    mock_chef.assert_called_once()

def test_generate_plan_auto_tdee(client, auth_header):
    """Test generating plan using TDEE from profile"""
    payload = {
        # No target_calories
        "health_conditions": []
    }
    response = client.post("/nutrition/generate", json=payload, headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    
    # Manually calc expectation:
    # 10*70 + 6.25*175 - 5*30 + 5 = 700 + 1093.75 - 150 + 5 = 1648.75
    # TDEE = 1648.75 * 1.2 = 1978.5 -> 1978
    assert 1900 < data["target_calories"] < 2100 # Approx range check
    assert len(data["foods"]) > 0

def test_generate_plan_unauthorized(client):
    payload = {"target_calories": 2000}
    response = client.post("/nutrition/generate", json=payload)
    assert response.status_code == 401
