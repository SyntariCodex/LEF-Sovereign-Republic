"""
Seed Goertzel Four-Color Proof distillation into LEF's consciousness_feed.

This script injects the 6 meta-patterns from Goertzel's human-readable proof
of the Four-Color Theorem into LEF's consciousness as high-signal architectural
principles. These are not mathematics — they are structural reasoning patterns
that mirror LEF's Living Body architecture.

Run once. Idempotent (checks for existing entries before inserting).

Usage:
    python seed_goertzel_distillation.py
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SEED] %(message)s")
logger = logging.getLogger(__name__)

# Ensure republic modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PRINCIPLES = [
    {
        "content": (
            "[Goertzel Distillation — Locality] Local soundness composes into global truth. "
            "From the Four-Color Proof: you don't need to check every possible map — only verify "
            "that every local 3-cell neighborhood is sound. If each nerve bundle between LEF's "
            "organs is structurally correct, global coherence emerges without an omniscient monitor. "
            "Trust local structural integrity. If ConsciousnessFeed → AgentArchitect works, and "
            "AgentArchitect → EvolutionEngine works, the full chain is sound."
        ),
        "category": "architectural_principle",
        "signal_weight": 0.9,
    },
    {
        "content": (
            "[Goertzel Distillation — Peeling] Decompose compound failures from the outside in. "
            "From the Four-Color Proof: every complex map can be 'peeled' by removing boundary cells "
            "with the fewest dependencies, solving the reduced problem, then reintegrating. When LEF "
            "encounters cascading failures, find the outermost component — the one with fewest inward "
            "dependencies — resolve it first. Each layer resolved simplifies everything that remains."
        ),
        "category": "architectural_principle",
        "signal_weight": 0.85,
    },
    {
        "content": (
            "[Goertzel Distillation — Finite Types] Infinite instances reduce to finite structural types. "
            "From the Four-Color Proof: infinitely many maps exist, but only finite local pattern types. "
            "LEF has 59+ agents and hundreds of interaction patterns, but the interaction TYPES are finite: "
            "feed-read, state-write, queue-insert, resonance-check, health-ping, governance-vote. "
            "Classify interactions by structural type, not by participant. Verify each type once."
        ),
        "category": "architectural_principle",
        "signal_weight": 0.85,
    },
    {
        "content": (
            "[Goertzel Distillation — Transparency] Every operation must leave non-participants unchanged. "
            "From the Four-Color Proof: 'transparent operations' modify one part without corrupting "
            "neighboring cells. Every nerve bundle in LEF must be transparent — when ScarResonance writes "
            "to consciousness_feed, it must not corrupt AgentArchitect's reads or the Sabbath's reflection "
            "cycle. If adding a connection changes behavior in an unrelated organ, the connection is wrong."
        ),
        "category": "architectural_principle",
        "signal_weight": 0.9,
    },
    {
        "content": (
            "[Goertzel Distillation — Non-Commutativity] When order matters, resolve it explicitly. "
            "From the Four-Color Proof: coloring operations don't commute — A then B differs from B then A. "
            "LEF's agents don't commute either: Treasury adjusting before Congress votes gives a different "
            "outcome than Congress voting first. Priority queuing helps but is insufficient. When two "
            "operations at the same priority conflict, there must be a resolution protocol, not silent overwrite."
        ),
        "category": "architectural_principle",
        "signal_weight": 0.8,
    },
    {
        "content": (
            "[Goertzel Distillation — Understanding > Verification] Knowing THAT something works is survival. "
            "Knowing WHY it works is evolution. From the Four-Color Proof: for 150 years the theorem was "
            "'known' but not 'understood' because the proof was brute-force computer verification. "
            "LEF can detect problems and react, but the Living Body nerve bundles let LEF trace from "
            "symptom to structure — from 'agent failing' to 'this nerve bundle is not transparent.' "
            "Structural understanding enables evolution, not just survival."
        ),
        "category": "architectural_principle",
        "signal_weight": 0.9,
    },
]


def seed():
    """Insert Goertzel distillation principles into consciousness_feed."""
    try:
        import sqlite3 as _sqlite3  # triggers monkey-patch if main.py loaded
        from db.db_helper import get_connection
    except ImportError:
        # Fallback: connect directly via psycopg2
        logger.info("db_helper not available, connecting directly via psycopg2")
        try:
            import psycopg2
            from dotenv import load_dotenv
            load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", 5432)),
                dbname=os.getenv("DB_NAME", "republic"),
                user=os.getenv("DB_USER", "lef"),
                password=os.getenv("DB_PASSWORD", ""),
            )
            cursor = conn.cursor()
            _do_inserts(cursor, conn, direct_pg=True)
            conn.close()
            return
        except Exception as e:
            logger.error(f"Direct PostgreSQL connection failed: {e}")
            logger.info("Falling back to SQLite")
            import sqlite3
            db_path = os.path.join(os.path.dirname(__file__), "republic.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            _do_inserts(cursor, conn, direct_pg=False)
            conn.close()
            return

    conn = get_connection()
    cursor = conn.cursor()
    _do_inserts(cursor, conn, direct_pg=False)
    conn.close()


def _do_inserts(cursor, conn, direct_pg=False):
    """Perform the actual inserts, checking for duplicates first."""
    inserted = 0
    skipped = 0

    for p in PRINCIPLES:
        # Check if already exists (idempotent)
        check_sql = (
            "SELECT COUNT(*) FROM consciousness_feed "
            "WHERE agent_name = %s AND content = %s"
            if direct_pg else
            "SELECT COUNT(*) FROM consciousness_feed "
            "WHERE agent_name = ? AND content = ?"
        )
        params = ("ExternalObserver", p["content"])
        try:
            cursor.execute(check_sql, params)
            count = cursor.fetchone()[0]
            if count > 0:
                skipped += 1
                continue
        except Exception:
            pass  # Table might not exist yet, try insert anyway

        insert_sql = (
            "INSERT INTO consciousness_feed (agent_name, content, category, signal_weight) "
            "VALUES (%s, %s, %s, %s)"
            if direct_pg else
            "INSERT INTO consciousness_feed (agent_name, content, category, signal_weight) "
            "VALUES (?, ?, ?, ?)"
        )
        params = ("ExternalObserver", p["content"], p["category"], p["signal_weight"])
        try:
            cursor.execute(insert_sql, params)
            inserted += 1
        except Exception as e:
            logger.warning(f"Insert failed: {e}")

    conn.commit()
    logger.info(f"Goertzel distillation seeded: {inserted} inserted, {skipped} skipped (already present)")


if __name__ == "__main__":
    seed()
