#!/usr/bin/env python3
"""
Batch Migration Script for SQLite Connection Pool
Adds db_helper imports and converts simple sqlite3.connect patterns.
"""
import os
import re

REPUBLIC_DIR = "/Users/zmoore-macbook/Desktop/LEF Ai/republic"

# Files to skip (already migrated or special)
SKIP_FILES = {
    'db_helper.py', 'db_pool.py',
    'agent_immune.py', 'agent_chronicler.py', 'agent_dean.py',
    'intent_listener.py', 'moltbook_learner.py'
}

# The import block to add
IMPORT_BLOCK = '''
# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    from contextlib import contextmanager
    import sqlite3 as _sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = _sqlite3.connect(db_path, timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()
'''

def add_db_helper_import(filepath):
    """Add db_helper import to a file if it uses sqlite3.connect"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    if 'sqlite3.connect' not in content:
        return False, "No sqlite3.connect calls"
    
    if 'from db.db_helper import' in content or 'db_connection' in content:
        return False, "Already has db_helper"
    
    # Find position after imports
    lines = content.split('\n')
    insert_idx = 0
    
    for i, line in enumerate(lines):
        # Find the end of imports section
        if line.startswith('import ') or line.startswith('from '):
            insert_idx = i + 1
        elif line.strip() and not line.startswith('#') and not line.startswith('"""') and insert_idx > 0:
            # Found first non-import, non-comment line
            break
    
    # Need to add sys.path insert for db import to work
    needs_sys_path = 'sys.path' not in content
    
    if needs_sys_path:
        # Add sys.path manipulation
        base_dir_pattern = r"BASE_DIR\s*=.*os\.path\.dirname.*"
        if re.search(base_dir_pattern, content):
            # Add after BASE_DIR definition
            new_content = re.sub(
                base_dir_pattern + r"\n",
                lambda m: m.group(0) + "import sys\nif BASE_DIR not in sys.path:\n    sys.path.insert(0, BASE_DIR)\n",
                content,
                count=1
            )
            content = new_content
    
    # Add the import block after existing imports
    lines = content.split('\n')
    new_lines = lines[:insert_idx] + [IMPORT_BLOCK] + lines[insert_idx:]
    new_content = '\n'.join(new_lines)
    
    with open(filepath, 'w') as f:
        f.write(new_content)
    
    return True, "Added db_helper import"


def find_python_files(directory):
    """Find all Python files in directory tree"""
    files = []
    for root, dirs, filenames in os.walk(directory):
        # Skip pycache
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for fname in filenames:
            if fname.endswith('.py') and fname not in SKIP_FILES:
                files.append(os.path.join(root, fname))
    return files


def main():
    print("=== SQLite Connection Pool Migration ===")
    
    # Focus on departments directory (active agents)
    dept_dir = os.path.join(REPUBLIC_DIR, 'departments')
    files = find_python_files(dept_dir)
    
    print(f"Found {len(files)} Python files in departments/")
    
    modified = 0
    for filepath in files:
        basename = os.path.basename(filepath)
        success, msg = add_db_helper_import(filepath)
        if success:
            print(f"  ✅ {basename}: {msg}")
            modified += 1
        else:
            print(f"  ⏭️  {basename}: {msg}")
    
    print(f"\n=== Added db_helper import to {modified} files ===")
    print("NOTE: You still need to manually convert sqlite3.connect calls to use db_connection context manager")


if __name__ == '__main__':
    main()
