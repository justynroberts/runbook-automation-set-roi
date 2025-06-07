#!/bin/bash
# Setup script for Rundeck ROI Plugin Manager on Linux
# This script creates a virtual environment and installs dependencies

set -e  # Exit on any error

echo "Setting up Rundeck ROI Plugin Manager..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.7"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 7) else 1)"; then
    echo "Error: Python $REQUIRED_VERSION or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "Python version: $PYTHON_VERSION ✓"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists ✓"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Install the package in development mode
echo "Installing package in development mode..."
pip install -e .

echo ""
echo "Setup complete! ✓"
echo ""
echo "To use the tool:"
echo "1. Activate the virtual environment: source .venv/bin/activate"
echo "2. Set environment variables:"
echo "   export RUNDECK_URL='https://your-rundeck-server.com'"
echo "   export RUNDECK_API_TOKEN='your-api-token'"
echo "3. Run the tool:"
echo "   python main.py --help"
echo "   python main.py --project myproject --no-dry-run"
echo ""
echo "To deactivate the virtual environment later: deactivate"