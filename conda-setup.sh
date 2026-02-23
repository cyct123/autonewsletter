#!/bin/bash

# AutoNewsletter - Conda Environment Setup Script

set -e

echo "🐍 AutoNewsletter - Conda Environment Setup"
echo "============================================"
echo ""

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "❌ Conda not found. Please install Miniconda or Anaconda first."
    echo ""
    echo "Download Miniconda:"
    echo "  https://docs.conda.io/en/latest/miniconda.html"
    echo ""
    echo "Or install via:"
    echo "  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    echo "  bash Miniconda3-latest-Linux-x86_64.sh"
    exit 1
fi

echo "✅ Conda found: $(conda --version)"
echo ""

# Check if environment already exists
if conda env list | grep -q "^autonewsletter "; then
    echo "⚠️  Environment 'autonewsletter' already exists."
    read -p "Do you want to remove and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Removing existing environment..."
        conda env remove -n autonewsletter -y
    else
        echo "Updating existing environment..."
        conda env update -n autonewsletter -f environment.yml --prune
        echo "✅ Environment updated!"
        exit 0
    fi
fi

# Create conda environment
echo "📦 Creating conda environment from environment.yml..."
conda env create -f environment.yml

echo ""
echo "✅ Conda environment created successfully!"
echo ""
echo "🎯 Next steps:"
echo "   1. Activate the environment:"
echo "      conda activate autonewsletter"
echo ""
echo "   2. Verify installation:"
echo "      python test_setup.py"
echo ""
echo "   3. Start the application:"
echo "      uvicorn app.main:app --reload"
echo ""
