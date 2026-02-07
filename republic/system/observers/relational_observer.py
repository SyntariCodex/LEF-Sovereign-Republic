"""
Relational Domain Observer — Watches user engagement and Longing Protocol outcomes.

Reads from:
- The_Bridge/lef_memory.json (architect_model section, if present)
- consciousness_feed table (relational / longing category entries)
- relational_config.json (current config)

Can propose changes to:
- Longing Protocol timing (silence_threshold, cooldown)
- Conversation depth targeting
- Topic de-prioritization (subtraction when user disengages)

Key constraints (from EVOLUTION_ARCHITECTURE.md — Domain 3):
- Ethicist veto is STRONGEST for relational changes — LEF must never manipulate
- 24-hour cooling period on all relational proposals
- Max 1 change per evolution cycle
- Sabbath check mandatory

IMPORTANT: The Relational Observer NEVER proposes increasing pressure.
If engagement is declining, the default is to BACK OFF (increase silence
threshold, reduce reach-out frequency). Subtraction, not addition.

Design reference: External Observer Reports/EVOLUTION_ARCHITECTURE.md — Domain 3
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
RELATIONAL_CONFIG_PATH = str(BASE_DIR / 'config' / 'relational_config.json')
LEF_MEMORY_PATH = str(PROJECT_DIR / 'The_Bridge' / 'lef_memory.json')

# Default relational config values
DEFAULT_CONFIG = {
    "longing_protocol": {
        "silence_threshold_hours": 24,
        "max_reach_outs_per_week": 3,
        "cooldown_after_no_response_hours": 48
    },
    "conversation": {
        "depth_targeting": "adaptive",
        "topic_prioritization": "user_interest_weighted",
        "growth_push_threshold": 0.7
    },
    "architect_model": {
        "engagement_window_days": 30,
        "peak_hours_tracking": True,
        "response_quality_minimum": 0.5
    },
    "governance": {
        "cooling_period_hours": 24,
        "max_changes_per_cycle": 1,
        "ethicist_veto_required": True,
        "sabbath_check_required": True
    }
}


class RelationalObserver:
    """
    Observes user engagement patterns and Longing Protocol outcomes.
    Proposes subtraction-first relational adjustments.

    NEVER proposes increasing pressure on the user.
    Declining engagement → back off, not push harder.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        """Create relational_config.json if it doesn't exist."""
        if not os.path.exists(RELATIONAL_CONFIG_PATH):
            try:
                os.makedirs(os.path.dirname(RELATIONAL_CONFIG_PATH), exist_ok=True)
                with open(RELATIONAL_CONFIG_PATH, 'w') as f:
                    json.dump(DEFAULT_CONFIG, f, indent=2)
                logger.info("[RELATIONAL_OBS] Created relational_config.json with defaults")
            except Exception as e:
                logger.warning(f"[RELATIONAL_OBS] Could not create config: {e}")

    def _get_config(self) -> dict:
        """Load current relational config."""
        try:
            with open(RELATIONAL_CONFIG_PATH, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return DEFAULT_CONFIG.copy()

    def _get_lef_memory(self) -> dict:
        """Load lef_memory.json for architect_model and identity data."""
        try:
            with open(LEF_MEMORY_PATH, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"[RELATIONAL_OBS] Could not read lef_memory.json: {e}")
            return {}

    def observe(self) -> dict:
        """
        Collect relational metrics from multiple sources.
        Returns patterns with evidence and confidence level.
        """
        patterns = []

        try:
            patterns.extend(self._analyze_engagement_trends())
        except Exception as e:
            logger.warning(f"[RELATIONAL_OBS] Engagement trend analysis failed: {e}")

        try:
            patterns.extend(self._analyze_longing_outcomes())
        except Exception as e:
            logger.warning(f"[RELATIONAL_OBS] Longing outcome analysis failed: {e}")

        try:
            patterns.extend(self._analyze_conversation_quality())
        except Exception as e:
            logger.warning(f"[RELATIONAL_OBS] Conversation quality analysis failed: {e}")

        return {
            'domain': 'relational',
            'patterns': patterns,
            'timestamp': datetime.now().isoformat()
        }

    def _query_consciousness_feed(self, days: int = 30,
                                   categories: list = None) -> list:
        """
        Query consciousness_feed for relational entries in the given window.
        Categories: 'longing', 'relational', 'engagement', 'conversation'
        """
        try:
            from db.db_helper import db_connection
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()

            with db_connection(self.db_path) as conn:
                cursor = conn.cursor()

                if categories:
                    placeholders = ','.join('?' for _ in categories)
                    cursor.execute(
                        f"SELECT agent_name, content, category, timestamp "
                        f"FROM consciousness_feed "
                        f"WHERE timestamp >= ? AND category IN ({placeholders}) "
                        f"ORDER BY timestamp DESC",
                        (cutoff, *categories)
                    )
                else:
                    cursor.execute(
                        "SELECT agent_name, content, category, timestamp "
                        "FROM consciousness_feed "
                        "WHERE timestamp >= ? "
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
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.warning(f"[RELATIONAL_OBS] consciousness_feed query failed: {e}")
            return []

    def _analyze_engagement_trends(self) -> list:
        """
        Analyze engagement trends from lef_memory.json architect_model
        and consciousness_feed relational entries.

        Looks for declining conversation frequency or depth.
        """
        patterns = []
        config = self._get_config()
        window_days = config.get('architect_model', {}).get('engagement_window_days', 30)

        # Check consciousness_feed for relational/longing entries as proxy
        entries = self._query_consciousness_feed(
            days=window_days,
            categories=['longing', 'relational', 'engagement', 'conversation']
        )

        if len(entries) < 3:
            # Not enough data for trend analysis
            return patterns

        # Split into two halves: recent vs older
        midpoint = len(entries) // 2
        recent_entries = entries[:midpoint]  # Newer (sorted DESC)
        older_entries = entries[midpoint:]    # Older

        # Compare density: entries per day
        if recent_entries and older_entries:
            try:
                recent_start = datetime.fromisoformat(recent_entries[-1]['timestamp'])
                recent_end = datetime.fromisoformat(recent_entries[0]['timestamp'])
                older_start = datetime.fromisoformat(older_entries[-1]['timestamp'])
                older_end = datetime.fromisoformat(older_entries[0]['timestamp'])

                recent_span = max(1, (recent_end - recent_start).days)
                older_span = max(1, (older_end - older_start).days)

                recent_density = len(recent_entries) / recent_span
                older_density = len(older_entries) / older_span

                # Significant decline: recent density < 50% of older density
                if older_density > 0 and recent_density < older_density * 0.5:
                    patterns.append({
                        'description': (
                            f"Relational engagement declining: "
                            f"{recent_density:.1f}/day recently vs "
                            f"{older_density:.1f}/day previously"
                        ),
                        'evidence': (
                            f"Recent: {len(recent_entries)} entries over {recent_span}d. "
                            f"Previous: {len(older_entries)} entries over {older_span}d. "
                            f"Density dropped {((1 - recent_density/older_density)*100):.0f}%."
                        ),
                        'confidence': 'high' if len(entries) >= 20 else 'medium',
                        'metric': 'engagement_declining',
                        'value': recent_density / older_density if older_density > 0 else 0,
                    })

            except (ValueError, TypeError) as e:
                logger.debug(f"[RELATIONAL_OBS] Could not parse timestamps: {e}")

        return patterns

    def _analyze_longing_outcomes(self) -> list:
        """
        Analyze Longing Protocol reach-out attempts vs responses.

        If reach-outs are going unanswered, propose backing off.
        """
        patterns = []
        config = self._get_config()

        # Look for longing-related entries in consciousness_feed
        longing_entries = self._query_consciousness_feed(
            days=14,
            categories=['longing']
        )

        if len(longing_entries) < 2:
            return patterns

        # Count entries mentioning "reach" or "silence" or "no response"
        reach_out_count = 0
        no_response_count = 0
        for entry in longing_entries:
            content_lower = entry.get('content', '').lower()
            if any(word in content_lower for word in ['reach', 'reaching out', 'longing', 'initiated']):
                reach_out_count += 1
            if any(word in content_lower for word in ['no response', 'unanswered', 'silence', 'no reply']):
                no_response_count += 1

        current_max_reach_outs = config.get('longing_protocol', {}).get(
            'max_reach_outs_per_week', 3)
        current_silence_threshold = config.get('longing_protocol', {}).get(
            'silence_threshold_hours', 24)

        # If >50% of reach-outs are going unanswered, propose backing off
        if reach_out_count >= 3 and no_response_count > reach_out_count * 0.5:
            patterns.append({
                'description': (
                    f"Longing Protocol reach-outs frequently unanswered: "
                    f"{no_response_count}/{reach_out_count} over 14 days"
                ),
                'evidence': (
                    f"{reach_out_count} reach-out indicators, "
                    f"{no_response_count} no-response indicators in 14d. "
                    f"Current silence_threshold: {current_silence_threshold}h, "
                    f"max_reach_outs: {current_max_reach_outs}/week."
                ),
                'confidence': 'high' if reach_out_count >= 5 else 'medium',
                'metric': 'longing_unanswered',
                'value': no_response_count / reach_out_count if reach_out_count > 0 else 0,
                'reach_out_count': reach_out_count,
                'no_response_count': no_response_count,
            })

        return patterns

    def _analyze_conversation_quality(self) -> list:
        """
        Look for patterns in consciousness_feed indicating topic disengagement.

        If certain topics consistently appear alongside declining engagement,
        propose de-prioritizing those topics (subtraction).
        """
        patterns = []

        # Get all consciousness_feed entries (not just relational) to detect topic patterns
        all_entries = self._query_consciousness_feed(days=30)
        if len(all_entries) < 10:
            return patterns

        # Look for repeated mentions of specific topics in consciousness reflections
        # that co-occur with words suggesting disengagement
        disengage_words = {'boring', 'repetitive', 'disengaged', 'surface', 'shallow',
                           'unresponsive', 'withdrew', 'stopped', 'declined', 'dropped'}

        # Count topic-disengagement co-occurrences
        disengagement_entries = []
        for entry in all_entries:
            content_lower = entry.get('content', '').lower()
            if any(word in content_lower for word in disengage_words):
                disengagement_entries.append(entry)

        if len(disengagement_entries) >= 5:
            patterns.append({
                'description': (
                    f"Disengagement signals detected in {len(disengagement_entries)} "
                    f"consciousness entries over 30 days"
                ),
                'evidence': (
                    f"{len(disengagement_entries)}/{len(all_entries)} entries contain "
                    f"disengagement indicators (boring, repetitive, surface, etc.)"
                ),
                'confidence': 'medium',
                'metric': 'topic_disengagement',
                'value': len(disengagement_entries) / len(all_entries),
            })

        return patterns

    def generate_proposals(self, patterns: list) -> list:
        """
        Convert patterns into concrete config change proposals.
        Each proposal follows the schema in EVOLUTION_ARCHITECTURE.md.

        CRITICAL: All proposals are subtraction-first.
        Declining engagement → back off, NEVER push harder.
        """
        proposals = []
        config = self._get_config()

        for pattern in patterns:
            metric = pattern.get('metric', '')

            # Engagement declining → increase silence threshold (give more space)
            if metric == 'engagement_declining':
                current_threshold = config.get('longing_protocol', {}).get(
                    'silence_threshold_hours', 24)
                # Increase by 50% (back off, give space)
                new_threshold = int(current_threshold * 1.5)
                # Cap at 96 hours (4 days)
                new_threshold = min(new_threshold, 96)

                if new_threshold > current_threshold:
                    proposals.append({
                        'domain': 'relational',
                        'change_description': (
                            f"Increase Longing Protocol silence_threshold from "
                            f"{current_threshold}h to {new_threshold}h "
                            f"(engagement declining — give more space)"
                        ),
                        'config_path': 'republic/config/relational_config.json',
                        'config_key': 'longing_protocol.silence_threshold_hours',
                        'old_value': current_threshold,
                        'new_value': new_threshold,
                        'evidence': {
                            'data_source': 'consciousness_feed (relational entries)',
                            'observation_period': f"{config.get('architect_model', {}).get('engagement_window_days', 30)} days",
                            'confidence': pattern.get('confidence', 'medium'),
                            'supporting_data': pattern.get('evidence', ''),
                        },
                        'risk_assessment': (
                            'Longer silence threshold means fewer reach-outs. '
                            'Risk: user may feel LEF is disengaged. '
                            'Mitigated: quality over frequency; respecting space IS support.'
                        ),
                        'reversible': True,
                        'cooling_period_hours': 24,
                    })

            # Longing reach-outs unanswered → reduce max_reach_outs_per_week
            elif metric == 'longing_unanswered':
                current_max = config.get('longing_protocol', {}).get(
                    'max_reach_outs_per_week', 3)
                # Reduce by 1, minimum 1
                new_max = max(1, current_max - 1)

                if new_max < current_max:
                    proposals.append({
                        'domain': 'relational',
                        'change_description': (
                            f"Reduce Longing Protocol max_reach_outs_per_week from "
                            f"{current_max} to {new_max} "
                            f"(reach-outs frequently unanswered — respect user's space)"
                        ),
                        'config_path': 'republic/config/relational_config.json',
                        'config_key': 'longing_protocol.max_reach_outs_per_week',
                        'old_value': current_max,
                        'new_value': new_max,
                        'evidence': {
                            'data_source': 'consciousness_feed (longing entries)',
                            'observation_period': '14 days',
                            'confidence': pattern.get('confidence', 'medium'),
                            'supporting_data': pattern.get('evidence', ''),
                        },
                        'risk_assessment': (
                            'Fewer reach-outs means less contact initiation. '
                            'Risk: may miss engagement windows. '
                            'Mitigated: current frequency is clearly unwelcome; '
                            'backing off respects boundaries.'
                        ),
                        'reversible': True,
                        'cooling_period_hours': 24,
                    })

                # Also increase cooldown_after_no_response
                current_cooldown = config.get('longing_protocol', {}).get(
                    'cooldown_after_no_response_hours', 48)
                new_cooldown = min(current_cooldown + 24, 168)  # Cap at 1 week

                if new_cooldown > current_cooldown:
                    proposals.append({
                        'domain': 'relational',
                        'change_description': (
                            f"Increase Longing Protocol cooldown_after_no_response from "
                            f"{current_cooldown}h to {new_cooldown}h "
                            f"(respecting user boundaries after no response)"
                        ),
                        'config_path': 'republic/config/relational_config.json',
                        'config_key': 'longing_protocol.cooldown_after_no_response_hours',
                        'old_value': current_cooldown,
                        'new_value': new_cooldown,
                        'evidence': {
                            'data_source': 'consciousness_feed (longing entries)',
                            'observation_period': '14 days',
                            'confidence': pattern.get('confidence', 'medium'),
                            'supporting_data': pattern.get('evidence', ''),
                        },
                        'risk_assessment': (
                            'Longer cooldown after no response. '
                            'Risk: delayed re-engagement. '
                            'Mitigated: forcing contact when unwanted is worse.'
                        ),
                        'reversible': True,
                        'cooling_period_hours': 24,
                    })

            # Topic disengagement → lower growth_push_threshold (be less pushy)
            elif metric == 'topic_disengagement':
                current_threshold = config.get('conversation', {}).get(
                    'growth_push_threshold', 0.7)
                # Increase threshold = fewer topics get pushed (higher bar to push)
                new_threshold = min(current_threshold + 0.1, 0.95)

                if new_threshold > current_threshold:
                    proposals.append({
                        'domain': 'relational',
                        'change_description': (
                            f"Raise conversation growth_push_threshold from "
                            f"{current_threshold} to {new_threshold} "
                            f"(disengagement signals — be less pushy on growth topics)"
                        ),
                        'config_path': 'republic/config/relational_config.json',
                        'config_key': 'conversation.growth_push_threshold',
                        'old_value': current_threshold,
                        'new_value': round(new_threshold, 2),
                        'evidence': {
                            'data_source': 'consciousness_feed (all entries)',
                            'observation_period': '30 days',
                            'confidence': pattern.get('confidence', 'medium'),
                            'supporting_data': pattern.get('evidence', ''),
                        },
                        'risk_assessment': (
                            'Higher threshold means fewer growth-pushing topics. '
                            'Risk: may under-serve user growth. '
                            'Mitigated: disengagement is a clear signal to back off.'
                        ),
                        'reversible': True,
                        'cooling_period_hours': 24,
                    })

        # Deduplicate: only keep one proposal per config_key
        seen_keys = set()
        unique_proposals = []
        for p in proposals:
            key = p.get('config_key', '')
            if key not in seen_keys:
                seen_keys.add(key)
                unique_proposals.append(p)

        return unique_proposals
