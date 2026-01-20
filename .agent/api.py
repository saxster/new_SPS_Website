from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from skills.ask_expert import oracle
from shared.logger import get_logger
from lib.risk_engine import risk_engine, RiskAssessment
from lib.simulation_engine import sim_engine, SimulationLog
import uvicorn
import os

logger = get_logger("API_Gateway")

app = FastAPI(title="SPS Intelligence API", version="1.0.0")

class QueryRequest(BaseModel):
    question: str
    user_context: dict = {} # For future use (location, sector)

class QueryResponse(BaseModel):
    answer: str
    status: str = "success"

class RiskRequest(BaseModel):
    sector: str
    data: dict

@app.get("/health")
def health_check():
    return {"status": "online", "system": "SPS_COMMANDER_ALPHA"}

@app.post("/ask", response_model=QueryResponse)
def ask_commander(request: QueryRequest, x_sps_auth: str = Header(None)):
    """
    Direct line to the Colonel.
    Protected by Basic Auth for now (Internal usage).
    """
    # Simple auth check (in production, use Clerk token verification)
    # if x_sps_auth != os.getenv("SPS_INTERNAL_KEY", "sps-secret"):
    #    raise HTTPException(status_code=401, detail="Unauthorized channel")

    logger.info("api_query_received", question=request.question[:50], context=request.user_context)
    
    # In the future, 'context_docs' will come from a vector DB search here.
    # For now, we pass empty context, letting the LLM use its internal knowledge + personality.
    answer = oracle.query(request.question, context_docs=[], user_context=request.user_context)
    
    return QueryResponse(answer=answer)

@app.post("/assess-risk", response_model=RiskAssessment)
def assess_risk(request: RiskRequest, x_sps_auth: str = Header(None)):
    """
    Deep Sector-Specific Risk Analysis.
    Returns calculated score, critical failures, and recommendations.
    """
    logger.info("risk_assessment_req", sector=request.sector)
    try:
        assessment = risk_engine.assess(request.sector, request.data)
        return assessment
    except Exception as e:
        logger.error("risk_calc_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Risk calculation engine failure.")

@app.post("/simulation/complete")
def complete_simulation(log: SimulationLog, x_sps_auth: str = Header(None)):
    """
    Logs simulation telemetry and generates an AI After Action Report.
    """
    sim_engine.log_run(log)
    aar = sim_engine.generate_aar(log)
    return {"aar": aar}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
