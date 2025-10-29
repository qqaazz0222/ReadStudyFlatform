@echo off
REM CT Read Study Platform 빠른 시작 스크립트 (Windows)

echo ==================================================
echo 🏥 CT Read Study Platform - Quick Start
echo ==================================================
echo.

REM 1. Conda 설치 확인
where conda >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Conda가 설치되어 있지 않습니다.
    echo    Anaconda 또는 Miniconda를 먼저 설치해주세요.
    echo    https://docs.conda.io/en/latest/miniconda.html
    pause
    exit /b 1
)
echo ✅ Conda 설치 확인됨
echo.

REM 2. .env 파일 생성
if not exist .env (
    echo 📝 .env 파일 생성 중...
    copy .env.example .env
    echo ✅ .env 파일 생성 완료
) else (
    echo ✅ .env 파일이 이미 존재합니다
)
echo.

REM 3. Conda 환경 확인
conda env list | findstr "read-study-platform" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 🔧 Conda 환경 생성 중...
    conda env create -f environment.yml
    echo ✅ Conda 환경 생성 완료
) else (
    echo ✅ Conda 환경이 이미 존재합니다
)
echo.

REM 4. 환경 활성화 안내
echo 📌 Conda 환경 활성화:
echo    conda activate read-study-platform
echo.

REM 5. 샘플 데이터 생성 안내
echo 🔬 샘플 데이터 생성 (선택사항):
echo    python create_sample_data.py --num-patients 5
echo.

REM 6. 실행 안내
echo 🚀 플랫폼 실행:
echo    python main.py
echo.

echo ==================================================
echo ✅ 준비 완료!
echo ==================================================
pause
