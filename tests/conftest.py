import pytest
import os
import sys
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# ================= 🛡️ MOCK AI ENGINES (ROBUST) =================
# We mock these modules in sys.modules so that when `backend.main` 
# tries to import them, it gets our mocks instead of loading real files.

MOCK_MODULES = [
    "backend.services.risk_engine",
    "backend.services.gene_service",
    "backend.services.fusion_service",
    "backend.services.pharm_service",
    "backend.services.food_service",
    "backend.services.inference_service",
    "backend.services.admin_service",
]

# Create a dictionary of mocks
module_mocks = {}
for mod_name in MOCK_MODULES:
    mock = MagicMock()
    # Setup specific return values to avoid AttributeError
    if "risk_engine" in mod_name:
        mock.DiseaseRiskEngine.return_value.assess_health.return_value = {}
    if "pharm_service" in mod_name:
        mock.PharmService.return_value.get_supported_drugs.return_value = ["MockDrug"]
    
    module_mocks[mod_name] = mock

# Apply patch.dict to sys.modules GLOBALLY for the test session
# This is critical: must happen before `from backend.main import app`
patcher = patch.dict(sys.modules, module_mocks)
patcher.start()

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
from backend.database import get_session
from backend.models import User, UserProfile

@pytest.fixture(scope="session", autouse=True)
def stop_mocking():
    yield
    patcher.stop()

@pytest.fixture(name="session")
def session_fixture():
    # Use in-memory SQLite with StaticPool for thread safety in tests
    engine = create_engine(
        "sqlite://", 
        connect_args={"check_same_thread": False}, 
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
