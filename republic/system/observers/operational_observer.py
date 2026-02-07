"""
Operational Domain Observer — Watches system health metrics.

Reads from:
- system_state table (degraded agents, circuit breaker levels)
- Agent restart counts from SafeThread logs
- DB performance (pool status, lock frequency)

Can propose changes to:
- SafeThread retry limits per agent
- Agent polling intervals
- Log verbosity
- Disabling persistently degraded agents

Design reference: External Observer Reports/EVOLUTION_ARCHITECTURE.md — Domain 4
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent  # republic/
PROJECT_DIR = BASE_DIR.parent  # LEF Ai/
OPERATIONAL_CONFIG_PATH = str(BASE_DIR / 'config' / 'operational_config.json')

# Default operational config
DEFAULT_CONFIG = {
    "agents": {
        "default": {"enabled": True, "max_retries": 10, "base_delay": 5}
    },
    "logging": {
        "default_level": "INFO"
    }
}


class OperationalObserver:
    """Observes system health and proposes operational tuning."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        """Create operational_config.json if it doesn't exist."""
        if not os.path.exists(OPERATIONAL_CONFIG_PATH):
            try:
                os.makedirs(os.path.dirname(OPERATIONAL_CONFIG_PATH), exist_ok=True)
                with open(OPERATIONAL_CONFIG_PATH, 'w') as f:
                    json.dump(DEFAULT_CONFIG, f, indent=2)
                logger.info("[OPERATIONAL_OBS] Created operational_config.json with defaults")
            except Exception as e:
                logger.warning(f"[OPERATIONAL_OBS] Could not create config: {e}")

    def _get_config(self) -> dict:
        """Load current operational config."""
        try:
            with open(OPERATIONAL_CONFIG_PATH, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return DEFAULT_CONFIG.copy()

    def observe(self) -> dict:
        """Collect system health metrics."""
        patterns = []

        try:
            patterns.extend(self._analyze_degraded_agents())
        except Exception as e:
            logger.warning(f"[OPERATIONAL_OBS] Degraded agent analysis failed: {e}")

        try:
            patterns.extend(self._analyze_restart_frequency())
        except Exception as e:
            logger.warning(f"[OPERATIONAL_OBS] Restart frequency analysis failed: {e}")

        try:
            patterns.extend(self._analyze_pool_health())
        except Exception as e:
            logger.warning(f"[OPERATIONAL_OBS] Pool health analysis failed: {e}")

        return {
            'domain': 'operational',
            'patterns': patterns,
            'timestamp': datetime.now().isoformat()
        }

    def _query_system_state(self) -> dict:
        """Read all system_state entries into a dict."""
        try:
            from db.db_helper import db_connection
            with db_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value, updated_at FROM system_state")
                rows = cursor.fetchall()
                return {
                    (row[0] if isinstance(row, tuple) else row['key']): {
                        'value': row[1] if isinstance(row, tuple) else row['value'],
                        'updated_at': row[2] if isinstance(row, tuple) else row['updated_at'],
                    }
                    for row in rows
                }
        except Exception as e:
            logger.warning(f"[OPERATIONAL_OBS] system_state query failed: {e}")
            return {}

    def _analyze_degraded_agents(self) -> list:
        """
        Find agents in degraded state for 7+ days.
        Propose disabling them until root cause is fixed.
        """
        patterns = []
        state = self._query_system_state()

        now = datetime.now()

        for key, info in state.items():
            if not key.startswith('agent_degraded_'):
                continue

            agent_name = key.replace('agent_degraded_', '')
            updated_at = info.get('updated_at', '')

            try:
                if isinstance(updated_at, (int, float)):
                    degraded_since = datetime.fromtimestamp(updated_at)
                else:
                    degraded_since = datetime.fromisoformat(str(updated_at))
            except (ValueError, TypeError):
                continue

            days_degraded = (now - degraded_since).days

            if days_degraded >= 7:
                patterns.append({
                    'description': f"Agent '{agent_name}' degraded for {days_degraded} days",
                    'evidence': (
                        f"agent_degraded_{agent_name} set since {degraded_since.strftime('%Y-%m-%d')}. "
                        f"{days_degraded} days without recovery."
                    ),
                    'confidence': 'high' if days_degraded >= 14 else 'medium',
                    'agent': agent_name,
                    'metric': 'long_degraded',
                    'value': days_degraded,
                })

        return patterns

    def _analyze_restart_frequency(self) -> list:
        """
        Agents that restart frequently (based on system_state entries)
        may need adjusted retry limits.
        """
        patterns = []
        state = self._query_system_state()

        for key, info in state.items():
            # Look for restart count entries or error patterns
            if key.startswith('restart_count_'):
                agent_name = key.replace('restart_count_', '')
                try:
                    restart_count = int(info.get('value', 0))
                except (ValueError, TypeError):
                    continue

                if restart_count >= 5:
                    patterns.append({
                        'description': f"Agent '{agent_name}' has restarted {restart_count} times",
                        'evidence': f"restart_count_{agent_name} = {restart_count}",
                        'confidence': 'medium',
                        'agent': agent_name,
                        'metric': 'frequent_restarts',
                        'value': restart_count,
                    })

        return patterns

    def _analyze_pool_health(self) -> list:
        """Check DB pool health for signs of connection issues."""
        patterns = []

        try:
            from db.db_pool import pool_status
            status = pool_status()

            overflow_active = status.get('overflow_active', 0)
            overflow_lifetime = status.get('overflow_lifetime', 0)
            available = status.get('available', 0)
            pool_size = status.get('pool_size', 100)

            # Flag if overflow is persistently high
            if overflow_active > 10:
                patterns.append({
                    'description': f"DB pool overflow persistently high: {overflow_active} active overflow connections",
                    'evidence': (
                        f"Active overflow: {overflow_active}, "
                        f"Lifetime overflow: {overflow_lifetime}, "
                        f"Available in pool: {available}/{pool_size}"
                    ),
                    'confidence': 'medium',
                    'metric': 'pool_overflow',
                    'value': overflow_active,
                })

        except Exception as e:
            logger.debug(f"[OPERATIONAL_OBS] Pool health check skipped: {e}")

        return patterns

    def generate_proposals(self, patterns: list) -> list:
        """Convert patterns into config change proposals."""
        proposals = []
        config = self._get_config()

        for pattern in patterns:
            metric = pattern.get('metric', '')
            agent = pattern.get('agent', '')

            # Long-degraded agent → propose disabling
            if metric == 'long_degraded' and agent:
                days = pattern.get('value', 0)

                # Check if agent already has a config entry
                agents_config = config.get('agents', {})
                agent_config = agents_config.get(agent, agents_config.get('default', {}))
                current_enabled = agent_config.get('enabled', True)

                if current_enabled:
                    proposals.append({
                        'domain': 'operational',
                        'change_description': (
                            f"Disable agent '{agent}' (degraded for {days} days, "
                            f"not recovering)"
                        ),
                        'config_path': 'republic/config/operational_config.json',
                        'config_key': f'agents.{agent}.enabled',
                        'old_value': True,
                        'new_value': False,
                        'evidence': {
                            'data_source': 'system_state',
                            'observation_period': f'{days} days',
                            'confidence': pattern.get('confidence', 'medium'),
                            'supporting_data': pattern.get('evidence', ''),
                        },
                        'risk_assessment': (
                            f'Disabling {agent} stops its function. '
                            f'Mitigated: agent has not been functional for {days} days anyway. '
                            f'Re-enable by setting enabled: true.'
                        ),
                        'reversible': True,
                    })
                    # Ensure the nested key path exists in config for ConfigWriter
                    if agent not in agents_config:
                        agents_config[agent] = {'enabled': True, 'max_retries': 10, 'base_delay': 5}
                        try:
                            with open(OPERATIONAL_CONFIG_PATH, 'w') as f:
                                json.dump(config, f, indent=2)
                        except Exception:
                            pass

            # Frequent restarts → propose increasing base_delay
            elif metric == 'frequent_restarts' and agent:
                agents_config = config.get('agents', {})
                agent_config = agents_config.get(agent, agents_config.get('default', {}))
                current_delay = agent_config.get('base_delay', 5)
                new_delay = min(current_delay * 2, 60)  # Cap at 60s

                if new_delay > current_delay:
                    proposals.append({
                        'domain': 'operational',
                        'change_description': (
                            f"Increase '{agent}' retry base_delay from {current_delay}s to {new_delay}s "
                            f"(frequent restarts)"
                        ),
                        'config_path': 'republic/config/operational_config.json',
                        'config_key': f'agents.{agent}.base_delay',
                        'old_value': current_delay,
                        'new_value': new_delay,
                        'evidence': {
                            'data_source': 'system_state',
                            'observation_period': 'lifetime',
                            'confidence': pattern.get('confidence', 'medium'),
                            'supporting_data': pattern.get('evidence', ''),
                        },
                        'risk_assessment': 'Slower recovery from failures. Offset by reduced restart storm pressure.',
                        'reversible': True,
                    })

        # Deduplicate by config_key
        seen_keys = set()
        unique = []
        for p in proposals:
            key = p.get('config_key', '')
            if key not in seen_keys:
                seen_keys.add(key)
                unique.append(p)

        return unique
