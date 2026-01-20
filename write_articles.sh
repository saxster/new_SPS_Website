#!/bin/bash
# write_articles.sh 🖋️
# The "Midnight Runner" Logic
# 1. Ask CCO what to do.
# 2. Execute.

cd "$(dirname "$0")" || exit
source .agent/venv/bin/activate

echo "[$(date)] 👔 Chief Content Officer stepping in..."

# We use a python one-liner to get the action from CCO
# This is a simple implementation. Ideally we'd have a orchestrator.py
# But for now, let's just run the CCO script which prints strategy.

# Actually, let's create a python runner `run_mission.py` that uses the CCO class directly
# because parsing bash output is brittle.

python .agent/skills/run_mission.py
