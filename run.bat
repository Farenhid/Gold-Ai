@echo off
REM Smart Gold Accounting Middleware - Startup Script for Windows

echo 🏆 Starting Smart Gold Accounting Middleware...
echo.

REM Check if .env exists
if not exist .env (
    echo ⚠️  Warning: .env file not found!
    echo 📝 Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo ⚠️  IMPORTANT: Please edit .env and add your OpenAI API key!
    echo    Open .env and set OPENAI_API_KEY=your_actual_key_here
    echo.
    pause
)

REM Check if virtual environment exists
if not exist venv (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/update dependencies
echo 📥 Installing dependencies...
pip install -q -r requirements.txt

echo.
echo ✅ Setup complete!
echo 🚀 Starting server on http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
