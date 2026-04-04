import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("module_name", ["backend.models", "backend.main"])
def test_backend_imports_do_not_raise_pydantic_deprecation_warnings(module_name):
    result = subprocess.run(
        [
            sys.executable,
            "-W",
            "error",
            "-c",
            f"import {module_name}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
