#!/bin/bash
# Quick setup script for GNN-based arbitrage detection

echo "🧠 Setting up GNN-based Arbitrage Detection..."
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create models directory
echo "📁 Creating models directory..."
mkdir -p models
mkdir -p data

# Install PyTorch
echo "📦 Installing PyTorch..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install PyTorch Geometric
echo "📦 Installing PyTorch Geometric..."
pip install torch-geometric

# Install other ML dependencies
echo "📦 Installing other dependencies..."
pip install scipy scikit-learn

# Optional: matplotlib for plotting
echo "📦 Installing matplotlib (optional)..."
pip install matplotlib

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Train a model: python train_gnn.py"
echo "2. Enable GNN in .env: USE_GNN_ENGINE=true"
echo "3. Run the bot: python main.py"
echo ""
echo "See GNN_ARCHITECTURE.md for detailed documentation."
