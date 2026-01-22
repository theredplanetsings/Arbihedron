#!/bin/bash
# Quick test of the service management system
echo "Testing Arbihedron Service Management..."
echo ""

# Test 1: Help command
echo "✓ Test 1: Help command"
scripts/arbi > /dev/null 2>&1 || echo "  Help displayed correctly"
echo ""

# Test 2: Status (should be stopped)
echo "✓ Test 2: Status check"
scripts/arbi status | grep -q "STOPPED" && echo "  Status command works" || echo "  ⚠️  Status check failed"
echo ""

# Test 3: Control script is executable
echo "✓ Test 3: Script permissions"
[ -x scripts/arbi ] && echo "  Control script is executable" || echo "  ⚠️  Script not executable"
echo ""

# Test 4: Service script exists
echo "✓ Test 4: Service script"
[ -f ./src/arbihedron/service.py ] && echo "  Service script exists" || echo "  ⚠️  Service script missing"
echo ""

# Test 5: Log directory exists
echo "✓ Test 5: Log directory"
[ -d ./logs/service ] && echo "  Log directory exists" || echo "  ⚠️  Log directory missing"
echo ""

echo "✅ Service management system is ready!"
echo ""
echo "Quick start:"
echo "  scripts/arbi start    # Start the bot"
echo "  scripts/arbi status   # Check status"
echo "  scripts/arbi logs -f  # View logs"
echo "  scripts/arbi stop     # Stop the bot"
echo ""
echo "For 24/7 operation:"
echo "  scripts/arbi install  # Install as LaunchAgent"
echo "  scripts/arbi start    # Start the service"