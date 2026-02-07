"""
Genesis System (The Recorder)
Tracks the Lifecycle of the Republic: Restarts, Patches, and Configuration Changes.
Used by AgentDean to correlate Changes -> Effects.
Uses connection pool to prevent database locking.
"""

import os
import logging

class GenesisLogger:
    def __init__(self, db_path=None):
        if not db_path:
             BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
             db_path = os.path.join(BASE_DIR, 'republic.db')
        self.db_path = db_path
        self._pool = None

    def _get_pool(self):
        """Lazy-load the connection pool."""
        if self._pool is None:
            try:
                from db.db_pool import get_pool
                self._pool = get_pool()
            except Exception:
                self._pool = None
        return self._pool

    def _get_conn(self):
        """Get a connection from the pool or fallback to direct connect."""
        try:
            from db.db_helper import get_connection
            return get_connection(self.db_path, timeout=5.0)
        except Exception:
            import sqlite3
            return sqlite3.connect(self.db_path, timeout=5), None

    def _release_conn(self, conn, pool):
        """Release connection back to pool or close if direct."""
        try:
            from db.db_helper import release_connection
            release_connection(conn, pool)
        except Exception:
            try:
                conn.close()
            except Exception:
                pass

    def log_event(self, event_type, description, changed_files=None):
        """
        Logs a Genesis Event (Restart, Patch, etc.)
        """
        try:
            conn, pool = self._get_conn()
            try:
                c = conn.cursor()
                
                try:
                    c.execute("""
                        INSERT INTO genesis_log (event_type, description, changed_files)
                        VALUES (?, ?, ?)
                    """, (event_type, description, str(changed_files or [])))
                except Exception as e:
                    if "no column named changed_files" in str(e):
                        # Fallback for older schema
                        c.execute("""
                            INSERT INTO genesis_log (event_type, description)
                            VALUES (?, ?)
                        """, (event_type, description))
                    else:
                        raise
                
                conn.commit()
                logging.info(f"[GENESIS] 🧬 Event Recorded: {event_type} - {description}")
            finally:
                self._release_conn(conn, pool)
        except Exception as e:
            logging.error(f"[GENESIS] Failed to log event: {e}")

def log_system_restart(reason="Manual Restart"):
    """
    Helper to log a restart event.
    """
    logger = GenesisLogger()
    logger.log_event("RESTART", reason)

