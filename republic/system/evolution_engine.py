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
        """Persist proposal history to disk."""
        try:
            os.makedirs(os.path.dirname(self.PROPOSAL_LOG_PATH), exist_ok=True)
            with open(self.PROPOSAL_LOG_PATH, 'w') as f:
                json.dump(self._proposal_history, f, indent=2, default=str)
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
                        all_proposals.append(p)
                except Exception as e:
                    logger.error(f"[EVOLUTION] Proposal generation failed for {domain}: {e}")
            else:
                logger.debug(f"[EVOLUTION] Observer '{domain}' has no generate_proposals method")

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

            approved, report = self._spark.vest_action(
                intent=intent,
                resonance=resonance
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

            with open(lef_memory_path, 'w') as f:
                json.dump(memory, f, indent=2, default=str)

        except Exception as e:
            logger.warning(f"[EVOLUTION] Failed to write to evolution_log: {e}")

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

    def run_evolution_cycle(self):
        """
        Full cycle: observe → reflect → propose → govern → enact.
        Called once every 24 hours (same cadence as TradeAnalyst).
        """
        logger.info("[EVOLUTION] === Starting evolution cycle ===")
        self._update_velocity_counters()

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

            self._log_proposal(proposal)

        # Check cooling proposals from previous cycles
        self._check_cooled_proposals()

        logger.info(
            f"[EVOLUTION] === Cycle complete. "
            f"Enacted: {enacted}, Vetoed: {len(proposals) - enacted}, "
            f"Weekly total: {self.enacted_this_week + enacted} ==="
        )


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
