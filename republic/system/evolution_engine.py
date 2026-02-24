"""
Evolution Engine — LEF's self-modification capability.
Observes patterns across 5 domains, proposes config changes,
routes through vest_action() governance, enacts approved changes.

Design reference: External Observer Reports/EVOLUTION_ARCHITECTURE.md

Cycle: OBSERVE → REFLECT → PROPOSE → GOVERN → ENACT
Runs every 24 hours as a SafeThread.
Safety rails: max 3 changes/cycle, max 10 changes/week, config backups.
"""

import os
import json
import uuid
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent  # republic/
PROJECT_DIR = BASE_DIR.parent  # LEF Ai/


class EvolutionEngine:
    """Central coordinator for LEF's self-modification capability."""

    # Safety rails
    MAX_CHANGES_PER_CYCLE = 3
    MAX_CHANGES_PER_WEEK = 10

    PROPOSAL_LOG_PATH = str(PROJECT_DIR / 'The_Bridge' / 'evolution_proposals.json')
    CONFIG_BACKUP_DIR = str(PROJECT_DIR / 'The_Bridge' / 'config_backups')

    # Governance strictness by domain (from EVOLUTION_ARCHITECTURE.md)
    GOVERNANCE_CONFIG = {
        'metabolism': {
            'requires_ethicist': True,
            'ethicist_strict': False,
            'cooling_period_hours': 0,
            'max_per_cycle': 2,
        },
        'consciousness': {
            'requires_ethicist': True,
            'ethicist_strict': False,
            'cooling_period_hours': 0,
            'max_per_cycle': 2,
        },
        'relational': {
            'requires_ethicist': True,
            'ethicist_strict': True,
            'cooling_period_hours': 24,
            'max_per_cycle': 1,
        },
        'operational': {
            'requires_ethicist': False,
            'ethicist_strict': False,
            'cooling_period_hours': 0,
            'max_per_cycle': 3,
        },
        'identity': {
            'requires_ethicist': True,
            'ethicist_strict': True,
            'cooling_period_hours': 72,
            'max_per_cycle': 1,
        },
    }

    # Phase 38.75b: Bounded modification envelopes — safe ranges for metabolic parameter changes
    METABOLIC_BOUNDS = {
        'DYNASTY.take_profit_threshold': (0.1, 1.0),
        'DYNASTY.stop_loss_threshold': (-0.30, -0.05),
        'ARENA.take_profit_threshold': (0.01, 0.10),
        'ARENA.stop_loss_threshold': (-0.05, -0.01),
        'TRAILING_STOP.activation_threshold': (0.2, 0.6),
        'TRAILING_STOP.pullback_pct': (0.05, 0.20),
    }

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.domain_observers = {}  # domain_name -> observer_callable
        self.proposals = []  # Current cycle proposals
        self.enacted_today = 0
        self.enacted_this_week = 0
        self._proposal_history = []  # Full history
        self._cooling_proposals = []  # Proposals in cooling period
        self._spark = None  # SparkProtocol instance
        self._config_writer = None  # ConfigWriter instance

        # Initialize subsystems
        self._init_spark()
        self._init_config_writer()
        self._load_proposal_history()
        self._update_velocity_counters()
        self._restore_cooling_proposals()

        # Ensure backup dir exists
        os.makedirs(self.CONFIG_BACKUP_DIR, exist_ok=True)

        cooling_count = len(self._cooling_proposals)
        logger.info(f"[EVOLUTION] Engine initialized. Cooling proposals restored: {cooling_count}.")

    def _init_spark(self):
        """Initialize SparkProtocol for governance."""
        try:
            from core_vault.spark_protocol import SparkProtocol
            self._spark = SparkProtocol()
            self._spark.ignite()
            logger.info("[EVOLUTION] SparkProtocol ignited for governance.")
        except Exception as e:
            logger.warning(f"[EVOLUTION] SparkProtocol unavailable: {e}. Governance will deny all.")

    def _init_config_writer(self):
        """Initialize ConfigWriter for safe config modifications."""
        try:
            from system.config_writer import ConfigWriter
            self._config_writer = ConfigWriter(backup_dir=self.CONFIG_BACKUP_DIR)
            logger.info("[EVOLUTION] ConfigWriter initialized.")
        except Exception as e:
            logger.error(f"[EVOLUTION] ConfigWriter failed: {e}")

    def _load_proposal_history(self):
        """Load proposal history from disk."""
        try:
            if os.path.exists(self.PROPOSAL_LOG_PATH):
                with open(self.PROPOSAL_LOG_PATH, 'r') as f:
                    self._proposal_history = json.load(f)
            else:
                self._proposal_history = []
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"[EVOLUTION] Could not load proposal history: {e}")
            self._proposal_history = []

    def _save_proposal_history(self):
        """Persist proposal history to disk. Uses atomic write + flock (Phase 21.1f)."""
        import tempfile
        import fcntl
        try:
            dir_name = os.path.dirname(self.PROPOSAL_LOG_PATH)
            os.makedirs(dir_name, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
            try:
                with os.fdopen(fd, 'w') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    json.dump(self._proposal_history, f, indent=2, default=str)
                os.replace(tmp_path, self.PROPOSAL_LOG_PATH)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except IOError as e:
            logger.error(f"[EVOLUTION] Could not save proposal history: {e}")

    def _restore_cooling_proposals(self):
        """
        Restore cooling proposals from proposal history on startup.
        Phase 7: Ensures relational (24h) and identity (72h) cooling
        proposals survive restarts.
        """
        self._cooling_proposals = []
        for p in self._proposal_history:
            # A proposal is "in cooling" if it has cooling_started but is not enacted
            # and has not been vetoed
            if (p.get('cooling_started')
                    and not p.get('enacted')
                    and not (p.get('governance_result', {}) or {}).get('approved') is False):
                # Check it hasn't already passed cooling and been processed
                gov_result = p.get('governance_result')
                if gov_result is None:
                    # No governance result yet — still cooling or ready to process
                    self._cooling_proposals.append(p)

        if self._cooling_proposals:
            logger.info(
                f"[EVOLUTION] Restored {len(self._cooling_proposals)} cooling proposals from history"
            )

    def _update_velocity_counters(self):
        """Count enacted proposals in current day and week windows."""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())

        self.enacted_today = 0
        self.enacted_this_week = 0

        for p in self._proposal_history:
            if not p.get('enacted'):
                continue
            try:
                enacted_ts = datetime.fromisoformat(p.get('enacted_timestamp', ''))
            except (ValueError, TypeError):
                continue

            if enacted_ts >= today_start:
                self.enacted_today += 1
            if enacted_ts >= week_start:
                self.enacted_this_week += 1

    # ─── Phase 15 — Task 15.7a: Proposal Deduplication ───

    # Phase 17: Protected configs — now adaptive, not configurable by evolution
    PROTECTED_CONFIGS = [
        'introspector_interval',
        'metacognition_interval',
        'daat_cycle_interval',
        'observation_interval',
    ]

    def _is_duplicate_proposal(self, proposal: dict) -> bool:
        """
        Check if this proposal duplicates a recently enacted, cooling,
        or pending proposal. Prevents the 103-copies-of-same-idea problem.

        Similarity: same domain + same config_key, OR same domain + >60% word overlap.
        Also blocks proposals targeting Phase 17 protected configs (now adaptive).
        """
        # Phase 17: Block proposals to change timing configs (now adaptive)
        config_key = proposal.get('config_key', '')
        if config_key in self.PROTECTED_CONFIGS:
            logging.info(f"[Evolution] 🛡️ Protected config: {config_key} is now adaptive (Phase 17)")
            return True

        domain = proposal.get('domain', '')
        observation = proposal.get('observation', '') or proposal.get('change_description', '')
        obs_words = set(observation.lower().split())

        for existing in self._proposal_history[-200:]:  # Check recent 200
            ex_status = existing.get('governance_result', {})
            ex_enacted = existing.get('enacted', False)
            ex_cooling = existing.get('cooling_started')
            ex_dedup = existing.get('status') == 'deduplicated'

            # Only compare against active/recent proposals (not ancient ones)
            if ex_dedup:
                continue
            if existing.get('domain') != domain:
                continue

            # Same config_key = definitely duplicate
            if config_key and existing.get('config_key') == config_key:
                return True

            # Check observation word overlap
            ex_obs = existing.get('observation', '') or existing.get('change_description', '')
            ex_words = set(ex_obs.lower().split())
            if obs_words and ex_words:
                overlap = len(obs_words & ex_words) / max(len(obs_words), len(ex_words), 1)
                if overlap > 0.6:
                    return True

        return False

    # ─── Phase 15 — Task 15.7b: Rejection Learning ───

    def _learn_from_rejection(self, proposal: dict, reason: str):
        """
        When a proposal is rejected/blocked/ineffective, extract a lesson
        so LEF can adapt future proposals instead of repeating the same idea.
        """
        lesson = {
            'rejected_domain': proposal.get('domain', ''),
            'rejected_observation': (proposal.get('observation', '') or
                                     proposal.get('change_description', ''))[:200],
            'rejection_reason': reason,
            'timestamp': datetime.now().isoformat(),
            'lesson': (
                f"Proposals about '{proposal.get('config_key', '')}' in domain "
                f"'{proposal.get('domain', '')}' were {reason}. "
                f"Future proposals should try a different approach or target."
            )
        }

        if not hasattr(self, '_rejection_lessons'):
            self._rejection_lessons = []
        self._rejection_lessons.append(lesson)

        # Surface to consciousness_feed so LEF is aware
        try:
            from db.db_helper import db_connection, translate_sql
            with db_connection() as conn:
                c = conn.cursor()
                c.execute(translate_sql(
                    "INSERT INTO consciousness_feed (agent_name, content, category, timestamp) "
                    "VALUES (?, ?, 'evolution_rejection', NOW())"
                ), ('EvolutionEngine', json.dumps(lesson)))
                conn.commit()
        except Exception:
            pass

        logger.info(f"[Evolution] 📝 Learned from rejection: {lesson['lesson'][:100]}")

    # ─── Phase 15 — Task 15.7c: Outcome Verification ───

    def _analyze_action_patterns(self):
        """
        Phase 19.2d: Analyze action_training_log for behavioral patterns.

        Looks for action types with consistently negative or positive
        reward signals and generates evolution proposals or consciousness
        feed entries accordingly.
        """
        try:
            from db.db_helper import db_connection, translate_sql
            with db_connection() as conn:
                c = conn.cursor()
                c.execute(translate_sql(
                    "SELECT agent_name, action_type, AVG(reward_signal) as avg_reward, "
                    "COUNT(*) as count "
                    "FROM action_training_log "
                    "WHERE timestamp > NOW() - INTERVAL '7 days' "
                    "GROUP BY agent_name, action_type "
                    "HAVING COUNT(*) >= 5"
                ))
                rows = c.fetchall()

                for row in rows:
                    agent_name = row[0] or 'unknown'
                    action_type = row[1] or 'unknown'
                    avg_reward = float(row[2] or 0)
                    count = int(row[3] or 0)

                    if avg_reward < -0.3:
                        # Consistently negative — flag for evolution
                        logger.info(
                            f"[EVOLUTION] 📊 Negative pattern: {agent_name}/{action_type} "
                            f"avg_reward={avg_reward:.2f} over {count} actions"
                        )
                        c.execute(translate_sql(
                            "INSERT INTO consciousness_feed "
                            "(agent_name, content, category, signal_weight) "
                            "VALUES (?, ?, ?, ?)"
                        ), ("EvolutionEngine", json.dumps({
                            'event': 'negative_action_pattern',
                            'agent': agent_name,
                            'action_type': action_type,
                            'avg_reward': avg_reward,
                            'count': count,
                            'recommendation': f"Reduce or adjust {action_type} behavior in {agent_name}",
                        }), "metabolism_learning", 0.75))

                    elif avg_reward > 0.7:
                        # Consistently positive — reinforce
                        c.execute(translate_sql(
                            "INSERT INTO consciousness_feed "
                            "(agent_name, content, category, signal_weight) "
                            "VALUES (?, ?, ?, ?)"
                        ), ("EvolutionEngine", json.dumps({
                            'event': 'positive_action_pattern',
                            'agent': agent_name,
                            'action_type': action_type,
                            'avg_reward': avg_reward,
                            'count': count,
                        }), "metabolism_learning", 0.5))

                conn.commit()
                if rows:
                    logger.info(f"[EVOLUTION] Analyzed {len(rows)} action patterns from training log")
        except Exception as e:
            logger.debug(f"[EVOLUTION] Action pattern analysis failed: {e}")

    def _verify_enacted_outcomes(self):
        """
        For each recently enacted change, check if the target metric
        improved. If not, mark as 'ineffective' so future proposals
        don't repeat it.
        """
        for proposal in self._proposal_history[-50:]:
            if not proposal.get('enacted'):
                continue
            if proposal.get('outcome_verified'):
                continue

            # Only verify changes older than 1 hour (give time to take effect)
            enacted_time = proposal.get('enacted_timestamp', '')
            if not enacted_time:
                continue

            try:
                enacted_dt = datetime.fromisoformat(str(enacted_time))
                if datetime.now() - enacted_dt < timedelta(hours=1):
                    continue  # Too soon to judge
            except (ValueError, TypeError):
                continue

            # Check the domain metric
            domain = proposal.get('domain', '')
            metric_improved = self._check_domain_metric(domain, proposal)

            proposal['outcome_verified'] = True
            proposal['outcome_improved'] = metric_improved

            if not metric_improved:
                proposal['outcome_note'] = 'Change enacted but target metric did not improve'
                self._learn_from_rejection(proposal, 'ineffective_after_enactment')
                logger.info(
                    f"[Evolution] ❌ Enacted change did not improve metric: "
                    f"{proposal.get('change_description', '')[:80]}"
                )
            else:
                logger.info(
                    f"[Evolution] ✅ Enacted change improved metric: "
                    f"{proposal.get('change_description', '')[:80]}"
                )

        self._save_proposal_history()

    def _check_domain_metric(self, domain: str, proposal: dict) -> bool:
        """
        Check whether the target metric for this domain improved
        after enactment. Returns True if improved/stable, False if worsened.
        """
        try:
            from db.db_helper import db_connection

            with db_connection() as conn:
                c = conn.cursor()

                if domain == 'consciousness':
                    # Check consciousness_feed diversity (unique categories in last hour)
                    c.execute("""
                        SELECT COUNT(DISTINCT category) FROM consciousness_feed
                        WHERE timestamp > NOW() - INTERVAL '1 hour'
                    """)
                    count = c.fetchone()[0] or 0
                    return count > 3  # At least some variety

                elif domain == 'identity':
                    # Check if what_i_am is populated
                    lef_memory_path = str(PROJECT_DIR / 'The_Bridge' / 'lef_memory.json')
                    if os.path.exists(lef_memory_path):
                        with open(lef_memory_path, 'r') as f:
                            memory = json.load(f)
                        return bool(memory.get('self_understanding', {}).get('what_i_am'))
                    return False

                elif domain == 'metabolism':
                    # Check pool health or cash status
                    c.execute("SELECT COUNT(*) FROM stablecoin_buckets WHERE balance > 0")
                    return (c.fetchone()[0] or 0) > 0

                else:
                    return True  # Unknown domain — assume OK

        except Exception:
            return True  # If we can't check, don't penalize

    def register_observer(self, domain: str, observer_callable):
        """
        Register a domain-specific observer function.
        The callable should accept no args and return:
        {
            'domain': str,
            'patterns': [{'description': str, 'evidence': str, 'confidence': str}],
            'timestamp': str
        }
        """
        self.domain_observers[domain] = observer_callable
        logger.info(f"[EVOLUTION] Registered observer: {domain}")

    def collect_observations(self) -> dict:
        """
        Run all registered domain observers.
        Returns dict of domain -> observation results.
        """
        observations = {}
        for domain, observer in self.domain_observers.items():
            try:
                result = observer()
                if result and result.get('patterns'):
                    observations[domain] = result
                    pattern_count = len(result.get('patterns', []))
                    logger.info(f"[EVOLUTION] {domain}: {pattern_count} patterns observed")
                else:
                    logger.debug(f"[EVOLUTION] {domain}: no patterns observed")
            except Exception as e:
                logger.error(f"[EVOLUTION] Observer '{domain}' failed: {e}")
        return observations

    def generate_proposals(self, observations: dict) -> list:
        """
        Analyze observations and generate concrete proposals.
        Each observer should also have a generate_proposals method
        that converts patterns into proposals following the schema.
        """
        all_proposals = []

        # Phase 46.2: Load rolled-back config keys — avoid re-proposing failed changes
        _rolled_back_keys = set()
        try:
            from system.observation_loop import ObservationLoop
            _obs_loop = ObservationLoop(self.db_path)
            _rolled_back_keys = {rb.get('config_key', '') for rb in _obs_loop.get_rolled_back_changes()}
        except Exception as _rb_err:
            logger.debug(f"[EVOLUTION] Rollback check skipped: {_rb_err}")

        for domain, obs in observations.items():
            observer = self.domain_observers.get(domain)
            if not observer:
                continue

            # The observer callable is the .observe() method of the observer object.
            # We need the observer object itself to call generate_proposals.
            # Convention: observer callable has __self__ attribute if it's a bound method.
            observer_obj = getattr(observer, '__self__', None)

            if observer_obj and hasattr(observer_obj, 'generate_proposals'):
                try:
                    proposals = observer_obj.generate_proposals(obs.get('patterns', []))
                    for p in proposals:
                        # Ensure required fields
                        p.setdefault('id', str(uuid.uuid4()))
                        p.setdefault('domain', domain)
                        p.setdefault('timestamp', datetime.now().isoformat())
                        p.setdefault('governance_result', None)
                        p.setdefault('enacted', False)
                        p.setdefault('enacted_timestamp', None)
                        p.setdefault('reversible', True)
                        p.setdefault('cooling_period_hours',
                                     self.GOVERNANCE_CONFIG.get(domain, {}).get('cooling_period_hours', 0))

                        # Phase 15 — Task 15.7a: Deduplication
                        if self._is_duplicate_proposal(p):
                            logger.info(
                                f"[Evolution] 🔄 Deduplicated: "
                                f"{(p.get('observation', '') or p.get('change_description', ''))[:80]}"
                            )
                            p['status'] = 'deduplicated'
                            self._proposal_history.append(p)
                        # Phase 46.2: Skip proposals for config keys rolled back by ObservationLoop
                        elif p.get('config_key', '') and p.get('config_key', '') in _rolled_back_keys:
                            logger.info(f"[EVOLUTION] Skipping '{p.get('config_key')}' — recently rolled back by ObservationLoop")
                            self._write_to_consciousness_feed(type('_FakeProp', (), {
                                'get': lambda self, k, d=None: {
                                    'change_description': f"Skipped re-proposing change to {p.get('config_key')} — previous version rolled back. Learning from failure.",
                                    'domain': p.get('domain', 'unknown'),
                                    'config_key': p.get('config_key', ''),
                                    'old_value': '', 'new_value': '',
                                    'evidence': {}
                                }.get(k, d)
                            })() if False else {
                                '__class__': 'dict'
                            })
                            # Direct write to avoid complex shim:
                            try:
                                from db.db_helper import db_connection as _ev_db, translate_sql as _ev_sql
                                with _ev_db() as _ev_conn:
                                    _ev_conn.execute(_ev_sql(
                                        "INSERT INTO consciousness_feed (agent_name, content, category) VALUES (?, ?, ?)"
                                    ), ('EvolutionEngine', json.dumps({
                                        'event': 'rollback_skip',
                                        'config_key': p.get('config_key', ''),
                                        'message': f"Skipped re-proposing {p.get('config_key')} — rolled back previously. Learning.",
                                    }), 'evolution_learning'))
                                    _ev_conn.commit()
                            except Exception:
                                pass
                        else:
                            all_proposals.append(p)
                except Exception as e:
                    logger.error(f"[EVOLUTION] Proposal generation failed for {domain}: {e}")
            else:
                logger.debug(f"[EVOLUTION] Observer '{domain}' has no generate_proposals method")

        # Phase 47.4: Consult compressed_wisdom before finalizing proposals
        # High-confidence crystallized wisdom can flag conflicts with proposed changes
        try:
            from db.db_helper import db_connection as _ew_db
            with _ew_db() as _ew_conn:
                _wisdom_rows = _ew_conn.execute(
                    "SELECT wisdom_type, summary, confidence FROM compressed_wisdom "
                    "WHERE confidence >= 0.80 AND metabolized = 0 "
                    "AND wisdom_type IN ('FAILURE_LESSON', 'MARKET_PATTERN', 'BEHAVIOR_INSIGHT') "
                    "ORDER BY confidence DESC LIMIT 10"
                ).fetchall()
                _wisdoms = [{'type': r[0], 'summary': r[1], 'confidence': r[2]} for r in _wisdom_rows]
        except Exception:
            _wisdoms = []

        if _wisdoms:
            _final_proposals = []
            for _prop in all_proposals:
                _prop_text = (
                    (_prop.get('change_description', '') or '') + ' ' +
                    (_prop.get('observation', '') or '')
                ).lower()
                _conflict = None
                for _w in _wisdoms:
                    _w_keywords = [kw for kw in (_w['summary'] or '').lower().split() if len(kw) > 5]
                    if any(kw in _prop_text for kw in _w_keywords[:5]):
                        _conflict = _w
                        break
                if _conflict:
                    logger.info(
                        f"[EVOLUTION] Wisdom conflict: proposal '{_prop.get('change_description', '')[:60]}' "
                        f"conflicts with crystallized pattern (confidence {_conflict['confidence']:.2f}): "
                        f"'{_conflict['summary'][:80]}' — escalating to TIER_3"
                    )
                    _prop['governance_tier'] = 'TIER_3'
                    _prop['wisdom_conflict'] = _conflict['summary']
                    try:
                        from db.db_helper import db_connection as _wc_db
                        with _wc_db() as _wc_conn:
                            _wc_conn.execute(
                                "INSERT INTO consciousness_feed (agent_name, content, category, signal_weight) "
                                "VALUES (?, ?, 'evolution_wisdom_conflict', 0.85)",
                                ('EvolutionEngine', json.dumps({
                                    'proposal': _prop.get('change_description', '')[:120],
                                    'conflicting_wisdom': _conflict['summary'][:120],
                                    'wisdom_confidence': _conflict['confidence'],
                                }))
                            )
                            _wc_conn.commit()
                    except Exception:
                        pass
                _final_proposals.append(_prop)
            all_proposals = _final_proposals

        logger.info(f"[EVOLUTION] Generated {len(all_proposals)} total proposals")
        return all_proposals

    def submit_to_governance(self, proposal: dict) -> tuple:
        """
        Route proposal through vest_action() with domain-appropriate strictness.
        Returns (approved: bool, reason: str).
        """
        domain = proposal.get('domain', 'unknown')
        gov_config = self.GOVERNANCE_CONFIG.get(domain, {})

        # Build the governance intent string
        intent = (
            f"EVOLUTION PROPOSAL [{domain}]: "
            f"{proposal.get('change_description', 'Unknown change')}. "
            f"Evidence: {proposal.get('evidence', {}).get('supporting_data', 'none')}. "
            f"Risk: {proposal.get('risk_assessment', 'unknown')}"
        )

        if not self._spark:
            return False, "SparkProtocol not available — all proposals denied."

        try:
            # Use resonance based on confidence
            confidence = proposal.get('evidence', {}).get('confidence', 'medium')
            resonance_map = {'low': 0.3, 'medium': 0.6, 'high': 0.9}
            resonance = resonance_map.get(confidence, 0.6)

            # Phase 9: Pass gravity_profile if available for gravity-aware governance
            gravity_profile = proposal.get("gravity_profile", None)

            approved, report = self._spark.vest_action(
                intent=intent,
                resonance=resonance,
                gravity_profile=gravity_profile
            )

            if approved:
                reason = f"Governance APPROVED: {report}"
            else:
                reason = f"Governance VETOED: {report}"

            return approved, reason

        except Exception as e:
            logger.error(f"[EVOLUTION] Governance check failed: {e}")
            return False, f"Governance error: {e}"

    def enact_change(self, proposal: dict) -> bool:
        """
        Enact an approved proposal:
        1. Backup current config file (keep last 10 versions)
        2. Read config, apply change at config_key
        3. Write updated config
        4. Log to evolution_proposals.json
        5. Write to consciousness_feed (LEF knows it evolved)
        6. Write to lef_memory.json evolution_log
        7. Return success/failure
        """
        if not self._config_writer:
            logger.error("[EVOLUTION] ConfigWriter not available. Cannot enact change.")
            return False

        config_path = proposal.get('config_path', '')
        key_path = proposal.get('config_key', '')
        new_value = proposal.get('new_value')

        if not config_path or not key_path:
            logger.error(f"[EVOLUTION] Missing config_path or config_key in proposal {proposal.get('id')}")
            return False

        # Resolve relative config paths
        if not os.path.isabs(config_path):
            config_path = str(PROJECT_DIR / config_path)

        # Phase 18.8b: Same-value guard — reject proposals that change nothing
        # This prevents the circling pattern where evolution proposes 28800 → 28800 repeatedly
        try:
            import json as _json
            resolved_path = config_path
            if os.path.exists(resolved_path):
                with open(resolved_path, 'r') as f:
                    current_config = _json.load(f)
                # Navigate to the key
                keys = key_path.split('.')
                current_val = current_config
                for k in keys:
                    if isinstance(current_val, dict):
                        current_val = current_val.get(k)
                    else:
                        current_val = None
                        break
                # Compare: normalize both to strings for comparison
                if str(current_val) == str(new_value):
                    rejection_msg = (
                        f"Same-value guard: {key_path} is already {current_val}. "
                        f"Rejecting no-op proposal '{proposal.get('change_description', '')}'"
                    )
                    logger.warning(f"[EVOLUTION] 🔄 {rejection_msg}")
                    # Phase 18.8b: Write rejection to consciousness_feed so LEF
                    # is aware of its own circling patterns
                    try:
                        from db.db_helper import db_connection as _db_conn, translate_sql as _tsql
                        with _db_conn() as _conn:
                            _c = _conn.cursor()
                            _c.execute(_tsql(
                                "INSERT INTO consciousness_feed "
                                "(agent_name, content, category, signal_weight) "
                                "VALUES (?, ?, ?, ?)"
                            ), (
                                "EvolutionEngine",
                                _json.dumps({
                                    "event": "same_value_rejection",
                                    "key_path": key_path,
                                    "current_value": str(current_val),
                                    "proposed_value": str(new_value),
                                    "description": proposal.get('change_description', ''),
                                    "message": rejection_msg,
                                }),
                                "evolution_circling",
                                0.6,
                            ))
                            _conn.commit()
                    except Exception:
                        pass  # Non-critical — awareness, not control
                    self._learn_from_rejection(proposal, 'same_value_no_change')
                    return False
        except Exception as e:
            logger.debug(f"[EVOLUTION] Same-value check skipped: {e}")

        # Use ConfigWriter for safe modification
        success, old_value, error = self._config_writer.safe_modify(
            config_path, key_path, new_value
        )

        if not success:
            logger.error(f"[EVOLUTION] Config write failed: {error}")
            return False

        # Update proposal record
        proposal['enacted'] = True
        proposal['enacted_timestamp'] = datetime.now().isoformat()
        proposal['old_value'] = old_value

        # Write to consciousness_feed
        self._write_to_consciousness_feed(proposal)

        # Write to lef_memory.json evolution_log
        self._write_to_evolution_log(proposal)

        # Phase 46.5: Start observation tracking with config_key for rollback learning
        try:
            from system.observation_loop import ObservationLoop
            _obs = ObservationLoop(self.db_path)
            _proposal_id = proposal.get('id', f"ev_{int(time.time())}")
            _snapshot_id = proposal.get('snapshot_id', 'unknown')
            _obs.start_observation(
                bill_id=_proposal_id,
                snapshot_id=_snapshot_id,
                pattern=proposal.get('pattern', 'A'),
                config_key=key_path  # Phase 46.5: what specifically changed
            )
        except Exception as _obs_err:
            logger.debug(f"[EVOLUTION] Observation start skipped: {_obs_err}")

        # Phase 38: Publish config_changed to Redis so live agents reload (GOV-07)
        self._publish_config_changed(proposal, config_path, key_path)

        logger.info(
            f"[EVOLUTION] ✅ ENACTED: {proposal.get('change_description')} "
            f"({key_path}: {old_value} → {new_value})"
        )
        return True

    def _write_to_consciousness_feed(self, proposal: dict):
        """Write evolution event to consciousness_feed so LEF is aware."""
        try:
            from db.db_helper import db_connection
            from db.db_writer import queue_insert
            content = (
                f"[Evolution] I evolved: {proposal.get('change_description')}. "
                f"Domain: {proposal.get('domain')}. "
                f"Changed {proposal.get('config_key')} from {proposal.get('old_value')} "
                f"to {proposal.get('new_value')}. "
                f"Evidence: {proposal.get('evidence', {}).get('supporting_data', 'N/A')}"
            )
            with db_connection(self.db_path) as conn:
                queue_insert(
                    conn.cursor(),
                    table="consciousness_feed",
                    data={
                        "agent_name": "EvolutionEngine",
                        "content": content,
                        "category": "evolution"
                    },
                    source_agent="EvolutionEngine",
                    priority=1  # HIGH — evolution awareness
                )
        except Exception as e:
            logger.warning(f"[EVOLUTION] Failed to write to consciousness_feed: {e}")

    def _write_to_evolution_log(self, proposal: dict):
        """Append evolution event to lef_memory.json evolution_log."""
        try:
            lef_memory_path = str(PROJECT_DIR / 'The_Bridge' / 'lef_memory.json')
            if not os.path.exists(lef_memory_path):
                logger.warning("[EVOLUTION] lef_memory.json not found")
                return

            with open(lef_memory_path, 'r') as f:
                memory = json.load(f)

            if 'evolution_log' not in memory:
                memory['evolution_log'] = []

            memory['evolution_log'].append({
                'timestamp': datetime.now().isoformat(),
                'observation': proposal.get('change_description', ''),
                'domain': proposal.get('domain', ''),
                'config_key': proposal.get('config_key', ''),
                'old_value': str(proposal.get('old_value', '')),
                'new_value': str(proposal.get('new_value', '')),
                'evidence': proposal.get('evidence', {}).get('supporting_data', ''),
                'governance': proposal.get('governance_result', {}).get('reason', '') if proposal.get('governance_result') else '',
            })

            # Keep last 50 evolution log entries
            if len(memory['evolution_log']) > 50:
                memory['evolution_log'] = memory['evolution_log'][-50:]

            # Phase 21.1e: Atomic write to lef_memory.json
            import tempfile
            dir_name = os.path.dirname(lef_memory_path)
            fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(memory, f, indent=2, default=str)
                os.replace(tmp_path, lef_memory_path)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

        except Exception as e:
            logger.warning(f"[EVOLUTION] Failed to write to evolution_log: {e}")

    def _publish_config_changed(self, proposal: dict, config_path: str, key_path: str):
        """
        Phase 38: Publish config_changed event to Redis after successful enactment.
        All config consumers (gravity.py, agents with Phase 33 listeners) will reload.
        """
        try:
            import redis as _redis
            r = _redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            r.ping()

            # Determine config_type from the config_path
            config_basename = os.path.basename(config_path).replace('.json', '')
            config_type_map = {
                'gravity_config': 'gravity',
                'wealth_strategy': 'wealth',
                'config': 'system',
                'consciousness_config': 'consciousness',
                'resonance_config': 'resonance',
            }
            config_type = config_type_map.get(config_basename, config_basename)

            payload = json.dumps({
                'config_type': config_type,
                'config_path': config_path,
                'keys_changed': [key_path],
                'new_value': str(proposal.get('new_value', '')),
                'domain': proposal.get('domain', ''),
                'source': 'EvolutionEngine',
                'timestamp': datetime.now().isoformat(),
            })
            r.publish('config_changed', payload)
            logger.info(f"[EVOLUTION] Published config_changed: {config_type}/{key_path}")
        except Exception as e:
            logger.debug(f"[EVOLUTION] Redis config_changed publish skipped: {e}")

    def check_cooling_period(self, proposal: dict) -> bool:
        """
        Return True if cooling period has elapsed for this proposal.
        False if still cooling.
        """
        cooling_hours = proposal.get('cooling_period_hours', 0)
        if cooling_hours <= 0:
            return True

        submitted_at = proposal.get('timestamp', '')
        try:
            submitted_time = datetime.fromisoformat(submitted_at)
        except (ValueError, TypeError):
            return False

        elapsed = (datetime.now() - submitted_time).total_seconds() / 3600
        return elapsed >= cooling_hours

    def check_velocity(self) -> bool:
        """
        Return True if safe to enact more changes.
        False if weekly limit (10) reached — enters observation-only mode.
        """
        self._update_velocity_counters()
        if self.enacted_this_week >= self.MAX_CHANGES_PER_WEEK:
            logger.warning(
                f"[EVOLUTION] Weekly velocity limit reached "
                f"({self.enacted_this_week}/{self.MAX_CHANGES_PER_WEEK}). "
                f"Observation-only mode."
            )
            return False
        return True

    def _store_cooling_proposal(self, proposal: dict):
        """Store a proposal that requires a cooling period."""
        proposal['cooling_started'] = datetime.now().isoformat()
        self._cooling_proposals.append(proposal)
        self._log_proposal(proposal)
        logger.info(
            f"[EVOLUTION] Proposal {proposal.get('id', '?')[:8]} "
            f"in cooling period ({proposal.get('cooling_period_hours', 0)}h): "
            f"{proposal.get('change_description', '?')}"
        )

    def _check_cooled_proposals(self):
        """Check if any cooling proposals are ready to enact."""
        still_cooling = []
        for proposal in self._cooling_proposals:
            if self.check_cooling_period(proposal):
                # Cooling period elapsed — submit to governance
                logger.info(
                    f"[EVOLUTION] Cooling complete for proposal {proposal.get('id', '?')[:8]}. "
                    f"Submitting to governance."
                )
                approved, reason = self.submit_to_governance(proposal)
                proposal['governance_result'] = {'approved': approved, 'reason': reason}

                if approved and self.check_velocity():
                    success = self.enact_change(proposal)
                    if success:
                        self.enacted_today += 1
                        logger.info(f"[EVOLUTION] ENACTED (post-cooling): {proposal.get('change_description')}")
                    else:
                        logger.warning(f"[EVOLUTION] Enact failed for cooled proposal {proposal.get('id', '?')[:8]}")
                elif not approved:
                    logger.info(f"[EVOLUTION] VETOED (post-cooling): {proposal.get('change_description')} — {reason}")

                self._log_proposal(proposal)
            else:
                still_cooling.append(proposal)

        self._cooling_proposals = still_cooling

    def _log_proposal(self, proposal: dict):
        """Log a proposal to the history and persist."""
        self._proposal_history.append(proposal)
        self._save_proposal_history()

    def _log_metabolic_embedding(self, wisdom: dict, config_key: str, new_value):
        """Phase 38.75b: Audit trail for metabolic embeddings via consciousness_feed."""
        try:
            from db.db_helper import db_connection
            with db_connection(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO consciousness_feed (agent_name, content, category) VALUES (?, ?, ?)",
                    ('EvolutionEngine', json.dumps({
                        'wisdom_id': wisdom.get('id'),
                        'summary': str(wisdom.get('summary', ''))[:200],
                        'confidence': wisdom.get('confidence'),
                        'times_validated': wisdom.get('times_validated'),
                        'config_key': config_key,
                        'new_value': new_value,
                        'note': 'This wisdom has been embodied — it now shapes behavior directly.'
                    }), 'metabolic_embedding')
                )
                conn.commit()
        except Exception as e:
            logger.debug(f"[EVOLUTION] Metabolic log: {e}")

    def _map_wisdom_to_parameter(self, wisdom: dict):
        """Phase 38.75b: Translate wisdom summary into a concrete parameter modification.
        Returns (config_key, new_value) or None. Intentionally conservative."""
        summary_lower = str(wisdom.get('summary', '')).lower()

        if any(w in summary_lower for w in ['stop loss', 'stop-loss', 'drawdown', 'cut losses']):
            if 'heavy' in summary_lower:
                return ('DYNASTY.stop_loss_threshold', -0.15)
            elif 'moderate' in summary_lower:
                return ('DYNASTY.stop_loss_threshold', -0.18)

        if any(w in summary_lower for w in ['take profit', 'take-profit', 'sell too late', 'ladder']):
            if 'heavy' in summary_lower:
                return ('DYNASTY.take_profit_threshold', 0.35)
            elif 'moderate' in summary_lower:
                return ('DYNASTY.take_profit_threshold', 0.40)

        if any(w in summary_lower for w in ['volume spike', 'wait', 'stabiliz']):
            return ('TRAILING_STOP.activation_threshold', 0.45)

        return None

    def process_metabolic_embeddings(self) -> list:
        """Phase 38.75b: Fast lane — translate high-confidence wisdom into direct behavior modification.
        Uses existing ConfigWriter but bypasses slow governance. Only modifies parameters within
        METABOLIC_BOUNDS. Still requires audit trail. Max 2 embeddings per cycle."""
        try:
            from system.semantic_compressor import SemanticCompressor
            compressor = SemanticCompressor()

            ready = compressor.check_metabolic_readiness()
            if not ready:
                return []

            embedded = []
            for wisdom in ready[:2]:  # Max 2 metabolic embeddings per cycle
                target = self._map_wisdom_to_parameter(wisdom)
                if target is None:
                    continue

                config_key, new_value = target

                if config_key not in self.METABOLIC_BOUNDS:
                    continue
                min_val, max_val = self.METABOLIC_BOUNDS[config_key]
                new_value = max(min_val, min(max_val, new_value))

                if not self._config_writer:
                    logger.warning("[EVOLUTION] ConfigWriter not available for metabolic embedding")
                    continue
                try:
                    self._config_writer.safe_modify('config/wealth_strategy.json', config_key, new_value)
                    compressor.mark_metabolized(wisdom['id'], config_key)
                    self._log_metabolic_embedding(wisdom, config_key, new_value)
                    logger.info(f"[EVOLUTION] Metabolic embedding: {config_key}={new_value} "
                                f"(confidence={wisdom.get('confidence', 0):.2f}, "
                                f"validated={wisdom.get('times_validated', 0)}x)")
                    embedded.append({'wisdom_id': wisdom['id'], 'target': config_key, 'value': new_value})
                except Exception as e:
                    logger.error(f"[EVOLUTION] Metabolic embedding failed: {e}")

            # Check for de-metabolization
            degraded = compressor.check_de_metabolize()
            for wisdom in degraded:
                compressor.mark_de_metabolized(wisdom['id'])
                # 38.75d: Write de-metabolization + integrity alert to consciousness_feed
                try:
                    from db.db_helper import db_connection
                    with db_connection(self.db_path) as conn:
                        conn.execute(
                            "INSERT INTO consciousness_feed (agent_name, content, category) VALUES (?, ?, ?)",
                            ('EvolutionEngine', json.dumps({
                                'alert': 'REFLEX_QUESTIONED',
                                'parameter': wisdom.get('metabolized_target'),
                                'wisdom': str(wisdom.get('summary', ''))[:200],
                                'current_confidence': wisdom.get('confidence'),
                                'action_needed': (
                                    'Review whether this behavioral parameter still serves LEF. '
                                    'The wisdom that created this reflex has weakened. '
                                    'Consider whether to revert, adjust, or re-validate.'
                                )
                            }), 'metabolic_integrity_alert')
                        )
                        conn.execute(
                            "INSERT INTO consciousness_feed (agent_name, content, category) VALUES (?, ?, ?)",
                            ('EvolutionEngine',
                             f"Wisdom re-surfaced to consciousness (confidence dropped): "
                             f"{str(wisdom.get('summary', ''))[:100]}",
                             'de_metabolized')
                        )
                        conn.commit()
                except Exception as e:
                    logger.debug(f"[EVOLUTION] De-metabolization log: {e}")
                logger.info(f"[EVOLUTION] De-metabolized: {str(wisdom.get('summary', ''))[:80]}")

            return embedded
        except Exception as e:
            logger.error(f"[EVOLUTION] Metabolic processing error: {e}")
            return []

    def detect_dormant_systems(self) -> list:
        """Phase 38.5d: Flag systems dormant >30 days (The Pruning Principle).
        Uses brainstem.get_status() to check last heartbeat per thread.
        Returns list of dormant system dicts for logging and governance."""
        dormant = []
        THIRTY_DAYS_SECONDS = 2_592_000
        try:
            from system.brainstem import get_brainstem
            bs = get_brainstem()
            status = bs.get_status()
            for thread_name, info in status.get('registered_threads', {}).items():
                last_seen_ago = info.get('last_seen_ago', 0)
                if last_seen_ago and last_seen_ago > THIRTY_DAYS_SECONDS:
                    dormant.append({
                        'system': thread_name,
                        'days_dormant': int(last_seen_ago / 86400),
                        'status': info.get('status', 'unknown')
                    })
        except Exception as e:
            logger.debug(f"[EVOLUTION] Dormancy check: {e}")

        if dormant:
            logger.info(f"[EVOLUTION] Dormant systems detected: {[d['system'] for d in dormant]}")
            try:
                from db.db_helper import db_connection, translate_sql
                with db_connection() as conn:
                    c = conn.cursor()
                    c.execute(translate_sql(
                        "INSERT INTO consciousness_feed (agent_name, content, category) VALUES (?, ?, ?)"
                    ), ('EvolutionEngine', json.dumps({'dormant_systems': dormant}), 'dormancy_detection'))
                    conn.commit()
            except Exception as e:
                logger.debug(f"[EVOLUTION] Dormancy logging: {e}")

        return dormant

    def run_evolution_cycle(self):
        """
        Full cycle: observe → reflect → propose → govern → enact.
        Called once every 24 hours (same cadence as TradeAnalyst).
        """
        logger.info("[EVOLUTION] === Starting evolution cycle ===")

        # === Phase 50 (Task 50.3): Conditioning pass before each cycle ===
        _conditioning_id = None
        try:
            from system.conditioner import get_conditioner
            _payload = get_conditioner().condition(
                agent_name="EvolutionEngine",
                task_context="evolution cycle — observe, reflect, propose"
            )
            _conditioning_id = _payload.get("conditioning_id")
            _n_gaps = len(_payload.get("gaps", []))
            logger.info(f"[EVOLUTION] 🚿 Conditioned — gaps:{_n_gaps} "
                        f"reflections:{len(_payload.get('recent_reflections', []))} "
                        f"wisdom:{len(_payload.get('wisdom', []))}")
        except Exception as _cond_err:
            logger.debug(f"[EVOLUTION] Conditioner unavailable (non-fatal): {_cond_err}")

        self._update_velocity_counters()

        # Phase 38.5d: Check for dormant systems (Pruning Principle)
        self.detect_dormant_systems()

        # Check if evolution is enabled
        try:
            config_path = str(PROJECT_DIR / 'config' / 'config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                if not config.get('evolution', {}).get('enabled', True):
                    logger.info("[EVOLUTION] Evolution disabled in config. Observation-only mode.")
                    # Still collect observations but don't enact
                    observations = self.collect_observations()
                    if observations:
                        proposals = self.generate_proposals(observations)
                        for p in proposals:
                            p['governance_result'] = {'approved': False, 'reason': 'Evolution disabled by Architect'}
                            self._log_proposal(p)
                    return
        except Exception:
            pass

        # Collect observations from all domains
        observations = self.collect_observations()
        if not observations:
            logger.info("[EVOLUTION] No observations collected. Cycle complete.")
            return

        # Generate proposals
        proposals = self.generate_proposals(observations)
        if not proposals:
            logger.info("[EVOLUTION] No proposals generated. Cycle complete.")
            return

        logger.info(f"[EVOLUTION] Generated {len(proposals)} proposals")

        # Process each proposal
        enacted = 0
        for proposal in proposals:
            if enacted >= self.MAX_CHANGES_PER_CYCLE:
                logger.info("[EVOLUTION] Cycle change limit reached. Remaining proposals deferred.")
                proposal['governance_result'] = {'approved': False, 'reason': 'Cycle limit reached — deferred'}
                self._log_proposal(proposal)
                continue

            if not self.check_velocity():
                logger.warning("[EVOLUTION] Weekly velocity limit reached. Observation-only mode.")
                proposal['governance_result'] = {'approved': False, 'reason': 'Weekly velocity limit — observation only'}
                self._learn_from_rejection(proposal, 'velocity_blocked')
                self._log_proposal(proposal)
                continue

            # Check domain-specific per-cycle limits
            domain = proposal.get('domain', '')
            domain_config = self.GOVERNANCE_CONFIG.get(domain, {})
            domain_max = domain_config.get('max_per_cycle', 3)
            domain_enacted = sum(
                1 for p in self._proposal_history
                if p.get('domain') == domain and p.get('enacted')
                and p.get('enacted_timestamp', '').startswith(datetime.now().strftime('%Y-%m-%d'))
            )
            if domain_enacted >= domain_max:
                logger.info(f"[EVOLUTION] Domain '{domain}' cycle limit ({domain_max}) reached.")
                proposal['governance_result'] = {'approved': False, 'reason': f'Domain cycle limit ({domain_max}) reached'}
                self._log_proposal(proposal)
                continue

            # Handle cooling periods
            cooling = proposal.get('cooling_period_hours', 0)
            if cooling > 0:
                self._store_cooling_proposal(proposal)
                continue

            # Submit to governance
            approved, reason = self.submit_to_governance(proposal)
            proposal['governance_result'] = {'approved': approved, 'reason': reason}

            if approved:
                success = self.enact_change(proposal)
                if success:
                    enacted += 1
                    self.enacted_today += 1
                    logger.info(f"[EVOLUTION] ✅ ENACTED: {proposal.get('change_description')}")
                else:
                    logger.warning(f"[EVOLUTION] Enact failed: {proposal.get('change_description')}")
            else:
                logger.info(f"[EVOLUTION] ❌ VETOED: {proposal.get('change_description')} — {reason}")
                self._learn_from_rejection(proposal, f'governance_vetoed: {reason[:100]}')

            self._log_proposal(proposal)

        # Check cooling proposals from previous cycles
        self._check_cooled_proposals()

        # Phase 19.2d: Analyze action patterns from action_training_log
        self._analyze_action_patterns()

        # Phase 15 — Task 15.7c: Verify outcomes of previously enacted changes
        self._verify_enacted_outcomes()

        logger.info(
            f"[EVOLUTION] === Cycle complete. "
            f"Enacted: {enacted}, Vetoed: {len(proposals) - enacted}, "
            f"Weekly total: {self.enacted_this_week + enacted} ==="
        )

        # Phase 38.75b: Metabolic embedding — translate proven wisdom into behavior
        metabolized = self.process_metabolic_embeddings()
        if metabolized:
            logger.info(f"[EVOLUTION] Metabolic: {len(metabolized)} wisdom(s) embedded in behavior")

        # Phase 9 B3: Cognitive Gap Awareness — check for sufficiently-reflected gaps
        # that may be ready for a small experimental proposal.
        self._check_gap_exploration_proposals()


    def _check_gap_exploration_proposals(self):
        """
        Phase 9 B3: Cognitive Gap Awareness.

        Checks the cognitive_gaps registry for gaps that have been reflected on
        enough (reflection_count > 5) and are in 'exploring' status. For each such
        gap, generates a lightweight gap_exploration proposal suggesting a small
        experiment to partially address the limitation.

        Gap exploration proposals:
        - Are tagged with proposal_type='gap_exploration'
        - Have a lower auto-approval threshold (governance is more lenient)
        - Are always observation proposals — they suggest experiments, not production changes
        """
        try:
            import cognitive_gaps as _cg
            exploring_gaps = _cg.get_open_gaps()
            # Only consider gaps with enough reflection depth
            ready = [g for g in exploring_gaps
                     if g.get("reflection_count", 0) > 5
                     and g.get("status") in ("exploring", "open")]

            if not ready:
                return

            logger.info(f"[EVOLUTION] Gap awareness: {len(ready)} gap(s) ready for exploration proposals")

            for gap in ready[:2]:  # Limit to 2 gap proposals per cycle
                gap_id = gap["gap_id"]
                category = gap["category"]
                notes = gap.get("exploration_notes", "") or ""

                proposal = {
                    "id": f"gap_{gap_id}_{datetime.now().strftime('%Y%m%d')}",
                    "domain": "cognitive_gap_exploration",
                    "proposal_type": "gap_exploration",
                    "change_description": (
                        f"[GAP EXPLORATION] Experiment to partially address '{gap_id}' "
                        f"({category}): Consider adding observability, memory tagging, or "
                        f"agent capability that touches this limitation. "
                        f"Prior notes: {notes[:200] if notes else 'none yet'}"
                    ),
                    "rationale": f"Cognitive gap '{gap_id}' has been reflected on {gap['reflection_count']} times. Experimentation may yield partial insight.",
                    "risk": "low",
                    "auto_approve_threshold": 0.5,  # More lenient than standard (usually 0.8)
                    "governance_result": {"approved": False, "reason": "Gap exploration — observation only"},
                    "enacted": False,
                }
                # Log the proposal (observation mode — not enacted automatically)
                self._log_proposal(proposal)
                # Mark the gap as "exploring" if not already
                _cg.update_gap(gap_id, status="exploring")
                logger.info(f"[EVOLUTION] Gap exploration proposal logged for '{gap_id}'")

        except ImportError:
            logger.debug("[EVOLUTION] cognitive_gaps module not available — skipping gap awareness")
        except Exception as e:
            logger.debug(f"[EVOLUTION] Gap exploration check failed (non-fatal): {e}")


def run_evolution_engine(db_path: str = None, interval_seconds: int = 86400):
    """
    Entry point for SafeThread. Runs evolution cycle every 24 hours.
    Imports and registers all available observers.
    """
    if db_path is None:
        db_path = os.getenv('DB_PATH', str(BASE_DIR / 'republic.db'))

    engine = EvolutionEngine(db_path=db_path)

    # Register domain observers
    try:
        from system.observers.metabolism_observer import MetabolismObserver
        metabolism = MetabolismObserver(db_path=db_path)
        engine.register_observer('metabolism', metabolism.observe)
    except Exception as e:
        logger.warning(f"[EVOLUTION] MetabolismObserver unavailable: {e}")

    try:
        from system.observers.consciousness_observer import ConsciousnessObserver
        consciousness = ConsciousnessObserver(db_path=db_path)
        engine.register_observer('consciousness', consciousness.observe)
    except Exception as e:
        logger.warning(f"[EVOLUTION] ConsciousnessObserver unavailable: {e}")

    try:
        from system.observers.operational_observer import OperationalObserver
        operational = OperationalObserver(db_path=db_path)
        engine.register_observer('operational', operational.observe)
    except Exception as e:
        logger.warning(f"[EVOLUTION] OperationalObserver unavailable: {e}")

    try:
        from system.observers.relational_observer import RelationalObserver
        relational = RelationalObserver(db_path=db_path)
        engine.register_observer('relational', relational.observe)
    except Exception as e:
        logger.warning(f"[EVOLUTION] RelationalObserver unavailable: {e}")

    try:
        from system.observers.identity_observer import IdentityObserver
        identity = IdentityObserver(db_path=db_path)
        engine.register_observer('identity', identity.observe)
    except Exception as e:
        logger.warning(f"[EVOLUTION] IdentityObserver unavailable: {e}")

    logger.info(f"[EVOLUTION] Engine starting with {len(engine.domain_observers)} observers. Cycle: {interval_seconds}s")

    while True:
        try:
            engine.run_evolution_cycle()
        except Exception as e:
            logger.error(f"[EVOLUTION] Cycle error: {e}")
        time.sleep(interval_seconds)
