#!/bin/bash
# Quick Start Script untuk Chatbot Hadis
# Usage: ./start.sh

cd /home/rakacoder/Documents/A_Project/chatbot-hadis

echo "🚀 Starting Chatbot Hadis..."
echo "================================"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "❌ Virtual environment not found!"
    echo "   Run: python -m venv venv"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
fi

# Start server
echo ""
echo "📡 Starting FastAPI server..."
echo "   URL: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo "================================"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
