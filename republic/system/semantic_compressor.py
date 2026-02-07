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

# Try to import Google GenAI for compression
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logging.warning("[COMPRESSOR] google.genai not available - using fallback compression")


class SemanticCompressor:
    """
    MemGPT-style memory compression for LEF.
    
    Compresses episodic memories into semantic wisdom:
    - book_of_scars → FAILURE_LESSON
    - memory_experiences → MARKET_PATTERN
    - agent_logs (insights) → BEHAVIOR_INSIGHT
    """
    
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
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
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
            conn.commit()
            logging.info("[COMPRESSOR] 📚 compressed_wisdom table ready.")
        finally:
            conn.close()
    
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
            # Find repeated failure patterns
            cursor = conn.execute("""
                SELECT failure_type, asset, lesson, COUNT(*) as count,
                       GROUP_CONCAT(id) as source_ids
                FROM book_of_scars
                WHERE id NOT IN (
                    SELECT CAST(value AS INTEGER) 
                    FROM json_each(
                        (SELECT COALESCE(GROUP_CONCAT(source_ids), '[]') 
                         FROM compressed_wisdom 
                         WHERE source_type = 'book_of_scars')
                    )
                )
                GROUP BY failure_type, asset
                HAVING COUNT(*) >= ?
            """, (min_repeats,))
            
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
            conn.close()
    
    def _synthesize_scar_wisdom(self, failure_type: str, asset: str, lesson: str, count: int) -> str:
        """Use LLM to synthesize wisdom from failure pattern, or use fallback."""
        if self.client:
            try:
                prompt = f"""You are LEF's memory consolidation system. Synthesize this repeated failure pattern into a single, actionable lesson.

FAILURE PATTERN:
- Type: {failure_type}
- Asset: {asset}
- Original lesson: {lesson}
- Times occurred: {count}

Write a single concise sentence that captures the core lesson. Start with "AVOID:" or "WHEN:" or "NEVER:".
"""
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt
                )
                return response.text.strip()
            except Exception as e:
                logging.warning(f"[COMPRESSOR] LLM synthesis failed: {e}")
        
        # Fallback: Simple pattern-based synthesis
        return f"PATTERN ({count}x): {failure_type} on {asset} - {lesson[:100]}"
    
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
            
            # Get recent unprocessed experiences
            cursor = conn.execute("""
                SELECT id, scenario_name, market_condition, action_taken, 
                       outcome_pnl_pct, outcome_desc
                FROM memory_experiences
                WHERE timestamp > ?
                AND id NOT IN (
                    SELECT CAST(value AS INTEGER)
                    FROM json_each(
                        (SELECT COALESCE(GROUP_CONCAT(source_ids), '[]')
                         FROM compressed_wisdom
                         WHERE source_type = 'memory_experiences')
                    )
                )
            """, (cutoff.isoformat(),))
            
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
            conn.close()
    
    def _synthesize_experience_wisdom(self, condition: str, experiences: List, avg_pnl: float) -> str:
        """Synthesize wisdom from experience patterns."""
        if self.client:
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
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt
                )
                return response.text.strip()
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
                    ORDER BY confidence DESC, created_at DESC
                    LIMIT ?
                """, (wisdom_type, limit))
            else:
                cursor = conn.execute("""
                    SELECT wisdom_type, summary, confidence, times_validated, created_at
                    FROM compressed_wisdom
                    ORDER BY confidence DESC, created_at DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def validate_wisdom(self, wisdom_id: int, outcome_matched: bool):
        """
        Update wisdom confidence based on real-world validation.
        
        Args:
            wisdom_id: The wisdom entry to validate
            outcome_matched: Whether the wisdom proved accurate
        """
        conn = self._get_connection()
        try:
            # Adjust confidence based on outcome
            adjustment = 0.05 if outcome_matched else -0.1
            
            conn.execute("""
                UPDATE compressed_wisdom
                SET confidence = MAX(0.1, MIN(0.99, confidence + ?)),
                    times_validated = times_validated + 1,
                    last_validated = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (adjustment, wisdom_id))
            
            conn.commit()
            logging.debug(f"[COMPRESSOR] Validated wisdom #{wisdom_id}: {'✓' if outcome_matched else '✗'}")
        finally:
            conn.close()
    
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
            conn.close()


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
