#!/bin/bash
# Arbihedron Setup Script
# Usage: ./setup.sh [--gnn] [--full]

set -e  # Exit on error

# Parse arguments
INSTALL_GNN=false
FULL_SETUP=false

for arg in "$@"; do
    case $arg in
        --gnn)
            INSTALL_GNN=true
            shift
            ;;
        --full)
            INSTALL_GNN=true
            FULL_SETUP=true
            shift
            ;;
        --help)
            echo "Usage: ./setup.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --gnn      Install GNN dependencies (PyTorch, PyTorch Geometric)"
            echo "  --full     Complete setup with all optional dependencies"
            echo "  --help     Show this help message"
            echo ""
            exit 0
            ;;
    esac
done

echo "=========================================="
echo "     Arbihedron Setup"
echo "=========================================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install core dependencies
echo ""
echo "Installing core dependencies..."
pip install -r requirements.txt

# Install GNN dependencies if requested
if [ "$INSTALL_GNN" = true ]; then
    echo ""
    echo "=========================================="
    echo "Installing GNN Dependencies"
    echo "=========================================="
    echo ""
    
    echo "Installing PyTorch..."
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
    
    echo "Installing PyTorch Geometric..."
    pip install torch-geometric
    
    echo "Installing ML dependencies..."
    pip install scipy scikit-learn matplotlib
    
    echo ""
    echo "✓ GNN dependencies installed"
fi

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p logs
mkdir -p data
mkdir -p models
mkdir -p exports
mkdir -p tests

echo "✓ Directories created"

# Copy .env file if it doesn't exist
echo ""
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration"
else
    echo "✓ .env file already exists"
fi

# Make scripts executable
echo ""
echo "Making scripts executable..."
chmod +x arbi
chmod +x test_service.sh

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure your settings:"
echo "   nano .env  # or your preferred editor"
echo ""
echo "2. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "3. Run the bot:"
echo "   python main.py              # Live monitoring"
echo "   python examples.py          # Quick example"
echo "   python backtest.py          # Backtest strategies"
echo ""

if [ "$INSTALL_GNN" = true ]; then
    echo "4. Train the GNN model (optional):"
    echo "   python train_gnn_real.py --num-scans 100"
    echo ""
    echo "5. Compare engines:"
    echo "   python compare_engines.py --num-scans 20"
    echo ""
    echo "   See docs/GNN_ARCHITECTURE.md for details"
    echo ""
fi

echo "Service control:"
echo "   ./arbi start     # Start as background service"
echo "   ./arbi status    # Check status"
echo "   ./arbi logs      # View logs"
echo "   ./arbi stop      # Stop service"
echo ""
echo "⚠️  Important: Keep paper trading enabled for testing!"
echo "   ENABLE_PAPER_TRADING=true in .env"
echo ""