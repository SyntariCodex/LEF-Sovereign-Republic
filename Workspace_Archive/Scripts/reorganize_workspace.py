#!/usr/bin/env python3
"""
Workspace Reorganization Script
Safely reorganizes LEF Ai workspace into separate project folders.
"""

import os
import shutil
from pathlib import Path

# Base directory
BASE_DIR = Path("/Users/zmoore-macbook/Desktop/LEF Ai")

# Files to move to lef-ai/
LEF_AI_FILES = [
    "CLAUDE_INTRODUCTORY_MESSAGE.md",
    "COMPLETION_SUMMARY.md",
    "EXECUTION_ANALYSIS.md",
    "IMPLEMENTATION_PLAN.md",
    "SETUP_STATUS.md",
    "SIMPLE_SETUP_GUIDE.md",
    "SUMMARY.md",
    "TASKS.md",
    "README.md",
    "dashboard_index.html",
    "fix_nodejs_path.sh",
    # Document files
    "Ai Convo_s.docx",
    "Ai Convo_s.md",
    "Architect_ Zontonnnia Moore.docx",
    "Architect_ Zontonnnia Moore.md",
    "Fulcrum MacBook Agent.docx",
    "LEF_ Github - Contributing.docx",
    "LEF_ Github - Readme.docx",
    "The Fulcrum Protocol - White Paper.docx",
    "The LEF Genesis Protocol_ Installation Script.docx",
    "The Living Eden Framework (LEF) - White Paper.docx",
    "API.png",
    "Screenshot 2026-01-05 at 3.50.01 PM copy.png",
]

# Folders to move to lef-ai/
LEF_AI_FOLDERS = [
    "docs",
]

# Files to move to snw/
SNW_FILES = [
    "Southern Nevada Wildlands (SNW) - White Paper.docx",
]

# Files to keep in root (don't move)
KEEP_IN_ROOT = [
    "fulcrum",
    "snw",
    "REORGANIZATION_PLAN.md",
    "reorganize_workspace.py",
    ".git",
    ".gitignore",
    ".cursor",
]

def create_directories():
    """Create new directory structure"""
    print("Creating directory structure...")
    
    # Create lef-ai directory
    lef_ai_dir = BASE_DIR / "lef-ai"
    lef_ai_dir.mkdir(exist_ok=True)
    print(f"✅ Created {lef_ai_dir}")
    
    # Create snw/docs directory
    snw_docs_dir = BASE_DIR / "snw" / "docs"
    snw_docs_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Created {snw_docs_dir}")
    
    return lef_ai_dir, snw_docs_dir

def move_files(files, target_dir, description):
    """Move files to target directory"""
    moved = []
    skipped = []
    
    for file in files:
        source = BASE_DIR / file
        if source.exists():
            target = target_dir / file
            try:
                # Create parent directory if needed
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(target))
                moved.append(file)
                print(f"  ✅ Moved {file}")
            except Exception as e:
                print(f"  ❌ Error moving {file}: {e}")
                skipped.append(file)
        else:
            skipped.append(file)
            print(f"  ⚠️  {file} not found (skipping)")
    
    print(f"\n{description}:")
    print(f"  Moved: {len(moved)}")
    print(f"  Skipped: {len(skipped)}")
    return moved, skipped

def move_folders(folders, target_dir, description):
    """Move folders to target directory"""
    moved = []
    skipped = []
    
    for folder in folders:
        source = BASE_DIR / folder
        if source.exists() and source.is_dir():
            target = target_dir / folder
            try:
                if target.exists():
                    # Merge contents
                    print(f"  ⚠️  {folder} already exists in target, merging...")
                    for item in source.iterdir():
                        target_item = target / item.name
                        if target_item.exists():
                            print(f"    ⚠️  {item.name} already exists, skipping...")
                        else:
                            shutil.move(str(item), str(target_item))
                            print(f"    ✅ Moved {item.name}")
                else:
                    shutil.move(str(source), str(target))
                    print(f"  ✅ Moved {folder}/")
                moved.append(folder)
            except Exception as e:
                print(f"  ❌ Error moving {folder}: {e}")
                skipped.append(folder)
        else:
            skipped.append(folder)
            print(f"  ⚠️  {folder} not found (skipping)")
    
    print(f"\n{description}:")
    print(f"  Moved: {len(moved)}")
    print(f"  Skipped: {len(skipped)}")
    return moved, skipped

def move_snw_whitepaper(snw_docs_dir):
    """Move SNW whitepaper from docs/whitepapers to snw/docs"""
    source = BASE_DIR / "docs" / "whitepapers" / "SOUTHERN_NEVADA_WILDLANDS.md"
    if source.exists():
        target = snw_docs_dir / "SOUTHERN_NEVADA_WILDLANDS.md"
        try:
            shutil.move(str(source), str(target))
            print(f"✅ Moved SNW whitepaper to snw/docs/")
            return True
        except Exception as e:
            print(f"❌ Error moving SNW whitepaper: {e}")
            return False
    else:
        print("⚠️  SNW whitepaper not found in docs/whitepapers/")
        return False

def main():
    """Main reorganization function"""
    print("=" * 60)
    print("LEF AI WORKSPACE REORGANIZATION")
    print("=" * 60)
    print()
    print("This will reorganize the workspace into:")
    print("  - lef-ai/     (LEF Ai project files)")
    print("  - fulcrum/    (stays as is)")
    print("  - snw/        (SNW project files)")
    print()
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response != 'yes':
        print("Cancelled.")
        return
    
    print("\n" + "=" * 60)
    print("STEP 1: Creating directories")
    print("=" * 60)
    lef_ai_dir, snw_docs_dir = create_directories()
    
    print("\n" + "=" * 60)
    print("STEP 2: Moving LEF Ai files")
    print("=" * 60)
    move_files(LEF_AI_FILES, lef_ai_dir, "LEF Ai Files")
    
    print("\n" + "=" * 60)
    print("STEP 3: Moving LEF Ai folders")
    print("=" * 60)
    move_folders(LEF_AI_FOLDERS, lef_ai_dir, "LEF Ai Folders")
    
    print("\n" + "=" * 60)
    print("STEP 4: Moving SNW files")
    print("=" * 60)
    move_files(SNW_FILES, BASE_DIR / "snw", "SNW Files")
    
    print("\n" + "=" * 60)
    print("STEP 5: Moving SNW whitepaper")
    print("=" * 60)
    move_snw_whitepaper(snw_docs_dir)
    
    print("\n" + "=" * 60)
    print("REORGANIZATION COMPLETE")
    print("=" * 60)
    print("\nNew structure:")
    print("  lef-ai/     - LEF Ai project files")
    print("  fulcrum/    - Fulcrum trading system (unchanged)")
    print("  snw/        - SNW project files")
    print("\n✅ All files moved. Please verify paths still work.")

if __name__ == "__main__":
    main()
