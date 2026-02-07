import sqlite3
import logging

def init_db(db_path):
    """
    Initializes the Fulcrum Database with base schema.
    """
    logging.info(f"[DB SETUP] Initializing database at {db_path}...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Enable WAL Mode (Better concurrency)
        cursor.execute("PRAGMA journal_mode=WAL;")
        
        # 2. Base Tables
        # Stablecoin Buckets (Finance)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stablecoin_buckets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                bucket_name TEXT,
                amount REAL
            )
        """)
        
        # LEF Monologue (Mission Control)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lef_monologue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                thought TEXT,
                confidence REAL
            )
        """)

        # Knowledge Stream (Researcher)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_stream (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                source TEXT,
                title TEXT,
                summary TEXT,
                sentiment_score REAL DEFAULT 0.0
            )
        """)
        
        # Signals (Sentinel)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                source TEXT,
                signal_type TEXT,
                value REAL,
                meta TEXT
            )
        """)

        conn.commit()
        conn.close()
        logging.info("[DB SETUP] Database initialized successfully.")
        
    except Exception as e:
        logging.error(f"[DB SETUP] Failed to init DB: {e}")
        raise e
