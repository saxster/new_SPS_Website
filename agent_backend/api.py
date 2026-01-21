from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import sys
import os
import subprocess
import logging

# Add .agent to path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lib.risk_engine import RiskEngine, RiskAssessment
from skills.news_miner import NewsMiner

app = FastAPI(title="SPS Brain API", description="The Nervous System for SPS", version="1.0.0")

# --- Risk Engine Models & Endpoints ---

class RiskRequest(BaseModel):
    sector: str
    data: Dict[str, Any]

@app.post("/assess-risk", response_model=RiskAssessment)
async def assess_risk(request: RiskRequest):
    """
    Evaluates physical security posture against Indian Regulations and Best Practices.
    """
    print(f"--- [API] Hit /assess-risk with sector: {request.sector} ---")
    engine = RiskEngine()
    try:
        result = engine.assess(request.sector, request.data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Intelligence Models & Endpoints ---

class MineRequest(BaseModel):
    # Optional filters in the future
    source_filter: Optional[str] = None

@app.post("/intelligence/mine")
async def mine_news(request: MineRequest):
    """
    Triggers the NewsMiner to fetch latest signals from RSS feeds.
    """
    miner = NewsMiner()
    try:
        signals = miner.fetch_signals()
        return {"count": len(signals), "signals": signals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Mission Control (Subprocesses) ---

def run_script(script_path: str):
    """Helper to run a script and log output"""
    try:
        logging.info(f"Starting script: {script_path}")
        result = subprocess.run(["python3", script_path], capture_output=True, text=True)
        if result.returncode == 0:
            logging.info(f"Script {script_path} succeeded:\n{result.stdout}")
        else:
            logging.error(f"Script {script_path} failed:\n{result.stderr}")
    except Exception as e:
        logging.error(f"Failed to run script {script_path}: {e}")

@app.post("/mission/run")
async def run_mission(background_tasks: BackgroundTasks):
    """
    Triggers the full CCO mission (Content Creation) in the background.
    """
    script_path = os.path.join(os.path.dirname(__file__), "skills/run_mission.py")
    background_tasks.add_task(run_script, script_path)
    return {"status": "Mission started in background"}

@app.get("/system/status")
async def system_status():
    """
    Returns the current status of all background agents and recent logs.
    """
    try:
        # Read last 10 lines of api_debug.log if it exists
        logs = []
        if os.path.exists("api_debug.log"):
            with open("api_debug.log", "r") as f:
                logs = f.readlines()[-10:]
        
        return {
            "agents": {
                "CCO": "IDLE",
                "Miner": "IDLE",
                "Analyst": "IDLE",
                "RedTeam": "IDLE"
            },
            "recent_logs": logs,
            "uptime": "TODO"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "operational", "version": "1.0.0"}