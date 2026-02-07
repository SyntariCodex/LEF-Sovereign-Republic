"""
Handoff Packet System
Creates AutoGen/CrewAI-style context preservation between agents.

A "handoff packet" carries context from one agent to another, enabling:
1. Lessons learned from failures to reach future decision-makers
2. Context preservation when work transfers between agents
3. Broadcast messages for system-wide awareness

Usage:
    from system.handoff_packet import HandoffManager
    
    # Create handoff (in source agent)
    mgr = HandoffManager()
    mgr.create_handoff(
        source_agent="AgentPostMortem",
        target_agent="AgentStrategist",  # or None for broadcast
        context={"lesson": "BTC slippage was high due to low liquidity"},
        intent_type="LESSON_LEARNED"
    )
    
    # Consume handoffs (in target agent)
    packets = mgr.consume_handoffs("AgentStrategist")
    for p in packets:
        print(f"From {p['source_agent']}: {p['context']}")
"""

import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))

logging.basicConfig(level=logging.INFO)


class HandoffManager:
    """
    Manages creation, storage, and consumption of handoff packets.
    
    Handoff Types:
        - LESSON_LEARNED: Post-mortem insights for future decisions
        - CONTEXT_TRANSFER: Work state from one agent to another
        - BROADCAST: System-wide announcements (target_agent=None)
        - INTENT_RESULT: Result of an executed intent
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._ensure_table()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory for dict-like access."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _ensure_table(self):
        """Create handoff table if it doesn't exist."""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_handoffs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_agent TEXT NOT NULL,
                    target_agent TEXT,  -- NULL = broadcast to all
                    context TEXT NOT NULL,  -- JSON blob
                    intent_type TEXT,
                    priority INTEGER DEFAULT 5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    consumed_at TIMESTAMP,  -- NULL until read
                    ttl_days INTEGER DEFAULT 7
                )
            """)
            # Index for efficient querying
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_handoffs_target 
                ON agent_handoffs(target_agent, consumed_at)
            """)
            conn.commit()
        finally:
            conn.close()
    
    def create_handoff(
        self,
        source_agent: str,
        context: Dict[str, Any],
        target_agent: Optional[str] = None,
        intent_type: str = "CONTEXT_TRANSFER",
        priority: int = 5,
        ttl_days: int = 7
    ) -> int:
        """
        Create a new handoff packet.
        
        Args:
            source_agent: Name of the agent creating the handoff
            context: Dictionary of context data (will be JSON serialized)
            target_agent: Specific agent to receive, or None for broadcast
            intent_type: Type of handoff (LESSON_LEARNED, CONTEXT_TRANSFER, etc.)
            priority: 1-10 priority (10 = urgent)
            ttl_days: Time-to-live in days before auto-cleanup
            
        Returns:
            ID of the created handoff
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO agent_handoffs 
                (source_agent, target_agent, context, intent_type, priority, ttl_days)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                source_agent,
                target_agent,
                json.dumps(context),
                intent_type,
                priority,
                ttl_days
            ))
            conn.commit()
            handoff_id = cursor.lastrowid
            
            target_desc = target_agent or "BROADCAST"
            logging.debug(f"[HANDOFF] 📦 Created: {source_agent} → {target_desc} ({intent_type})")
            
            return handoff_id
        finally:
            conn.close()
    
    def consume_handoffs(
        self,
        agent_name: str,
        intent_types: Optional[List[str]] = None,
        include_broadcasts: bool = True,
        mark_consumed: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve and optionally consume handoffs for an agent.
        
        Args:
            agent_name: Name of the agent consuming handoffs
            intent_types: Filter by specific types, or None for all
            include_broadcasts: Include broadcast handoffs (target_agent=NULL)
            mark_consumed: Whether to mark handoffs as consumed
            
        Returns:
            List of handoff packet dicts
        """
        conn = self._get_connection()
        try:
            # Build query
            conditions = ["consumed_at IS NULL"]
            params = []
            
            if include_broadcasts:
                conditions.append("(target_agent = ? OR target_agent IS NULL)")
            else:
                conditions.append("target_agent = ?")
            params.append(agent_name)
            
            if intent_types:
                placeholders = ",".join("?" * len(intent_types))
                conditions.append(f"intent_type IN ({placeholders})")
                params.extend(intent_types)
            
            query = f"""
                SELECT id, source_agent, target_agent, context, intent_type, 
                       priority, created_at, ttl_days
                FROM agent_handoffs
                WHERE {' AND '.join(conditions)}
                ORDER BY priority DESC, created_at ASC
            """
            
            rows = conn.execute(query, params).fetchall()
            
            packets = []
            for row in rows:
                packet = dict(row)
                packet['context'] = json.loads(packet['context'])
                packets.append(packet)
                
                # Mark as consumed
                if mark_consumed:
                    conn.execute("""
                        UPDATE agent_handoffs 
                        SET consumed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (row['id'],))
            
            if mark_consumed and packets:
                conn.commit()
                logging.debug(f"[HANDOFF] 📬 {agent_name} consumed {len(packets)} packet(s)")
            
            return packets
        finally:
            conn.close()
    
    def peek_handoffs(self, agent_name: str) -> int:
        """
        Check how many unconsumed handoffs are waiting for an agent.
        Does not consume them.
        """
        conn = self._get_connection()
        try:
            row = conn.execute("""
                SELECT COUNT(*) as count FROM agent_handoffs
                WHERE (target_agent = ? OR target_agent IS NULL)
                AND consumed_at IS NULL
            """, (agent_name,)).fetchone()
            return row['count'] if row else 0
        finally:
            conn.close()
    
    def cleanup_expired(self) -> int:
        """
        Remove handoffs older than their TTL.
        Run periodically (e.g., daily).
        
        Returns:
            Number of handoffs cleaned up
        """
        conn = self._get_connection()
        try:
            # Delete where created_at + ttl_days < now
            cursor = conn.execute("""
                DELETE FROM agent_handoffs
                WHERE datetime(created_at, '+' || ttl_days || ' days') < datetime('now')
            """)
            conn.commit()
            count = cursor.rowcount
            if count > 0:
                logging.info(f"[HANDOFF] 🧹 Cleaned up {count} expired packet(s)")
            return count
        finally:
            conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get handoff system statistics."""
        conn = self._get_connection()
        try:
            stats = {}
            
            # Total pending
            row = conn.execute("""
                SELECT COUNT(*) as count FROM agent_handoffs 
                WHERE consumed_at IS NULL
            """).fetchone()
            stats['pending'] = row['count']
            
            # By type
            rows = conn.execute("""
                SELECT intent_type, COUNT(*) as count 
                FROM agent_handoffs 
                WHERE consumed_at IS NULL
                GROUP BY intent_type
            """).fetchall()
            stats['by_type'] = {row['intent_type']: row['count'] for row in rows}
            
            # Total consumed today
            row = conn.execute("""
                SELECT COUNT(*) as count FROM agent_handoffs 
                WHERE date(consumed_at) = date('now')
            """).fetchone()
            stats['consumed_today'] = row['count']
            
            return stats
        finally:
            conn.close()


# Convenience functions for quick use
def create_lesson(source_agent: str, lesson: str, asset: str = None, severity: str = "INFO"):
    """Quick helper to create a lesson-learned handoff."""
    mgr = HandoffManager()
    context = {
        "lesson": lesson,
        "severity": severity,
        "timestamp": datetime.now().isoformat()
    }
    if asset:
        context["asset"] = asset
    
    return mgr.create_handoff(
        source_agent=source_agent,
        context=context,
        target_agent=None,  # Broadcast
        intent_type="LESSON_LEARNED",
        priority=7 if severity == "CRITICAL" else 5
    )


def get_recent_lessons(agent_name: str, limit: int = 5) -> List[Dict]:
    """Quick helper to get recent lessons for an agent."""
    mgr = HandoffManager()
    return mgr.consume_handoffs(
        agent_name=agent_name,
        intent_types=["LESSON_LEARNED"],
        include_broadcasts=True,
        mark_consumed=False  # Just peek, don't consume
    )[:limit]


if __name__ == "__main__":
    # Test the handoff system
    mgr = HandoffManager()
    
    print("🧪 Testing Handoff System...")
    
    # Create a test handoff
    hid = mgr.create_handoff(
        source_agent="TestAgent",
        target_agent="AgentStrategist",
        context={"message": "Test handoff", "value": 42},
        intent_type="TEST"
    )
    print(f"✅ Created handoff #{hid}")
    
    # Check pending
    pending = mgr.peek_handoffs("AgentStrategist")
    print(f"📬 AgentStrategist has {pending} pending handoff(s)")
    
    # Consume
    packets = mgr.consume_handoffs("AgentStrategist")
    print(f"📦 Consumed {len(packets)} packet(s):")
    for p in packets:
        print(f"   From {p['source_agent']}: {p['context']}")
    
    # Stats
    stats = mgr.get_stats()
    print(f"📊 Stats: {stats}")
    
    print("✅ Handoff System Working!")
