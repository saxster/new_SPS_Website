#!/usr/bin/env python3
"""
Janus Design Enforcer 2.0 (AST/DOM Edition)
Scans .astro and .tsx files using BeautifulSoup to parse structure.
Eliminates false positives from comments/scripts.
"""

import os
import sys
import argparse
import re
from bs4 import BeautifulSoup, Comment

# "Iron Laws" of Janus
# We check 'class' attributes against these rules.
PROHIBITED_CLASSES = [
    (r'^text-blue-\d+$', "No generic Blue allowed. Use Slate/Amber/Emerald."),
    (r'^bg-blue-\d+$', "No generic Blue allowed. Use Slate/Amber/Emerald."),
    (r'^rounded-(?!xl|none|full|lg|md|sm).*', "Non-standard border radius. Use rounded-xl or rounded-none."),
    (r'^p[btrlxy]?-(?!20)(9|[1-9]\d+)$', "Layout Padding Violation. Use p-20 (80px) for containers, or standard component padding."),
    # Note: pt-0 logic needs context, handled separately if needed.
]

def check_classes(classes: list, filename: str) -> list:
    issues = []
    for cls in classes:
        for pattern, reason in PROHIBITED_CLASSES:
            if re.match(pattern, cls):
                issues.append(f"Found prohibited class '{cls}' - {reason}")
    return issues

def audit_file(filepath: str, content: str) -> list:
    issues = []
    try:
        # Treat Astro/TSX as HTML/XML for structural parsing
        # 'html.parser' works well for lenient parsing of Astro files
        soup = BeautifulSoup(content, 'html.parser')

        # 1. Check Class Attributes
        # Finds all tags with a class attribute
        for tag in soup.find_all(attrs={"class": True}):
            # class can be a list or string
            classes = tag.get("class")
            if isinstance(classes, str):
                classes = classes.split()
            
            tag_issues = check_classes(classes, filepath)
            if tag_issues:
                # Try to find line number (approximate as BS4 loses precise location)
                # We grep the source to provide context, or just report the tag
                tag_str = str(tag)[:50] + "..."
                for i in tag_issues:
                    issues.append(f"In <{tag.name}> near '{tag_str}': {i}")

        # 2. Check Inline Styles (Iron Law: No Inline Styles)
        for tag in soup.find_all(attrs={"style": True}):
            issues.append(f"Inline Style detected in <{tag.name}>: '{tag['style']}'. Use Janus utility classes.")

    except Exception as e:
        issues.append(f"Parsing error: {str(e)}")
        
    return issues

def audit_directory(scan_path: str) -> dict:
    results = {}
    for root, dirs, files in os.walk(scan_path):
        for file in files:
            if file.endswith(('.astro', '.tsx', '.jsx', '.html')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                    
                    file_issues = audit_file(filepath, content)
                    if file_issues:
                        results[filepath] = file_issues
                        
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    return results

def main():
    parser = argparse.ArgumentParser(description="Enforce Janus Design System (DOM/AST)")
    parser.add_argument('path', nargs='?', default='website/src', help='Directory to scan')
    args = parser.parse_args()
    
    scan_path = args.path
    if not os.path.exists(scan_path):
        print(f"❌ Path not found: {scan_path}")
        sys.exit(1)
        
    print(f"🛡️  Janus Validator 2.0 (DOM Engine) Scanning {scan_path}...\n")
    
    results = audit_directory(scan_path)
    
    for filepath, issues in results.items():
        print(f"🛑 {os.path.relpath(filepath, scan_path)}")
        for issue in issues:
            print(f"   {issue}")
        print("")

    if not results:
        print("✅ Janus Compliance: 100%")
    else:
        print(f"⚠️  Found Design Violations in {len(results)} files.")
        sys.exit(1)

if __name__ == "__main__":
    main()
