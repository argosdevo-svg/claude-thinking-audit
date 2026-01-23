#!/bin/bash
# Claude Thinking Audit - Setup Script

set -e

echo "=== Claude Thinking Budget Audit Tool ==="
echo ""

# Check Python version
python3 --version || { echo "Error: Python 3 required"; exit 1; }

# Create virtual environment
echo "[1/4] Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
echo "[2/4] Installing dependencies..."
pip install -q mitmproxy

# Create data directory
echo "[3/4] Creating data directory..."
mkdir -p ~/.claude-audit

# Generate CA certificate
echo "[4/4] Generating mitmproxy CA certificate..."
echo "You will need to trust this certificate in your system."
echo ""

echo "=== Setup Complete ==="
echo ""
echo "To start the audit proxy:"
echo "  source .venv/bin/activate"
echo "  mitmdump -s addon/thinking_audit.py -p 8888"
echo ""
echo "Then set your proxy to: http://localhost:8888"
echo ""
echo "Data will be stored in: ~/.claude-audit/thinking_audit.db"
