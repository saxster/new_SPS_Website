from typing import List, Dict
from pydantic import BaseModel
from shared.logger import get_logger
from skills.ask_expert import oracle
import json
import os

logger = get_logger("SimEngine")

class SimulationLog(BaseModel):
    scenario_id: str
    sector: str
    path: List[str] # List of Choice IDs made
    outcome: str
    final_state_text: str

class SimulationEngine:
    """
    Handles Crisis Simulation logic:
    1. Logs user performance (telemetry).
    2. Generates AI 'After Action Reports' (AAR) using RAG.
    """
    
    def __init__(self, log_dir=".agent/data/sim_logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
    
    def log_run(self, log: SimulationLog):
        """Saves anonymized run data."""
        try:
            # Simple append to JSONL for now
            with open(os.path.join(self.log_dir, "runs.jsonl"), "a") as f:
                f.write(log.model_dump_json() + "\n")
            logger.info("sim_run_logged", scenario=log.scenario_id, outcome=log.outcome)
        except Exception as e:
            logger.error("sim_log_failed", error=str(e))

    def generate_aar(self, log: SimulationLog) -> str:
        """
        Uses the ExpertOracle to generate a Consulting-Grade Debrief.
        It critiques the user's specific decisions against Indian Law.
        """
        
        # Construct the narrative for the AI
        prompt = f"""
        ACT AS: The Colonel (SPS Chief Security Officer).
        TASK: Generate a strict 'After Action Report' (AAR) for a training simulation.
        
        SCENARIO: {log.scenario_id} ({log.sector} Sector)
        OUTCOME: {log.outcome.upper()}
        FINAL SITUATION: "{log.final_state_text}"
        
        USER DECISIONS PATH (IDs): {', '.join(log.path)}
        
        REQUIREMENTS:
        1. Be brutal but educational. This is a life-safety drill.
        2. If they failed due to fire safety (NBC 2016) or guard protocols (PSARA), CITE THE LAW.
        3. Explain strictly WHY their specific choices led to this outcome.
        4. Keep it under 150 words. Format as: "CRITIQUE:" followed by "REGULATORY NOTE:".
        """
        
        # We assume the Oracle has the RAG context loaded (PSARA/NBC)
        # We can pass empty context_docs here and let the Oracle retrieve relevant laws dynamically if we upgraded query(),
        # but for now, the Oracle's internal knowledge + personality is strong.
        # Ideally, we would fetch relevant laws based on the scenario tags.
        
        try:
            aar = oracle.agent.generate(prompt)
            return aar
        except Exception as e:
            logger.error("aar_gen_failed", error=str(e))
            return "AAR Generation Failed. Protocol reference unavailable."

sim_engine = SimulationEngine()
