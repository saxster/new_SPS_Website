#!/bin/bash
# Setup the Agent Intelligence Environment

set -e

echo "🧠 Initializing Antigravity Agent Intelligence..."

# Create venv if not exists
if [ ! -d ".agent/venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .agent/venv
fi

# Activate
source .agent/venv/bin/activate

# Install dependencies
echo "⬇️  Installing dependencies..."
pip install --upgrade pip
pip install -r .agent/skills/fact_checker/requirements.txt
pip install beautifulsoup4 structlog watchdog # Explicitly ensure structlog, bs4, watchdog

echo "✅ Agent Intelligence Ready."
echo "   Run skills with: source .agent/venv/bin/activate && python .agent/skills/..."
