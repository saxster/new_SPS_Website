from fastapi import (
    FastAPI,
    HTTPException,
    BackgroundTasks,
    WebSocket,
    WebSocketDisconnect,
    Header,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import sys
import os
import subprocess
import logging
import secrets

# Add .agent to path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lib.risk_engine import RiskEngine, RiskAssessment
from skills.news_miner import NewsMiner
from lib.signal_tower import signal_tower
from lib.knowledge_vault import vault

app = FastAPI(
    title="SPS Brain API", description="The Nervous System for SPS", version="2.0.0"
)

# ==========================================
# SECURITY CONFIGURATION
# ==========================================

# Load API key from environment
API_KEY = os.getenv("SPS_API_KEY")
if not API_KEY:
    # Generate one on first run if not set
    API_KEY = secrets.token_urlsafe(32)
    print("=" * 80)
    print("⚠️  WARNING: SPS_API_KEY not found in environment!")
    print("⚠️  GENERATED NEW API KEY (save this immediately!):")
    print(f"⚠️  SPS_API_KEY={API_KEY}")
    print("=" * 80)
    print("⚠️  Add this to your .env file:")
    print(f"⚠️  echo 'SPS_API_KEY={API_KEY}' >> .env")
    print("=" * 80)

# CORS Configuration - Only allow requests from your domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://sukhi.in",
        "https://www.sukhi.in",
        "https://automator.sukhi.in",  # For n8n workflows
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# API Key Authentication Dependency
async def verify_api_key(
    x_api_key: str = Header(..., description="API Key for authentication"),
):
    """
    Dependency that verifies the API key in the X-API-Key header.
    Protects all endpoints that use this dependency.
    """
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API key. Include 'X-API-Key' header.",
        )
    return x_api_key


# ==========================================
# PUBLIC ENDPOINTS (No Auth Required)
# ==========================================


@app.get("/")
async def root():
    """Root endpoint - shows API is alive"""
    return {
        "message": "SPS Brain API",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint - no auth required for monitoring"""
    return {"status": "operational", "version": "2.0.0"}


# ==========================================
# PROTECTED ENDPOINTS (Require API Key)
# ==========================================

# --- Risk Engine Models & Endpoints ---


class RiskRequest(BaseModel):
    sector: str
    data: Dict[str, Any]


@app.post(
    "/assess-risk",
    response_model=RiskAssessment,
    dependencies=[Depends(verify_api_key)],
)
async def assess_risk(request: RiskRequest):
    """
    Evaluates physical security posture against Indian Regulations and Best Practices.

    **Requires Authentication**: Include 'X-API-Key' header
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


@app.post("/intelligence/mine", dependencies=[Depends(verify_api_key)])
async def mine_news(request: MineRequest):
    """
    Triggers the NewsMiner to fetch latest signals from RSS feeds.

    **Requires Authentication**: Include 'X-API-Key' header
    """
    miner = NewsMiner()
    try:
        signals = miner.fetch_signals()
        return {"count": len(signals), "signals": signals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Mission Control (Subprocesses) ---


class MissionRequest(BaseModel):
    """Request body for /mission/run endpoint."""

    mode: str = "auto"  # "auto" or "manual"
    pillars: Optional[List[str]] = None  # Filter by content pillar(s)
    max_articles: int = 3  # Maximum articles to generate


def run_script(script_path: str, args: List[str] = None):
    """Helper to run a script and log output"""
    try:
        cmd = ["python3", script_path]
        if args:
            cmd.extend(args)
        logging.info(f"Starting script: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logging.info(f"Script {script_path} succeeded:\n{result.stdout}")
        else:
            logging.error(f"Script {script_path} failed:\n{result.stderr}")
    except Exception as e:
        logging.error(f"Failed to run script {script_path}: {e}")


@app.post("/mission/run", dependencies=[Depends(verify_api_key)])
async def run_mission(
    background_tasks: BackgroundTasks, request: MissionRequest = MissionRequest()
):
    """
    Triggers the full CCO mission (Content Creation) in the background.

    **Requires Authentication**: Include 'X-API-Key' header

    **Request Body (optional):**
    - mode: "auto" (default) or "manual"
    - pillars: List of content pillars to focus on (e.g., ["scam_watch", "economic_security"])
    - max_articles: Maximum number of articles to generate (default: 3)

    **Available Pillars:**
    - scam_watch: Real-time fraud alerts, prevention
    - economic_security: Markets, investment fraud, corporate crime
    - personal_security: Home, travel, digital safety
    - senior_safety: Elder-specific threats and protection
    - business_security: Practical SMB security guides
    - sector_intelligence: Deep dives by industry
    - product_reviews: Security products evaluated
    """
    script_path = os.path.join(os.path.dirname(__file__), "skills/run_mission.py")

    # Build command-line arguments
    args = []
    if request.pillars:
        args.extend(["--pillars", ",".join(request.pillars)])
    if request.max_articles:
        args.extend(["--max-articles", str(request.max_articles)])

    background_tasks.add_task(run_script, script_path, args)
    return {
        "status": "Mission started in background",
        "pillars": request.pillars,
        "max_articles": request.max_articles,
    }


@app.get("/system/status", dependencies=[Depends(verify_api_key)])
async def system_status():
    """
    Returns the current status of all background agents and recent logs.

    **Requires Authentication**: Include 'X-API-Key' header
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
                "RedTeam": "IDLE",
            },
            "recent_logs": logs,
            "uptime": "TODO",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- REAL-TIME SIGNAL TOWER (WebSockets) ---


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time alerts.

    Note: WebSocket authentication should be handled via query params or initial message.
    For now, this is open for internal use only (not exposed to public).
    """
    await signal_tower.connect(websocket)
    try:
        while True:
            # Keep connection open, wait for messages (optional)
            # In our case, we mostly push TO the client, not read FROM it
            data = await websocket.receive_text()
            # Echo for health check
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        signal_tower.disconnect(websocket)


class BroadcastRequest(BaseModel):
    title: str
    severity: str
    message: str


@app.post("/internal/broadcast", dependencies=[Depends(verify_api_key)])
async def broadcast_alert(request: BroadcastRequest):
    """
    Called by n8n to push an alert to all connected browsers.

    **Requires Authentication**: Include 'X-API-Key' header
    """
    await signal_tower.broadcast(request.dict())
    return {"status": "broadcast_sent"}


# --- KNOWLEDGE VAULT (RAG) ---


class IngestRequest(BaseModel):
    id: str
    title: str
    text: str
    meta: Dict[str, Any]


@app.post("/knowledge/ingest", dependencies=[Depends(verify_api_key)])
async def ingest_intel(request: IngestRequest):
    """
    Called by n8n/Consensus Engine to save a report to the Vector DB.

    **Requires Authentication**: Include 'X-API-Key' header
    """
    vault.ingest(request.id, request.title, request.text, request.meta)
    return {"status": "ingested"}


class QueryRequest(BaseModel):
    query: str


@app.post("/knowledge/query", dependencies=[Depends(verify_api_key)])
async def query_intel(request: QueryRequest):
    """
    Called by the 'Ask Commander' widget.

    **Requires Authentication**: Include 'X-API-Key' header
    """
    answer = vault.ask(request.query)
    return {"answer": answer}


# --- AUTO-PUBLISHED ARTICLES API ---

from skills.content_brain import ContentBrain


@app.get("/articles/{slug}")
async def get_article(slug: str):
    """
    Fetch a published article by slug.

    This endpoint is PUBLIC for website SSR.
    """
    brain = ContentBrain()
    article = brain.get_published_article(slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@app.get("/articles")
async def list_articles(limit: int = 20, offset: int = 0):
    """
    List published articles with pagination.

    This endpoint is PUBLIC for website SSR.

    Query params:
    - limit: Maximum number of articles (default 20)
    - offset: Number of articles to skip (default 0)
    """
    brain = ContentBrain()
    articles = brain.get_published_articles(limit=limit, offset=offset)
    return {"articles": articles, "count": len(articles)}
