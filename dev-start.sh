#!/bin/bash

# Development startup script for Fabric Management Portal

set -e

echo "🚀 Starting Fabric Management Portal Development Environment"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "📋 Please copy .env-sample to .env and configure your settings:"
    echo "   cp .env-sample .env"
    echo "   # Edit .env with your actual values"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install/upgrade dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check database connectivity (optional)
echo "🔍 Checking configuration..."
python -c "
import os
from dotenv import load_dotenv
load_dotenv('.env')

required_vars = ['TENANT_ID', 'CLIENT_ID', 'CLIENT_SECRET', 'DB_SERVER', 'DB_NAME']
missing = [var for var in required_vars if not os.getenv(var)]

if missing:
    print(f'❌ Missing required environment variables: {missing}')
    exit(1)
else:
    print('✅ All required environment variables are set')
"

# Start the development server
echo "🌐 Starting development server..."
echo "📱 Application will be available at: http://localhost:8000"
echo "🔧 Debug endpoints:"
echo "   - User info: http://localhost:8000/debug/user"
echo "   - Headers: http://localhost:8000/debug/headers"
echo ""
echo "Press Ctrl+C to stop the server"

uvicorn main:app --reload --host 0.0.0.0 --port 8000
