#!/bin/bash

# SPS Autonomous Intelligence Runner
# ----------------------------------
# 1. Activates Python environment
# 2. Runs the Consensus Engine (Miner -> Analyst -> Red Team -> Strategist)
# 3. Logs output to intelligence.log

# Define paths
PROJECT_ROOT=$(pwd)
LOG_FILE="$PROJECT_ROOT/intelligence.log"
PYTHON_SCRIPT="$PROJECT_ROOT/.agent/skills/consensus_engine.py"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "--- STARTING INTELLIGENCE CYCLE ---"

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    log "ERROR: Python script not found at $PYTHON_SCRIPT"
    exit 1
fi

# Run the engine
log "Running Consensus Engine..."
python3 "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1

# Check exit status
if [ $? -eq 0 ]; then
    log "SUCCESS: Intelligence cycle completed."
else
    log "FAILURE: Consensus Engine encountered an error."
    exit 1
fi

log "--- CYCLE COMPLETE ---"