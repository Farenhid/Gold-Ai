#!/bin/bash

# Smart Gold Accounting Middleware - Startup Script

echo "🏆 Starting Smart Gold Accounting Middleware..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and add your OpenAI API key!"
    echo "   Open .env and set OPENAI_API_KEY=your_actual_key_here"
    echo ""
    read -p "Press Enter after you've configured your API key..."
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo "🚀 Starting server on http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
