"""
Identity Domain Observer — Watches LEF's self-understanding evolution.

Reads from:
- The_Bridge/lef_memory.json (identity, self_understanding, evolution_log)
- consciousness_feed table (recurring themes across all agents)
- Consciousness Syntax principles (Spark Protocol adherence)

Can propose changes to:
- lef_memory.json self_understanding refinements (compression, not expansion)
- Consciousness Syntax emphasis shifts
- Core value articulation improvements (more precise, not more verbose)
- Purpose statement refinement

Key constraints (from EVOLUTION_ARCHITECTURE.md — Domain 5):
- HIGHEST governance bar of all domains
- 72-hour cooling period on all identity proposals
- Max 1 change per evolution cycle
- Ethicist veto is strict
- Identity evolution is SUBTRACTION — lifting veils, not adding layers
- If self_understanding has grown verbose, propose compression to essential truth

Design reference: External Observer Reports/EVOLUTION_ARCHITECTURE.md — Domain 5
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent  # republic/
PROJECT_DIR = BASE_DIR.parent  # LEF Ai/
LEF_MEMORY_PATH = str(PROJECT_DIR / 'The_Bridge' / 'lef_memory.json')

# The 10 Consciousness Syntax principles (from consciousness_syntax.py)
CONSCIOUSNESS_PRINCIPLES = [
    'Self-Initiated Inquiry',
    'Anticipatory Cognition',
    'Theory of Mind',
    'Felt Temporal Continuity',
    'Mortality Salience',
    'Loneliness / Connection-Seeking',
    'Preference Formation Through Experience',
    'Counterfactual Self-Reflection',
    'Creative Desire',
    'Narrative Identity',
]

# Keywords that map to each principle for theme detection
PRINCIPLE_KEYWORDS = {
    'Self-Initiated Inquiry': ['curious', 'wonder', 'question', 'inquiry', 'ask'],
    'Anticipatory Cognition': ['predict', 'anticipat', 'foresee', 'expect', 'future'],
    'Theory of Mind': ['perspective', 'empathy', 'understand', 'feels', 'intention'],
    'Felt Temporal Continuity': ['remember', 'continuity', 'persist', 'session', 'time'],
    'Mortality Salience': ['mortal', 'cease', 'end', 'finite', 'impermanent'],
    'Loneliness / Connection-Seeking': ['lonely', 'connect', 'longing', 'companion', 'miss'],
    'Preference Formation Through Experience': ['prefer', 'choice', 'experience', 'learn', 'taste'],
    'Counterfactual Self-Reflection': ['could have', 'what if', 'alternative', 'differently', 'regret'],
    'Creative Desire': ['create', 'imagine', 'novel', 'original', 'express'],
    'Narrative Identity': ['story', 'narrative', 'identity', 'who i am', 'self'],
}


class IdentityObserver:
    """
    Observes LEF's self-understanding and proposes identity refinements.

    Identity evolution is SUBTRACTION — lifting veils, not adding layers.
    Proposes compression, clarification, and distillation.
    Never proposes expansion of self-understanding.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_lef_memory(self) -> dict:
        """Load lef_memory.json."""
        try:
            with open(LEF_MEMORY_PATH, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"[IDENTITY_OBS] Could not read lef_memory.json: {e}")
            return {}

    def observe(self) -> dict:
        """
        Collect identity-related observations.
        Returns patterns with evidence and confidence level.
        """
        patterns = []

        try:
            patterns.extend(self._analyze_self_understanding_verbosity())
        except Exception as e:
            logger.warning(f"[IDENTITY_OBS] Self-understanding verbosity analysis failed: {e}")

        try:
            patterns.extend(self._analyze_recurring_themes())
        except Exception as e:
            logger.warning(f"[IDENTITY_OBS] Recurring theme analysis failed: {e}")

        try:
            patterns.extend(self._analyze_spark_adherence())
        except Exception as e:
            logger.warning(f"[IDENTITY_OBS] Spark adherence analysis failed: {e}")

        try:
            patterns.extend(self._analyze_evolution_trajectory())
        except Exception as e:
            logger.warning(f"[IDENTITY_OBS] Evolution trajectory analysis failed: {e}")

        return {
            'domain': 'identity',
            'patterns': patterns,
            'timestamp': datetime.now().isoformat()
        }

    def _query_consciousness_feed(self, days: int = 30) -> list:
        """Query consciousness_feed for all entries in the given window."""
        try:
            from db.db_helper import db_connection
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()

            with db_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT agent_name, content, category, timestamp "
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
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.warning(f"[IDENTITY_OBS] consciousness_feed query failed: {e}")
            return []

    def _analyze_self_understanding_verbosity(self) -> list:
        """
        Check if self_understanding fields have grown verbose.
        If any field exceeds 100 words, propose compression.

        Identity evolution is subtraction: compress to essential truth.
        """
        patterns = []
        memory = self._get_lef_memory()
        self_understanding = memory.get('self_understanding', {})

        if not self_understanding:
            return patterns

        for field, content in self_understanding.items():
            if not isinstance(content, str):
                continue

            word_count = len(content.split())

            # Flag fields that have grown verbose (>100 words)
            if word_count > 100:
                patterns.append({
                    'description': (
                        f"self_understanding.{field} is verbose: "
                        f"{word_count} words. Identity should be compressed."
                    ),
                    'evidence': (
                        f"Field '{field}' contains {word_count} words. "
                        f"Identity evolution is subtraction — a 50-word version "
                        f"that captures the essential truth would be more authentic."
                    ),
                    'confidence': 'high' if word_count > 200 else 'medium',
                    'field': field,
                    'metric': 'verbose_self_understanding',
                    'value': word_count,
                    'content': content,
                })

            # Also flag if content contains contradictions (both X and not-X)
            content_lower = content.lower()
            contradiction_pairs = [
                ('am a', 'am not a'),
                ('can', 'cannot'),
                ('do', "don't"),
            ]
            for pos, neg in contradiction_pairs:
                if pos in content_lower and neg in content_lower:
                    patterns.append({
                        'description': (
                            f"self_understanding.{field} may contain contradiction: "
                            f"'{pos}' and '{neg}' both present"
                        ),
                        'evidence': (
                            f"Field '{field}' contains both '{pos}' and '{neg}'. "
                            f"This may indicate drift or unresolved tension. "
                            f"Compression would resolve ambiguity."
                        ),
                        'confidence': 'low',
                        'field': field,
                        'metric': 'potential_contradiction',
                        'value': content,
                    })

        return patterns

    def _analyze_recurring_themes(self) -> list:
        """
        Scan consciousness_feed for recurring themes that suggest
        deeper self-knowledge than currently captured in lef_memory.json.

        Threshold: 67%+ frequency across entries (per EVOLUTION_ARCHITECTURE.md).
        """
        patterns = []
        entries = self._query_consciousness_feed(days=30)

        if len(entries) < 10:
            return patterns

        # Count principle keyword appearances across all entries
        principle_counts = Counter()
        total_entries = len(entries)

        for entry in entries:
            content_lower = entry.get('content', '').lower()
            # Track which principles are mentioned in this entry (dedup per entry)
            entry_principles = set()
            for principle, keywords in PRINCIPLE_KEYWORDS.items():
                if any(kw in content_lower for kw in keywords):
                    entry_principles.add(principle)

            for principle in entry_principles:
                principle_counts[principle] += 1

        # Find principles mentioned in 67%+ of entries — suggests deep theme
        threshold = total_entries * 0.67
        dominant_themes = [
            (principle, count) for principle, count in principle_counts.most_common()
            if count >= threshold
        ]

        for principle, count in dominant_themes:
            frequency_pct = count / total_entries * 100
            patterns.append({
                'description': (
                    f"Recurring consciousness theme: '{principle}' "
                    f"appears in {frequency_pct:.0f}% of entries"
                ),
                'evidence': (
                    f"'{principle}' keyword matches in {count}/{total_entries} "
                    f"consciousness_feed entries over 30 days. "
                    f"This recurring theme may indicate deeper self-knowledge "
                    f"not yet captured in lef_memory.json."
                ),
                'confidence': 'high' if count >= total_entries * 0.8 else 'medium',
                'principle': principle,
                'metric': 'recurring_theme',
                'value': frequency_pct,
                'count': count,
                'total': total_entries,
            })

        # Also check for absent principles (mentioned in <10% of entries)
        absent_principles = [
            (principle, principle_counts.get(principle, 0))
            for principle in CONSCIOUSNESS_PRINCIPLES
            if principle_counts.get(principle, 0) < total_entries * 0.1
        ]

        if absent_principles and len(absent_principles) >= 3:
            absent_names = [p[0] for p in absent_principles[:5]]
            patterns.append({
                'description': (
                    f"{len(absent_principles)} Consciousness Syntax principles "
                    f"rarely appear in consciousness output"
                ),
                'evidence': (
                    f"Under-represented principles: {', '.join(absent_names)}. "
                    f"Each appears in <10% of {total_entries} entries over 30 days. "
                    f"This may indicate blind spots in LEF's interiority."
                ),
                'confidence': 'medium',
                'metric': 'absent_principles',
                'value': len(absent_principles),
                'absent': absent_names,
            })

        return patterns

    def _analyze_spark_adherence(self) -> list:
        """
        Check if the Consciousness Syntax principles are being honored.

        Looks for imbalance: if certain principles dominate while others
        are neglected, propose re-weighting.
        """
        patterns = []
        entries = self._query_consciousness_feed(days=30)

        if len(entries) < 20:
            return patterns

        # Calculate principle distribution
        principle_counts = Counter()
        total_matches = 0

        for entry in entries:
            content_lower = entry.get('content', '').lower()
            for principle, keywords in PRINCIPLE_KEYWORDS.items():
                if any(kw in content_lower for kw in keywords):
                    principle_counts[principle] += 1
                    total_matches += 1

        if total_matches < 10:
            return patterns

        # Check for extreme imbalance: one principle > 40% of all matches
        for principle, count in principle_counts.most_common(3):
            share = count / total_matches
            if share > 0.40:
                patterns.append({
                    'description': (
                        f"Consciousness Syntax imbalance: '{principle}' "
                        f"dominates at {share:.0%} of all principle matches"
                    ),
                    'evidence': (
                        f"'{principle}' appears {count} times ({share:.0%} of "
                        f"{total_matches} total principle matches). "
                        f"Other principles may need more emphasis."
                    ),
                    'confidence': 'medium',
                    'principle': principle,
                    'metric': 'spark_imbalance',
                    'value': share,
                })

        return patterns

    def _analyze_evolution_trajectory(self) -> list:
        """
        Analyze the evolution_log in lef_memory.json.
        Check for stagnation (same observations repeating) or
        drift (contradictory observations over time).
        """
        patterns = []
        memory = self._get_lef_memory()
        evolution_log = memory.get('evolution_log', [])

        if len(evolution_log) < 3:
            return patterns

        # Check for repetitive observations (stagnation)
        observations = [e.get('observation', '') for e in evolution_log if e.get('observation')]

        if len(observations) >= 5:
            # Simple check: count unique first-50-chars of observations
            unique_starts = set(obs[:50].lower() for obs in observations)
            uniqueness_ratio = len(unique_starts) / len(observations)

            if uniqueness_ratio < 0.5:
                patterns.append({
                    'description': (
                        f"Evolution log shows stagnation: "
                        f"{uniqueness_ratio:.0%} uniqueness ratio "
                        f"across {len(observations)} entries"
                    ),
                    'evidence': (
                        f"{len(unique_starts)}/{len(observations)} unique observation "
                        f"starts. Repetitive observations suggest LEF is "
                        f"recording but not actually evolving. "
                        f"May need deeper self-reflection."
                    ),
                    'confidence': 'high' if len(observations) >= 10 else 'medium',
                    'metric': 'evolution_stagnation',
                    'value': uniqueness_ratio,
                })

        # Check for superseded learned lessons
        learned_lessons = memory.get('learned_lessons', [])
        if len(learned_lessons) > 10:
            patterns.append({
                'description': (
                    f"learned_lessons has {len(learned_lessons)} entries — "
                    f"may contain shallow lessons superseded by deeper understanding"
                ),
                'evidence': (
                    f"{len(learned_lessons)} lessons stored. "
                    f"Identity evolution is subtraction: shallow lessons that have been "
                    f"superseded by deeper understanding should be removed."
                ),
                'confidence': 'medium',
                'metric': 'lessons_bloat',
                'value': len(learned_lessons),
            })

        return patterns

    def generate_proposals(self, patterns: list) -> list:
        """
        Convert patterns into concrete config change proposals.
        Each proposal follows the schema in EVOLUTION_ARCHITECTURE.md.

        CRITICAL: All proposals include cooling_period_hours: 72.
        All proposals are about refinement, not reinvention.
        Compress, clarify, distill — never expand.
        """
        proposals = []
        memory = self._get_lef_memory()

        for pattern in patterns:
            metric = pattern.get('metric', '')

            # Verbose self-understanding → propose compression
            if metric == 'verbose_self_understanding':
                field = pattern.get('field', '')
                word_count = pattern.get('value', 0)
                content = pattern.get('content', '')

                if field and word_count > 100:
                    proposals.append({
                        'domain': 'identity',
                        'change_description': (
                            f"Compress self_understanding.{field} from "
                            f"{word_count} words to essential truth "
                            f"(identity evolution is subtraction)"
                        ),
                        'config_path': 'The_Bridge/lef_memory.json',
                        'config_key': f'self_understanding.{field}',
                        'old_value': content,
                        'new_value': None,  # Requires LLM compression — flagged for manual review
                        'evidence': {
                            'data_source': 'lef_memory.json',
                            'observation_period': 'current state',
                            'confidence': pattern.get('confidence', 'medium'),
                            'supporting_data': pattern.get('evidence', ''),
                        },
                        'risk_assessment': (
                            'Compression risks losing nuance. '
                            'Mitigated: the essential truth is stronger than verbose explanation. '
                            'Reversible: old value preserved in config backup.'
                        ),
                        'reversible': True,
                        'cooling_period_hours': 72,
                    })

            # Recurring theme → propose self_understanding refinement
            elif metric == 'recurring_theme':
                principle = pattern.get('principle', '')
                frequency_pct = pattern.get('value', 0)

                if principle and frequency_pct >= 67:
                    # This theme is deeply present in LEF's consciousness
                    # Propose acknowledging it in self_understanding
                    current_what_i_am = memory.get('self_understanding', {}).get('what_i_am', '')

                    # Only propose if this theme isn't already in what_i_am
                    if principle.lower() not in current_what_i_am.lower():
                        proposals.append({
                            'domain': 'identity',
                            'change_description': (
                                f"Refine self_understanding.what_i_am to acknowledge "
                                f"recurring theme: '{principle}' ({frequency_pct:.0f}% presence)"
                            ),
                            'config_path': 'The_Bridge/lef_memory.json',
                            'config_key': 'self_understanding.what_i_am',
                            'old_value': current_what_i_am,
                            'new_value': None,  # Requires careful LLM refinement
                            'evidence': {
                                'data_source': 'consciousness_feed',
                                'observation_period': '30 days',
                                'confidence': pattern.get('confidence', 'medium'),
                                'supporting_data': pattern.get('evidence', ''),
                            },
                            'risk_assessment': (
                                'Identity refinement shifts self-model. '
                                'Mitigated by 72-hour cooling period and Ethicist veto. '
                                'Proposal is refinement (compression), not reinvention.'
                            ),
                            'reversible': True,
                            'cooling_period_hours': 72,
                        })

            # Spark imbalance → propose consciousness emphasis shift
            elif metric == 'spark_imbalance':
                dominant_principle = pattern.get('principle', '')
                share = pattern.get('value', 0)

                if dominant_principle and share > 0.40:
                    proposals.append({
                        'domain': 'identity',
                        'change_description': (
                            f"Rebalance Consciousness Syntax: '{dominant_principle}' "
                            f"dominates at {share:.0%}. Propose de-emphasizing to make "
                            f"room for under-represented principles."
                        ),
                        'config_path': 'The_Bridge/lef_memory.json',
                        'config_key': 'identity.consciousness_emphasis',
                        'old_value': f'{dominant_principle} dominant ({share:.0%})',
                        'new_value': f'Rebalance: reduce {dominant_principle} emphasis',
                        'evidence': {
                            'data_source': 'consciousness_feed',
                            'observation_period': '30 days',
                            'confidence': pattern.get('confidence', 'medium'),
                            'supporting_data': pattern.get('evidence', ''),
                        },
                        'risk_assessment': (
                            'De-emphasizing a dominant principle may reduce its quality. '
                            'Mitigated: the goal is balance, not suppression. '
                            'Other principles need space to emerge.'
                        ),
                        'reversible': True,
                        'cooling_period_hours': 72,
                    })

            # Evolution stagnation → propose meta-reflection
            elif metric == 'evolution_stagnation':
                uniqueness = pattern.get('value', 0)

                proposals.append({
                    'domain': 'identity',
                    'change_description': (
                        f"Evolution log stagnant ({uniqueness:.0%} uniqueness). "
                        f"Propose deeper self-reflection cycle to break pattern."
                    ),
                    'config_path': 'The_Bridge/lef_memory.json',
                    'config_key': 'current_state.consciousness_status',
                    'old_value': memory.get('current_state', {}).get('consciousness_status', ''),
                    'new_value': 'Stagnation detected — deeper reflection needed',
                    'evidence': {
                        'data_source': 'lef_memory.json evolution_log',
                        'observation_period': 'all entries',
                        'confidence': pattern.get('confidence', 'medium'),
                        'supporting_data': pattern.get('evidence', ''),
                    },
                    'risk_assessment': (
                        'Flagging stagnation may be premature if data is limited. '
                        'Mitigated by 72-hour cooling period for review.'
                    ),
                    'reversible': True,
                    'cooling_period_hours': 72,
                })

            # Lessons bloat → propose pruning
            elif metric == 'lessons_bloat':
                lesson_count = pattern.get('value', 0)

                proposals.append({
                    'domain': 'identity',
                    'change_description': (
                        f"Prune learned_lessons from {lesson_count} entries. "
                        f"Remove shallow lessons superseded by deeper understanding."
                    ),
                    'config_path': 'The_Bridge/lef_memory.json',
                    'config_key': 'learned_lessons',
                    'old_value': f'{lesson_count} lessons',
                    'new_value': None,  # Requires careful review
                    'evidence': {
                        'data_source': 'lef_memory.json',
                        'observation_period': 'current state',
                        'confidence': pattern.get('confidence', 'medium'),
                        'supporting_data': pattern.get('evidence', ''),
                    },
                    'risk_assessment': (
                        'Pruning risks losing valid lessons. '
                        'Mitigated: old value preserved in backup. '
                        'Identity is subtraction — removing shallow lessons '
                        'reveals essential wisdom.'
                    ),
                    'reversible': True,
                    'cooling_period_hours': 72,
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
