"""
Citation and claim validator.
Ensures citations exist, map to sources, and are used consistently.
Includes recency checks for time-sensitive content.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from config.manager import config
from shared.logger import get_logger

logger = get_logger("CitationValidator")


class CitationValidator:
    def __init__(self):
        self.min_citations_per_paragraph = config.get("citation.min_per_paragraph", 1)
        self.min_words_per_paragraph = config.get("citation.min_words_per_paragraph", 40)
        self.recency_days = config.get("citation.recency_days", 365)
        self.recency_by_type = config.get("citation.recency_by_type", {})
        self.recency_types = set(config.get("citation.recency_types", ["News"]))
        self.require_sources_section = config.get("citation.require_sources_section", True)
        self.require_numeric_citations = config.get("citation.require_numeric_citations", True)
        self.max_ngram_words = config.get("citation.max_ngram_words", 12)
        self.primary_reg_domains = set(config.get("citation.regulation_primary_domains", []))
        self.paraphrase_similarity_threshold = config.get("citation.paraphrase_similarity_threshold", 0.88)

    def validate(self, draft: Dict, evidence: Optional[List[Dict]] = None) -> Dict:
        body = draft.get("body", "") or ""
        sources = draft.get("sources", []) or []
        content_type = draft.get("content_type") or draft.get("contentType") or draft.get("category")
        title = draft.get("title", "")

        citations = self._extract_citations(body)
        source_ids = {s.get("id") for s in sources if isinstance(s, dict) and s.get("id")}

        issues = []
        warnings = []

        if self.require_sources_section and "## Sources" not in body:
            issues.append("Missing '## Sources' section.")

        # Citation to source mapping
        unknown_citations = [c for c in citations if c not in source_ids]
        if unknown_citations:
            issues.append(f"Citations not found in sources list: {sorted(set(unknown_citations))}")

        # Ensure each source is used at least once
        unused_sources = [sid for sid in source_ids if sid not in citations]
        if unused_sources:
            warnings.append(f"Sources not cited in body: {sorted(unused_sources)}")

        # Paragraph coverage
        para_issues = self._check_paragraph_citations(body)
        issues.extend(para_issues)

        # Numeric claim citations
        if self.require_numeric_citations:
            numeric_issues = self._check_numeric_citations(body)
            issues.extend(numeric_issues)

        # Regulation mentions must be cited
        reg_issues = self._check_regulations_cited(draft, body)
        issues.extend(reg_issues)
        reg_primary = self._check_regulation_primary_sources(draft, evidence)
        issues.extend(reg_primary)

        # Recency enforcement for time-sensitive content
        if self._requires_recency(content_type, title, body):
            recency_issue = self._check_recency(evidence, content_type)
            if recency_issue:
                issues.append(recency_issue)

        # Paraphrase risk detection
        if evidence:
            paraphrase_issue = self._check_paraphrase_risk(body, evidence)
            if paraphrase_issue:
                warnings.append(paraphrase_issue)

        return {
            "passes": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "metrics": {
                "citation_count": len(citations),
                "source_count": len(source_ids),
                "unknown_citations": len(unknown_citations),
                "unused_sources": len(unused_sources),
            }
        }

    def _extract_citations(self, text: str) -> List[str]:
        return re.findall(r"\[(S\d+)\]", text or "")

    def _check_paragraph_citations(self, body: str) -> List[str]:
        issues = []
        paragraphs = [p.strip() for p in (body or "").split("\n\n") if p.strip()]
        for idx, para in enumerate(paragraphs, 1):
            # Skip headings
            if para.startswith("#"):
                continue
            word_count = len(para.split())
            if word_count < self.min_words_per_paragraph:
                continue
            if not re.search(r"\[(S\d+)\]", para):
                issues.append(f"Paragraph {idx} lacks required citation.")
        return issues

    def _check_numeric_citations(self, body: str) -> List[str]:
        issues = []
        sentences = re.split(r"(?<=[.!?])\s+", body or "")
        for i, sent in enumerate(sentences, 1):
            if re.search(r"\d", sent) and not re.search(r"\[(S\d+)\]", sent):
                issues.append(f"Sentence {i} contains numeric claim without citation.")
        return issues

    def _check_regulations_cited(self, draft: Dict, body: str) -> List[str]:
        issues = []
        regs = draft.get("regulations", []) or []
        for reg in regs:
            if not reg:
                continue
            pattern = re.escape(reg)
            if not re.search(pattern, body, flags=re.IGNORECASE):
                issues.append(f"Regulation not mentioned in body: {reg}")
            else:
                # Require citation in same sentence
                for sent in re.split(r"(?<=[.!?])\s+", body):
                    if re.search(pattern, sent, flags=re.IGNORECASE) and not re.search(r"\[(S\d+)\]", sent):
                        issues.append(f"Regulation lacks citation in sentence: {reg}")
                        break
        return issues

    def _check_regulation_primary_sources(self, draft: Dict, evidence: Optional[List[Dict]]) -> List[str]:
        regs = draft.get("regulations", []) or []
        if not regs:
            return []
        if not evidence:
            return ["Regulation mentioned but no evidence sources provided."]
        if not self.primary_reg_domains:
            return []
        domains = set()
        for e in evidence:
            domain = e.get("domain")
            if not domain:
                url = e.get("url", "")
                if "://" in url:
                    domain = url.split("://", 1)[1].split("/", 1)[0]
            if domain:
                domains.add(domain.lower())
        if not domains.intersection(self.primary_reg_domains):
            return ["No primary regulatory sources cited for regulations."]
        return []

    def _requires_recency(self, content_type: Optional[str], title: str, body: str) -> bool:
        if content_type in self.recency_types or content_type in (self.recency_by_type or {}):
            return True
        signal = f"{title} {body}".lower()
        return any(k in signal for k in ["latest", "recent", "2025", "2026", "this year", "last year"])

    def _check_recency(self, evidence: Optional[List[Dict]], content_type: Optional[str]) -> Optional[str]:
        if not evidence:
            return "No evidence available to verify recency."
        days = self.recency_by_type.get(content_type, self.recency_days) if self.recency_by_type else self.recency_days
        cutoff = datetime.utcnow() - timedelta(days=int(days))
        for item in evidence:
            published = item.get("published")
            if not published:
                continue
            dt = self._parse_date(published)
            if dt and dt >= cutoff:
                return None
        return f"No sources published within last {days} days for time-sensitive content."

    def _parse_date(self, text: str) -> Optional[datetime]:
        # Accept YYYY or YYYY-MM or YYYY-MM-DD
        try:
            if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
                return datetime.strptime(text, "%Y-%m-%d")
            if re.match(r"^\d{4}-\d{2}$", text):
                return datetime.strptime(text, "%Y-%m")
            if re.match(r"^\d{4}$", text):
                return datetime.strptime(text, "%Y")
        except Exception:
            return None
        return None

    def _check_paraphrase_risk(self, body: str, evidence: List[Dict]) -> Optional[str]:
        body_lower = (body or "").lower()
        for item in evidence:
            snippet = (item.get("snippet") or "").lower()
            words = snippet.split()
            if len(words) < self.max_ngram_words:
                continue
            # sample sliding windows of size N
            for i in range(0, min(len(words) - self.max_ngram_words + 1, 30)):
                phrase = " ".join(words[i:i + self.max_ngram_words])
                if phrase and phrase in body_lower:
                    return "Potential close paraphrase from source snippet detected; consider rewriting."
            similarity = self._similarity_ratio(snippet, body_lower)
            if similarity >= self.paraphrase_similarity_threshold:
                return "High similarity to source snippet detected; consider rewriting for originality."
        return None

    def _similarity_ratio(self, a: str, b: str) -> float:
        import difflib
        if not a or not b:
            return 0.0
        a_tokens = set(a.split())
        b_tokens = set(b.split())
        if not a_tokens or not b_tokens:
            return 0.0
        jaccard = len(a_tokens & b_tokens) / max(1, len(a_tokens | b_tokens))
        seq = difflib.SequenceMatcher(None, a[:2000], b[:2000]).ratio()
        return max(jaccard, seq)
