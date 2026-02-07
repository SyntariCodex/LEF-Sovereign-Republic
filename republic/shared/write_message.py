"""
Write Message Format for Write-Ahead Queue (WAQ)

All database writes should be published as WriteMessage instances.
The Scribe agent consumes these and performs the actual writes.
"""
import time
import uuid
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any


@dataclass
class WriteMessage:
    """
    Standard message format for the write queue.
    
    Attributes:
        operation: SQL operation type (INSERT, UPDATE, DELETE, EXECUTE)
        table: Target database table
        data: Column-value pairs for INSERT/UPDATE, or SQL params for EXECUTE
        priority: 0=normal, 1=high, 2=critical (e.g., stop-loss execution)
        source_agent: Name of the agent that queued this write
        timestamp: Unix timestamp when queued
        callback_key: Optional Redis key for result notification (for sync waits)
        message_id: Unique identifier for this message
        sql: Raw SQL for EXECUTE operations (optional)
        where_clause: WHERE conditions for UPDATE/DELETE (optional)
    """
    operation: str
    table: str
    data: Dict[str, Any]
    source_agent: str
    priority: int = 0
    timestamp: float = field(default_factory=time.time)
    callback_key: Optional[str] = None
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    sql: Optional[str] = None
    where_clause: Optional[Dict[str, Any]] = None
    
    def to_json(self) -> str:
        """Serialize to JSON for Redis."""
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> 'WriteMessage':
        """Deserialize from JSON."""
        data = json.loads(json_str)
        return cls(**data)
    
    def to_sql(self, backend: str = 'sqlite') -> tuple:
        """
        Convert to SQL statement and parameters.

        Args:
            backend: 'sqlite' or 'postgresql'. Controls placeholder format.
                     SQLite uses ?, PostgreSQL uses %s.

        Returns:
            (sql_string, params) where params is dict for named placeholders or tuple for positional
        """
        ph = '%s' if backend == 'postgresql' else '?'

        if self.operation == 'EXECUTE' and self.sql:
            # Raw SQL execution
            sql = self.sql
            if backend == 'postgresql':
                # Convert ? → %s in raw SQL
                sql = sql.replace('?', '%s')
            # Check if SQL uses named placeholders (:name) or positional
            if ':' in sql and self.data and any(f':{k}' in sql for k in self.data.keys()):
                # Named placeholders
                if backend == 'postgresql':
                    # Convert :name → %(name)s for psycopg2
                    import re
                    sql = re.sub(r':(\w+)', r'%(\1)s', sql)
                return (sql, self.data)
            else:
                # Positional placeholders - return tuple
                params = tuple(self.data.values()) if self.data else ()
                return (sql, params)

        elif self.operation == 'INSERT':
            columns = ', '.join(self.data.keys())
            placeholders = ', '.join([ph for _ in self.data])
            sql = f"INSERT INTO {self.table} ({columns}) VALUES ({placeholders})"
            return (sql, tuple(self.data.values()))

        elif self.operation == 'UPDATE':
            set_clause = ', '.join([f"{k} = {ph}" for k in self.data.keys()])
            sql = f"UPDATE {self.table} SET {set_clause}"
            params = list(self.data.values())

            if self.where_clause:
                where_parts = ' AND '.join([f"{k} = {ph}" for k in self.where_clause.keys()])
                sql += f" WHERE {where_parts}"
                params.extend(self.where_clause.values())

            return (sql, tuple(params))

        elif self.operation == 'DELETE':
            sql = f"DELETE FROM {self.table}"
            params = []

            if self.where_clause:
                where_parts = ' AND '.join([f"{k} = {ph}" for k in self.where_clause.keys()])
                sql += f" WHERE {where_parts}"
                params = list(self.where_clause.values())

            return (sql, tuple(params))

        else:
            raise ValueError(f"Unknown operation: {self.operation}")


# Priority constants
PRIORITY_NORMAL = 0
PRIORITY_HIGH = 1
PRIORITY_CRITICAL = 2  # For stop-losses, emergency actions


def create_insert(table: str, data: Dict[str, Any], source: str, priority: int = 0) -> WriteMessage:
    """Helper to create an INSERT message."""
    return WriteMessage(
        operation='INSERT',
        table=table,
        data=data,
        source_agent=source,
        priority=priority
    )


def create_update(table: str, data: Dict[str, Any], where: Dict[str, Any], source: str, priority: int = 0) -> WriteMessage:
    """Helper to create an UPDATE message."""
    return WriteMessage(
        operation='UPDATE',
        table=table,
        data=data,
        where_clause=where,
        source_agent=source,
        priority=priority
    )


def create_execute(sql: str, params: Dict[str, Any], source: str, priority: int = 0) -> WriteMessage:
    """Helper for raw SQL execution."""
    return WriteMessage(
        operation='EXECUTE',
        table='_raw',
        data=params,
        sql=sql,
        source_agent=source,
        priority=priority
    )
