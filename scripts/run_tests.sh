#!/bin/bash
# Quick test runner for Arbihedron

echo "🔺 Running Arbihedron Tests..."
echo "================================"

# Run fast unit tests only
pytest tests/test_cache.py tests/test_error_handling.py tests/test_database.py -v --tb=short -k "not TestPerformanceMonitoring" 

echo ""
echo "================================"
echo "✅ Fast tests complete!"
echo ""
echo "To run ALL tests (slow, takes time):"
echo "  pytest -v"
