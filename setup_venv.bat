@echo off
echo 가상환경 설정 및 패키지 설치 스크립트
echo ======================================

REM 가상환경 디렉토리 설정
set VENV_DIR=venv

echo 1. 가상환경 생성 중...
python -m venv %VENV_DIR%

echo 2. 가상환경 활성화 중...
call %VENV_DIR%\Scripts\activate.bat

echo 3. pip 업그레이드 중...
python -m pip install --upgrade pip

echo 4. 필요한 패키지 설치 중...
pip install -r requirements.txt

echo ======================================
echo 설치 완료!
echo 가상환경이 성공적으로 생성되었으며 필요한 패키지가 설치되었습니다.
echo.
echo 가상환경을 활성화하려면 다음 명령어를 실행하세요:
echo   %VENV_DIR%\Scripts\activate.bat
echo.
echo 프로젝트를 실행하려면 다음 명령어를 실행하세요:
echo   python run_demo.py
echo ======================================

pause