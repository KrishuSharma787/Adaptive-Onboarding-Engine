#!/bin/bash
# =============================================================
# Adaptive Onboarding Engine - Quick Setup Script
# =============================================================

set -e

echo "=================================================="
echo "  AI-Adaptive Onboarding Engine - Setup"
echo "=================================================="

# Check for .env
if [ ! -f .env ]; then
    echo ""
    echo "  No .env file found. Creating from template..."
    cp .env.example .env
    echo "   Please edit .env and add your GROQ_API_KEY"
    echo "   Then re-run this script."
    exit 1
fi

# Check for Resume.csv
if [ ! -f data/Resume.csv ]; then
    echo ""
    echo "  No Resume.csv found in data/"
    echo "   Please download from: https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset/data"
    echo "   Place Resume.csv in the data/ directory"
    echo ""
    mkdir -p data
fi

# Backend setup
echo ""
echo " Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt --quiet

echo " Backend dependencies installed"

# Pre-build course catalog
if [ -f "../data/Resume.csv" ] && [ ! -f "app/data/course_catalog.json" ]; then
    echo ""
    echo " Building course catalog from resume dataset..."
    python3 -c "
import os, sys
sys.path.insert(0, '.')
os.makedirs('app/data', exist_ok=True)
from app.services.catalog_builder import build_catalog_from_csv
build_catalog_from_csv('../data/Resume.csv', 'app/data/course_catalog.json')
"
    echo " Course catalog built"
fi

cd ..

# Frontend setup
echo ""
echo " Setting up frontend..."
cd frontend
npm install --silent
echo " Frontend dependencies installed"
cd ..

echo ""
echo "=================================================="
echo "   Setup Complete!"
echo "=================================================="
echo ""
echo "  To start the application:"
echo ""
echo "  Terminal 1 (Backend):"
echo "    cd backend && source venv/bin/activate"
echo "    uvicorn app.main:app --reload --port 8000"
echo ""
echo "  Terminal 2 (Frontend):"
echo "    cd frontend && npm run dev"
echo ""
echo "  Then open: http://localhost:3000"
echo ""
echo "  Or use Docker:"
echo "    docker-compose up --build"
echo "=================================================="
