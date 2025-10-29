# Multi-stage build for Arbihedron
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 arbihedron && \
    chown -R arbihedron:arbihedron /app

# ============================================
# Development stage
# ============================================
FROM base as development

# Copy requirements first for better caching
COPY --chown=arbihedron:arbihedron requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install development tools
RUN pip install --no-cache-dir \
    pytest>=7.4.0 \
    pytest-asyncio>=0.21.0 \
    pytest-cov>=4.1.0 \
    pytest-mock>=3.11.0 \
    black>=23.0.0 \
    flake8>=6.0.0 \
    mypy>=1.5.0 \
    ipython>=8.14.0

USER arbihedron

# Copy application code
COPY --chown=arbihedron:arbihedron . .

# Create necessary directories
RUN mkdir -p data logs models exports

CMD ["python", "main.py"]

# ============================================
# Production stage (optimized)
# ============================================
FROM base as production

# Copy only requirements first
COPY --chown=arbihedron:arbihedron requirements.txt .

# Install only production dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn>=21.2.0

USER arbihedron

# Copy application code
COPY --chown=arbihedron:arbihedron *.py ./
COPY --chown=arbihedron:arbihedron docs/ ./docs/
COPY --chown=arbihedron:arbihedron models/ ./models/

# Create necessary directories
RUN mkdir -p data logs exports

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["python", "main.py"]

# ============================================
# Testing stage
# ============================================
FROM development as testing

# Run tests during build
RUN pytest tests/ -v --cov=. --cov-report=term-missing || true

# ============================================
# GNN-enabled stage
# ============================================
FROM base as gnn

# Install additional system dependencies for PyTorch
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=arbihedron:arbihedron requirements.txt .

# Install with GNN dependencies
RUN pip install --no-cache-dir -r requirements.txt

USER arbihedron

COPY --chown=arbihedron:arbihedron . .

RUN mkdir -p data logs models exports

ENV USE_GNN_ENGINE=true

CMD ["python", "main.py"]
