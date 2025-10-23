#!/bin/bash
# Setup script for Arbihedron

echo "Setting up Arbihedron..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create logs directory
echo "Creating logs directory..."
mkdir -p logs

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env with your exchange API credentials"
else
    echo ".env file already exists"
fi

# Make scripts executable
echo "Making scripts executable..."
chmod +x main.py
chmod +x examples.py
chmod +x backtest.py

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your configuration"
echo "2. Activate the virtual environment: source venv/bin/activate"
echo "3. Run the bot: python main.py"
echo ""
echo "For testing: python examples.py"
echo "For backtesting: python backtest.py"
echo ""
echo "Important:"
echo "Remember to enable paper trading mode first!"
echo "Set ENABLE_PAPER_TRADING=true in .env"
