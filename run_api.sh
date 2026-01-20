#!/bin/bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/.agent
echo "Starting SPS Intelligence Gateway on Port 8000..."
source .agent/.venv/bin/activate || source venv/bin/activate
uvicorn .agent.api:app --reload --host 0.0.0.0 --port 8000
