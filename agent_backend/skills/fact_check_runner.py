"""
Consensus fact-check runner for drafts.
Uses ensemble validation when multiple providers are configured.
"""

import os
import asyncio
from typing import Dict, Any, List, Optional

from lib.fact_check.adversarial_fact_checker import AdversarialFactChecker
from lib.fact_check.ensemble import EnsembleOrchestrator
from lib.fact_check.providers import ProviderFactory
from lib.fact_check.validators import ArticleInput
from lib.fact_check.config import ValidationConfig


class ConsensusFactChecker:
    def __init__(self):
        self.config = ValidationConfig.from_env(os.getenv("ENVIRONMENT", "production"))
        # Reuse parser and prompt builder from adversarial checker
        try:
            self._single = AdversarialFactChecker(config=self.config)
        except Exception:
            self._single = None

    def _build_prompt_fallback(self, article_input: ArticleInput) -> str:
        regs_formatted = "\n".join([f"- {reg}" for reg in article_input.proposed_regulations])
        return f"""
You are conducting a CRITICAL REVIEW of an article for the \"Bloomberg of Indian Security\" platform.
Be adversarial and thorough.

Title: {article_input.article_title}
Topic: {article_input.topic}
Summary: {article_input.article_summary}

PROPOSED INDIAN REGULATIONS:
{regs_formatted if regs_formatted else '(None proposed)'}

PROPOSED COST ESTIMATE (India):
{article_input.proposed_costs}

Return JSON:
{{
  "regulations_approved": [],
  "regulations_disputed": [],
  "regulations_missing": [],
  "factual_errors": [],
  "factual_warnings": [],
  "cost_valid": true,
  "cost_feedback": "",
  "confidence": 0,
  "critique": ""
}}
"""

    def _extract_json_robust(self, text: str) -> dict:
        import json, re
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            parts = text.split("```")
            if len(parts) >= 3:
                text = parts[1].strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
        text = text.replace("'", "\"").replace("True", "true").replace("False", "false").replace("None", "null")
        return json.loads(text)

    def _build_providers(self):
        providers = []
        if os.getenv("OPENAI_API_KEY"):
            providers.append(ProviderFactory.create_provider("openai", os.getenv("OPENAI_API_KEY")))
        if os.getenv("ANTHROPIC_API_KEY"):
            providers.append(ProviderFactory.create_provider("anthropic", os.getenv("ANTHROPIC_API_KEY")))
        if os.getenv("GOOGLE_API_KEY"):
            providers.append(ProviderFactory.create_provider("google", os.getenv("GOOGLE_API_KEY")))
        return providers

    def validate(self, article_input: ArticleInput) -> Dict[str, Any]:
        providers = self._build_providers()
        if not self._single and not providers:
            return {
                "consensus": {
                    "level": "skipped",
                    "score": 0.0,
                    "confidence_mean": 0.0,
                    "confidence_std": 0.0,
                    "models": [],
                    "total_cost_usd": 0.0
                },
                "synthesized": {},
                "dissent": {}
            }

        prompt = self._single._build_adversarial_prompt(article_input) if self._single else self._build_prompt_fallback(article_input)

        if len(providers) >= 2:
            orchestrator = EnsembleOrchestrator(
                providers=providers,
                config=self.config,
                json_parser=self._single._extract_json_robust if self._single else self._extract_json_robust
            )
            result = asyncio.run(
                orchestrator.validate_ensemble_async(
                    prompt=prompt,
                    article_input=article_input,
                    correlation_id="auto",
                    tier="full"
                )
            )
            return {
                "consensus": {
                    "level": result.consensus_level.value,
                    "score": result.consensus_score,
                    "confidence_mean": result.confidence_mean,
                    "confidence_std": result.confidence_std,
                    "models": result.models_used,
                    "total_cost_usd": result.total_cost_usd
                },
                "synthesized": result.synthesized_result.model_dump(),
                "dissent": result.get_dissenting_views()
            }

        # Fallback to single-model adversarial check
        if not self._single:
            return {
                "consensus": {
                    "level": "skipped",
                    "score": 0.0,
                    "confidence_mean": 0.0,
                    "confidence_std": 0.0,
                    "models": [],
                    "total_cost_usd": 0.0
                },
                "synthesized": {},
                "dissent": {}
            }

        single = self._single.validate_article(
            article_title=article_input.article_title,
            article_summary=article_input.article_summary,
            proposed_regulations=article_input.proposed_regulations,
            proposed_costs=article_input.proposed_costs,
            topic=article_input.topic
        )
        return {
            "consensus": {
                "level": "single",
                "score": single.confidence,
                "confidence_mean": single.confidence,
                "confidence_std": 0.0,
                "models": [single.llm_provider],
                "total_cost_usd": single.estimate_cost()
            },
            "synthesized": single.model_dump(),
            "dissent": {}
        }
