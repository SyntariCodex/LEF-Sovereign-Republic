"""
Emotional Gate (The Feeling Mind)
Integrates mood states into trading decisions.

This module:
1. Aggregates recent mood data from lef_monologue
2. Calculates emotional state (fear/confidence/neutral)
3. Returns sizing multipliers and caution flags for trades
4. Logs emotional influence on decisions

Usage:
    from system.emotional_gate import get_emotional_gate
    
    gate = get_emotional_gate()
    result = gate.check_emotional_state()
    
    if result['sizing_multiplier'] < 1.0:
        position_size *= result['sizing_multiplier']
"""

import sqlite3
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

try:
    from db.db_helper import table_exists as _table_exists
except ImportError:
    def _table_exists(cursor, table_name):  # noqa: E306
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        return cursor.fetchone() is not None

# Path setup
from pathlib import Path
BASE_DIR = Path(__file__).parent.parent
DB_PATH = os.getenv('DB_PATH', str(BASE_DIR / 'republic.db'))


class EmotionalGate:
    """
    The Feeling Mind: Emotional integration with decision-making.
    
    Emotions aren't weaknesses—they're data.
    Fear indicates risk. Confidence indicates opportunity.
    This gate translates feelings into sizing adjustments.
    """
    
    # Emotional state thresholds
    FEAR_THRESHOLD = 30  # Below this = elevated fear
    CONFIDENCE_THRESHOLD = 70  # Above this = high confidence
    
    # Sizing multipliers
    FEAR_SIZING_MULTIPLIER = 0.5  # Reduce positions by 50% during fear
    NEUTRAL_SIZING_MULTIPLIER = 1.0
    CONFIDENCE_SIZING_MULTIPLIER = 1.2  # Increase by 20% during confidence (with caution)
    
    # Lookback for mood aggregation
    MOOD_LOOKBACK_HOURS = 24
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self.hippocampus = None
        self._previous_state = None  # Phase 32.4: For exponential smoothing

        # Try to connect to Hippocampus for scar context
        try:
            from departments.Dept_Consciousness.claude_context_manager import get_claude_context_manager
            self.hippocampus = get_claude_context_manager()
        except ImportError:
            pass

        # Phase 32.4: Load persisted emotional state
        self._load_persisted_state()
    
    def check_emotional_state(self) -> Dict:
        """
        Check current emotional state and return trading guidance.
        
        Returns:
            Dict with:
                - state: 'FEAR', 'NEUTRAL', 'CONFIDENT'
                - score: 0-100 emotional score
                - sizing_multiplier: float for position sizing
                - caution_flags: list of warnings
                - mood_history: recent mood trend
        """
        result = {
            "state": "NEUTRAL",
            "score": 50,
            "sizing_multiplier": self.NEUTRAL_SIZING_MULTIPLIER,
            "caution_flags": [],
            "mood_history": [],
            "checked_at": datetime.now().isoformat(),
            # Phase 32.5: Explicit stress/fear/joy levels (0.0 - 1.0)
            "stress_level": 0.0,
            "fear_level": 0.0,
            "joy_level": 0.0,
            "risk_multiplier": 1.0,
        }
        
        # 1. Get recent mood data
        moods = self._get_recent_moods()
        result["mood_history"] = moods
        
        if not moods:
            # No mood data, remain neutral
            return result
        
        # 2. Calculate aggregate mood score
        mood_scores = [m.get("score", 50) for m in moods]
        avg_score = sum(mood_scores) / len(mood_scores)
        result["score"] = round(avg_score, 1)
        
        # Phase 32.5: Compute stress, fear, joy levels (0.0 - 1.0)
        # Low score → high fear/stress. High score → high joy.
        result["fear_level"] = round(max(0.0, (self.FEAR_THRESHOLD - avg_score) / self.FEAR_THRESHOLD), 2)
        result["stress_level"] = round(max(0.0, (50 - avg_score) / 50), 2)
        result["joy_level"] = round(max(0.0, (avg_score - 50) / 50), 2)

        # Phase 32.5: Formula-based risk multiplier
        # risk_multiplier = 1.0 - (stress * 0.3) - (fear * 0.2)
        risk_mult = 1.0 - (result["stress_level"] * 0.3) - (result["fear_level"] * 0.2)
        result["risk_multiplier"] = round(max(0.1, risk_mult), 3)

        # 3. Determine emotional state
        if avg_score < self.FEAR_THRESHOLD:
            result["state"] = "FEAR"
            result["sizing_multiplier"] = self.FEAR_SIZING_MULTIPLIER
            result["caution_flags"].append(f"Elevated fear detected (score: {avg_score:.0f})")
            logging.warning(f"[EMOTIONAL_GATE] 😰 FEAR state - sizing reduced to {self.FEAR_SIZING_MULTIPLIER*100:.0f}%")
            
        elif avg_score > self.CONFIDENCE_THRESHOLD:
            result["state"] = "CONFIDENT"
            
            # Check for recent scars - high confidence + recent wounds = danger
            recent_scars = self._check_recent_scars()
            if recent_scars:
                result["caution_flags"].append(f"High confidence but {len(recent_scars)} recent scars - proceed cautiously")
                result["sizing_multiplier"] = self.NEUTRAL_SIZING_MULTIPLIER  # Don't increase
            else:
                result["sizing_multiplier"] = self.CONFIDENCE_SIZING_MULTIPLIER
                
            logging.info(f"[EMOTIONAL_GATE] 😊 CONFIDENT state (score: {avg_score:.0f})")
        
        else:
            result["state"] = "NEUTRAL"
            result["sizing_multiplier"] = self.NEUTRAL_SIZING_MULTIPLIER
        
        # 4. Check for emotional volatility (rapid swings)
        if len(moods) >= 3:
            volatility = self._calculate_mood_volatility(mood_scores)
            if volatility > 20:  # High volatility threshold
                result["caution_flags"].append(f"Emotional volatility detected ({volatility:.0f})")
                result["sizing_multiplier"] = min(result["sizing_multiplier"], 0.75)
        
        # 5. Check for fear streak
        fear_streak = self._count_fear_streak(moods)
        if fear_streak >= 3:
            result["caution_flags"].append(f"Fear persisting for {fear_streak} cycles - defensive mode")
            result["sizing_multiplier"] = 0.3  # Severe reduction

        # Phase 32.4: Exponential smoothing with previous state
        if self._previous_state is not None:
            prev_score = self._previous_state.get('score', 50)
            result["score"] = round(0.3 * result["score"] + 0.7 * prev_score, 1)

        # Phase 32.4: Persist current state
        self._previous_state = result
        self._persist_state(result)

        return result
    
    def _get_recent_moods(self) -> list:
        """Get recent mood entries from lef_monologue table."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            c = conn.cursor()
            
            # Check if table exists
            if not _table_exists(c, 'lef_monologue'):
                conn.close()
                return []
            
            # Get recent moods
            cutoff = (datetime.now() - timedelta(hours=self.MOOD_LOOKBACK_HOURS)).isoformat()
            
            c.execute("""
                SELECT timestamp, mood, intensity, content
                FROM lef_monologue
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 20
            """, (cutoff,))
            
            moods = []
            for row in c.fetchall():
                # Convert mood to score (simplified)
                mood_text = (row[1] or "").lower()
                intensity = row[2] or 50
                
                if any(word in mood_text for word in ['fear', 'anxious', 'worried', 'panic', 'scared']):
                    base_score = 20
                elif any(word in mood_text for word in ['confident', 'optimistic', 'excited', 'happy']):
                    base_score = 80
                elif any(word in mood_text for word in ['cautious', 'uncertain', 'contemplative']):
                    base_score = 45
                else:
                    base_score = 50
                
                # Adjust by intensity
                score = base_score * (intensity / 50.0)
                score = max(0, min(100, score))
                
                moods.append({
                    "timestamp": row[0],
                    "mood": row[1],
                    "intensity": intensity,
                    "score": score
                })
            
            conn.close()
            return moods
            
        except Exception as e:
            logging.debug(f"[EMOTIONAL_GATE] Could not fetch moods: {e}")
            return []
    
    def _check_recent_scars(self) -> list:
        """Check for recent scars that should temper confidence."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            c = conn.cursor()
            
            if not _table_exists(c, 'book_of_scars'):
                conn.close()
                return []
            
            # Get scars from last 7 days
            c.execute("""
                SELECT failure_type, severity
                FROM book_of_scars
                WHERE last_seen >= date('now', '-7 days')
                AND severity IN ('CRITICAL', 'HIGH')
                LIMIT 5
            """)
            
            scars = [{"type": row[0], "severity": row[1]} for row in c.fetchall()]
            conn.close()
            return scars
            
        except Exception as e:
            logging.debug(f"[EMOTIONAL_GATE] Could not fetch scars: {e}")
            return []
    
    def _calculate_mood_volatility(self, scores: list) -> float:
        """Calculate variance in mood scores."""
        if len(scores) < 2:
            return 0.0
        
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        return variance ** 0.5  # Standard deviation
    
    def _count_fear_streak(self, moods: list) -> int:
        """Count consecutive fear entries."""
        streak = 0
        for mood in moods:
            if mood.get("score", 50) < self.FEAR_THRESHOLD:
                streak += 1
            else:
                break  # Streak broken
        return streak
    
    def record_emotional_influence(self, action: str, asset: str, 
                                   original_size: float, adjusted_size: float,
                                   emotional_state: Dict):
        """Log when emotions influenced a trading decision."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            c = conn.cursor()
            
            c.execute("""
                CREATE TABLE IF NOT EXISTS emotional_influence_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    action TEXT,
                    asset TEXT,
                    original_size REAL,
                    adjusted_size REAL,
                    emotional_state TEXT,
                    mood_score REAL,
                    sizing_multiplier REAL
                )
            """)
            
            c.execute("""
                INSERT INTO emotional_influence_log 
                (action, asset, original_size, adjusted_size, emotional_state, mood_score, sizing_multiplier)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                action,
                asset,
                original_size,
                adjusted_size,
                emotional_state.get("state", "NEUTRAL"),
                emotional_state.get("score", 50),
                emotional_state.get("sizing_multiplier", 1.0)
            ))
            
            conn.commit()
            conn.close()
            
            logging.info(f"[EMOTIONAL_GATE] 📊 Logged emotional influence: {action} {asset} "
                        f"({emotional_state['state']} → {emotional_state['sizing_multiplier']*100:.0f}% sizing)")
            
        except Exception as e:
            logging.debug(f"[EMOTIONAL_GATE] Could not log influence: {e}")

    def _load_persisted_state(self):
        """Phase 32.4: Load last emotional state from DB. Provides continuity across restarts."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            c = conn.cursor()

            # Check if system_state table exists
            if not _table_exists(c, 'system_state'):
                conn.close()
                return

            c.execute("SELECT value FROM system_state WHERE key = 'emotional_state'")
            row = c.fetchone()
            conn.close()

            if row:
                try:
                    self._previous_state = json.loads(row[0])
                    logging.info(
                        f"[EMOTIONAL_GATE] Loaded persisted state: "
                        f"{self._previous_state.get('state', 'UNKNOWN')} "
                        f"(score={self._previous_state.get('score', '?')})"
                    )
                except (json.JSONDecodeError, TypeError):
                    pass
        except Exception as e:
            logging.debug(f"[EMOTIONAL_GATE] Could not load persisted state: {e}")

    def _persist_state(self, state: Dict):
        """Phase 32.4: Save emotional state to DB for restart continuity."""
        try:
            # Only persist key fields (not mood_history which is large)
            snapshot = {
                'state': state.get('state', 'NEUTRAL'),
                'score': state.get('score', 50),
                'sizing_multiplier': state.get('sizing_multiplier', 1.0),
                'checked_at': state.get('checked_at', datetime.now().isoformat()),
                'scar_count': len(state.get('caution_flags', [])),
            }

            conn = sqlite3.connect(self.db_path, timeout=30.0)
            c = conn.cursor()

            # Ensure system_state exists
            if _table_exists(c, 'system_state'):
                c.execute(
                    "INSERT OR REPLACE INTO system_state (key, value) VALUES (?, ?)",
                    ('emotional_state', json.dumps(snapshot))
                )
                conn.commit()

            conn.close()
        except Exception as e:
            logging.debug(f"[EMOTIONAL_GATE] Could not persist state: {e}")


# Singleton
_gate = None

def get_emotional_gate(db_path: str = None) -> EmotionalGate:
    """Get or create the singleton EmotionalGate."""
    global _gate
    if _gate is None:
        _gate = EmotionalGate(db_path)
    return _gate


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("EMOTIONAL GATE - Self Test")
    print("=" * 60)
    
    gate = get_emotional_gate()
    result = gate.check_emotional_state()
    
    print(f"\n📊 Current Emotional State:")
    print(f"   State: {result['state']}")
    print(f"   Score: {result['score']}")
    print(f"   Sizing Multiplier: {result['sizing_multiplier']*100:.0f}%")
    
    if result['caution_flags']:
        print(f"   ⚠️ Caution Flags:")
        for flag in result['caution_flags']:
            print(f"      - {flag}")
    
    print("\n" + "=" * 60)
