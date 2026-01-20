#!/bin/bash
# Autonomous Newsroom Orchestrator 🤖
# Add to crontab: 0 4 * * * /path/to/repo/run_newsroom.sh

cd "$(dirname "$0")" || exit
# Assumes a unified venv in .venv or similar. Adjust as needed.
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".agent/venv" ]; then
    source .agent/venv/bin/activate
else
    echo "⚠️  No venv found. Please run 'python3 -m venv venv && pip install -r requirements.txt'"
    exit 1
fi

# Ensure .agent packages are importable
export PYTHONPATH=$PYTHONPATH:$(pwd)/.agent

echo "=================================================="
echo "📰 Newsroom Start: $(date)"
echo "=================================================="

echo "🧠 Running CCO-directed Mission..."
python .agent/skills/run_mission.py

echo "=================================================="
echo "🏁 Newsroom Finished: $(date)"
echo "=================================================="
