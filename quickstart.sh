#!/bin/bash

# AutoNewsletter - Quick Start Script

set -e

echo "🚀 AutoNewsletter - Quick Start"
echo "======================================"
echo ""

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "   Python version: $python_version"

if ! python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo "❌ Python 3.11+ required. Please upgrade Python."
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and configure:"
    echo "   - DATABASE_URL"
    echo "   - DEEPSEEK_API_KEY or OPENAI_API_KEY"
    echo "   - RSS_FEEDS"
    echo "   - PUSHPLUS_TOKENS (optional)"
    echo ""
    echo "Then run this script again."
    exit 0
fi

# Install dependencies
echo ""
echo "📦 Installing Python dependencies..."

# Check if running in conda environment
if [ -n "$CONDA_DEFAULT_ENV" ]; then
    echo "   Detected conda environment: $CONDA_DEFAULT_ENV"
    echo "   Using conda for dependency management..."

    # Check if environment.yml exists
    if [ -f environment.yml ]; then
        conda env update -f environment.yml --prune
    else
        echo "   ⚠️  environment.yml not found, falling back to pip..."
        pip install -q -r requirements.txt
    fi
else
    echo "   Using pip for dependency management..."
    echo "   💡 Tip: Consider using conda for better environment isolation:"
    echo "      ./conda-setup.sh"
    pip install -q -r requirements.txt
fi

# Check Docker
echo ""
echo "🐳 Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker not found. Please install Docker to run PostgreSQL and Redis."
    echo "   Or configure DATABASE_URL and REDIS_URL to point to existing services."
else
    echo "   Starting PostgreSQL and Redis..."
    docker-compose up -d db redis
    echo "   Waiting for database to be ready..."
    sleep 5
fi

# Run migrations
echo ""
echo "🗄️  Running database migrations..."
alembic upgrade head

# Run setup test
echo ""
echo "🧪 Running setup tests..."
python test_setup.py

# Start application
echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "   1. Start the application:"
echo "      uvicorn app.main:app --reload"
echo ""
echo "   2. Or use Docker:"
echo "      docker-compose up -d"
echo ""
echo "   3. Check health:"
echo "      curl http://localhost:8000/health"
echo ""
echo "   4. Manual trigger:"
echo "      curl -X POST http://localhost:8000/trigger"
echo ""
echo "📚 Documentation:"
echo "   - README.md - Full guide"
echo "   - CLAUDE.md - Developer docs"
echo ""
