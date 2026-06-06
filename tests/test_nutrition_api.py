from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import Session, select

from backend.auth import create_access_token
from backend.models import User, UserProfile
from backend.services.nutrition_service import DietOptimizer


@pytest.fixture
def auth_header(session: Session):
    user = session.exec(select(User).where(User.username == "test_nutrition_user")).first()
    if not user:
        user = User(username="test_nutrition_user", hashed_password="hashed_password")
        session.add(user)
        session.commit()
        session.refresh(user)

        profile = UserProfile(
            user_id=user.id,
            Age=30,
            Gender=1,
            Height=175.0,
            Weight=70.0,
        )
        session.add(profile)
        session.commit()

    token = create_access_token(data={"sub": user.username})
    return {"Authorization": f"Bearer {token}"}


@patch("backend.api.nutrition.optimizer.generate_daily_plan", new_callable=AsyncMock)
def test_generate_plan_explicit_calories(mock_generate, client, auth_header):
    """Generate plan with explicit target calories."""
    mock_generate.return_value = {
        "status": "success",
        "target_calories": 2500,
        "actual_calories": 2480.0,
        "macros": {"protein_g": 130.0, "fat_g": 80.0, "carbs_g": 270.0, "sodium_mg": 1200.0},
        "macro_ratios": {"protein": 0.2, "fat": 0.3, "carbs": 0.5},
        "foods": [
            {
                "name": "Chicken Breast",
                "amount_desc": "200g",
                "calories": 330.0,
                "protein": 62.0,
                "fat": 7.0,
                "carbs": 0.0,
            }
        ],
        "recipe_suggestion": {
            "dish_name": "Mock Dish",
            "tags": ["Mock Tag"],
            "description": "Tasty mock dish",
            "steps": ["Step 1"],
            "chef_tips": "Mock Tip",
        },
        "warnings": ["hypertension"],
    }

    payload = {
        "target_calories": 2500,
        "health_conditions": ["hypertension"],
        "cuisine_preference": "Asian",
    }
    response = client.post("/nutrition/generate", json=payload, headers=auth_header)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["target_calories"] == 2500
    assert len(data["foods"]) > 0
    assert data["macros"]["sodium_mg"] <= 1500
    assert data["recipe_suggestion"]["dish_name"] == "Mock Dish"

    mock_generate.assert_called_once_with(target_calories=2500, restrictions=["hypertension"])


@patch("backend.api.nutrition.optimizer.generate_daily_plan", new_callable=AsyncMock)
def test_generate_plan_auto_tdee(mock_generate, client, auth_header):
    """Generate plan using TDEE inferred from profile."""
    mock_generate.return_value = {
        "status": "success",
        "target_calories": 1978,
        "actual_calories": 1960.0,
        "macros": {"protein_g": 95.0, "fat_g": 64.0, "carbs_g": 245.0, "sodium_mg": 1300.0},
        "macro_ratios": {"protein": 0.2, "fat": 0.3, "carbs": 0.5},
        "foods": [
            {
                "name": "Rice",
                "amount_desc": "150g",
                "calories": 200.0,
                "protein": 4.0,
                "fat": 0.3,
                "carbs": 45.0,
            }
        ],
        "recipe_suggestion": None,
        "warnings": [],
    }

    payload = {"health_conditions": []}
    response = client.post("/nutrition/generate", json=payload, headers=auth_header)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert 1900 < data["target_calories"] < 2100
    assert len(data["foods"]) > 0

    mock_generate.assert_called_once_with(target_calories=1978, restrictions=[])


def test_generate_plan_unauthorized(client):
    payload = {"target_calories": 2000}
    response = client.post("/nutrition/generate", json=payload)
    assert response.status_code == 401


def test_fallback_plan_matches_response_contract():
    plan = DietOptimizer()._fallback_plan(target_calories=1800, restrictions=["diabetes"])

    assert plan["status"] == "success"
    assert plan["target_calories"] == 1800
    assert plan["actual_calories"] > 0
    assert plan["macros"].keys() >= {"protein_g", "fat_g", "carbs_g", "sodium_mg"}
    assert plan["macro_ratios"].keys() >= {"protein", "fat", "carbs"}
    assert plan["warnings"] == ["diabetes"]
    assert plan["foods"]
    assert plan["recipe_suggestion"]["dish_name"]
