-- LEF Database Schema Migration
-- Date: 2026-02-05
-- Purpose: Fix missing tables/columns-- Migration 002: Fix Runtime Issues
-- Date: 2026-02-05
-- Root Cause: Multiple recurring errors identified in Structural Integrity Audit

-- 1. Fix missing knowledge_stream columns (Governance calculation errors)
ALTER TABLE knowledge_stream ADD COLUMN implication_bullish REAL DEFAULT 0.0;
ALTER TABLE knowledge_stream ADD COLUMN implication_bearish REAL DEFAULT 0.0;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_knowledge_stream_implication 
    ON knowledge_stream(implication_bullish, implication_bearish);

-- 2. Create agent_health_ledger (SURGEON monitoring errors)
CREATE TABLE IF NOT EXISTS agent_health_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    health_score INTEGER DEFAULT 100,
    crash_count INTEGER DEFAULT 0,
    chronic_issue_detected INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create lef_scars (AgentImmune stress calculation errors)
CREATE TABLE IF NOT EXISTS lef_scars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT,
    description TEXT,
    severity INTEGER DEFAULT 1,
    learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Create genesis_log if missing (AgentDean errors)
CREATE TABLE IF NOT EXISTS genesis_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT,
    description TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 5. Enable WAL mode for concurrent access (database locked errors)
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=30000;

-- To run this migration:
-- sqlite3 republic/republic.db < migrations/002_fix_runtime_issues.sql
