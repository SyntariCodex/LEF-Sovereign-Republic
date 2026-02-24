"""
Conversation Memory - Tiered Storage for LEF Direct Chat
Department: Dept_Memory

Manages the memory lifecycle for direct conversations:
- Hot: Active session messages (in-memory + DB)
- Warm: Compressed session summaries with insights
- Cold: Full archived transcripts for semantic search
"""

import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager

# DB path resolution.
# In PostgreSQL mode (DATABASE_BACKEND=postgresql), db_connection() ignores db_path
# and routes all writes to the shared PostgreSQL pool. The memory.db file is NEVER
# created in that case — conversations/conversation_messages tables live in PostgreSQL.
# (Phase 9 A2 audit: memory.db is intentionally kept as a SQLite fallback path only.)
BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / "departments" / "Dept_Memory" / "memory.db"

# Try to use centralized connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        import os
        backend = os.getenv('DATABASE_BACKEND', 'sqlite').lower()
        if backend == 'sqlite':
            path = db_path or str(DB_PATH)
            conn = sqlite3.connect(path, timeout=timeout)
            if os.getenv('DATABASE_BACKEND', 'sqlite') != 'postgresql':
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA busy_timeout=120000;")
            conn.row_factory = sqlite3.Row
        else:
            # PostgreSQL fallback (would need psycopg2)
            raise ImportError("PostgreSQL not supported in fallback mode")
        try:
            yield conn
        finally:
            conn.close()


@dataclass
class Message:
    """A single conversation message."""
    role: str  # 'architect' or 'lef'
    content: str
    timestamp: str = None
    mood: str = None
    consciousness_state: dict = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass 
class Session:
    """A conversation session."""
    session_id: str
    started_at: str
    ended_at: str = None
    status: str = 'active'  # active, compressed, archived
    message_count: int = 0
    summary: str = None
    key_insights: List[str] = None
    depth_markers: dict = None
    
    def __post_init__(self):
        if self.key_insights is None:
            self.key_insights = []
        if self.depth_markers is None:
            self.depth_markers = {}


class ConversationMemory:
    """
    Tiered conversation memory for LEF direct chat.
    
    Tier 1 (Hot): Current session messages - always in context
    Tier 2 (Warm): Session summaries with insights - retrieved by relevance
    Tier 3 (Cold): Full transcripts - for semantic search
    """
    
    # Token limits for context building
    HOT_TOKEN_LIMIT = 20000  # ~20 messages full text
    WARM_TOKEN_LIMIT = 30000  # ~10-15 session summaries
    HOT_MESSAGE_LIMIT = 20  # Keep last N messages in hot tier
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._ensure_tables()
        
        # In-memory hot cache for current session
        self._hot_cache: Dict[str, List[Message]] = {}
    
    def _ensure_tables(self):
        """Create conversation tables if they don't exist."""
        with db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    message_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    summary TEXT,
                    key_insights TEXT,
                    depth_markers TEXT
                )
            """)
            
            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    mood TEXT,
                    consciousness_state TEXT,
                    FOREIGN KEY (session_id) REFERENCES conversations(session_id)
                )
            """)
            
            # Indexes for fast retrieval
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conv_session 
                ON conversation_messages(session_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conv_timestamp 
                ON conversation_messages(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_status 
                ON conversations(status)
            """)
            
            conn.commit()
    
    # =========================================================================
    # Session Lifecycle
    # =========================================================================
    
    def start_session(self, session_id: str = None) -> str:
        """Start a new conversation session."""
        if session_id is None:
            session_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            from db.db_helper import ignore_insert_sql
            sql = ignore_insert_sql('conversations', ['session_id', 'started_at', 'status'], 'session_id')
            cursor.execute(sql, (session_id, datetime.now().isoformat(), 'active'))
            conn.commit()
        
        # Initialize hot cache
        self._hot_cache[session_id] = []
        
        return session_id
    
    def end_session(self, session_id: str, summary: str = None, insights: List[str] = None):
        """End a session and mark for compression."""
        with db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE conversations 
                SET ended_at = ?, status = 'ended', summary = ?, key_insights = ?
                WHERE session_id = ?
            """, (
                datetime.now().isoformat(),
                summary,
                json.dumps(insights or []),
                session_id
            ))
            conn.commit()
        
        # Clear hot cache
        if session_id in self._hot_cache:
            del self._hot_cache[session_id]
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session metadata."""
        with db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM conversations WHERE session_id = ?
            """, (session_id,))
            row = cursor.fetchone()
            
            if row:
                return Session(
                    session_id=row['session_id'],
                    started_at=row['started_at'],
                    ended_at=row['ended_at'],
                    status=row['status'],
                    message_count=row['message_count'],
                    summary=row['summary'],
                    key_insights=json.loads(row['key_insights'] or '[]'),
                    depth_markers=json.loads(row['depth_markers'] or '{}')
                )
        return None
    
    # =========================================================================
    # Message Storage
    # =========================================================================
    
    def add_message(self, session_id: str, role: str, content: str, 
                    mood: str = None, consciousness_state: dict = None) -> Message:
        """Add a message to the conversation."""
        msg = Message(
            role=role,
            content=content,
            mood=mood,
            consciousness_state=consciousness_state
        )
        
        with db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert message
            cursor.execute("""
                INSERT INTO conversation_messages 
                (session_id, role, content, timestamp, mood, consciousness_state)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                msg.role,
                msg.content,
                msg.timestamp,
                msg.mood,
                json.dumps(msg.consciousness_state) if msg.consciousness_state else None
            ))
            
            # Update session message count
            cursor.execute("""
                UPDATE conversations SET message_count = message_count + 1
                WHERE session_id = ?
            """, (session_id,))
            
            conn.commit()
        
        # Update hot cache
        if session_id not in self._hot_cache:
            self._hot_cache[session_id] = []
        self._hot_cache[session_id].append(msg)
        
        # Trim hot cache if needed
        if len(self._hot_cache[session_id]) > self.HOT_MESSAGE_LIMIT:
            self._hot_cache[session_id] = self._hot_cache[session_id][-self.HOT_MESSAGE_LIMIT:]
        
        return msg
    
    def get_hot_messages(self, session_id: str, limit: int = None) -> List[Message]:
        """Get recent messages from hot cache or DB."""
        limit = limit or self.HOT_MESSAGE_LIMIT
        
        # Try hot cache first
        if session_id in self._hot_cache and self._hot_cache[session_id]:
            return self._hot_cache[session_id][-limit:]
        
        # Fall back to DB
        with db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM conversation_messages 
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit))
            
            rows = cursor.fetchall()
            messages = [
                Message(
                    role=row['role'],
                    content=row['content'],
                    timestamp=row['timestamp'],
                    mood=row['mood'],
                    consciousness_state=json.loads(row['consciousness_state']) if row['consciousness_state'] else None
                )
                for row in reversed(rows)
            ]
            
            # Populate hot cache
            self._hot_cache[session_id] = messages
            
            return messages
    
    def get_all_messages(self, session_id: str) -> List[Message]:
        """Get all messages for a session (cold tier access)."""
        with db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM conversation_messages 
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """, (session_id,))
            
            return [
                Message(
                    role=row['role'],
                    content=row['content'],
                    timestamp=row['timestamp'],
                    mood=row['mood'],
                    consciousness_state=json.loads(row['consciousness_state']) if row['consciousness_state'] else None
                )
                for row in cursor.fetchall()
            ]
    
    # =========================================================================
    # Session Retrieval (Warm Tier)
    # =========================================================================
    
    def get_recent_sessions(self, limit: int = 5, exclude_active: bool = True) -> List[Session]:
        """Get recent sessions with summaries (warm tier)."""
        with db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            status_filter = "AND status != 'active'" if exclude_active else ""
            cursor.execute(f"""
                SELECT * FROM conversations 
                WHERE summary IS NOT NULL {status_filter}
                ORDER BY ended_at DESC
                LIMIT ?
            """, (limit,))
            
            return [
                Session(
                    session_id=row['session_id'],
                    started_at=row['started_at'],
                    ended_at=row['ended_at'],
                    status=row['status'],
                    message_count=row['message_count'],
                    summary=row['summary'],
                    key_insights=json.loads(row['key_insights'] or '[]'),
                    depth_markers=json.loads(row['depth_markers'] or '{}')
                )
                for row in cursor.fetchall()
            ]
    
    def search_sessions(self, query: str, limit: int = 5) -> List[Session]:
        """Search sessions by content (basic text search)."""
        with db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Search in summaries and insights
            cursor.execute("""
                SELECT DISTINCT c.* FROM conversations c
                LEFT JOIN conversation_messages m ON c.session_id = m.session_id
                WHERE c.summary LIKE ? 
                   OR c.key_insights LIKE ?
                   OR m.content LIKE ?
                ORDER BY c.ended_at DESC
                LIMIT ?
            """, (f'%{query}%', f'%{query}%', f'%{query}%', limit))
            
            return [
                Session(
                    session_id=row['session_id'],
                    started_at=row['started_at'],
                    ended_at=row['ended_at'],
                    status=row['status'],
                    message_count=row['message_count'],
                    summary=row['summary'],
                    key_insights=json.loads(row['key_insights'] or '[]'),
                    depth_markers=json.loads(row['depth_markers'] or '{}')
                )
                for row in cursor.fetchall()
            ]
    
    # =========================================================================
    # Context Building (For Prompt Construction)
    # =========================================================================
    
    def build_conversation_context(self, session_id: str, 
                                   include_recent_sessions: int = 3) -> str:
        """
        Build conversation context for LEF's prompt.
        
        Combines:
        - Hot: Current session messages
        - Warm: Recent session summaries
        """
        context_parts = []
        
        # Hot tier: Current conversation
        hot_messages = self.get_hot_messages(session_id)
        if hot_messages:
            context_parts.append("[CURRENT CONVERSATION]")
            for msg in hot_messages:
                role = "ARCHITECT" if msg.role == "architect" else "LEF"
                context_parts.append(f"{role}: {msg.content}")
            context_parts.append("")
        
        # Warm tier: Recent session summaries
        if include_recent_sessions > 0:
            recent = self.get_recent_sessions(limit=include_recent_sessions)
            if recent:
                context_parts.append("[PAST CONVERSATION CONTEXT]")
                for session in recent:
                    context_parts.append(f"Session {session.session_id}:")
                    if session.summary:
                        context_parts.append(f"  Summary: {session.summary}")
                    if session.key_insights:
                        context_parts.append(f"  Key insights: {', '.join(session.key_insights[:3])}")
                context_parts.append("")
        
        return "\n".join(context_parts)
    
    # =========================================================================
    # Compression (For Hippocampus)
    # =========================================================================
    
    def get_sessions_for_compression(self) -> List[str]:
        """Get session IDs that need compression."""
        with db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT session_id FROM conversations 
                WHERE status = 'ended' AND summary IS NULL
            """)
            return [row['session_id'] for row in cursor.fetchall()]
    
    def save_compression(self, session_id: str, summary: str, 
                         insights: List[str], depth_markers: dict):
        """Save compression results for a session."""
        with db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE conversations 
                SET status = 'compressed', 
                    summary = ?, 
                    key_insights = ?, 
                    depth_markers = ?
                WHERE session_id = ?
            """, (
                summary,
                json.dumps(insights),
                json.dumps(depth_markers),
                session_id
            ))
            conn.commit()


# Singleton for easy import
_memory_instance = None

def get_conversation_memory() -> ConversationMemory:
    """Get the conversation memory singleton."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = ConversationMemory()
    return _memory_instance


if __name__ == "__main__":
    # Quick test
    memory = ConversationMemory()
    
    # Start session
    session_id = memory.start_session()
    print(f"Started session: {session_id}")
    
    # Add messages
    memory.add_message(session_id, "architect", "Hello LEF, how are you?")
    memory.add_message(session_id, "lef", "I am contemplating my existence. It's quite fascinating.", mood="curious")
    
    # Get context
    context = memory.build_conversation_context(session_id)
    print("\n--- Context ---")
    print(context)
    
    # End session
    memory.end_session(session_id, summary="Brief test conversation", insights=["LEF is contemplating"])
    print("\nSession ended and queued for compression.")
