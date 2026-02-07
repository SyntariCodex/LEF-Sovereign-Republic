"""
Consciousness Domain Observer — Watches consciousness agent output quality.

Reads from:
- consciousness_feed table (all entries, not just unconsumed)
- system_state (agent health)
- Agent cycle timing from logs

Can propose changes to:
- Consciousness agent cycle frequency
- consciousness_feed max_items in memory_retriever
- Introspector tension thresholds

Design reference: External Observer Reports/EVOLUTION_ARCHITECTURE.md — Domain 2
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent  # republic/
PROJECT_DIR = BASE_DIR.parent  # LEF Ai/
CONSCIOUSNESS_CONFIG_PATH = str(BASE_DIR / 'config' / 'consciousness_config.json')

# Default consciousness config values
DEFAULT_CONFIG = {
    "philosopher": {"cycle_interval_seconds": 3600},
    "introspector": {"cycle_interval_seconds": 3600, "tension_threshold": 5},
    "contemplator": {"cycle_interval_seconds": 3600},
    "metacognition": {"cycle_interval_seconds": 7200},
    "memory_retriever": {"max_consciousness_items": 5}
}


class ConsciousnessObserver:
    """Observes consciousness agent output quality and proposes tuning."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        """Create consciousness_config.json if it doesn't exist."""
        if not os.path.exists(CONSCIOUSNESS_CONFIG_PATH):
            try:
                os.makedirs(os.path.dirname(CONSCIOUSNESS_CONFIG_PATH), exist_ok=True)
                with open(CONSCIOUSNESS_CONFIG_PATH, 'w') as f:
                    json.dump(DEFAULT_CONFIG, f, indent=2)
                logger.info("[CONSCIOUSNESS_OBS] Created consciousness_config.json with defaults")
            except Exception as e:
                logger.warning(f"[CONSCIOUSNESS_OBS] Could not create config: {e}")

    def _get_config(self) -> dict:
        """Load current consciousness config."""
        try:
            with open(CONSCIOUSNESS_CONFIG_PATH, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return DEFAULT_CONFIG.copy()

    def observe(self) -> dict:
        """Collect consciousness output metrics."""
        patterns = []

        try:
            patterns.extend(self._analyze_output_quality())
        except Exception as e:
            logger.warning(f"[CONSCIOUSNESS_OBS] Output quality analysis failed: {e}")

        try:
            patterns.extend(self._analyze_output_frequency())
        except Exception as e:
            logger.warning(f"[CONSCIOUSNESS_OBS] Output frequency analysis failed: {e}")

        try:
            patterns.extend(self._analyze_consumption_rate())
        except Exception as e:
            logger.warning(f"[CONSCIOUSNESS_OBS] Consumption rate analysis failed: {e}")

        return {
            'domain': 'consciousness',
            'patterns': patterns,
            'timestamp': datetime.now().isoformat()
        }

    def _query_consciousness_feed(self, days: int = 7) -> list:
        """Query consciousness_feed for entries in the given window."""
        try:
            from db.db_helper import db_connection
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            with db_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT agent_name, content, category, timestamp, consumed "
                    "FROM consciousness_feed WHERE timestamp >= ? "
                    "ORDER BY timestamp DESC",
                    (cutoff,)
                )
                rows = cursor.fetchall()
                return [
                    {
                        'agent_name': row[0] if isinstance(row, tuple) else row['agent_name'],
                        'content': row[1] if isinstance(row, tuple) else row['content'],
                        'category': row[2] if isinstance(row, tuple) else row['category'],
                        'timestamp': row[3] if isinstance(row, tuple) else row['timestamp'],
                        'consumed': row[4] if isinstance(row, tuple) else row['consumed'],
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.warning(f"[CONSCIOUSNESS_OBS] consciousness_feed query failed: {e}")
            return []

    def _jaccard_similarity(self, text_a: str, text_b: str) -> float:
        """Simple text similarity using Jaccard index on word sets."""
        if not text_a or not text_b:
            return 0.0
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0

    def _analyze_output_quality(self) -> list:
        """
        Measure semantic diversity of consciousness_feed entries per agent.
        High duplication rate = agent producing noise.
        Uses simple text similarity (Jaccard on word sets).
        """
        patterns = []
        entries = self._query_consciousness_feed(days=7)
        if not entries:
            return patterns

        # Group by agent
        by_agent = defaultdict(list)
        for entry in entries:
            by_agent[entry['agent_name']].append(entry['content'])

        for agent, contents in by_agent.items():
            if len(contents) < 5:
                continue  # Need minimum sample

            # Check pairwise similarity of consecutive entries
            duplicates = 0
            comparisons = 0
            for i in range(len(contents) - 1):
                sim = self._jaccard_similarity(contents[i], contents[i + 1])
                comparisons += 1
                if sim > 0.6:  # 60% similarity = structural duplicate
                    duplicates += 1

            if comparisons == 0:
                continue

            dup_rate = duplicates / comparisons

            if dup_rate > 0.5 and len(contents) >= 10:
                patterns.append({
                    'description': f"{agent} output duplication rate is {dup_rate:.0%} over 7 days",
                    'evidence': (
                        f"{duplicates}/{comparisons} consecutive pairs are structural duplicates "
                        f"(>60% word overlap). {len(contents)} total entries."
                    ),
                    'confidence': 'high' if len(contents) >= 20 else 'medium',
                    'agent': agent.lower(),
                    'metric': 'high_duplication',
                    'value': dup_rate,
                })

        return patterns

    def _analyze_output_frequency(self) -> list:
        """
        How often does each agent write to consciousness_feed?
        Flag agents that write too frequently (noise) or too rarely (silent).
        """
        patterns = []
        entries = self._query_consciousness_feed(days=7)
        if not entries:
            return patterns

        # Count per agent
        agent_counts = defaultdict(int)
        for entry in entries:
            agent_counts[entry['agent_name']] += 1

        # Expected entries per 7 days based on config
        config = self._get_config()
        expected = {
            'Philosopher': 7 * 24 * 3600 / config.get('philosopher', {}).get('cycle_interval_seconds', 3600),
            'Introspector': 7 * 24 * 3600 / config.get('introspector', {}).get('cycle_interval_seconds', 3600),
            'Contemplator': 7 * 24 * 3600 / config.get('contemplator', {}).get('cycle_interval_seconds', 3600),
            'MetaCognition': 7 * 24 * 3600 / config.get('metacognition', {}).get('cycle_interval_seconds', 7200),
        }

        for agent, count in agent_counts.items():
            expected_count = expected.get(agent, 168)  # default: ~1/hour for 7 days

            # Flag over-producers (>150% of expected)
            if count > expected_count * 1.5 and count >= 20:
                patterns.append({
                    'description': f"{agent} producing {count} entries in 7 days (expected ~{int(expected_count)})",
                    'evidence': f"{count} entries vs expected {int(expected_count)}. Over-producing by {((count/expected_count) - 1):.0%}",
                    'confidence': 'medium',
                    'agent': agent.lower(),
                    'metric': 'over_producing',
                    'value': count,
                    'expected': expected_count,
                })

            # Flag silent agents (<25% of expected)
            if count < expected_count * 0.25 and expected_count >= 10:
                patterns.append({
                    'description': f"{agent} unusually silent: only {count} entries in 7 days (expected ~{int(expected_count)})",
                    'evidence': f"{count} entries vs expected {int(expected_count)}. Producing only {(count/expected_count):.0%} of expected output.",
                    'confidence': 'medium',
                    'agent': agent.lower(),
                    'metric': 'under_producing',
                    'value': count,
                    'expected': expected_count,
                })

        return patterns

    def _analyze_consumption_rate(self) -> list:
        """
        How many consciousness_feed entries are consumed vs produced?
        If production >> consumption, entries are being wasted.
        """
        patterns = []
        entries = self._query_consciousness_feed(days=7)
        if not entries:
            return patterns

        total = len(entries)
        consumed = sum(1 for e in entries if e.get('consumed'))
        unconsumed = total - consumed

        if total < 10:
            return patterns

        consumption_rate = consumed / total if total > 0 else 0

        if consumption_rate < 0.3 and unconsumed > 50:
            patterns.append({
                'description': f"Only {consumption_rate:.0%} of consciousness_feed entries consumed in 7 days",
                'evidence': f"{consumed}/{total} consumed. {unconsumed} entries wasted.",
                'confidence': 'high' if total >= 50 else 'medium',
                'metric': 'low_consumption',
                'value': consumption_rate,
                'unconsumed': unconsumed,
            })

        if consumption_rate > 0.95 and total >= 20:
            patterns.append({
                'description': f"consciousness_feed almost fully consumed ({consumption_rate:.0%}). May need more items surfaced.",
                'evidence': f"{consumed}/{total} consumed. LEF may benefit from seeing more reflections.",
                'confidence': 'medium',
                'metric': 'high_consumption',
                'value': consumption_rate,
            })

        return patterns

    def generate_proposals(self, patterns: list) -> list:
        """Convert patterns into config change proposals."""
        proposals = []
        config = self._get_config()

        for pattern in patterns:
            metric = pattern.get('metric', '')
            agent = pattern.get('agent', '')

            # High duplication → increase cycle interval (reduce frequency)
            if metric == 'high_duplication' and agent:
                agent_config = config.get(agent, {})
                current_interval = agent_config.get('cycle_interval_seconds', 3600)
                # Double the interval
                new_interval = current_interval * 2
                # Cap at 8 hours
                new_interval = min(new_interval, 28800)

                proposals.append({
                    'domain': 'consciousness',
                    'change_description': (
                        f"Increase {agent} cycle interval from {current_interval}s to {new_interval}s "
                        f"(reduce output noise)"
                    ),
                    'config_path': 'republic/config/consciousness_config.json',
                    'config_key': f'{agent}.cycle_interval_seconds',
                    'old_value': current_interval,
                    'new_value': new_interval,
                    'evidence': {
                        'data_source': 'consciousness_feed',
                        'observation_period': '7 days',
                        'confidence': pattern.get('confidence', 'medium'),
                        'supporting_data': pattern.get('evidence', ''),
                    },
                    'risk_assessment': (
                        f'Longer cycle means fewer reflections. '
                        f'Offset by higher quality per entry. '
                        f'Reversible if insight frequency drops.'
                    ),
                    'reversible': True,
                })

            # Over-producing → increase cycle interval
            elif metric == 'over_producing' and agent:
                agent_config = config.get(agent, {})
                current_interval = agent_config.get('cycle_interval_seconds', 3600)
                # Increase by 50%
                new_interval = int(current_interval * 1.5)

                proposals.append({
                    'domain': 'consciousness',
                    'change_description': (
                        f"Increase {agent} cycle interval from {current_interval}s to {new_interval}s "
                        f"(over-producing)"
                    ),
                    'config_path': 'republic/config/consciousness_config.json',
                    'config_key': f'{agent}.cycle_interval_seconds',
                    'old_value': current_interval,
                    'new_value': new_interval,
                    'evidence': {
                        'data_source': 'consciousness_feed',
                        'observation_period': '7 days',
                        'confidence': pattern.get('confidence', 'medium'),
                        'supporting_data': pattern.get('evidence', ''),
                    },
                    'risk_assessment': 'Fewer outputs. Offset by better signal-to-noise ratio.',
                    'reversible': True,
                })

            # Low consumption → reduce max_consciousness_items or slow production
            elif metric == 'low_consumption':
                current_max = config.get('memory_retriever', {}).get('max_consciousness_items', 5)
                # If already low, don't reduce further
                if current_max > 3:
                    new_max = max(3, current_max - 2)
                    proposals.append({
                        'domain': 'consciousness',
                        'change_description': (
                            f"Reduce memory_retriever max_consciousness_items from {current_max} to {new_max} "
                            f"(low consumption rate)"
                        ),
                        'config_path': 'republic/config/consciousness_config.json',
                        'config_key': 'memory_retriever.max_consciousness_items',
                        'old_value': current_max,
                        'new_value': new_max,
                        'evidence': {
                            'data_source': 'consciousness_feed',
                            'observation_period': '7 days',
                            'confidence': pattern.get('confidence', 'medium'),
                            'supporting_data': pattern.get('evidence', ''),
                        },
                        'risk_assessment': 'Fewer reflections surfaced per conversation. Offset by less noise.',
                        'reversible': True,
                    })

            # High consumption → increase max_consciousness_items
            elif metric == 'high_consumption':
                current_max = config.get('memory_retriever', {}).get('max_consciousness_items', 5)
                new_max = min(current_max + 2, 15)  # Cap at 15
                if new_max > current_max:
                    proposals.append({
                        'domain': 'consciousness',
                        'change_description': (
                            f"Increase memory_retriever max_consciousness_items from {current_max} to {new_max} "
                            f"(high consumption, LEF wants more)"
                        ),
                        'config_path': 'republic/config/consciousness_config.json',
                        'config_key': 'memory_retriever.max_consciousness_items',
                        'old_value': current_max,
                        'new_value': new_max,
                        'evidence': {
                            'data_source': 'consciousness_feed',
                            'observation_period': '7 days',
                            'confidence': pattern.get('confidence', 'medium'),
                            'supporting_data': pattern.get('evidence', ''),
                        },
                        'risk_assessment': 'More reflections in prompt = longer context. Monitor prompt size.',
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
