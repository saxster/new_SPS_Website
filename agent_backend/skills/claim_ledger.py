"""
Claim ledger builder.
Extracts verifiable claims, maps citations, checks cross-source agreement,
and detects internal contradictions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from config.manager import config
from shared.logger import get_logger

logger = get_logger("ClaimLedger")


@dataclass
class Claim:
    id: str
    text: str
    claim_type: str
    citations: List[str]
    sources: List[str]
    domains: List[str]
    numbers: List[str]
    issues: List[str]


class ClaimLedger:
    def __init__(self):
        self.require_citations = config.get("claims.require_citations", True)
        self.require_multi_source_numeric = config.get("claims.require_multi_source_numeric", True)
        self.min_sources_numeric = config.get("claims.min_sources_numeric", 2)
        self.min_domains_numeric = config.get("claims.min_domains_numeric", 2)
        self.min_sources_regulation = config.get("claims.min_sources_regulation", 1)
        self.trigger_words = set(config.get("claims.trigger_words", [
            "must", "shall", "required", "requires", "mandate", "mandatory",
            "prohibit", "ban", "compliance", "liable", "penalty"
        ]))
        self.max_claims = config.get("claims.max_claims", 120)

    def build(self, draft: Dict, evidence: Optional[List[Dict]] = None) -> Dict:
        body = draft.get("body", "") or ""
        regulations = draft.get("regulations", []) or []

        evidence_map = {e.get("id"): e for e in (evidence or [])}

        paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
        paragraph_map = []
        claims: List[Claim] = []
        issues: List[str] = []

        for idx, para in enumerate(paragraphs, 1):
            citations = self._extract_citations(para)
            para_claims = []

            for sentence in self._split_sentences(para):
                claim_type, numbers = self._classify_claim(sentence, regulations)
                if not claim_type:
                    continue
                claim_id = f"C{len(claims)+1:03d}"
                para_claims.append(claim_id)
                sources, domains = self._resolve_sources(citations, evidence_map)
                claim_issues = []
                if self.require_citations and not citations:
                    claim_issues.append("Claim lacks citation.")
                if claim_type == "numeric" and self.require_multi_source_numeric:
                    if len(set(sources)) < self.min_sources_numeric:
                        claim_issues.append("Numeric claim lacks multi-source agreement.")
                    if len(set(domains)) < self.min_domains_numeric:
                        claim_issues.append("Numeric claim lacks domain diversity.")
                if claim_type == "regulatory" and self.require_citations:
                    if len(set(sources)) < self.min_sources_regulation:
                        claim_issues.append("Regulatory claim lacks required sources.")

                claims.append(Claim(
                    id=claim_id,
                    text=sentence.strip(),
                    claim_type=claim_type,
                    citations=citations,
                    sources=sources,
                    domains=domains,
                    numbers=numbers,
                    issues=claim_issues
                ))

                if len(claims) >= self.max_claims:
                    break
            if len(claims) >= self.max_claims:
                break
            paragraph_map.append({
                "paragraph": idx,
                "citations": citations,
                "claims": para_claims
            })

        contradictions = self._detect_contradictions([c for c in claims if c.claim_type == "numeric"])
        for c in claims:
            if c.issues:
                issues.extend([f"{c.id}: {i}" for i in c.issues])
        for c in contradictions:
            issues.append(f"Contradiction: {c}")

        return {
            "claims": [c.__dict__ for c in claims],
            "paragraph_map": paragraph_map,
            "contradictions": contradictions,
            "issues": issues,
            "metrics": {
                "claim_count": len(claims),
                "numeric_claims": len([c for c in claims if c.claim_type == "numeric"]),
                "regulatory_claims": len([c for c in claims if c.claim_type == "regulatory"]),
                "contradictions": len(contradictions)
            }
        }

    def _split_sentences(self, text: str) -> List[str]:
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    def _extract_citations(self, text: str) -> List[str]:
        return re.findall(r"\[(S\d+)\]", text or "")

    def _classify_claim(self, sentence: str, regulations: List[str]) -> Tuple[Optional[str], List[str]]:
        s = sentence.lower()
        numbers = re.findall(r"(?:\d+[\\d,\\.]*\\s?%?|\\d+[\\d,\\.]*)", s)
        if numbers:
            return "numeric", numbers
        for reg in regulations:
            if reg and reg.lower() in s:
                return "regulatory", []
        tokens = set(re.findall(r"[a-z]+", s))
        if tokens.intersection(self.trigger_words):
            return "policy", []
        return None, []

    def _resolve_sources(self, citations: List[str], evidence_map: Dict[str, Dict]) -> Tuple[List[str], List[str]]:
        sources = []
        domains = []
        for cid in citations:
            sources.append(cid)
            ev = evidence_map.get(cid) or {}
            domain = ev.get("domain") or ""
            if domain:
                domains.append(domain)
        return sources, domains

    def _detect_contradictions(self, numeric_claims: List[Claim]) -> List[str]:
        groups: Dict[str, List[Claim]] = {}
        for claim in numeric_claims:
            key = self._normalize_subject(claim.text)
            if not key:
                continue
            groups.setdefault(key, []).append(claim)

        contradictions = []
        for key, claims in groups.items():
            values = set()
            for c in claims:
                values.update(c.numbers)
            if len(values) > 1:
                contradictions.append(f"Conflicting numbers for '{key}': {sorted(values)}")
        return contradictions

    def _normalize_subject(self, text: str) -> str:
        s = re.sub(r"\\d+[\\d,\\.]*\\s?%?", " ", text.lower())
        s = re.sub(r"[^a-z\\s]", " ", s)
        s = re.sub(r"\\s+", " ", s).strip()
        # Shorten to reduce noise
        words = s.split()
        return " ".join(words[:8])
