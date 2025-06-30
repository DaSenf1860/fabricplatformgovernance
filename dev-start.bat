@echo off
REM Development startup script for Fabric Management Portal (Windows)

echo 🚀 Starting Fabric Management Portal Development Environment

REM Check if .env file exists
if not exist ".env" (
    echo ❌ .env file not found!
    echo 📋 Please copy .env-sample to .env and configure your settings:
    echo    copy .env-sample .env
    echo    REM Edit .env with your actual values
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate

REM Install/upgrade dependencies
echo 📚 Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Check configuration
echo 🔍 Checking configuration...
python -c "import os; from dotenv import load_dotenv; load_dotenv('.env'); required_vars = ['TENANT_ID', 'CLIENT_ID', 'CLIENT_SECRET', 'DB_SERVER', 'DB_NAME']; missing = [var for var in required_vars if not os.getenv(var)]; print(f'❌ Missing required environment variables: {missing}') if missing else print('✅ All required environment variables are set'); exit(1) if missing else exit(0)"

if errorlevel 1 (
    pause
    exit /b 1
)

REM Start the development server
echo 🌐 Starting development server...
echo 📱 Application will be available at: http://localhost:8000
echo 🔧 Debug endpoints:
echo    - User info: http://localhost:8000/debug/user
echo    - Headers: http://localhost:8000/debug/headers
echo.
echo Press Ctrl+C to stop the server

uvicorn main:app --reload --host 0.0.0.0 --port 8000
