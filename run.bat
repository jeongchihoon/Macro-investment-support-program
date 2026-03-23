@echo off
echo FinVision 시작 중...
echo.
echo 백엔드 시작 (http://localhost:8000)
start "FinVision Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --reload --port 8000"
timeout /t 2 /nobreak >nul
echo 프론트엔드 시작 (http://localhost:5173)
start "FinVision Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 3 /nobreak >nul
echo.
echo 브라우저에서 http://localhost:5173 을 열어주세요.
start http://localhost:5173
