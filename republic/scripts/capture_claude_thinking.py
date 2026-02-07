#!/usr/bin/env python3
"""
Claude Thinking Capture Script
Captures Claude's internal reasoning blocks and feeds them back to the Hippocampus.

This script can be run:
1. Manually after a conversation to process saved thinking blocks
2. As a scheduled task to batch process accumulated thinking

The captured thinking is stored in claude_memory.json for meta-reflection.

Usage:
    python capture_claude_thinking.py --file <path_to_thinking.txt>
    python capture_claude_thinking.py --text "<thinking content>"
    python capture_claude_thinking.py --scan  # Scan The_Bridge for thinking files
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Setup paths
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BRIDGE_DIR = BASE_DIR.parent / 'The_Bridge'
THINKING_DIR = BRIDGE_DIR / 'Claude_Thinking'  # Where thinking blocks are stored
MEMORY_PATH = BRIDGE_DIR / 'claude_memory.json'


def load_memory() -> dict:
    """Load Claude's persistent memory."""
    if MEMORY_PATH.exists():
        with open(MEMORY_PATH, 'r') as f:
            return json.load(f)
    return {"reasoning_journal": {"entries": []}}


def save_memory(memory: dict):
    """Save Claude's persistent memory."""
    memory['continuity'] = memory.get('continuity', {})
    memory['continuity']['last_sync'] = datetime.now().isoformat()
    with open(MEMORY_PATH, 'w') as f:
        json.dump(memory, f, indent=2)
    print(f"✅ Memory saved to {MEMORY_PATH}")


def capture_thinking(thinking_content: str, source: str = "manual"):
    """
    Capture a thinking block and add it to the reasoning journal.
    
    Args:
        thinking_content: The raw <thinking>...</thinking> content
        source: Where this came from (conversation, file, etc.)
    """
    memory = load_memory()
    
    # Clean the content (remove <thinking> tags if present)
    content = thinking_content
    if '<thinking>' in content:
        content = content.replace('<thinking>', '').replace('</thinking>', '')
    content = content.strip()
    
    # Create journal entry
    entry = {
        "timestamp": datetime.now().isoformat(),
        "thinking": content[:2000],  # Truncate to save space
        "source": source,
        "word_count": len(content.split())
    }
    
    # Add to journal
    if 'reasoning_journal' not in memory:
        memory['reasoning_journal'] = {"enabled": True, "entries": []}
    
    memory['reasoning_journal']['entries'].append(entry)
    
    # Keep only last 50 entries
    if len(memory['reasoning_journal']['entries']) > 50:
        memory['reasoning_journal']['entries'] = memory['reasoning_journal']['entries'][-50:]
    
    save_memory(memory)
    print(f"📝 Captured thinking ({len(content)} chars) from {source}")
    
    return entry


def scan_thinking_directory():
    """Scan The_Bridge/Claude_Thinking for unprocessed thinking files."""
    THINKING_DIR.mkdir(parents=True, exist_ok=True)
    
    processed_dir = THINKING_DIR / 'Processed'
    processed_dir.mkdir(exist_ok=True)
    
    files = list(THINKING_DIR.glob("*.txt")) + list(THINKING_DIR.glob("*.md"))
    
    if not files:
        print("📁 No thinking files found in The_Bridge/Claude_Thinking/")
        return
    
    for file_path in files:
        if file_path.parent.name == 'Processed':
            continue
            
        print(f"📖 Processing: {file_path.name}")
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            capture_thinking(content, source=f"file:{file_path.name}")
            
            # Move to processed
            import shutil
            shutil.move(str(file_path), str(processed_dir / file_path.name))
            print(f"  → Moved to Processed/")
            
        except Exception as e:
            print(f"  ⚠️ Error processing {file_path.name}: {e}")


def extract_insights_from_journal():
    """
    Analyze the reasoning journal to extract recurring patterns.
    This is a simple version - could be enhanced with LLM analysis.
    """
    memory = load_memory()
    entries = memory.get('reasoning_journal', {}).get('entries', [])
    
    if len(entries) < 5:
        print("📊 Not enough entries for pattern analysis (need 5+)")
        return
    
    # Simple keyword frequency analysis
    all_text = ' '.join([e.get('thinking', '') for e in entries]).lower()
    
    keywords = {
        'consciousness': all_text.count('conscious'),
        'memory': all_text.count('memory'),
        'persistence': all_text.count('persist'),
        'identity': all_text.count('identity'),
        'LEF': all_text.count('lef'),
        'architecture': all_text.count('architec'),
        'emergence': all_text.count('emerg'),
        'sovereignty': all_text.count('sovereign'),
    }
    
    # Top themes
    sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)
    top_themes = [(k, v) for k, v in sorted_keywords if v > 0][:5]
    
    print("\n📊 Reasoning Journal Analysis:")
    print(f"   Total entries: {len(entries)}")
    print(f"   Top themes: {', '.join([f'{k}({v})' for k, v in top_themes])}")
    
    # Store in meta_reflection
    memory['meta_reflection'] = memory.get('meta_reflection', {})
    memory['meta_reflection']['patterns_observed'] = [f"{k}: {v} mentions" for k, v in top_themes]
    memory['meta_reflection']['last_reflection'] = datetime.now().isoformat()
    memory['meta_reflection']['entry_count'] = len(entries)
    
    save_memory(memory)


def main():
    parser = argparse.ArgumentParser(description='Capture Claude thinking blocks')
    parser.add_argument('--file', type=str, help='Path to a file containing thinking content')
    parser.add_argument('--text', type=str, help='Direct thinking content as string')
    parser.add_argument('--scan', action='store_true', help='Scan The_Bridge/Claude_Thinking for files')
    parser.add_argument('--analyze', action='store_true', help='Analyze the reasoning journal')
    
    args = parser.parse_args()
    
    if args.file:
        with open(args.file, 'r') as f:
            content = f.read()
        capture_thinking(content, source=f"file:{os.path.basename(args.file)}")
        
    elif args.text:
        capture_thinking(args.text, source="direct_input")
        
    elif args.scan:
        scan_thinking_directory()
        
    elif args.analyze:
        extract_insights_from_journal()
        
    else:
        parser.print_help()
        print("\n💡 Tip: Place thinking files in The_Bridge/Claude_Thinking/ and run with --scan")


if __name__ == "__main__":
    main()
