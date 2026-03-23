@echo off
echo FinVision 패키지 설치 중...
echo.
echo [1/2] 백엔드 패키지 설치...
cd /d %~dp0backend
pip install -r requirements.txt
echo.
echo [2/2] 프론트엔드 패키지 설치...
cd /d %~dp0frontend
npm install
echo.
echo 설치 완료! run.bat 을 실행하면 서버가 시작됩니다.
pause
