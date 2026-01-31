"""
Adversarial Council - Three-Agent Debate System

Three AI agents with different mandates debate every piece before publishing:
- Advocate: Pushes to publish (Speed bias) - evaluates timeliness and demand
- Skeptic: Challenges veracity (Accuracy bias) - evaluates sources and facts
- Guardian: Protects brand (Reputation bias) - evaluates tone and risk
"""

import os
import sys
from typing import List, Dict, Any, Optional

# Allow running from repo root without PYTHONPATH
AGENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from config.manager import config
from shared.logger import get_logger
from shared.models import ArticleDraft, AgentView, CouncilVerdict, CouncilThresholds
from skills.gemini_client import GeminiAgent

logger = get_logger("AdversarialCouncil")


class AdversarialCouncil:
    """
    Three-agent debate system for final publish approval.

    Each agent evaluates the draft from their specific perspective:
    - Advocate: Why should we publish? (timeliness, demand, uniqueness)
    - Skeptic: What's wrong with this? (sources, facts, claims)
    - Guardian: What's the risk? (brand, legal, ethical)
    """

    def __init__(self, client: Optional[GeminiAgent] = None):
        self.client = client or GeminiAgent()
        self.config = {
            "require_unanimous": config.get("council.require_unanimous", False),
            "min_advocate_score": config.get("council.min_advocate_score", 70),
            "min_skeptic_score": config.get("council.min_skeptic_score", 60),
            "min_guardian_score": config.get("council.min_guardian_score", 70),
            "kill_threshold": config.get("council.kill_threshold", 50),
        }

    def convene(
        self,
        draft: ArticleDraft,
        evidence: List[Dict],
        thresholds: Optional[CouncilThresholds] = None,
        gates: Optional[List[str]] = None,
    ) -> CouncilVerdict:
        """
        Run the 3-agent debate and return verdict.

        Args:
            draft: The article draft to evaluate
            evidence: List of evidence items used in the article
            thresholds: Optional profile-specific thresholds (overrides defaults)
            gates: Optional list of gate checks to apply (e.g., ['opinion_balance', 'expert_citation'])

        Returns:
            CouncilVerdict with decision (PUBLISH/REVISE/KILL)
        """
        logger.info("council_convening", title=draft.title[:50])

        # Phase 0: Run gate checks if specified
        gate_results = {}
        if gates:
            for gate in gates:
                if gate == "opinion_balance":
                    gate_results["opinion_balance"] = self.check_opinion_balance(draft)
                elif gate == "expert_citation":
                    gate_results["expert_citation"] = self.check_expert_citation(draft)

            # Log gate results
            for gate_name, result in gate_results.items():
                logger.info(
                    "gate_check",
                    gate=gate_name,
                    passed=result.get("passed", False),
                    score=result.get("balance_score")
                    or result.get("authoritative_count"),
                )

        # Phase 1: Each agent evaluates independently
        advocate_view = self._agent_advocate(draft, evidence)
        skeptic_view = self._agent_skeptic(draft, evidence)
        guardian_view = self._agent_guardian(draft, evidence)

        # Phase 2: Synthesis - resolve conflicts (with optional profile thresholds)
        verdict = self._synthesize_verdict(
            advocate_view, skeptic_view, guardian_view, thresholds=thresholds
        )

        # Phase 3: Apply gate check penalties
        if gate_results:
            verdict = self._apply_gate_penalties(verdict, gate_results)

        logger.info(
            "council_verdict",
            decision=verdict.decision,
            avg_score=verdict.average_score,
            advocate=verdict.advocate_score,
            skeptic=verdict.skeptic_score,
            guardian=verdict.guardian_score,
        )

        return verdict

    def _agent_advocate(self, draft: ArticleDraft, evidence: List[Dict]) -> AgentView:
        """
        Advocate Agent - Argues FOR publishing.
        Evaluates: timeliness, audience demand, competitive advantage, uniqueness.
        """
        prompt = f"""You are the ADVOCATE agent in a newsroom council. Your role is to argue FOR publishing this article.

ARTICLE TO EVALUATE:
Title: {draft.title}
Description: {draft.description}
Category: {draft.category}
Content Type: {draft.contentType}
Word Count: {draft.wordCount}
Sources: {len(draft.sources)} sources
Body Preview: {draft.body[:2000]}...

EVIDENCE USED: {len(evidence)} pieces

YOUR MANDATE: Evaluate why this should be published NOW. Consider:
1. TIMELINESS (0-100): Is this timely? Is there urgency?
2. AUDIENCE DEMAND (0-100): Will our security-focused audience want this?
3. COMPETITIVE ADVANTAGE (0-100): Does this give us an edge over competitors?
4. UNIQUENESS (0-100): Is this a fresh angle or perspective?

Return JSON:
{{
    "score": <overall score 0-100>,
    "reasoning": "<why this should be published>",
    "key_points": ["<strength 1>", "<strength 2>"],
    "concerns": ["<any concerns even as advocate>"],
    "recommendations": ["<what would make this even better>"]
}}"""

        try:
            result = self.client.generate_json(prompt)
            return AgentView(
                agent="advocate",
                score=int(result.get("score", 70)),
                reasoning=result.get("reasoning", "Advocate evaluation complete"),
                key_points=result.get("key_points", []),
                concerns=result.get("concerns", []),
                recommendations=result.get("recommendations", []),
            )
        except Exception as e:
            logger.error("advocate_agent_error", error=str(e))
            # Return neutral score on error
            return AgentView(
                agent="advocate",
                score=70,
                reasoning=f"Advocate evaluation failed: {str(e)}",
                key_points=[],
                concerns=["Evaluation error"],
                recommendations=[],
            )

    def _agent_skeptic(self, draft: ArticleDraft, evidence: List[Dict]) -> AgentView:
        """
        Skeptic Agent - Challenges veracity.
        Evaluates: source quality, claim support, potential bias, factual accuracy.
        """
        # Analyze source quality
        sources_info = []
        for s in draft.sources:
            sources_info.append(f"- {s.id}: {s.title} ({s.url or 'no URL'})")
        sources_text = (
            "\n".join(sources_info) if sources_info else "NO SOURCES PROVIDED"
        )

        prompt = f"""You are the SKEPTIC agent in a newsroom council. Your role is to CHALLENGE the veracity of this article.

ARTICLE TO EVALUATE:
Title: {draft.title}
Category: {draft.category}
Content Type: {draft.contentType}
Word Count: {draft.wordCount}

SOURCES:
{sources_text}

BODY:
{draft.body[:3000]}

YOUR MANDATE: Find weaknesses. Question everything. Consider:
1. SOURCE QUALITY (0-100): Are sources authoritative? Government/academic preferred.
2. CLAIM SUPPORT (0-100): Is every factual claim backed by evidence?
3. BIAS CHECK (0-100): Is there hidden bias or one-sided presentation?
4. FACTUAL ACCURACY (0-100): Are statistics, dates, names correct?

Look for:
- Uncited statistics or numbers
- Claims from single sources
- Outdated information
- Missing context
- Potential factual errors

Return JSON:
{{
    "score": <overall veracity score 0-100, BE HARSH>,
    "reasoning": "<your skeptical assessment>",
    "key_points": ["<verified strength>"],
    "concerns": ["<specific issue 1>", "<specific issue 2>"],
    "recommendations": ["<what must be fixed>"]
}}"""

        try:
            result = self.client.generate_json(prompt)
            return AgentView(
                agent="skeptic",
                score=int(result.get("score", 60)),
                reasoning=result.get("reasoning", "Skeptic evaluation complete"),
                key_points=result.get("key_points", []),
                concerns=result.get("concerns", []),
                recommendations=result.get("recommendations", []),
            )
        except Exception as e:
            logger.error("skeptic_agent_error", error=str(e))
            # Skeptic defaults to cautious on error
            return AgentView(
                agent="skeptic",
                score=50,
                reasoning=f"Skeptic evaluation failed: {str(e)}",
                key_points=[],
                concerns=["Evaluation error - recommend manual review"],
                recommendations=["Manual verification required"],
            )

    def _agent_guardian(self, draft: ArticleDraft, evidence: List[Dict]) -> AgentView:
        """
        Guardian Agent - Protects brand.
        Evaluates: tone alignment, audience fit, legal risk, ethical concerns, brand voice.
        """
        prompt = f"""You are the GUARDIAN agent in a newsroom council. Your role is to PROTECT the brand and audience.

ARTICLE TO EVALUATE:
Title: {draft.title}
Description: {draft.description}
Category: {draft.category}
Content Type: {draft.contentType}
Tags: {", ".join(draft.tags) if draft.tags else "None"}

BODY:
{draft.body[:3000]}

OUR BRAND: We are a professional security intelligence publication for India. Our audience includes:
- Corporate security directors
- Compliance officers
- Risk managers
- Security consultants
- Law enforcement professionals

OUR VOICE: Authoritative, balanced, professional, evidence-based.

YOUR MANDATE: Protect our reputation. Consider:
1. TONE ALIGNMENT (0-100): Does this match our professional voice?
2. AUDIENCE FIT (0-100): Will our audience find this valuable?
3. LEGAL RISK (0-100): Any defamation, copyright, or regulatory concerns?
4. ETHICAL CONCERNS (0-100): Any bias, sensationalism, or harmful content?
5. BRAND SAFETY (0-100): Could this damage our reputation?

Look for:
- Sensational language
- Unbalanced reporting
- Legal liability
- Ethical issues
- Off-brand content

Return JSON:
{{
    "score": <overall brand safety score 0-100>,
    "reasoning": "<your brand protection assessment>",
    "key_points": ["<brand alignment strength>"],
    "concerns": ["<brand risk 1>", "<brand risk 2>"],
    "recommendations": ["<what would protect the brand>"]
}}"""

        try:
            result = self.client.generate_json(prompt)
            return AgentView(
                agent="guardian",
                score=int(result.get("score", 70)),
                reasoning=result.get("reasoning", "Guardian evaluation complete"),
                key_points=result.get("key_points", []),
                concerns=result.get("concerns", []),
                recommendations=result.get("recommendations", []),
            )
        except Exception as e:
            logger.error("guardian_agent_error", error=str(e))
            return AgentView(
                agent="guardian",
                score=60,
                reasoning=f"Guardian evaluation failed: {str(e)}",
                key_points=[],
                concerns=["Evaluation error - recommend manual review"],
                recommendations=["Manual brand review required"],
            )

    def _synthesize_verdict(
        self,
        advocate: AgentView,
        skeptic: AgentView,
        guardian: AgentView,
        thresholds: Optional[CouncilThresholds] = None,
    ) -> CouncilVerdict:
        """
        Synthesize the three agent views into a final verdict.

        Args:
            advocate: Advocate agent's view
            skeptic: Skeptic agent's view
            guardian: Guardian agent's view
            thresholds: Optional profile-specific thresholds (overrides defaults)

        Decision Rules:
        - PUBLISH: All agents score >= their minimums, OR 2/3 score >= 80 with no strong objection
        - REVISE: Any agent raises fixable issues (score 50-70)
        - KILL: Skeptic finds factual problems (score < 50), OR Guardian finds brand risk (score < 50)
        """
        avg_score = (advocate.score + skeptic.score + guardian.score) / 3.0
        kill_threshold = self.config["kill_threshold"]

        # Use profile thresholds if provided, otherwise use defaults
        if thresholds:
            min_advocate = thresholds.min_advocate
            min_skeptic = thresholds.min_skeptic
            min_guardian = thresholds.min_guardian
            require_unanimous = thresholds.require_unanimous
        else:
            min_advocate = self.config["min_advocate_score"]
            min_skeptic = self.config["min_skeptic_score"]
            min_guardian = self.config["min_guardian_score"]
            require_unanimous = self.config["require_unanimous"]

        # Collect all concerns and recommendations
        all_concerns = advocate.concerns + skeptic.concerns + guardian.concerns
        all_recommendations = (
            advocate.recommendations
            + skeptic.recommendations
            + guardian.recommendations
        )

        # Identify dissenting views
        dissenting_views = []
        if advocate.score < 60 and skeptic.score >= 70:
            dissenting_views.append(
                f"Advocate skeptical (score: {advocate.score}): {advocate.reasoning[:100]}"
            )
        if skeptic.score >= 70 and guardian.score < 60:
            dissenting_views.append(
                f"Guardian concerned (score: {guardian.score}): {guardian.reasoning[:100]}"
            )

        # Decision logic
        decision = "PUBLISH"
        confidence = 0.5
        kill_reason = None
        required_fixes = []

        # KILL conditions
        if skeptic.score < kill_threshold:
            decision = "KILL"
            kill_reason = (
                f"Skeptic score too low ({skeptic.score}): {skeptic.reasoning}"
            )
            confidence = 0.9
        elif guardian.score < kill_threshold:
            decision = "KILL"
            kill_reason = (
                f"Guardian score too low ({guardian.score}): {guardian.reasoning}"
            )
            confidence = 0.9
        elif avg_score < kill_threshold:
            decision = "KILL"
            kill_reason = f"Average score below threshold ({avg_score:.1f})"
            confidence = 0.8

        # REVISE conditions (if not KILL)
        elif skeptic.score < min_skeptic:
            decision = "REVISE"
            required_fixes = skeptic.recommendations or skeptic.concerns
            confidence = 0.7
        elif guardian.score < min_guardian:
            decision = "REVISE"
            required_fixes = guardian.recommendations or guardian.concerns
            confidence = 0.7
        elif advocate.score < min_advocate:
            decision = "REVISE"
            required_fixes = advocate.recommendations or ["Improve timeliness or angle"]
            confidence = 0.6

        # PUBLISH conditions
        else:
            # Check if unanimous is required
            if require_unanimous:
                all_pass = (
                    advocate.score >= min_advocate
                    and skeptic.score >= min_skeptic
                    and guardian.score >= min_guardian
                )
                if all_pass:
                    decision = "PUBLISH"
                    confidence = min(0.95, avg_score / 100)
                else:
                    decision = "REVISE"
                    required_fixes = all_recommendations[:3]
                    confidence = 0.6
            else:
                # 2/3 majority with high scores is enough
                high_score_count = sum(
                    1
                    for s in [advocate.score, skeptic.score, guardian.score]
                    if s >= 80
                )
                if high_score_count >= 2:
                    decision = "PUBLISH"
                    confidence = min(0.9, avg_score / 100)
                elif avg_score >= 70:
                    decision = "PUBLISH"
                    confidence = min(0.8, avg_score / 100)
                else:
                    decision = "REVISE"
                    required_fixes = all_recommendations[:3]
                    confidence = 0.6

        # Build debate summary
        debate_summary = (
            f"Advocate ({advocate.score}): {advocate.reasoning[:80]}... "
            f"Skeptic ({skeptic.score}): {skeptic.reasoning[:80]}... "
            f"Guardian ({guardian.score}): {guardian.reasoning[:80]}..."
        )

        return CouncilVerdict(
            decision=decision,
            confidence=round(confidence, 3),
            advocate_score=advocate.score,
            skeptic_score=skeptic.score,
            guardian_score=guardian.score,
            average_score=round(avg_score, 2),
            dissenting_views=dissenting_views,
            required_fixes=required_fixes,
            kill_reason=kill_reason,
            debate_summary=debate_summary,
        )

    def check_opinion_balance(self, draft: ArticleDraft) -> Dict[str, Any]:
        """
        Check if content presents balanced viewpoints (for views/analysis profile).

        Detects one-sided or biased content by analyzing:
        - Presence of contrasting viewpoints
        - Use of balanced language vs. absolute statements
        - Multiple perspectives represented

        Args:
            draft: The article draft to check

        Returns:
            Dict with: passed (bool), balance_score (int 0-100), issues (list)
        """
        body_lower = draft.body.lower()
        title_lower = draft.title.lower()

        issues = []
        balance_score = 70  # Start with a moderate score

        # Check for absolute/biased language patterns
        absolute_patterns = [
            "clearly superior",
            "the best",
            "the only",
            "everyone agrees",
            "no one should",
            "all experts",
            "without doubt",
            "no downsides",
            "no alternative",
            "inferior in every way",
            "competitors are",
            "obviously",
            "undoubtedly",
        ]

        absolute_count = sum(
            1 for pattern in absolute_patterns if pattern in body_lower
        )
        if absolute_count > 0:
            penalty = min(40, absolute_count * 10)
            balance_score -= penalty
            issues.append(f"Found {absolute_count} absolute/biased language patterns")

        # Check for balanced language patterns
        balanced_patterns = [
            "however",
            "on the other hand",
            "alternatively",
            "depends on",
            "trade-off",
            "pros and cons",
            "compared to",
            "both have",
            "different use cases",
            "considerations include",
            "challenges include",
            "limitations",
        ]

        balanced_count = sum(
            1 for pattern in balanced_patterns if pattern in body_lower
        )
        if balanced_count >= 2:
            bonus = min(20, balanced_count * 5)
            balance_score += bonus
        elif balanced_count == 0:
            balance_score -= 15
            issues.append("No balanced language patterns found")

        # Check for promotional title
        promotional_title_patterns = [
            "why .* is the best",
            "the best .*",
            "superior",
            "ultimate",
        ]
        import re

        for pattern in promotional_title_patterns:
            if re.search(pattern, title_lower):
                balance_score -= 10
                issues.append("Title appears promotional")
                break

        # Check source diversity (single vendor source is a red flag)
        if len(draft.sources) == 1:
            source_url = draft.sources[0].url.lower() if draft.sources[0].url else ""
            if "vendor" in source_url or ".com/blog" in source_url:
                balance_score -= 15
                issues.append("Single vendor/promotional source")

        # Ensure score stays in bounds
        balance_score = max(0, min(100, balance_score))

        passed = balance_score >= 50

        logger.debug(
            "opinion_balance_check",
            title=draft.title[:30],
            balance_score=balance_score,
            passed=passed,
        )

        return {
            "passed": passed,
            "balance_score": balance_score,
            "issues": issues,
        }

    def check_expert_citation(self, draft: ArticleDraft) -> Dict[str, Any]:
        """
        Check if content has authoritative citations (for research/guide profile).

        Verifies that guides and research content cite:
        - Government/regulatory sources
        - Academic/research institutions
        - Recognized standards bodies

        Args:
            draft: The article draft to check

        Returns:
            Dict with: passed (bool), authoritative_count (int), issues (list)
        """
        issues = []
        authoritative_count = 0

        # Define authoritative domain patterns
        authoritative_patterns = [
            # Government (India)
            ".gov.in",
            "pib.gov.in",
            "mha.gov.in",
            "rbi.org.in",
            "cert-in.org.in",
            "meity.gov.in",
            "sebi.gov.in",
            # Government (International)
            ".gov",
            ".gov.uk",
            # Academic
            ".edu",
            ".ac.in",
            "iit",
            "iisc",
            "university",
            # Standards bodies
            "iso.org",
            "nist.gov",
            "ieee.org",
            # Recognized research
            "gartner.com",
            "forrester.com",
        ]

        for source in draft.sources:
            url = source.url.lower() if source.url else ""
            title = source.title.lower() if source.title else ""

            is_authoritative = any(
                pattern in url or pattern in title for pattern in authoritative_patterns
            )

            if is_authoritative:
                authoritative_count += 1

        # For guides, require at least 2 authoritative sources
        min_required = 2
        passed = authoritative_count >= min_required

        if not passed:
            issues.append(
                f"Only {authoritative_count} authoritative sources (need {min_required})"
            )

        # Check for vendor-only sources
        vendor_patterns = ["vendor", "/blog", "product", "solution"]
        vendor_count = sum(
            1
            for source in draft.sources
            if any(
                p in (source.url.lower() if source.url else "") for p in vendor_patterns
            )
        )

        if vendor_count > 0 and authoritative_count == 0:
            issues.append("Content relies only on vendor/promotional sources")

        logger.debug(
            "expert_citation_check",
            title=draft.title[:30],
            authoritative_count=authoritative_count,
            passed=passed,
        )

        return {
            "passed": passed,
            "authoritative_count": authoritative_count,
            "issues": issues,
            "min_required": min_required,
        }

    def _apply_gate_penalties(
        self, verdict: CouncilVerdict, gate_results: Dict[str, Dict]
    ) -> CouncilVerdict:
        """
        Apply penalties to verdict based on failed gate checks.

        Args:
            verdict: The current verdict
            gate_results: Results from gate checks

        Returns:
            Modified verdict with gate penalties applied
        """
        # Collect issues from failed gates
        failed_gates = []
        gate_issues = []

        for gate_name, result in gate_results.items():
            if not result.get("passed", True):
                failed_gates.append(gate_name)
                gate_issues.extend(result.get("issues", []))

        # If any critical gates failed, downgrade decision
        if failed_gates:
            if verdict.decision == "PUBLISH":
                # Downgrade PUBLISH to REVISE if gates failed
                new_required_fixes = list(verdict.required_fixes) + gate_issues
                return CouncilVerdict(
                    decision="REVISE",
                    confidence=verdict.confidence * 0.8,
                    advocate_score=verdict.advocate_score,
                    skeptic_score=verdict.skeptic_score,
                    guardian_score=verdict.guardian_score,
                    average_score=verdict.average_score,
                    dissenting_views=verdict.dissenting_views,
                    required_fixes=new_required_fixes,
                    kill_reason=verdict.kill_reason,
                    debate_summary=verdict.debate_summary
                    + f" [Gates failed: {', '.join(failed_gates)}]",
                )

        return verdict


if __name__ == "__main__":
    # Quick test
    from shared.models import ArticleDraft

    council = AdversarialCouncil()

    test_draft = ArticleDraft(
        title="Test Security Article",
        description="A test article about security compliance.",
        category="Security",
        contentType="Guide",
        body="# Test\n\nThis is test content.",
        wordCount=500,
        sources=[],
    )

    verdict = council.convene(test_draft, [])
    print(f"Decision: {verdict.decision}")
    print(
        f"Scores: A={verdict.advocate_score}, S={verdict.skeptic_score}, G={verdict.guardian_score}"
    )
    print(f"Average: {verdict.average_score}")
