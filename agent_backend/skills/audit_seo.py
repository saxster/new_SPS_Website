#!/usr/bin/env python3
"""
SEO Specialist Agent (Active Fixer)
Scans Astro pages for missing meta tags.
If --fix is used, it uses an LLM to GENERATE and APPLY the missing tags.
"""

import os
import re
import sys
import argparse
import logging
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Setup Logger
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("SEO_Agent")

# OpenAI Setup
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except ImportError:
    client = None
    logger.warning("⚠️ OpenAI library not found. Auto-fix will be disabled.")

def parse_frontmatter(content: str) -> Tuple[Dict[str, str], str, str]:
    """
    Extracts frontmatter and body.
    Returns: (data_dict, raw_frontmatter, raw_body)
    """
    match = re.search(r'^(---\s*\n)(.*?)(\n---\s*\n)', content, re.DOTALL)
    if not match:
        return {}, "", content
    
    fm_raw = match.group(2)
    data = {}
    for line in fm_raw.split('\n'):
        if ':' in line:
            key, val = line.split(':', 1)
            data[key.strip()] = val.strip().strip('"\'')
        # Handle JS const/let/var (Astro)
        # matches: const title = ... (anything)
        js_match = re.search(r'(?:const|let|var)\s+(\w+)\s*=', line)
        if js_match:
            data[js_match.group(1)] = "DYNAMIC_VALUE"
            
    return data, match.group(0), content[len(match.group(0)):]

def generate_seo_tags(filename: str, body_content: str) -> Dict[str, str]:
    """Asks the LLM to generate title and description."""
    if not client:
        return {}
        
    prompt = f"""
    You are an SEO Expert for SPS Security (a high-security institutional brand).
    Generate a 'title' (max 60 chars) and 'description' (max 160 chars) for this page.
    
    Filename: {filename}
    Content Snippet:
    {body_content[:1500]}
    
    Return strictly valid JSON: {{"title": "...", "description": "..."}}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content.strip()
        # Clean markdown fences if present
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        
        import json
        return json.loads(content.strip())
    except Exception as e:
        logger.error(f"LLM Generation Failed: {e}")
        return {}

from skills.gemini_client import GeminiAgent

def analyze_intent(filename: str, title: str, body_content: str) -> Optional[str]:
    """Checks if the Title matches the Search Intent of the content (Gemini)."""
    agent = GeminiAgent()
    if not agent.model:
        return None
        
    prompt = f"""
    You are a Google Search Quality Rater.
    Analyze this content and determine the 'Search Intent' (Informational, Transactional, Navigational).
    Then, check if the Title is optimized for that intent.
    
    Title: {title}
    Content Snippet: {body_content[:1000]}
    
    If the title is POOR for the intent, return a short critique (max 15 words).
    If it is GOOD, return "OK".
    """
    result = agent.generate(prompt).strip()
    # Relaxed check: if "OK" is in the response (case-insensitive)
    if "OK" in result.upper():
         return None
    return result

def inject_tags(filepath: str, content: str, new_tags: Dict[str, str]):
    """Injects new tags into the frontmatter."""
    # Find frontmatter end
    match = re.search(r'^---\s*\n.*?\n---\s*\n', content, re.DOTALL)
    if match:
        fm_end = match.end() - 4 # Before the closing ---
        
        injection = ""
        for k, v in new_tags.items():
            injection += f'{k}: "{v}"\n'
            
        new_content = content[:fm_end] + injection + content[fm_end:]
        
        with open(filepath, 'w') as f:
            f.write(new_content)
        logger.info(f"✅ Fixed {os.path.basename(filepath)}: Added {list(new_tags.keys())}")
    else:
        logger.error(f"❌ Could not find frontmatter in {filepath}")

def audit_file(filepath: str, fix_mode: bool = False) -> List[str]:
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        data, _, body = parse_frontmatter(content)
        missing_tags = {}
        
        # Check Rules
        if 'title' not in data:
            issues.append("Missing 'title'")
            missing_tags['title'] = True
            
        if 'description' not in data:
            issues.append("Missing 'description'")
            missing_tags['description'] = True
            
        # SOTA Check: Search Intent
        if client and 'title' in data:
            critique = analyze_intent(os.path.basename(filepath), data['title'], body)
            if critique:
                issues.append(f"Intent Mismatch: {critique}")
            
        # If Issues & Fix Mode is ON
        if issues and fix_mode and missing_tags:
            logger.info(f"🤖 Auto-Fixing {os.path.basename(filepath)}...")
            generated = generate_seo_tags(os.path.basename(filepath), body)
            
            # Filter only missing ones
            to_inject = {k: v for k, v in generated.items() if k in missing_tags}
            
            if to_inject:
                inject_tags(filepath, content, to_inject)
                return [] # Issues resolved
             
    except Exception as e:
        issues.append(f"Failed to parse: {str(e)}")
        
    return issues

def main():
    parser = argparse.ArgumentParser(description="SEO Specialist Agent")
    parser.add_argument('path', nargs='?', default='website/src/pages', help='Directory to scan')
    parser.add_argument('--fix', action='store_true', help='Auto-generate missing tags using LLM')
    args = parser.parse_args()
    
    scan_path = args.path
    if not os.path.exists(scan_path):
        logger.error(f"❌ Path not found: {scan_path}")
        sys.exit(1)
        
    logger.info(f"🔍 SEO Specialist scanning {scan_path} (Fix Mode: {args.fix})\n")
    
def audit_directory(scan_path: str, fix_mode: bool = False) -> dict:
    results = {}
    for root, dirs, files in os.walk(scan_path):
        for file in files:
            if file.endswith('.astro') or file.endswith('.md'):
                filepath = os.path.join(root, file)
                issues = audit_file(filepath, fix_mode=fix_mode)
                if issues:
                    results[filepath] = issues
    return results

def main():
    parser = argparse.ArgumentParser(description="SEO Specialist Agent")
    parser.add_argument('path', nargs='?', default='website/src/pages', help='Directory to scan')
    parser.add_argument('--fix', action='store_true', help='Auto-generate missing tags using LLM')
    args = parser.parse_args()
    
    scan_path = args.path
    if not os.path.exists(scan_path):
        logger.error(f"❌ Path not found: {scan_path}")
        sys.exit(1)
        
    logger.info(f"🔍 SEO Specialist scanning {scan_path} (Fix Mode: {args.fix})\n")
    
    results = audit_directory(scan_path, fix_mode=args.fix)
    
    for filepath, issues in results.items():
        logger.warning(f"📄 {os.path.relpath(filepath, scan_path)}")
        for issue in issues:
            logger.warning(f"   ❌ {issue}")
        logger.warning("")
    
    if not results:
        logger.info(f"✅ SEO Compliance: 100%")
    else:
        logger.error(f"⚠️  Found SEO issues in {len(results)} files.")
        sys.exit(1)

if __name__ == "__main__":
    main()
