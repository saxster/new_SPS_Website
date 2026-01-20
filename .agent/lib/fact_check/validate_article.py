#!/usr/bin/env python3
"""
Adversarial Fact-Checker CLI - Production-Grade Validation Tool

Features:
- Interactive mode (prompts for input)
- File mode (JSON/YAML articles)
- Batch mode (validate multiple articles)
- Threshold overrides (custom confidence levels)
- Multiple output formats (text, JSON, markdown)
- Pre-built test scenarios
- Ensemble mode support

Usage Examples:
  # Interactive mode
  python validate_article.py --interactive
  
  # Validate from JSON file
  python validate_article.py --file article.json
  
  # Batch validation
  python validate_article.py --batch articles.json --output results.json
  
  # Override thresholds
  python validate_article.py --interactive --publish-threshold 90 --review-threshold 80
  
  # Use pre-built scenario
  python validate_article.py --scenario rbi_cybersecurity
  
  # JSON output
  python validate_article.py --file article.json --format json
"""

import sys
import os
import json
import argparse
from typing import Dict, List, Optional
from dataclasses import asdict

sys.path.insert(0, os.path.dirname(__file__))

from adversarial_fact_checker import AdversarialFactChecker
from .validators import ValidationAction, ArticleInput
from .config import ValidationConfig
import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# PRE-BUILT TEST SCENARIOS
# ============================================================================

SCENARIOS = {
    "rbi_cybersecurity": {
        "title": "RBI mandates enhanced cybersecurity framework for all scheduled commercial banks",
        "summary": """The Reserve Bank of India has issued comprehensive cybersecurity guidelines 
        requiring all scheduled commercial banks to implement advanced threat detection systems, 
        conduct quarterly security audits, and establish dedicated cybersecurity response teams. 
        The directive follows recent incidents of digital banking fraud.""",
        "regulations": [
            "RBI Master Direction on Cyber Security Framework (2016)",
            "Information Technology Act 2000",
            "Digital Personal Data Protection Act 2023",
            "Banking Regulation Act 1949"
        ],
        "costs": "₹50L-5Cr per bank for comprehensive cybersecurity infrastructure",
        "topic": "financial_cybersecurity"
    },
    "hospital_data_breach": {
        "title": "Major hospital suffers patient data breach, 50,000 records exposed",
        "summary": """A prominent private hospital chain reported unauthorized access to 
        patient medical records, exposing sensitive health information of approximately 50,000 
        patients. The breach involved electronic medical records and diagnostic reports.""",
        "regulations": [
            "Clinical Establishments Act",
            "Digital Personal Data Protection Act 2023"
        ],
        "costs": "₹10-100L for enterprise cybersecurity upgrade",
        "topic": "healthcare_data_protection"
    },
    "school_security": {
        "title": "Small school installs basic CCTV system for campus monitoring",
        "summary": """A small private school with 200 students has installed a basic 
        CCTV surveillance system covering main entry points and hallways.""",
        "regulations": [
            "Supreme Court School Safety Guidelines 2018",
            "RTE Act 2009"
        ],
        "costs": "₹2-5L for 8-camera CCTV system",
        "topic": "education_security"
    },
    "punjab_hospital_security": {
        "title": "Punjab Govt to deploy 200 security staff in district hospitals",
        "summary": """The Punjab government has deployed 200 security personnel across 
        district hospitals to ensure safety of medical staff and patients.""",
        "regulations": [
            "Clinical Establishments Act 2010",
            "Labour Laws (Minimum Wage Act, ESI Act, PF Act)"
        ],
        "costs": "₹12,000-18,000/guard/month",
        "topic": "healthcare_security"
    }
}


# ============================================================================
# INPUT METHODS
# ============================================================================

def interactive_input() -> Dict:
    """Collect article details interactively"""
    print("\n" + "="*80)
    print("INTERACTIVE ARTICLE INPUT")
    print("="*80 + "\n")
    
    title = input("Article Title: ").strip()
    print("\nArticle Summary (press Enter twice when done):")
    summary_lines = []
    while True:
        line = input()
        if line == "":
            break
        summary_lines.append(line)
    summary = " ".join(summary_lines).strip()
    
    print("\nProposed Regulations (one per line, press Enter twice when done):")
    regulations = []
    while True:
        reg = input(f"  {len(regulations)+1}. ").strip()
        if reg == "":
            break
        regulations.append(reg)
    
    costs = input("\nProposed Costs: ").strip()
    topic = input("Topic/Category: ").strip()
    
    return {
        "title": title,
        "summary": summary,
        "regulations": regulations,
        "costs": costs,
        "topic": topic
    }


def load_from_file(filepath: str) -> Dict:
    """Load article from JSON or YAML file"""
    with open(filepath, 'r') as f:
        if filepath.endswith('.json'):
            return json.load(f)
        elif filepath.endswith(('.yaml', '.yml')):
            import yaml
            return yaml.safe_load(f)
        else:
            raise ValueError("File must be .json, .yaml, or .yml")


def load_batch(filepath: str) -> List[Dict]:
    """Load multiple articles for batch validation"""
    with open(filepath, 'r') as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'articles' in data:
            return data['articles']
        else:
            raise ValueError("Batch file must contain array or {'articles': [...]}")


# ============================================================================
# OUTPUT FORMATTERS
# ============================================================================

def format_text(result, article_data: Dict, config: ValidationConfig) -> str:
    """Format result as human-readable text"""
    action_emoji = {
        ValidationAction.PUBLISH: "✅",
        ValidationAction.REVIEW: "⚠️",
        ValidationAction.REJECT: "❌"
    }
    
    output = []
    output.append("=" * 80)
    output.append(f"ARTICLE: {article_data['title'][:60]}...")
    output.append("=" * 80)
    output.append("")
    output.append(f"{action_emoji[result.recommended_action]} DECISION: {result.recommended_action.value.upper()}")
    output.append(f"📊 Confidence: {result.confidence}%")
    output.append("")
    
    # Threshold explanation
    if result.confidence >= config.CONFIDENCE_PUBLISH:
        output.append(f"✅ AUTO-PUBLISH (≥{config.CONFIDENCE_PUBLISH}%)")
    elif result.confidence >= config.CONFIDENCE_REVIEW:
        output.append(f"⚠️  MANUAL REVIEW ({config.CONFIDENCE_REVIEW}%-{config.CONFIDENCE_PUBLISH-1}%)")
    else:
        output.append(f"❌ REJECTED (<{config.CONFIDENCE_REVIEW}%)")
    
    output.append("")
    output.append(f"📋 Regulations: ✓{len(result.regulations_approved)} ⚠{len(result.regulations_disputed)} +{len(result.regulations_missing)}")
    output.append(f"💰 Cost Valid: {'YES' if result.cost_estimate_valid else 'NO'}")
    output.append(f"💵 API Cost: ${result.estimate_cost():.4f}")
    output.append("=" * 80)
    
    return "\n".join(output)


def format_json(result, article_data: Dict) -> str:
    """Format result as JSON"""
    output = {
        "article": article_data,
        "validation": {
            "decision": result.recommended_action.value,
            "confidence": result.confidence,
            "regulations_approved": result.regulations_approved,
            "regulations_disputed": result.regulations_disputed,
            "regulations_missing": result.regulations_missing,
            "cost_estimate_valid": result.cost_estimate_valid,
            "cost_feedback": result.cost_feedback,
            "critique": result.critique,
            "llm_provider": result.llm_provider,
            "cost_usd": result.estimate_cost(),
            "correlation_id": result.correlation_id
        }
    }
    return json.dumps(output, indent=2, ensure_ascii=False)


def format_markdown(result, article_data: Dict, config: ValidationConfig) -> str:
    """Format result as Markdown report"""
    action_emoji = {
        ValidationAction.PUBLISH: "✅",
        ValidationAction.REVIEW: "⚠️",
        ValidationAction.REJECT: "❌"
    }
    
    md = []
    md.append(f"# Validation Report: {article_data['title']}")
    md.append("")
    md.append(f"## {action_emoji[result.recommended_action]} Decision: {result.recommended_action.value.upper()}")
    md.append("")
    md.append(f"**Confidence Score**: {result.confidence}%")
    md.append("")
    
    # Threshold table
    md.append("| Threshold | Range | Status |")
    md.append("|-----------|-------|--------|")
    md.append(f"| Publish | ≥{config.CONFIDENCE_PUBLISH}% | {'✅' if result.confidence >= config.CONFIDENCE_PUBLISH else '—'} |")
    md.append(f"| Review | {config.CONFIDENCE_REVIEW}-{config.CONFIDENCE_PUBLISH-1}% | {'⚠️' if config.CONFIDENCE_REVIEW <= result.confidence < config.CONFIDENCE_PUBLISH else '—'} |")
    md.append(f"| Reject | <{config.CONFIDENCE_REVIEW}% | {'❌' if result.confidence < config.CONFIDENCE_REVIEW else '—'} |")
    md.append("")
    
    md.append("## Regulatory Analysis")
    if result.regulations_approved:
        md.append(f"\n**✓ Approved ({len(result.regulations_approved)})**:")
        for reg in result.regulations_approved:
            md.append(f"- {reg}")
    
    if result.regulations_disputed:
        md.append(f"\n**⚠ Disputed ({len(result.regulations_disputed)})**:")
        for reg in result.regulations_disputed:
            md.append(f"- {reg}")
    
    if result.regulations_missing:
        md.append(f"\n**+ Missing ({len(result.regulations_missing)})**:")
        for reg in result.regulations_missing:
            md.append(f"- {reg}")
    
    md.append("\n## Cost Analysis")
    md.append(f"- **Valid**: {'YES ✓' if result.cost_estimate_valid else 'NO ✗'}")
    md.append(f"- **Feedback**: {result.cost_feedback}")
    
    md.append("\n## Critique")
    md.append(f"{result.critique}")
    
    md.append(f"\n## Metadata")
    md.append(f"- **API Cost**: ${result.estimate_cost():.4f}")
    md.append(f"- **LLM Provider**: {result.llm_provider}")
    md.append(f"- **Correlation ID**: {result.correlation_id}")
    
    return "\n".join(md)


# ============================================================================
# MAIN CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Adversarial Fact-Checker CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Input methods (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--interactive', '-i', action='store_true',
                             help='Interactive mode (prompts for input)')
    input_group.add_argument('--file', '-f', metavar='FILE',
                             help='Validate article from JSON/YAML file')
    input_group.add_argument('--batch', '-b', metavar='FILE',
                             help='Batch validate articles from JSON file')
    input_group.add_argument('--scenario', '-s', choices=list(SCENARIOS.keys()),
                             help='Use pre-built test scenario')
    
    # Configuration
    parser.add_argument('--publish-threshold', type=float, metavar='PCT',
                       help='Override publish threshold (default: from config)')
    parser.add_argument('--review-threshold', type=float, metavar='PCT',
                       help='Override review threshold (default: from config)')
    parser.add_argument('--env', choices=['development', 'staging', 'production'],
                       default='production', help='Environment config (default: production)')
    
    # Output
    parser.add_argument('--format', choices=['text', 'json', 'markdown'],
                       default='text', help='Output format (default: text)')
    parser.add_argument('--output', '-o', metavar='FILE',
                       help='Write output to file instead of stdout')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Minimal output (decision only)')
    
    args = parser.parse_args()
    
    # Load configuration
    config = ValidationConfig.from_env(args.env)
    
    # Override thresholds if specified
    if args.publish_threshold:
        config.CONFIDENCE_PUBLISH = args.publish_threshold
    if args.review_threshold:
        config.CONFIDENCE_REVIEW = args.review_threshold
    
    # Initialize checker
    checker = AdversarialFactChecker(config=config)
    
    # Get article data
    if args.interactive:
        article_data = interactive_input()
    elif args.file:
        article_data = load_from_file(args.file)
    elif args.scenario:
        article_data = SCENARIOS[args.scenario]
    elif args.batch:
        articles = load_batch(args.batch)
        results = []
        for i, article_data in enumerate(articles, 1):
            print(f"\nValidating article {i}/{len(articles)}...")
            result = checker.validate_article(
                article_title=article_data['title'],
                article_summary=article_data['summary'],
                proposed_regulations=article_data['regulations'],
                proposed_costs=article_data['costs'],
                topic=article_data['topic']
            )
            results.append(format_json(result, article_data) if args.format == 'json' else format_text(result, article_data, config))
        
        output_text = "\n\n".join(results) if args.format != 'json' else json.dumps([json.loads(r) for r in results], indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output_text)
            print(f"\n✅ Batch results written to {args.output}")
        else:
            print(output_text)
        
        return 0
    
    # Single article validation
    result = checker.validate_article(
        article_title=article_data['title'],
        article_summary=article_data['summary'],
        proposed_regulations=article_data['regulations'],
        proposed_costs=article_data['costs'],
        topic=article_data['topic']
    )
    
    # Format output
    if args.quiet:
        output_text = result.recommended_action.value
    elif args.format == 'text':
        output_text = format_text(result, article_data, config)
    elif args.format == 'json':
        output_text = format_json(result, article_data)
    elif args.format == 'markdown':
        output_text = format_markdown(result, article_data, config)
    
    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_text)
        print(f"\n✅ Results written to {args.output}")
    else:
        print(f"\n{output_text}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
