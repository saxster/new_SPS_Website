"""
FactChecker 2.0 (CoVe) - Powered by Gemini ♊
"""

from typing import List, Dict, Optional
import os
import json
import logging
from pydantic import BaseModel
from dotenv import load_dotenv
from skills.gemini_client import GeminiAgent

load_dotenv()

logger = logging.getLogger("FactChecker2")

class VerificationQuestion(BaseModel):
    question: str
    context_needed: str

class VerificationPlan(BaseModel):
    questions: List[VerificationQuestion]

class FactCheckerCoVe:
    def __init__(self, api_key: str):
        self.agent = GeminiAgent()

    def check_article(self, content: str) -> Dict:
        """
        Orchestrates the CoVe process.
        """
        logger.info("🧠 starting Chain of Verification (Gemini)...")
        
        # Step 1: Baseline Analysis (Identify Claims)
        claims = self._identify_claims(content)
        logger.info(f"   Identified {len(claims)} verify-worthy claims.")
        
        # Step 2: Plan Verifications
        plan = self._plan_verifications(claims)
        logger.info(f"   Generated {len(plan.questions)} verification questions.")
        
        # Step 3: Execute Verifications (Simulated Search or Internal Knowledge)
        evidence = self._execute_verifications(plan)
        
        # Step 4: Final Verdict
        verdict = self._generate_verdict(content, evidence)
        return verdict

    def _identify_claims(self, content: str) -> List[str]:
        prompt = f"""
        Extract non-obvious, verifiable factual claims from this text. 
        Exclude opinions or general knowledge.
        Text: {content[:4000]}
        
        Return as JSON list of strings.
        """
        return self.agent.generate_json(prompt) or []

    def _plan_verifications(self, claims: List[str]) -> VerificationPlan:
        prompt = f"""
        For these claims, generate verification questions to check their truthfulness.
        Claims: {json.dumps(claims)}
        
        Return JSON format: {{ "questions": [ {{ "question": "...", "context_needed": "..." }} ] }}
        """
        data = self.agent.generate_json(prompt)
        try:
            return VerificationPlan.model_validate(data)
        except:
            return VerificationPlan(questions=[])

    def _execute_verifications(self, plan: VerificationPlan) -> List[Dict]:
        results = []
        for q in plan.questions:
            prompt = f"""
            Verification Question: {q.question}
            Context: {q.context_needed}
            
            Answer this strictly based on established facts. If you don't know, say "UNCERTAIN".
            """
            answer = self.agent.generate(prompt)
            results.append({
                "question": q.question,
                "answer": answer
            })
        return results

    def _generate_verdict(self, content: str, evidence: List[Dict]) -> Dict:
        evidence_text = "\n".join([f"Q: {e['question']}\nA: {e['answer']}" for e in evidence])
        
        prompt = f"""
        You are a strict Compliance Officer.
        Original Text: {content[:4000]}
        
        Verification Evidence:
        {evidence_text}
        
        Task: 
        1. Identify any contradictions between Text and Evidence.
        2. Assign a Truth Score (0-100).
        3. Determine output: PUBLISH or REJECT.
        
        Return JSON: {{ "score": 90, "decision": "PUBLISH", "reasoning": "..." }}
        """
        return self.agent.generate_json(prompt)

# Wrapper to replace old validator logic if needed
def validate_content(content: str):
    # API key check is internal to GeminiAgent now
    checker = FactCheckerCoVe("dummy")
    return checker.check_article(content)
