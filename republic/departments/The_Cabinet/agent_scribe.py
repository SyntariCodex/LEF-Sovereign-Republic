import time
import json
import sqlite3
import os
import redis
import logging

# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection, translate_sql, get_backend
except ImportError:
    from contextlib import contextmanager
    import sqlite3 as _sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = _sqlite3.connect(db_path, timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()
    def translate_sql(sql):
        return sql
    def get_backend():
        return 'sqlite'


# Connection pool for efficient DB access
try:
    from db.db_pool import get_pool
    _pool = get_pool()
except ImportError:
    _pool = None

# Phase 8: Determine database backend for SQL generation
_backend = os.getenv('DATABASE_BACKEND', 'sqlite').lower()

# Write Queue Support
try:
    from shared.write_message import WriteMessage
    WRITE_QUEUE_AVAILABLE = True
except ImportError:
    WRITE_QUEUE_AVAILABLE = False

# Write Queue Names (must match write_queue.py)
WRITE_QUEUE = 'db:write_queue'
WRITE_QUEUE_PRIORITY = 'db:write_queue:priority'
WRITE_QUEUE_CRITICAL = 'db:write_queue:critical'


class AgentScribe:
    """
    The Historian.
    Consumes log entries from the Redis Queue and writes them to the SQLite Database
    in efficient batches. This solves the 'Database Locked' concurrency issue.
    
    Phase 30: Also consumes the Write-Ahead Queue (WAQ) for general database writes.
    """
    def __init__(self, db_path=None, redis_host=None):
        self.queue_key = "logs:queue"
        self.db_path = db_path or os.getenv('DB_PATH', 'republic.db')
        
        _host = redis_host or os.getenv('REDIS_HOST', 'localhost')
        try:
            from system.redis_client import get_redis
            self.redis_client = get_redis()
        except ImportError:
            self.redis_client = redis.Redis(host=_host, port=6379, db=0, decode_responses=True)
        
        self.running = True
        self.batch_size = 100 # Phase 6.5: Increased from 50 to handle all-agent WAQ routing
        self.batch_timeout = 2.0 # Or every 2 seconds
        self.waq_batch_size = 100  # Phase 6.5: Max normal-queue writes per cycle

        # Write queue stats
        self.writes_processed = 0
        self.writes_failed = 0
        self.critical_processed = 0
        self.priority_processed = 0

        # Monitoring
        self.last_health_check = 0
        self.health_check_interval = 30  # seconds

    def run(self):
        print(f"[SCRIBE] 📜 Scribe Service Started. Watching {self.queue_key} + WAQ...")
        
        while self.running:
            try:
                # 0. Periodic Health Check (every 30s)
                if time.time() - self.last_health_check >= self.health_check_interval:
                    self._log_queue_health()
                    self.last_health_check = time.time()
                
                # 1. Process Write Queue FIRST (priority operations)
                if WRITE_QUEUE_AVAILABLE:
                    self._process_write_queue()
                
                # 2. Process Log Queue
                self._process_queue()
            except Exception as e:
                print(f"[SCRIBE] ⚠️ Loop Error: {e}")
                time.sleep(5)

    def _log_queue_health(self):
        """
        Log queue depths and throughput stats for monitoring.
        Called every 30 seconds.
        """
        try:
            # Get queue depths
            normal = self.redis_client.llen(WRITE_QUEUE)
            priority = self.redis_client.llen(WRITE_QUEUE_PRIORITY)
            critical = self.redis_client.llen(WRITE_QUEUE_CRITICAL)
            logs = self.redis_client.llen(self.queue_key)
            
            total_pending = normal + priority + critical
            
            # Determine health status
            if total_pending == 0:
                status = "✅ HEALTHY"
            elif total_pending < 10:
                status = "✅ HEALTHY"
            elif total_pending < 50:
                status = "⚠️ BACKLOG"
            else:
                status = "🚨 OVERLOADED"
            
            # Log summary — only print to console when there's a problem
            health_msg = (f"[SCRIBE] 📊 WAQ Health: {status} | "
                  f"Queues: C={critical} P={priority} N={normal} L={logs} | "
                  f"Processed: {self.writes_processed} (C:{self.critical_processed} P:{self.priority_processed}) | "
                  f"Failed: {self.writes_failed}")
            if total_pending >= 10 or self.writes_failed > 0:
                print(health_msg)
            else:
                logging.debug(health_msg)

            # Publish to Redis for external monitoring
            self.redis_client.set("scribe:health", json.dumps({
                'status': status,
                'queue_critical': critical,
                'queue_priority': priority,
                'queue_normal': normal,
                'queue_logs': logs,
                'writes_processed': self.writes_processed,
                'critical_processed': self.critical_processed,
                'priority_processed': self.priority_processed,
                'writes_failed': self.writes_failed,
                'batch_size': self.batch_size,
                'waq_batch_size': self.waq_batch_size,
                'timestamp': time.time()
            }))
            self.redis_client.expire("scribe:health", 120)  # 2 min TTL
            
        except Exception as e:
            print(f"[SCRIBE] Health check error: {e}")

    def _process_write_queue(self):
        """
        Consume and execute database writes from the Write-Ahead Queue.
        Processes in priority order: critical > priority > normal
        Phase 6.5: Drain critical/priority fully, then up to waq_batch_size normal writes.
        """
        # Process ALL critical queue items first (stop-losses, circuit breaker)
        while self._process_single_write_queue(WRITE_QUEUE_CRITICAL):
            self.critical_processed += 1

        # Then ALL priority queue items (consciousness, system_state)
        while self._process_single_write_queue(WRITE_QUEUE_PRIORITY):
            self.priority_processed += 1

        # Then normal queue (up to waq_batch_size to not starve logs)
        for _ in range(self.waq_batch_size):
            if not self._process_single_write_queue(WRITE_QUEUE):
                break

    def _process_single_write_queue(self, queue_name: str) -> bool:
        """
        Process one message from a write queue.
        
        Returns:
            True if a message was processed, False if queue was empty
        """
        try:
            # Non-blocking pop
            raw = self.redis_client.lpop(queue_name)
            if not raw:
                return False
            
            msg = WriteMessage.from_json(raw)
            success = self._execute_write(msg)
            
            # If callback requested, publish result
            if msg.callback_key:
                result = {
                    'success': success,
                    'message_id': msg.message_id,
                    'operation': msg.operation,
                    'table': msg.table
                }
                self.redis_client.rpush(msg.callback_key, json.dumps(result))
                # Set expiry so orphaned results don't accumulate
                self.redis_client.expire(msg.callback_key, 30)
            
            return True
            
        except Exception as e:
            logging.error(f"[SCRIBE] WAQ process error: {e}")
            return False

    def _execute_write(self, msg: WriteMessage) -> bool:
        """
        Execute a single write message against the database.
        Phase 8: Supports both SQLite and PostgreSQL backends.
        """
        conn = None
        try:
            if _pool:
                conn = _pool.get(timeout=30.0)
            else:
                if _backend == 'postgresql':
                    import psycopg2
                    from db.db_pool import _get_pg_params
                    conn = psycopg2.connect(**_get_pg_params())
                else:
                    conn = sqlite3.connect(self.db_path, timeout=60.0)

            cursor = conn.cursor()
            sql, params = msg.to_sql(backend=_backend)

            # Phase 8: For PostgreSQL, fix value-level incompatibilities
            if _backend == 'postgresql' and params:
                from datetime import datetime as _dt
                now_str = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
                # Keys that are known to hold timestamps
                _TS_KEYS = {'ts', 'last_active', 'last_heartbeat', 'timestamp', 'created_at',
                           'updated_at', 'ended_at', 'started_at', 'discovered_at', 'last_updated'}
                if isinstance(params, dict):
                    for k, v in list(params.items()):
                        # Convert epoch floats to timestamp strings for known timestamp keys
                        if k in _TS_KEYS and isinstance(v, (int, float)):
                            try:
                                params[k] = _dt.fromtimestamp(v).strftime('%Y-%m-%d %H:%M:%S')
                            except (ValueError, OSError):
                                pass
                        # Convert 'CURRENT_TIMESTAMP' literal to actual timestamp
                        elif isinstance(v, str) and v.upper() == 'CURRENT_TIMESTAMP':
                            params[k] = now_str
                elif isinstance(params, (list, tuple)):
                    params = list(params)
                    for i, v in enumerate(params):
                        if isinstance(v, str) and v.upper() == 'CURRENT_TIMESTAMP':
                            params[i] = now_str
                        elif isinstance(v, (int, float)) and i == 0:
                            # Heuristic: first param named 'ts' is often a timestamp
                            pass
                    params = tuple(params)

            cursor.execute(sql, params)
            conn.commit()

            self.writes_processed += 1
            logging.debug(f"[SCRIBE] WAQ: {msg.operation} on {msg.table} from {msg.source_agent}")
            return True

        except Exception as e:
            error_str = str(e).lower()
            is_lock = "locked" in error_str or "deadlock" in error_str
            if is_lock:
                logging.warning(f"[SCRIBE] WAQ locked, re-queuing: {msg.table}")
                time.sleep(0.5)
                self.redis_client.rpush(WRITE_QUEUE, msg.to_json())
            else:
                logging.error(f"[SCRIBE] WAQ Error: {e}")
                self.writes_failed += 1
            return False

        finally:
            if conn:
                if _pool:
                    _pool.release(conn)
                else:
                    conn.close()

    def _get_log_insert_sql(self):
        """Return the log INSERT SQL for the current backend."""
        if _backend == 'postgresql':
            return """
                INSERT INTO agent_logs (timestamp, source, level, message)
                VALUES (%(timestamp)s, %(agent_name)s, %(level)s, %(message)s)
            """
        else:
            return """
                INSERT INTO agent_logs (timestamp, source, level, message)
                VALUES (:timestamp, :agent_name, :level, :message)
            """

    def _process_queue(self):
        batch = []

        # 1. Fetch a batch of logs
        try:
            first_item = self.redis_client.blpop(self.queue_key, timeout=5)
            if first_item:
                batch.append(json.loads(first_item[1]))
                for _ in range(self.batch_size - 1):
                    item = self.redis_client.lpop(self.queue_key)
                    if item:
                        batch.append(json.loads(item))
                    else:
                        break
        except (redis.RedisError, json.JSONDecodeError) as e:
            pass

        if not batch:
            return

        # 2. Write Batch to Database
        conn = None
        try:
            if _pool:
                conn = _pool.get(timeout=10.0)
            else:
                if _backend == 'postgresql':
                    import psycopg2
                    from db.db_pool import _get_pg_params
                    conn = psycopg2.connect(**_get_pg_params())
                else:
                    conn = sqlite3.connect(self.db_path, timeout=60.0)
            cursor = conn.cursor()

            log_sql = self._get_log_insert_sql()
            cursor.executemany(log_sql, batch)
            conn.commit()

        except Exception as e:
            error_str = str(e).lower()
            if "locked" in error_str or "deadlock" in error_str:
                print(f"[SCRIBE] DB Locked. Retrying batch in 1s...")
                time.sleep(1)
                self._retry_batch(batch)
            else:
                print(f"[SCRIBE] SQL Error: {e}")
        finally:
            if conn:
                if _pool:
                    _pool.release(conn)
                else:
                    conn.close()

    def _retry_batch(self, batch, attempt: int = 1, max_retries: int = 5):
        """Retry with exponential backoff. Phase 8: Supports both backends."""
        if attempt > max_retries:
            print(f"[SCRIBE] Max retries exceeded. Re-queuing {len(batch)} logs to Redis.")
            try:
                for item in batch:
                    self.redis_client.rpush(self.queue_key, json.dumps(item))
            except Exception as e:
                print(f"[SCRIBE] Failed to re-queue: {e}. Logs lost: {len(batch)}")
            return

        delay = 0.5 * (2 ** (attempt - 1))
        time.sleep(delay)

        conn = None
        try:
            if _pool:
                conn = _pool.get(timeout=30.0)
            else:
                if _backend == 'postgresql':
                    import psycopg2
                    from db.db_pool import _get_pg_params
                    conn = psycopg2.connect(**_get_pg_params())
                else:
                    conn = sqlite3.connect(self.db_path, timeout=90.0)
            cursor = conn.cursor()
            log_sql = self._get_log_insert_sql()
            cursor.executemany(log_sql, batch)
            conn.commit()
            print(f"[SCRIBE] Retry {attempt} success.")
        except Exception as e:
            error_str = str(e).lower()
            if "locked" in error_str or "deadlock" in error_str:
                print(f"[SCRIBE] Retry {attempt} locked, backing off...")
                self._retry_batch(batch, attempt + 1, max_retries)
            else:
                print(f"[SCRIBE] Retry {attempt} failed: {e}")
                self._retry_batch(batch, attempt + 1, max_retries)
        finally:
            if conn:
                if _pool:
                    _pool.release(conn)
                else:
                    conn.close()

if __name__ == "__main__":
    scribe = AgentScribe()
    scribe.run()

