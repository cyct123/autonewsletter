#!/bin/bash

# AutoNewsletter Startup Script

set -e

echo "🚀 Starting AutoNewsletter..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Please create one from .env.example"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check database connection
echo "🔍 Checking database connection..."
if ! python -c "from app.database import engine; import asyncio; asyncio.run(engine.connect())" 2>/dev/null; then
    echo "⚠️  Database connection failed. Make sure PostgreSQL is running."
    echo "   Run: docker-compose up -d db redis"
    exit 1
fi

# Run migrations
echo "📦 Running database migrations..."
alembic upgrade head

# Start application
echo "✅ Starting FastAPI application..."
if [ "$1" = "dev" ]; then
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
else
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
fi
