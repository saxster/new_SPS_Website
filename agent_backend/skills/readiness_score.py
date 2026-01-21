#!/usr/bin/env python3
"""
Readiness Score Engine
Aggregates quality metrics from all Agents to produce a 'Project IQ' score (0-100).
"""

import sys
import os
import json
import logging
from datetime import datetime

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Scorecard")

# Add Skills to Path
sys.path.append(os.path.dirname(__file__))
import audit_seo
import verify_design

# Config
WEIGHTS = {
    'seo': 0.4,
    'design': 0.3,
    'content': 0.3
}

def analyze_project(base_dir: str):
    logger.info("📊 Calculating Project Readiness Score...")
    
    scores = {}
    details = {}
    
    # 1. SEO Audit
    seo_path = os.path.join(base_dir, "website/src/pages")
    seo_issues = audit_seo.audit_directory(seo_path)
    # Simple scoring: -5 points per failing file, min 0
    seo_score = max(0, 100 - (len(seo_issues) * 5))
    scores['seo'] = seo_score
    details['seo_issues'] = len(seo_issues)
    logger.info(f"   Search Optimization: {seo_score}/100 ({len(seo_issues)} issues)")
    
    # 2. Design Audit
    design_path = os.path.join(base_dir, "website/src")
    design_issues = verify_design.audit_directory(design_path)
    design_score = max(0, 100 - (len(design_issues) * 5))
    scores['design'] = design_score
    details['design_issues'] = len(design_issues)
    logger.info(f"   Design Compliance:   {design_score}/100 ({len(design_issues)} issues)")
    
    # 3. Content Health (Mocked for now - assuming Fact Checker passing rate)
    # In future, we hook into the Newsroom metrics
    content_score = 100 
    scores['content'] = content_score
    logger.info(f"   Content Authority:   {content_score}/100 (Baseline)")
    
    # Calculate Total
    total_score = (
        scores['seo'] * WEIGHTS['seo'] +
        scores['design'] * WEIGHTS['design'] +
        scores['content'] * WEIGHTS['content']
    )
    
    return total_score, scores, details

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    
    total, scores, details = analyze_project(base_dir)
    
    print("\n" + "="*40)
    print(f" 🎯 PROJECT READINESS SCORE: {total:.1f}/100")
    print("="*40)
    
    # Report Card
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_score": total,
        "components": scores,
        "details": details
    }
    
    # Save Report
    report_path = os.path.join(base_dir, ".agent/readiness_report.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
        
    print(f"\n📄 Full report saved to {os.path.relpath(report_path, base_dir)}")
    
    if total < 80:
        print("❌ Score below 80. Deployment NOT Recommended.")
        sys.exit(1)
    else:
        print("✅ Ready for Deployment.")

if __name__ == "__main__":
    main()
