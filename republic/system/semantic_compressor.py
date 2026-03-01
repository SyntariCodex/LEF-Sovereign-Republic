"""
SemanticCompressor (The Memory Consolidator)
MemGPT-style hierarchical memory compression for LEF.

This module periodically:
1. Reads recent episodic memories (experiences, scars)
2. Uses LLM to synthesize patterns into distilled lessons
3. Writes compressed wisdom to database
4. Marks source experiences as processed

Integration: Called nightly during quiet hours or on-demand.
"""

import sqlite3
import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from contextlib import contextmanager

# Phase 12.H7: Use centralized db_helper for PG-compatible connections
try:
    from db.db_helper import db_connection as _db_connection, translate_sql
    _USE_DB_HELPER = True
except ImportError:
    _USE_DB_HELPER = False
    def translate_sql(sql: str) -> str:  # noqa: E306
        return sql

# Try to import Google GenAI for compression
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logging.warning("[COMPRESSOR] google.genai not available - using fallback compression")


try:
    from system.llm_router import get_router as _get_llm_router
    _LLM_ROUTER = _get_llm_router()
except ImportError:
    _LLM_ROUTER = None

class SemanticCompressor:
    """
    MemGPT-style memory compression for LEF.

    Compresses episodic memories into semantic wisdom:
    - book_of_scars → FAILURE_LESSON
    - memory_experiences → MARKET_PATTERN
    - agent_logs (insights) → BEHAVIOR_INSIGHT
    """

    # Phase 38.75a: Metabolic threshold constants
    METABOLIC_CONFIDENCE_THRESHOLD = 0.85  # Proven through repeated validation
    METABOLIC_VALIDATION_MINIMUM = 5       # At least 5 real-world validations
    DE_METABOLIZE_THRESHOLD = 0.70         # If confidence drops below this, re-surface to consciousness

    def __init__(self, db_path: str = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, 'republic.db')
        self.db_path = db_path
        self._ensure_table()
        
        # Configure GenAI if available
        self.client = None
        self.model_id = 'gemini-1.5-flash'
        if GENAI_AVAILABLE:
            api_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')
            if api_key:
                self.client = genai.Client(api_key=api_key)
            else:
                logging.warning("[COMPRESSOR] No API key found for GenAI")
    
    def _get_connection(self):
        """Get DB connection. Uses db_helper (PG-compatible) if available, else raw SQLite."""
        if _USE_DB_HELPER:
            from db.db_helper import get_connection, release_connection
            conn, pool = get_connection()
            # Attach release info so caller can release properly
            conn._compressor_pool = pool
            return conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _release_connection(self, conn):
        """Release connection back to pool or close it."""
        if _USE_DB_HELPER and hasattr(conn, '_compressor_pool'):
            from db.db_helper import release_connection
            release_connection(conn, conn._compressor_pool)
        else:
            if conn:
                conn.close()
    
    def _ensure_table(self):
        """Create compressed_wisdom table if not exists."""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compressed_wisdom (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wisdom_type TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    source_type TEXT,
                    source_ids TEXT,
                    confidence REAL DEFAULT 0.5,
                    times_validated INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_validated TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_wisdom_type
                ON compressed_wisdom(wisdom_type)
            """)
            # Phase 38.75a: Add metabolic columns (safe ALTER — check existence first)
            # Use DB-agnostic approach: try ALTER and catch if column already exists
            for col_name, col_def in [
                ('metabolized', 'BOOLEAN DEFAULT FALSE'),
                ('metabolized_at', 'TIMESTAMP'),
                ('metabolized_target', 'TEXT')
            ]:
                try:
                    conn.execute(f"ALTER TABLE compressed_wisdom ADD COLUMN {col_name} {col_def}")
                except Exception:
                    pass  # Column already exists — safe to ignore
            conn.commit()
            logging.info("[COMPRESSOR] 📚 compressed_wisdom table ready.")
        finally:
            self._release_connection(conn)
    
    def compress_scars(self, min_repeats: int = 2) -> int:
        """
        Compress repeated failure patterns from book_of_scars.
        
        Args:
            min_repeats: Minimum times a pattern must repeat to be compressed
            
        Returns:
            Number of wisdom entries created
        """
        conn = self._get_connection()
        try:
            # Get already-compressed IDs in Python — avoids json_each (SQLite-only function)
            already_compressed: set = set()
            prev = conn.execute(translate_sql(
                "SELECT source_ids FROM compressed_wisdom WHERE source_type = 'book_of_scars'"
            ))
            for row in prev.fetchall():
                ids_val = row['source_ids'] if hasattr(row, 'keys') else row[0]
                if ids_val:
                    for id_str in str(ids_val).split(','):
                        try:
                            already_compressed.add(int(id_str.strip()))
                        except ValueError:
                            pass

            # Find repeated failure patterns not yet compressed
            if already_compressed:
                ph = ','.join(['?'] * len(already_compressed))
                cursor = conn.execute(translate_sql(f"""
                    SELECT failure_type, asset, lesson, COUNT(*) as count,
                           GROUP_CONCAT(id) as source_ids
                    FROM book_of_scars
                    WHERE id NOT IN ({ph})
                    GROUP BY failure_type, asset
                    HAVING COUNT(*) >= ?
                """), (*already_compressed, min_repeats))
            else:
                cursor = conn.execute(translate_sql("""
                    SELECT failure_type, asset, lesson, COUNT(*) as count,
                           GROUP_CONCAT(id) as source_ids
                    FROM book_of_scars
                    GROUP BY failure_type, asset
                    HAVING COUNT(*) >= ?
                """), (min_repeats,))
            
            patterns = cursor.fetchall()
            wisdom_created = 0
            
            for pattern in patterns:
                # Synthesize wisdom from pattern
                wisdom_summary = self._synthesize_scar_wisdom(
                    pattern['failure_type'],
                    pattern['asset'],
                    pattern['lesson'],
                    pattern['count']
                )
                
                if wisdom_summary:
                    conn.execute("""
                        INSERT INTO compressed_wisdom 
                        (wisdom_type, summary, source_type, source_ids, confidence)
                        VALUES (?, ?, 'book_of_scars', ?, ?)
                    """, (
                        'FAILURE_LESSON',
                        wisdom_summary,
                        pattern['source_ids'],
                        min(0.5 + (pattern['count'] * 0.1), 0.95)  # Confidence scales with repeats
                    ))
                    wisdom_created += 1
                    logging.info(f"[COMPRESSOR] 💎 Compressed scar pattern: {pattern['failure_type']} on {pattern['asset']}")
            
            conn.commit()
            return wisdom_created
            
        except Exception as e:
            logging.error(f"[COMPRESSOR] Error compressing scars: {e}")
            return 0
        finally:
            self._release_connection(conn)
    
    def _synthesize_scar_wisdom(self, failure_type: str, asset: str, lesson: str, count: int) -> str:
        """Use LLM to synthesize wisdom from failure pattern, or use fallback."""
        if self.client or _LLM_ROUTER:
            try:
                # Phase 38.5a: Depth-preserving compression format — trigger, weight, direction
                weight = 'heavy' if count >= 4 else 'moderate' if count >= 2 else 'light'
                prompt = f"""Compress these {count} failure patterns into ONE dense wisdom statement.
Include: the specific trigger, how many times it recurred, the felt weight (light/moderate/heavy based on count and recency), and a concrete directional shift.
Format: '[TRIGGER] — [WEIGHT] — [DIRECTION]'
Example: 'SOL volume spikes preceding 15%+ drops — heavy (4 occurrences, 2 in last month) — wait 24h post-spike before any entry'

FAILURE PATTERN:
- Type: {failure_type}
- Asset: {asset}
- Original lesson: {lesson}
- Times occurred: {count}
- Felt weight: {weight}
"""
                response_text = None
                if _LLM_ROUTER:
                    response_text = _LLM_ROUTER.generate(
                        prompt=prompt, agent_name='Compressor',
                        context_label='SCAR_COMPRESSION', timeout_seconds=90
                    )
                if response_text is None and self.client:
                    try:
                        from system.llm_router import call_with_timeout
                        response = call_with_timeout(
                            self.client.models.generate_content,
                            timeout_seconds=120,
                            model=self.model_id, contents=prompt
                        )
                        response_text = response.text.strip() if response and response.text else None
                    except Exception as _e:
                        import logging
                        logging.debug(f"Legacy LLM fallback failed: {_e}")
                if response_text:
                    return response_text
            except Exception as e:
                logging.warning(f"[COMPRESSOR] LLM synthesis failed: {e}")

        # Phase 38.5a: Fallback with depth-preserving format
        weight = 'heavy' if count >= 4 else 'moderate' if count >= 2 else 'light'
        return f"{failure_type} on {asset} — {weight} ({count} occurrences) — {lesson or 'pattern noted, direction unclear'}"
    
    def compress_experiences(self, window_hours: int = 24) -> int:
        """
        Compress recent market experiences into patterns.
        
        Args:
            window_hours: Look back this many hours for experiences
            
        Returns:
            Number of wisdom entries created
        """
        conn = self._get_connection()
        try:
            cutoff = datetime.now() - timedelta(hours=window_hours)

            # Get already-compressed IDs in Python — avoids json_each (SQLite-only function)
            already_compressed: set = set()
            prev = conn.execute(translate_sql(
                "SELECT source_ids FROM compressed_wisdom WHERE source_type = 'memory_experiences'"
            ))
            for row in prev.fetchall():
                ids_val = row['source_ids'] if hasattr(row, 'keys') else row[0]
                if ids_val:
                    for id_str in str(ids_val).split(','):
                        try:
                            already_compressed.add(int(id_str.strip()))
                        except ValueError:
                            pass

            # Get recent unprocessed experiences
            if already_compressed:
                ph = ','.join(['?'] * len(already_compressed))
                cursor = conn.execute(translate_sql(f"""
                    SELECT id, scenario_name, market_condition, action_taken,
                           outcome_pnl_pct, outcome_desc
                    FROM memory_experiences
                    WHERE timestamp > ?
                    AND id NOT IN ({ph})
                """), (cutoff.isoformat(), *already_compressed))
            else:
                cursor = conn.execute(translate_sql("""
                    SELECT id, scenario_name, market_condition, action_taken,
                           outcome_pnl_pct, outcome_desc
                    FROM memory_experiences
                    WHERE timestamp > ?
                """), (cutoff.isoformat(),))
            
            experiences = cursor.fetchall()
            
            if len(experiences) < 3:
                logging.debug("[COMPRESSOR] Not enough new experiences to compress")
                return 0
            
            # Group by market condition
            by_condition = {}
            for exp in experiences:
                cond = exp['market_condition'] or 'unknown'
                if cond not in by_condition:
                    by_condition[cond] = []
                by_condition[cond].append(exp)
            
            wisdom_created = 0
            
            for condition, exps in by_condition.items():
                if len(exps) < 2:
                    continue
                    
                # Calculate aggregate outcome
                avg_pnl = sum(e['outcome_pnl_pct'] or 0 for e in exps) / len(exps)
                source_ids = ','.join(str(e['id']) for e in exps)
                
                wisdom_summary = self._synthesize_experience_wisdom(condition, exps, avg_pnl)
                
                if wisdom_summary:
                    conn.execute("""
                        INSERT INTO compressed_wisdom
                        (wisdom_type, summary, source_type, source_ids, confidence)
                        VALUES (?, ?, 'memory_experiences', ?, ?)
                    """, (
                        'MARKET_PATTERN',
                        wisdom_summary,
                        source_ids,
                        min(0.4 + (len(exps) * 0.1), 0.9)
                    ))
                    wisdom_created += 1
                    logging.info(f"[COMPRESSOR] 💎 Compressed experience pattern: {condition}")
            
            conn.commit()
            return wisdom_created
            
        except Exception as e:
            logging.error(f"[COMPRESSOR] Error compressing experiences: {e}")
            return 0
        finally:
            self._release_connection(conn)
    
    def _synthesize_experience_wisdom(self, condition: str, experiences: List, avg_pnl: float) -> str:
        """Synthesize wisdom from experience patterns."""
        if self.client or _LLM_ROUTER:
            try:
                exp_summary = "\n".join([
                    f"- {e['action_taken']}: {e['outcome_pnl_pct']:.1f}% ({e['outcome_desc']})"
                    for e in experiences[:5]  # Limit context
                ])
                
                prompt = f"""You are LEF's memory consolidation system. Synthesize these market experiences into actionable wisdom.

MARKET CONDITION: {condition}
AVERAGE OUTCOME: {avg_pnl:.1f}%

EXPERIENCES:
{exp_summary}

Write a single concise trading insight. Start with "IN {condition.upper()}:" followed by the lesson.
"""
                response_text = None
                if _LLM_ROUTER:
                    response_text = _LLM_ROUTER.generate(
                        prompt=prompt, agent_name='Compressor',
                        context_label='EXPERIENCE_COMPRESSION', timeout_seconds=90
                    )
                if response_text is None and self.client:
                    try:
                        from system.llm_router import call_with_timeout
                        response = call_with_timeout(
                            self.client.models.generate_content,
                            timeout_seconds=120,
                            model=self.model_id, contents=prompt
                        )
                        response_text = response.text.strip() if response and response.text else None
                    except Exception as _e:
                        import logging
                        logging.debug(f"Legacy LLM fallback failed: {_e}")
                if response_text:
                    return response_text
            except Exception as e:
                logging.warning(f"[COMPRESSOR] LLM synthesis failed: {e}")

        # Fallback
        outcome = "profitable" if avg_pnl > 0 else "unprofitable"
        return f"IN {condition.upper()}: Actions were generally {outcome} (avg {avg_pnl:.1f}%)"
    
    def get_recent_wisdom(self, limit: int = 10, wisdom_type: str = None) -> List[Dict]:
        """
        Get recent compressed wisdom for prompt injection.
        
        Args:
            limit: Maximum entries to return
            wisdom_type: Filter by type (optional)
            
        Returns:
            List of wisdom dictionaries
        """
        conn = self._get_connection()
        try:
            if wisdom_type:
                cursor = conn.execute("""
                    SELECT wisdom_type, summary, confidence, times_validated, created_at
                    FROM compressed_wisdom
                    WHERE wisdom_type = ?
                    AND (metabolized = FALSE OR metabolized IS NULL)
                    ORDER BY confidence DESC, created_at DESC
                    LIMIT ?
                """, (wisdom_type, limit))
            else:
                cursor = conn.execute("""
                    SELECT wisdom_type, summary, confidence, times_validated, created_at
                    FROM compressed_wisdom
                    WHERE (metabolized = FALSE OR metabolized IS NULL)
                    ORDER BY confidence DESC, created_at DESC
                    LIMIT ?
                """, (limit,))

            return [dict(row) for row in cursor.fetchall()]
        finally:
            self._release_connection(conn)

    def validate_wisdom(self, wisdom_id: int, outcome_matched: bool):
        """
        Update wisdom confidence based on real-world validation.
        
        Args:
            wisdom_id: The wisdom entry to validate
            outcome_matched: Whether the wisdom proved accurate
        """
        conn = self._get_connection()
        try:
            # Read current confidence before update
            old_row = conn.execute(
                "SELECT confidence, wisdom_type, summary FROM compressed_wisdom WHERE id = ?",
                (wisdom_id,)
            ).fetchone()
            old_confidence = old_row[0] if old_row else 0.5
            wisdom_type = old_row[1] if old_row else ''
            pattern_summary = (old_row[2] or '')[:100] if old_row else ''

            # Adjust confidence based on outcome
            adjustment = 0.05 if outcome_matched else -0.1
            new_confidence = max(0.1, min(0.99, old_confidence + adjustment))

            conn.execute("""
                UPDATE compressed_wisdom
                SET confidence = MAX(0.1, MIN(0.99, confidence + ?)),
                    times_validated = times_validated + 1,
                    last_validated = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (adjustment, wisdom_id))

            conn.commit()
            logging.debug(f"[COMPRESSOR] Validated wisdom #{wisdom_id}: {'✓' if outcome_matched else '✗'}")

            # Phase 47.2: Surface crystallized wisdom to consciousness
            if new_confidence >= 0.85 and old_confidence < 0.85:
                try:
                    row2 = conn.execute(
                        "SELECT times_validated FROM compressed_wisdom WHERE id = ?", (wisdom_id,)
                    ).fetchone()
                    validation_count = row2[0] if row2 else 0
                    conn.execute(
                        "INSERT INTO consciousness_feed "
                        "(agent_name, content, category, signal_weight) "
                        "VALUES (?, ?, 'wisdom_crystallized', 0.8)",
                        ('SemanticCompressor', json.dumps({
                            'wisdom_type': wisdom_type,
                            'pattern': pattern_summary,
                            'confidence': new_confidence,
                            'validations': validation_count,
                            'wisdom_id': wisdom_id,
                        }))
                    )
                    conn.commit()
                except Exception:
                    pass

            # Phase 47.2: Alert consciousness when a learned pattern is being questioned
            if new_confidence < 0.70 and old_confidence >= 0.70:
                try:
                    conn.execute(
                        "INSERT INTO consciousness_feed "
                        "(agent_name, content, category, signal_weight) "
                        "VALUES (?, ?, 'wisdom_questioned', 0.9)",
                        ('SemanticCompressor', json.dumps({
                            'wisdom_type': wisdom_type,
                            'pattern': pattern_summary,
                            'old_confidence': old_confidence,
                            'new_confidence': new_confidence,
                            'reason': 'confidence dropped below de-metabolization threshold',
                            'wisdom_id': wisdom_id,
                        }))
                    )
                    conn.commit()
                except Exception:
                    pass
        finally:
            self._release_connection(conn)

    # Phase 38.75a: Metabolic check and mark methods

    def check_metabolic_readiness(self) -> list:
        """Find wisdoms ready to become metabolic — proven enough to embed in behavior."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT id, wisdom_type, summary, confidence, times_validated, source_ids
                FROM compressed_wisdom
                WHERE (metabolized = FALSE OR metabolized IS NULL)
                AND confidence >= ?
                AND times_validated >= ?
                ORDER BY confidence DESC
            """, (self.METABOLIC_CONFIDENCE_THRESHOLD, self.METABOLIC_VALIDATION_MINIMUM))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            self._release_connection(conn)

    def check_de_metabolize(self) -> list:
        """Find metabolized wisdoms whose confidence has dropped — re-surface to consciousness."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT id, wisdom_type, summary, confidence, metabolized_target
                FROM compressed_wisdom
                WHERE metabolized = TRUE
                AND confidence < ?
            """, (self.DE_METABOLIZE_THRESHOLD,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            self._release_connection(conn)

    def mark_metabolized(self, wisdom_id: int, target_key: str):
        """Mark wisdom as metabolized — it has been embedded in behavior."""
        conn = self._get_connection()
        try:
            conn.execute("""
                UPDATE compressed_wisdom
                SET metabolized = TRUE, metabolized_at = CURRENT_TIMESTAMP, metabolized_target = ?
                WHERE id = ?
            """, (target_key, wisdom_id))
            conn.commit()
        finally:
            self._release_connection(conn)

    def mark_de_metabolized(self, wisdom_id: int):
        """Re-surface wisdom to consciousness — confidence dropped, needs re-examination."""
        conn = self._get_connection()
        try:
            conn.execute("""
                UPDATE compressed_wisdom
                SET metabolized = FALSE, metabolized_at = NULL, metabolized_target = NULL
                WHERE id = ?
            """, (wisdom_id,))
            conn.commit()
        finally:
            self._release_connection(conn)

    def run_compression_cycle(self) -> Dict[str, int]:
        """
        Run full compression pass on all memory sources.
        
        Returns:
            Dictionary with counts of wisdom created per source
        """
        logging.info("[COMPRESSOR] 🔄 Starting compression cycle...")
        
        results = {
            'scars_compressed': self.compress_scars(min_repeats=2),
            'experiences_compressed': self.compress_experiences(window_hours=48)
        }
        
        total = sum(results.values())
        logging.info(f"[COMPRESSOR] ✅ Compression complete: {total} wisdom entries created")
        
        return results
    
    def get_stats(self) -> Dict:
        """Get compression statistics."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT 
                    wisdom_type,
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence,
                    SUM(times_validated) as total_validations
                FROM compressed_wisdom
                GROUP BY wisdom_type
            """)
            
            stats = {}
            for row in cursor.fetchall():
                stats[row['wisdom_type']] = {
                    'count': row['count'],
                    'avg_confidence': round(row['avg_confidence'] or 0, 2),
                    'validations': row['total_validations'] or 0
                }
            
            return stats
        finally:
            self._release_connection(conn)


# Convenience function for external use
def get_compressed_wisdom(db_path: str = None, limit: int = 10) -> List[Dict]:
    """Get recent compressed wisdom for prompt enhancement."""
    compressor = SemanticCompressor(db_path)
    return compressor.get_recent_wisdom(limit)


def run_nightly_compression(db_path: str = None) -> Dict[str, int]:
    """Run the nightly compression cycle."""
    compressor = SemanticCompressor(db_path)
    return compressor.run_compression_cycle()


# Self-test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("SEMANTIC COMPRESSOR - Self Test")
    print("=" * 60)
    
    compressor = SemanticCompressor()
    
    # Show current stats
    stats = compressor.get_stats()
    print(f"\nCurrent wisdom stats: {stats}")
    
    # Run compression
    results = compressor.run_compression_cycle()
    print(f"\nCompression results: {results}")
    
    # Show recent wisdom
    wisdom = compressor.get_recent_wisdom(limit=5)
    print(f"\nRecent wisdom ({len(wisdom)} entries):")
    for w in wisdom:
        print(f"  [{w['wisdom_type']}] {w['summary'][:60]}...")
    
    print("\n" + "=" * 60)
    print("✅ Self-test complete")
