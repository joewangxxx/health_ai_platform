from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTER_FILE = REPO_ROOT / "frontend" / "src" / "router" / "index.js"
VITE_CONFIG_FILE = REPO_ROOT / "frontend" / "vite.config.js"


def test_router_uses_lazy_loaded_views_for_main_pages():
    router_source = ROUTER_FILE.read_text(encoding="utf-8")

    assert "import MainLayout from" not in router_source
    assert "const MainLayout = () => import('../layout/MainLayout.vue')" in router_source

    expected_lazy_routes = [
        "DashboardView",
        "ClinicalView",
        "GenomicsView",
        "LifestyleView",
        "PharmacyView",
        "NutritionPlanView",
        "ProfileView",
        "SettingsView",
        "AdminDashboardView",
        "DataCenterView",
        "UserManagementView",
        "KnowledgeBaseView",
    ]

    for view_name in expected_lazy_routes:
        assert f"import {view_name}" not in router_source


def test_vite_build_defines_manual_chunks_for_large_dependencies():
    vite_source = VITE_CONFIG_FILE.read_text(encoding="utf-8")

    assert "manualChunks" in vite_source
    assert "element-plus" in vite_source
    assert "echarts" in vite_source
    assert "element-plus/es/components" in vite_source
    assert "zrender" in vite_source
