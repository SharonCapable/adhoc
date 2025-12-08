#!/bin/bash

# Research Agent Setup Script
# This automates the initial setup process

echo "╔═══════════════════════════════════════════════════╗"
echo "║   Research Agent - Setup Script                   ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""

# Check Python version
echo "🐍 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Found: Python $python_version"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python3 -m venv adhoc
echo "   ✅ Virtual environment created"

# Install dependencies into the virtualenv (don't assume sourcing inside script)
echo ""
echo "� Installing dependencies into the virtualenv (using venv pip)..."
PIP_PATH="adhoc/bin/pip"
PY_PATH="adhoc/bin/python"
if [ ! -f "$PIP_PATH" ]; then
    PIP_PATH="adhoc/Scripts/pip.exe"
    PY_PATH="adhoc/Scripts/python.exe"
fi

if [ -f "$PIP_PATH" ]; then
    echo "   Using pip: $PIP_PATH"
    "$PIP_PATH" install --upgrade pip
    if [ -f requirements.txt ]; then
        "$PIP_PATH" install -r requirements.txt
    else
        echo "   ⚠️  requirements.txt not found, skipping install"
    fi
    echo "   ✅ Dependencies installed into the virtualenv"
else
    echo "   ⚠️  pip not found inside venv; please activate the venv and install requirements manually"
fi

echo ""
echo "🔌 To use the virtualenv in your interactive shell, run one of the following:" 
echo "   source adhoc/bin/activate   # WSL / Git Bash / macOS / Linux"
echo "   .\\adhoc\\Scripts\\Activate   # PowerShell (Windows)"
echo "Or run the project with the venv python without activating:"
echo "   adhoc/bin/python run_cli.py   # WSL / Git Bash / Linux"
echo "   .\\adhoc\\Scripts\\python.exe run_cli.py  # Windows PowerShell"

# Create directories
echo ""
echo "📁 Creating directories..."
mkdir -p data/outputs
mkdir -p src
echo "   ✅ Directories created"

# Copy .env template
echo ""
echo "⚙️  Setting up environment file..."
if [ ! -f .env ]; then
    # cp .env.template .env
    echo "   ✅ .env file created"
    echo "   ⚠️  IMPORTANT: Edit .env and add your API keys!"
else
    echo "   ℹ️  .env already exists, skipping"
fi

# Check for Google credentials
echo ""
echo "🔐 Checking for Google credentials..."
if [ ! -f credentials.json ]; then
    echo "   ⚠️  credentials.json not found"
    echo "   📝 You need to:"
    echo "      1. Go to https://console.cloud.google.com"
    echo "      2. Enable Google Drive API"
    echo "      3. Create OAuth credentials"
    echo "      4. Download and save as credentials.json"
else
    echo "   ✅ credentials.json found"
fi

# Summary
echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║   Setup Complete!                                 ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Edit .env file with your API keys:"
echo "   nano .env"
echo ""
echo "2. Add Google credentials if not done:"
echo "   - Place credentials.json in project root"
echo ""
echo "3. Test the agent:"
echo "   python run_cli.py"
echo ""
echo "4. Or run Slack bot:"
echo "   python run_slack.py"
echo ""
echo "📖 See README.md for detailed instructions"
echo ""