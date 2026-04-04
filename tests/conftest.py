import pytest
import os
import sys
from types import SimpleNamespace
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
    "backend.services.rag_service",
    "backend.services.pdf_service",
    "backend.services.ocr_service",
    "backend.rag.build_kb",
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
    if "rag_service" in mod_name:
        def _default_search_context(query, k=3):
            return ""

        def _default_search_context_with_quality(query, k=3):
            context = mock.rag_service.search_context(query, k=k)
            if not context:
                return {
                    "context": "",
                    "rag_quality_summary": {
                        "retrieval_status": "empty",
                        "hit_count": 0,
                        "unique_source_count": 0,
                        "source_kind": "unknown",
                        "density_status": "unknown",
                        "ocr_fallback_state": "unknown",
                        "provenance_state": "missing",
                        "chunk_quality": "empty",
                    },
                }
            return {
                "context": context,
                "rag_quality_summary": {
                    "retrieval_status": "ok",
                    "hit_count": 1,
                    "unique_source_count": 1,
                    "source_kind": "pdf_text",
                    "density_status": "normal",
                    "ocr_fallback_state": "available",
                    "provenance_state": "full",
                    "chunk_quality": "strong",
                },
            }

        mock.rag_service = SimpleNamespace(
            search_context=_default_search_context,
            search_context_with_quality=_default_search_context_with_quality,
        )
    if "pdf_service" in mod_name:
        mock.pdf_service.export_health_report.return_value = b"%PDF-1.4"
        mock.PDFGenerationError = Exception
    if "ocr_service" in mod_name:
        mock.medical_ocr_service.parse_medical_report.return_value = {"status": "success", "data": {}}
    if "build_kb" in mod_name:
        mock.build_knowledge_base.return_value = None
        mock.DOCS_DIR = "tests/mock_docs"
    
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
