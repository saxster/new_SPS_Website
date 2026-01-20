#!/usr/bin/env python3
"""
Quality Scorer 📊
Pre-validation gate that enforces minimum quality thresholds before fact-checking.
Articles failing these thresholds are automatically rejected.

Based on: EDITORIAL_MANIFESTO.md quality thresholds
"""
import re
import json
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger("QualityScorer")


class QualityScorer:
    """
    Enforces minimum quality thresholds before sending to Fact Checker.
    
    Thresholds based on EDITORIAL_MANIFESTO.md:
    - Guide: 1500 words, 5 sections, 5 sources, 2 regulations
    - Analysis: 2000 words, 6 sections, 8 sources, 2 regulations
    - News: 600 words, 4 sections, 3 sources, 1 regulation
    - Review: 1200 words, 4 sections, 4 sources, 1 regulation
    """
    
    THRESHOLDS = {
        "Guide": {
            "min_words": 1500,
            "min_h2": 5,
            "min_sources": 5,
            "min_regulations": 2,
        },
        "Analysis": {
            "min_words": 2000,
            "min_h2": 6,
            "min_sources": 8,
            "min_regulations": 2,
        },
        "News": {
            "min_words": 600,
            "min_h2": 4,
            "min_sources": 3,
            "min_regulations": 1,
        },
        "Review": {
            "min_words": 1200,
            "min_h2": 4,
            "min_sources": 4,
            "min_regulations": 1,
        },
        "General": {
            "min_words": 1000,
            "min_h2": 4,
            "min_sources": 3,
            "min_regulations": 1,
        },
    }
    
    # Common Indian regulations to look for
    INDIAN_REGULATIONS = [
        # Data Protection & Privacy
        r"DPDP\s*Act",
        r"Digital\s*Personal\s*Data\s*Protection",
        r"IT\s*Act\s*2000",
        r"Information\s*Technology\s*Act",
        r"Section\s*43A",
        r"Section\s*66",
        r"SPDI\s*Rules",
        # Financial
        r"RBI",
        r"Reserve\s*Bank",
        r"SEBI",
        r"IRDAI",
        r"PCI\s*DSS",
        # Physical Security
        r"PSARA",
        r"Private\s*Security\s*Agencies",
        r"NBC\s*2016",
        r"National\s*Building\s*Code",
        r"Arms\s*Act",
        # Healthcare
        r"Clinical\s*Establishments\s*Act",
        r"BMW\s*Rules",
        r"Biomedical\s*Waste",
        r"PCPNDT",
        r"AERB",
        # Education
        r"RTE\s*Act",
        r"Right\s*to\s*Education",
        r"NCPCR",
        r"POCSO",
        r"UGC",
        # General
        r"NDMA",
        r"CERT-In",
        r"MeitY",
        r"Ministry\s*of\s*Home\s*Affairs",
        r"MHA",
    ]
    
    # Citation patterns
    CITATION_PATTERNS = [
        r"\[[\w\-]+\d+\]",           # [SOURCE-2025] or [MHA-2024-001]
        r"\([\w\s]+,\s*\d{4}\)",     # (DSCI Report, 2025)
        r"according\s+to\s+[\w\s]+", # according to FICCI
        r"as\s+per\s+[\w\s]+",       # as per RBI guidelines
    ]
    
    def __init__(self):
        self.compiled_regulations = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.INDIAN_REGULATIONS
        ]
        self.compiled_citations = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.CITATION_PATTERNS
        ]
    
    def count_words(self, text: str) -> int:
        """Count words in text."""
        if not text:
            return 0
        # Remove markdown formatting
        clean = re.sub(r'[#*`\[\](){}]', ' ', text)
        words = clean.split()
        return len(words)
    
    def count_h2_sections(self, text: str) -> int:
        """Count H2 (##) sections in markdown."""
        if not text:
            return 0
        h2_pattern = re.compile(r'^##\s+[^#]', re.MULTILINE)
        return len(h2_pattern.findall(text))
    
    def count_sources(self, article: Dict) -> int:
        """Count sources from both 'sources' field and inline citations."""
        count = 0
        
        # Count from sources array
        sources = article.get('sources', [])
        if isinstance(sources, list):
            count += len(sources)
        
        # Count inline citations in body
        body = article.get('body', '')
        for pattern in self.compiled_citations:
            matches = pattern.findall(body)
            count += len(matches)
        
        # Deduplicate rough estimate (citations often repeat)
        return min(count, len(sources) + 10) if sources else count
    
    def count_regulations(self, article: Dict) -> int:
        """Count Indian regulatory references."""
        text = article.get('body', '') + ' ' + str(article.get('regulations', []))
        
        found = set()
        for i, pattern in enumerate(self.compiled_regulations):
            if pattern.search(text):
                found.add(i)
        
        return len(found)
    
    def check_british_english(self, text: str) -> List[str]:
        """Check for American English spellings."""
        american_patterns = {
            r'\bcolor\b': 'colour',
            r'\bfavor\b': 'favour',
            r'\bhonor\b': 'honour',
            r'\brealize\b': 'realise',
            r'\borganize\b': 'organise',
            r'\brecognize\b': 'recognise',
            r'\banalyze\b': 'analyse',
            r'\bdefense\b': 'defence',
            r'\boffense\b': 'offence',
            r'\bcenter\b': 'centre',
            r'\btheater\b': 'theatre',
            r'\bgray\b': 'grey',
            r'\bbehavior\b': 'behaviour',
            r'\blabor\b': 'labour',
            r'\bprogram\b(?!\s*code)': 'programme',  # exclude "program code"
        }
        
        issues = []
        for american, british in american_patterns.items():
            pattern = re.compile(american, re.IGNORECASE)
            matches = pattern.findall(text)
            if matches:
                issues.append(f"'{matches[0]}' should be '{british}'")
        
        return issues
    
    def check_banned_phrases(self, text: str) -> List[str]:
        """Check for banned phrases from EDITORIAL_MANIFESTO."""
        banned = [
            "game-changer",
            "game changer",
            "best-in-class",
            "best in class",
            "cutting-edge",
            "cutting edge",
            "world-class",
            "world class",
            "synergy",
            "synergies",
            "going forward",
            "at the end of the day",
            "in today's fast-paced world",
            "needless to say",
            "it is important to note that",
            "leverage" # as verb - harder to detect context
        ]
        
        found = []
        text_lower = text.lower()
        for phrase in banned:
            if phrase in text_lower:
                found.append(phrase)
        
        return found
    
    def score(self, article: Dict) -> Dict:
        """
        Score an article against quality thresholds.
        
        Args:
            article: Dict with 'body', 'category'/'content_type', 'sources', 'regulations'
            
        Returns:
            Dict with scoring results and pass/fail status
        """
        # Determine content type
        content_type = article.get('content_type') or article.get('contentType') or article.get('category', 'General')
        if content_type not in self.THRESHOLDS:
            content_type = 'General'
        
        thresholds = self.THRESHOLDS[content_type]
        body = article.get('body', '')
        
        # Counts
        word_count = self.count_words(body)
        h2_count = self.count_h2_sections(body)
        source_count = self.count_sources(article)
        regulation_count = self.count_regulations(article)
        
        # Style checks
        british_issues = self.check_british_english(body)
        banned_found = self.check_banned_phrases(body)
        
        # Build issues list
        issues = []
        warnings = []
        
        # Hard failures
        if word_count < thresholds['min_words']:
            issues.append(
                f"Insufficient depth: {word_count} words "
                f"(minimum: {thresholds['min_words']})"
            )
        
        if h2_count < thresholds['min_h2']:
            issues.append(
                f"Insufficient structure: {h2_count} sections "
                f"(minimum: {thresholds['min_h2']})"
            )
        
        if source_count < thresholds['min_sources']:
            issues.append(
                f"Insufficient sourcing: ~{source_count} sources "
                f"(minimum: {thresholds['min_sources']})"
            )
        
        if regulation_count < thresholds['min_regulations']:
            issues.append(
                f"Insufficient India context: {regulation_count} regulations "
                f"(minimum: {thresholds['min_regulations']})"
            )
        
        # Soft warnings
        if british_issues:
            warnings.append(f"American spellings detected: {', '.join(british_issues[:3])}")
        
        if banned_found:
            warnings.append(f"Banned phrases used: {', '.join(banned_found[:3])}")
        
        # Calculate score (0-100)
        score_components = [
            min(100, (word_count / thresholds['min_words']) * 100),
            min(100, (h2_count / thresholds['min_h2']) * 100),
            min(100, (source_count / thresholds['min_sources']) * 100),
            min(100, (regulation_count / thresholds['min_regulations']) * 100),
        ]
        base_score = sum(score_components) / len(score_components)
        
        # Deductions
        deductions = len(british_issues) * 2 + len(banned_found) * 5
        final_score = max(0, base_score - deductions)
        
        return {
            "passes": len(issues) == 0,
            "score": round(final_score, 1),
            "content_type": content_type,
            "thresholds": thresholds,
            
            # Metrics
            "word_count": word_count,
            "h2_count": h2_count,
            "source_count": source_count,
            "regulation_count": regulation_count,
            
            # Issues
            "issues": issues,
            "warnings": warnings,
            "british_issues": british_issues,
            "banned_phrases": banned_found,
            
            # Recommendation
            "recommendation": "PUBLISH" if len(issues) == 0 else "REJECT"
        }


def validate_article_file(filepath: str) -> Dict:
    """Convenience function to validate a JSON article file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        article = json.load(f)
    
    scorer = QualityScorer()
    return scorer.score(article)


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python quality_scorer.py <article.json>")
        print("\nOr test with sample:")
        
        # Test with sample
        sample = {
            "body": """
# Sample Article Title

## Introduction
This is a sample article about security in India. According to DSCI Report 2025,
cybersecurity spending increased by 45% [DSCI-2025-001].

## The DPDP Act Impact
The Digital Personal Data Protection Act 2023 requires organisations to...
Section 8(1) mandates proper consent mechanisms.

## RBI Guidelines
The Reserve Bank of India cyber security framework outlines...

## Case Study: HDFC Bank
In Q3 2024, HDFC Bank implemented zero-trust architecture.

## Recommendations
Security leaders should prioritise these game-changer initiatives...

## Conclusion
Going forward, organisations must adapt.
""",
            "category": "Guide",
            "sources": [
                {"id": "DSCI-2025-001", "title": "DSCI Annual Report"},
                {"id": "RBI-2024", "title": "RBI Cyber Framework"}
            ],
            "regulations": ["DPDP Act 2023", "IT Act 2000"]
        }
        
        scorer = QualityScorer()
        result = scorer.score(sample)
        
        print("\n" + "="*60)
        print("QUALITY SCORE RESULTS")
        print("="*60)
        print(f"\nScore: {result['score']}/100")
        print(f"Passes: {'✅ YES' if result['passes'] else '❌ NO'}")
        print(f"Content Type: {result['content_type']}")
        print(f"\nMetrics:")
        print(f"  Words: {result['word_count']} (min: {result['thresholds']['min_words']})")
        print(f"  Sections: {result['h2_count']} (min: {result['thresholds']['min_h2']})")
        print(f"  Sources: ~{result['source_count']} (min: {result['thresholds']['min_sources']})")
        print(f"  Regulations: {result['regulation_count']} (min: {result['thresholds']['min_regulations']})")
        
        if result['issues']:
            print(f"\n❌ Issues:")
            for issue in result['issues']:
                print(f"   - {issue}")
        
        if result['warnings']:
            print(f"\n⚠️ Warnings:")
            for warning in result['warnings']:
                print(f"   - {warning}")
        
        if result['banned_phrases']:
            print(f"\n🚫 Banned phrases found: {result['banned_phrases']}")
        
        print("="*60)
    else:
        filepath = sys.argv[1]
        result = validate_article_file(filepath)
        print(json.dumps(result, indent=2))
