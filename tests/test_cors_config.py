from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from backend.auth import get_current_user
from backend.core.config import settings
from backend.main import app
from backend.models import User, UserProfile


def test_cors_middleware_uses_runtime_allowlist_without_wildcard():
    cors_middleware = next((item for item in app.user_middleware if item.cls is CORSMiddleware), None)
    assert cors_middleware is not None

    allow_origins = cors_middleware.kwargs.get("allow_origins", [])
    assert allow_origins == settings.BACKEND_CORS_ORIGINS
    assert "*" not in allow_origins
    assert "http://127.0.0.1:5173" in allow_origins
    assert cors_middleware.kwargs.get("allow_credentials") is True


def test_cors_preflight_allows_local_vite_origin(client: TestClient):
    response = client.options(
        "/user/profile",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert response.headers["access-control-allow-credentials"] == "true"

    allow_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "authorization" in allow_headers
    assert "content-type" in allow_headers


def test_cors_actual_authenticated_response_echoes_local_vite_origin(client: TestClient, session, monkeypatch):
    user = User(
        username="cors_user",
        email="cors_user@example.com",
        hashed_password="hashed",
        is_superuser=False,
    )
    profile = UserProfile(user_id=1)
    user.profile = profile
    session.add(user)
    session.add(profile)
    session.commit()

    monkeypatch.setattr("backend.core.cache.CacheManager.invalidate_user_cache", lambda user_id: None)
    app.dependency_overrides[get_current_user] = lambda: user

    response = client.post(
        "/user/profile",
        headers={"Origin": "http://127.0.0.1:5173"},
        json={"Age": 40, "Gender": 1, "Height": 170, "Weight": 70},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert response.headers["access-control-allow-credentials"] == "true"

    app.dependency_overrides.clear()
