import sqlite3
import os
from pathlib import Path
from republic.db.db_setup import init_db

def test_db_initialization(db_path):
    """Test that the database initializes with the correct schema."""
    # Run initialization
    init_db(str(db_path))
    
    assert db_path.exists()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check for key tables from LEF_CANON/schema
    tables = [
        "stablecoin_buckets",
        "assets",
        "lef_monologue",
        "snw_proposals"
    ]
    
    for table in tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        assert cursor.fetchone() is not None, f"Table {table} failed to create"
        
    conn.close()

def test_directory_structure():
    """Verify essential project structure exists."""
    root = Path(__file__).parent.parent
    assert (root / "republic").exists()
    assert (root / "Dockerfile").exists()
    assert (root / "LEF_CANON.md").exists()
