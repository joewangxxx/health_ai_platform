@echo off
echo ==========================================
echo 🛡️  HealthAI Static Code Analysis Tool
echo ==========================================

echo.
echo [1/2] Running Ruff Linter (Style & Errors)...
ruff check .

echo.
echo [2/2] Running Bandit (Security Scan)...
bandit -r backend -ll

echo.
echo ==========================================
echo ✅ Audit Complete.
echo ==========================================
pause
