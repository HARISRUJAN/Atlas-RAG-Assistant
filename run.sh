#!/bin/bash

# Script to run the MongoDB RAG System

echo "================================"
echo "MongoDB RAG System Startup"
echo "================================"
echo ""

# Check if virtual environment exists
if [ ! -d "rag_env" ]; then
    echo "Creating virtual environment..."
    python -m venv rag_env
fi

# Activate virtual environment
echo "Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source rag_env/Scripts/activate
else
    source rag_env/bin/activate
fi

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check environment variables
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Please create one from .env.example"
    exit 1
fi

# Start backend
echo ""
echo "Starting Flask backend on port 5000..."
cd backend
python app.py &
BACKEND_PID=$!
cd ..

# Wait a bit for backend to start
sleep 3

# Start frontend
echo ""
echo "Starting React frontend on port 5173..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "================================"
echo "System Started Successfully!"
echo "================================"
echo "Backend API: http://localhost:5000/api"
echo "Frontend UI: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for user interrupt
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait

