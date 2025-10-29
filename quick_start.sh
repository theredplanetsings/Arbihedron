#!/bin/bash
# Quick start script for Arbihedron with Docker

set -e

echo "🔺 Arbihedron Quick Start"
echo "=========================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker and Docker Compose are installed${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo -e "${YELLOW}⚠ No .env file found, creating from .env.example${NC}"
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env file${NC}"
        echo -e "${YELLOW}⚠ Please edit .env with your configuration${NC}"
    else
        echo -e "${YELLOW}⚠ No .env file found${NC}"
    fi
    echo ""
fi

# Parse command line arguments
MODE="standard"
REBUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            MODE="dev"
            shift
            ;;
        --gnn)
            MODE="gnn"
            shift
            ;;
        --monitoring)
            MODE="monitoring"
            shift
            ;;
        --rebuild)
            REBUILD=true
            shift
            ;;
        --help)
            echo "Usage: ./quick_start.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dev         Start in development mode with hot reload"
            echo "  --gnn         Start with GNN engine enabled"
            echo "  --monitoring  Start with Prometheus and Grafana"
            echo "  --rebuild     Rebuild Docker images"
            echo "  --help        Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./quick_start.sh                 # Standard deployment"
            echo "  ./quick_start.sh --dev           # Development mode"
            echo "  ./quick_start.sh --gnn           # With GNN engine"
            echo "  ./quick_start.sh --monitoring    # With monitoring stack"
            echo "  ./quick_start.sh --rebuild       # Rebuild containers"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Rebuild if requested
if [ "$REBUILD" = true ]; then
    echo "🔨 Rebuilding Docker images..."
    docker-compose build --no-cache
    echo -e "${GREEN}✓ Images rebuilt${NC}"
    echo ""
fi

# Start appropriate services
echo "🚀 Starting Arbihedron in $MODE mode..."
echo ""

case $MODE in
    dev)
        echo "Development mode:"
        echo "  - Hot reload enabled"
        echo "  - Debug port: 5678"
        echo "  - API: http://localhost:8000"
        echo ""
        docker-compose --profile dev up -d
        ;;
    gnn)
        echo "GNN mode:"
        echo "  - GNN engine enabled"
        echo "  - API: http://localhost:8001"
        echo ""
        docker-compose --profile gnn up -d arbihedron-gnn
        ;;
    monitoring)
        echo "Monitoring mode:"
        echo "  - Arbihedron: http://localhost:8000"
        echo "  - Prometheus: http://localhost:9090"
        echo "  - Grafana: http://localhost:3000 (admin/admin)"
        echo ""
        docker-compose --profile monitoring up -d
        ;;
    *)
        echo "Standard mode:"
        echo "  - API: http://localhost:8000"
        echo "  - Redis: localhost:6379"
        echo ""
        docker-compose up -d
        ;;
esac

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check service health
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo -e "${GREEN}✓ Arbihedron is running!${NC}"
echo ""
echo "Useful commands:"
echo "  docker-compose logs -f           # View logs"
echo "  docker-compose ps                # Check status"
echo "  docker-compose stop              # Stop services"
echo "  docker-compose down              # Stop and remove"
echo "  docker-compose down -v           # Stop and remove volumes"
echo ""
echo "View logs:"
echo "  docker-compose logs -f arbihedron"
echo ""
echo "For more information, see docs/INFRASTRUCTURE.md"
