from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DOCKERFILE = REPO_ROOT / "backend" / "Dockerfile"
FRONTEND_DOCKERFILE = REPO_ROOT / "frontend" / "Dockerfile"
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"


def test_backend_dockerfile_uses_production_uvicorn_entrypoint():
    dockerfile_source = BACKEND_DOCKERFILE.read_text(encoding="utf-8")

    assert "0.0.0.0" in dockerfile_source
    assert 'CMD ["python", "run.py"]' not in dockerfile_source


def test_frontend_dockerfile_healthcheck_targets_ipv4_loopback():
    dockerfile_source = FRONTEND_DOCKERFILE.read_text(encoding="utf-8")

    assert "http://127.0.0.1/" in dockerfile_source


def test_compose_runtime_uses_production_backend_command_and_ipv4_frontend_healthcheck():
    compose_source = COMPOSE_FILE.read_text(encoding="utf-8")

    assert 'command: ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]' in compose_source
    assert 'http://127.0.0.1/' in compose_source
    assert "version:" not in compose_source
