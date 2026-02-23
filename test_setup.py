"""
Simple test to verify Python setup
"""
import sys


def test_imports():
    """Test that all required packages can be imported"""
    try:
        import fastapi
        import sqlalchemy
        import asyncpg
        import redis
        import httpx
        import feedparser
        import openai
        import apscheduler
        import structlog
        import pydantic_settings
        import alembic

        print("✅ All required packages imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_app_structure():
    """Test that app structure is correct"""
    import os

    required_dirs = [
        "app",
        "app/models",
        "app/repositories",
        "app/services",
        "app/modules",
        "app/jobs",
        "app/utils",
        "app/api",
        "alembic",
    ]

    required_files = [
        "app/__init__.py",
        "app/main.py",
        "app/config.py",
        "app/database.py",
        "requirements.txt",
        "Dockerfile",
        "docker-compose.yml",
    ]

    all_ok = True

    for dir_path in required_dirs:
        if not os.path.isdir(dir_path):
            print(f"❌ Missing directory: {dir_path}")
            all_ok = False

    for file_path in required_files:
        if not os.path.isfile(file_path):
            print(f"❌ Missing file: {file_path}")
            all_ok = False

    if all_ok:
        print("✅ App structure is correct")

    return all_ok


def test_config():
    """Test configuration loading"""
    try:
        from app.config import settings

        print(f"✅ Configuration loaded")
        print(f"   - Database URL: {settings.database_url[:30]}...")
        print(f"   - Redis URL: {settings.redis_url}")
        print(f"   - Weekly Cron: {settings.weekly_cron}")
        return True
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        return False


def test_conda_environment():
    """Test if running in conda environment"""
    import os

    conda_env = os.environ.get("CONDA_DEFAULT_ENV")
    if conda_env:
        print(f"✅ Running in conda environment: {conda_env}")

        # Check if environment.yml exists
        if os.path.isfile("environment.yml"):
            print("✅ environment.yml found")
        else:
            print("⚠️  environment.yml not found")

        return True
    else:
        print("ℹ️  Not running in conda environment (using system Python)")
        return True


if __name__ == "__main__":
    print("🧪 Running AutoNewsletter Python setup tests...\n")

    results = [
        test_imports(),
        test_app_structure(),
        test_config(),
        test_conda_environment(),
    ]

    print("\n" + "=" * 50)
    if all(results):
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)
