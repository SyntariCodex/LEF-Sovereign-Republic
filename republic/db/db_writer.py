"""
Database Writer Utility for Write-Ahead Queue

A simple wrapper that agents can use to write to the database.
Automatically routes through WAQ when available, falls back to direct.

Phase 8: Supports both SQLite and PostgreSQL backends.
Fallback paths use translate_sql() for PostgreSQL compatibility.
"""
import os
import logging
from typing import Optional, Dict, Any

# Phase 8: Database backend
_backend = os.getenv('DATABASE_BACKEND', 'sqlite').lower()

# Try to load WAQ components
try:
    from db.write_queue import publish_write, is_queue_enabled
    from shared.write_message import WriteMessage, PRIORITY_NORMAL, PRIORITY_HIGH, PRIORITY_CRITICAL
    WAQ_AVAILABLE = True
except ImportError:
    WAQ_AVAILABLE = False
    PRIORITY_NORMAL = 0
    PRIORITY_HIGH = 1
    PRIORITY_CRITICAL = 2

# Try to load translate_sql for fallback paths
try:
    from db.db_helper import translate_sql
except ImportError:
    def translate_sql(sql):
        return sql


def queue_insert(
    cursor,  # SQLite cursor for fallback
    table: str,
    data: Dict[str, Any],
    source_agent: str,
    priority: int = PRIORITY_NORMAL
) -> bool:
    """
    Insert a row, routing through WAQ if available.
    
    Args:
        cursor: SQLite cursor (for fallback)
        table: Target table name
        data: Column-value dict
        source_agent: Agent name for logging
        priority: 0=normal, 1=high, 2=critical
        
    Returns:
        True if queued/executed successfully
    """
    if WAQ_AVAILABLE and is_queue_enabled():
        msg = WriteMessage(
            operation='INSERT',
            table=table,
            data=data,
            source_agent=source_agent,
            priority=priority
        )
        return publish_write(msg)
    else:
        # Direct write fallback
        ph = '%s' if _backend == 'postgresql' else '?'
        columns = ', '.join(data.keys())
        placeholders = ', '.join([ph for _ in data])
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        cursor.execute(sql, tuple(data.values()))
        return True


def queue_update(
    cursor,
    table: str,
    data: Dict[str, Any],
    where: Dict[str, Any],
    source_agent: str,
    priority: int = PRIORITY_NORMAL
) -> bool:
    """
    Update rows, routing through WAQ if available.
    
    Args:
        cursor: SQLite cursor (for fallback)
        table: Target table name
        data: Column-value dict for SET clause
        where: Column-value dict for WHERE clause
        source_agent: Agent name for logging
        priority: 0=normal, 1=high, 2=critical
        
    Returns:
        True if queued/executed successfully
    """
    if WAQ_AVAILABLE and is_queue_enabled():
        msg = WriteMessage(
            operation='UPDATE',
            table=table,
            data=data,
            where_clause=where,
            source_agent=source_agent,
            priority=priority
        )
        return publish_write(msg)
    else:
        # Direct write fallback
        ph = '%s' if _backend == 'postgresql' else '?'
        set_clause = ', '.join([f"{k} = {ph}" for k in data.keys()])
        where_clause = ' AND '.join([f"{k} = {ph}" for k in where.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        params = list(data.values()) + list(where.values())
        cursor.execute(sql, tuple(params))
        return True


def queue_execute(
    cursor,
    sql: str,
    params,
    source_agent: str,
    priority: int = PRIORITY_NORMAL
) -> bool:
    """
    Execute raw SQL, routing through WAQ if available.

    Args:
        cursor: SQLite cursor (for fallback)
        sql: Raw SQL with ? or :name placeholders
        params: Parameter tuple (for ? placeholders) or dict (for :name placeholders)
        source_agent: Agent name for logging
        priority: 0=normal, 1=high, 2=critical

    Returns:
        True if queued/executed successfully
    """
    if WAQ_AVAILABLE and is_queue_enabled():
        # Params can be dict (named :params) or tuple (positional ?)
        if isinstance(params, dict):
            param_dict = params
        elif isinstance(params, (list, tuple)):
            param_dict = {f'p{i}': v for i, v in enumerate(params)}
        else:
            param_dict = {}
        msg = WriteMessage(
            operation='EXECUTE',
            table='_raw',
            data=param_dict,
            sql=sql,
            source_agent=source_agent,
            priority=priority
        )
        return publish_write(msg)
    else:
        translated = translate_sql(sql)
        cursor.execute(translated, params)
        return True


def is_waq_enabled() -> bool:
    """Check if Write-Ahead Queue is enabled and available."""
    return WAQ_AVAILABLE and is_queue_enabled()
