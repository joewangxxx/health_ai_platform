"""
Tests for authentication and authorization (RBAC).
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from backend.models import User


# ================= Mock User Factories =================
def create_mock_regular_user():
    """Create a mock regular user (not superuser)."""
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testuser"
    user.email = "testuser@example.com"
    user.is_superuser = False
    user.profile = None
    return user


def create_mock_superuser():
    """Create a mock superuser."""
    user = MagicMock(spec=User)
    user.id = 2
    user.username = "admin"
    user.email = "admin@healthai.com"
    user.is_superuser = True
    user.profile = None
    return user


# ================= Tests =================
class TestAdminAccess:
    """Test admin-only endpoint access control."""
    
    def test_regular_user_cannot_access_admin_users(self, client: TestClient):
        """Regular user should get 403 when accessing admin endpoints."""
        from backend.main import app
        from backend.auth import get_current_user
        
        # Override to return a regular user
        app.dependency_overrides[get_current_user] = create_mock_regular_user
        
        response = client.get("/admin/users")
        
        assert response.status_code == 403
        assert "Not authorized" in response.json().get("detail", "")
        
        # Cleanup
        app.dependency_overrides.clear()
    
    def test_superuser_can_access_admin_users(self, client: TestClient):
        """Superuser should get 200 when accessing admin endpoints."""
        from backend.main import app
        from backend.auth import get_current_user
        
        # Override to return a superuser
        app.dependency_overrides[get_current_user] = create_mock_superuser
        
        response = client.get("/admin/users")
        
        assert response.status_code == 200
        # Response should be a list (even if empty due to mock session)
        assert isinstance(response.json(), list)
        
        # Cleanup
        app.dependency_overrides.clear()
    
    def test_regular_user_cannot_access_admin_logs(self, client: TestClient):
        """Regular user should get 403 when accessing admin logs."""
        from backend.main import app
        from backend.auth import get_current_user
        
        app.dependency_overrides[get_current_user] = create_mock_regular_user
        
        response = client.get("/admin/data/logs")
        
        assert response.status_code == 403
        
        app.dependency_overrides.clear()
    
    def test_superuser_can_access_admin_logs(self, client: TestClient):
        """Superuser should get 200 when accessing admin logs."""
        from backend.main import app
        from backend.auth import get_current_user
        
        app.dependency_overrides[get_current_user] = create_mock_superuser
        
        response = client.get("/admin/data/logs")
        
        assert response.status_code == 200
        
        app.dependency_overrides.clear()


class TestAuthContracts:
    def test_register_returns_bearer_token_type(self, client: TestClient):
        username = f"auth_{uuid.uuid4().hex[:8]}"

        response = client.post(
            "/auth/register",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": "SmokePass123",
            },
        )

        assert response.status_code == 200
        assert response.json()["access_token"]
        assert response.json()["token_type"] == "bearer"

    def test_login_returns_bearer_token_type(self, client: TestClient):
        username = f"login_{uuid.uuid4().hex[:8]}"

        register_response = client.post(
            "/auth/register",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": "SmokePass123",
            },
        )

        login_response = client.post(
            "/auth/token",
            data={
                "username": username,
                "password": "SmokePass123",
            },
        )

        assert register_response.status_code == 200
        assert login_response.status_code == 200
        assert login_response.json()["access_token"]
        assert login_response.json()["token_type"] == "bearer"
