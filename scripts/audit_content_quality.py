import os
import re

CONTENT_DIR = "website/src/content"

def analyze_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # 1. Remove Frontmatter (Metadata)
    content = re.sub(r'^---[\s\S]*?---', '', content)
    
    # 2. Identify and Remove Table of Contents (common source of "bad" list density)
    # Pattern: Look for "Table of Contents" followed by a list block
    content = re.sub(r'(?i)##\s+Table of Contents[\s\S]*?(?=\n##)', '', content)

    lines = content.split('\n')
    
    list_word_count = 0
    prose_word_count = 0
    header_count = 0
    total_list_items = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detect List Items (Bullets or Numbered)
        is_list = False
        if line.startswith('- ') or line.startswith('* '):
            is_list = True
        elif re.match(r'^\d+\.', line):
            is_list = True
            
        words = len(line.split())
        
        if line.startswith('#'):
            header_count += 1
        elif is_list:
            list_word_count += words
            total_list_items += 1
        else:
            prose_word_count += words

    total_words = list_word_count + prose_word_count
    if total_words == 0:
        return 0, 0, "EMPTY"

    # Metric A: Prose Ratio (What % of the content is narrative?)
    prose_ratio = (prose_word_count / total_words) * 100
    
    # Metric B: List Depth (Average words per list item)
    # High depth means the list items are detailed explanations, not just "thin" bullets.
    avg_list_depth = list_word_count / total_list_items if total_list_items > 0 else 0
    
    # Scoring Logic
    # 1. If Prose Ratio > 60%, it's definitely a PASS (mostly narrative).
    # 2. If Prose Ratio is lower (e.g. 40%), it CAN still pass IF the list items are "Deep" (>15 words avg).
    # This accounts for "Checklist" or "Manual" style articles which are validly lists but detailed. 
    
    status = "FAIL"
    reason = "Too Thin"
    
    if prose_ratio > 60:
        status = "PASS"
        reason = "Narrative"
    elif avg_list_depth > 15:
        status = "PASS"
        reason = "Deep List"
    elif prose_ratio > 40 and avg_list_depth > 10:
        status = "PASS"
        reason = "Hybrid"
        
    return prose_ratio, avg_list_depth, status, reason

print(f"{ 'File':<45} | { 'Prose%':<7} | { 'ListDepth':<10} | { 'Status':<5} | {'Reason'}")
print("-" * 95)

for root, dirs, files in os.walk(CONTENT_DIR):
    for file in files:
        if file.endswith(".md"):
            filepath = os.path.join(root, file)
            prose_ratio, list_depth, status, reason = analyze_file(filepath)
            
            # Color coding for terminal (optional, keeping simple text for now)
            print(f"{file:<45} | {prose_ratio:5.1f}% | {list_depth:5.1f} w/item | {status:<5} | {reason}")