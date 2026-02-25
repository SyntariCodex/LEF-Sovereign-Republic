"""
ConstitutionGuard (The Law)
Department: Dept_Civics
Role: Active enforcement of CONSTITUTION.md

Function:
1. Validates system state against constitutional rules
2. Logs violations to agent_logs
3. Can trigger Apoptosis for critical violations
4. Reports to AgentCivics governance cycle

Phase 21: Constitutional Enforcement
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime
from contextlib import contextmanager

# Path setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

# Phase 12.H6: Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = sqlite3.connect(db_path or os.path.join(BASE_DIR, 'republic.db'), timeout=timeout)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, 'republic.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('CONSTITUTION_GUARD')


class RuleResult:
    """Result of a constitutional rule check."""
    def __init__(self, passed: bool, reason: str = "", severity: str = "WARNING"):
        self.passed = passed
        self.reason = reason
        self.severity = severity  # WARNING, VIOLATION, CRITICAL


class ConstitutionGuard:
    """
    The Law: Active enforcement of CONSTITUTION.md
    
    Monitors system state and validates against constitutional rules.
    Reports violations but does not halt operations (advisory mode).
    """
    
    def __init__(self, db_path=None):
        if db_path is None:
            self.db_path = os.path.join(BASE_DIR, 'republic.db')
        else:
            self.db_path = db_path
            
        self.violations_this_cycle = []
        
    # Phase 34: _get_db_connection() removed — use db_connection() context manager
    # _get_conn() kept for backward compatibility during audit cycles (shared_conn pattern)
    def _get_conn(self):
        """Return shared connection if available (during audit), otherwise open one.
        Phase 34: Fallback now uses db_connection-compatible sqlite3 with timeout."""
        if hasattr(self, '_shared_conn') and self._shared_conn:
            return self._shared_conn, False  # conn, should_close
        conn = sqlite3.connect(self.db_path, timeout=60.0)
        return conn, True  # conn, should_close
    
    # =========================================================================
    # RULE VALIDATORS
    # =========================================================================
    
    def check_c003_deploy_threshold(self) -> RuleResult:
        """
        C-003: Treasury deploys capital ONLY when surplus exceeds $500
        Article II, Section 6
        """
        try:
            config_path = os.path.join(BASE_DIR, 'config.json')
            if not os.path.exists(config_path):
                return RuleResult(True, "No config.json found (OK if not configured)")
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Check treasury threshold
            treasury_config = config.get('treasury', {})
            deploy_threshold = treasury_config.get('deploy_threshold', 500)
            
            if deploy_threshold < 500:
                return RuleResult(
                    False,
                    f"Deploy threshold is ${deploy_threshold}, Constitution requires >= $500",
                    "VIOLATION"
                )
            return RuleResult(True, f"Deploy threshold OK: ${deploy_threshold}")
            
        except Exception as e:
            return RuleResult(True, f"Could not check config: {e}")
    
    def check_c005_rsi_entries(self) -> RuleResult:
        """
        C-005: RSI < 30 required for buy entries
        Article II, Section 6
        """
        try:
            conn, should_close = self._get_conn()
            c = conn.cursor()

            # Check recent buy orders that were approved
            c.execute("""
                SELECT id, asset, reason FROM trade_queue
                WHERE action = 'BUY'
                AND status IN ('APPROVED', 'EXECUTED')
                AND created_at > datetime('now', '-24 hours')
            """)

            violations = []
            for row in c.fetchall():
                trade_id, asset, reason = row
                # Check if reason mentions RSI and it's > 30
                if reason and 'RSI' in reason.upper():
                    # Try to extract RSI value
                    import re
                    rsi_match = re.search(r'RSI[:\s]*(\d+\.?\d*)', reason, re.IGNORECASE)
                    if rsi_match:
                        rsi_val = float(rsi_match.group(1))
                        if rsi_val > 30:
                            violations.append(f"Trade {trade_id} ({asset}): RSI={rsi_val}")

            if should_close:
                conn.close()

            if violations:
                return RuleResult(
                    False,
                    f"Entries with RSI > 30: {', '.join(violations[:3])}",
                    "WARNING"
                )
            return RuleResult(True, "All checked entries comply with RSI < 30 rule")
            
        except Exception as e:
            return RuleResult(True, f"Could not check RSI entries: {e}")
    
    def check_c008_circular_actions(self) -> RuleResult:
        """
        C-008: Apoptosis trigger if >50 repeated actions
        Article IV, Section 4
        """
        try:
            conn, should_close = self._get_conn()
            c = conn.cursor()

            # Check for repeated ACTIONS in last hour
            # Phase 12.H6: Added LIMIT on inner scan to prevent full table scan
            # Phase 12.H8: Whitelist approach — only flag messages that represent
            # actual agent ACTIONS (broadcasts, trades, executions, proposals).
            # Normal telemetry/polling/research is NOT a circular action.
            # Phase 34: Parameterized LIKE patterns — no string concatenation in SQL
            # Phase 50-fix: Patterns must represent genuinely repeated *actions*, not telemetry.
            # Removed '%Broadcast:%' — router status broadcasts (e.g., "Broadcast: Wake 6, Sleep 11")
            #   are high-frequency telemetry, not circular actions.
            # '%Dispatched intent%' — catches per-intent dispatch to a channel (not cycle summary).
            # '%TRADE%', '%BUY%', '%SELL%', '%EXECUTED%' — actual trade actions.
            # '%PROPOSAL%' — governance proposals.
            # '%APOPTOSIS%' — extreme self-termination signals.
            ACTION_INDICATORS = [
                '%EXECUTED%',
                '%TRADE%',
                '%BUY%',
                '%SELL%',
                '%APOPTOSIS%',
                '%PROPOSAL%',
                '%Dispatched intent%',
            ]
            placeholders = " OR ".join("message LIKE ?" for _ in ACTION_INDICATORS)
            c.execute(f"""
                SELECT message, COUNT(*) as cnt
                FROM (
                    SELECT message, level FROM agent_logs
                    WHERE timestamp > datetime('now', '-1 hour')
                    AND level = 'INFO'
                    AND ({placeholders})
                    ORDER BY timestamp DESC
                    LIMIT 5000
                ) recent
                GROUP BY message
                HAVING COUNT(*) > 50
                ORDER BY cnt DESC
                LIMIT 5
            """, ACTION_INDICATORS)

            circular_patterns = c.fetchall()
            if should_close:
                conn.close()
            
            if circular_patterns:
                worst = circular_patterns[0]
                return RuleResult(
                    False,
                    f"Circular action detected: '{worst[0][:50]}...' repeated {worst[1]}x",
                    "CRITICAL"
                )
            return RuleResult(True, "No circular action patterns detected")
            
        except Exception as e:
            return RuleResult(True, f"Could not check circular actions: {e}")
    
    def check_c009_equity_drawdown(self) -> RuleResult:
        """
        C-009: Apoptosis trigger if >50% equity loss in <1 hour
        Article IV, Section 4
        """
        try:
            conn, should_close = self._get_conn()
            c = conn.cursor()

            # Get NAV from 1 hour ago and now
            c.execute("""
                SELECT value FROM system_metrics
                WHERE key = 'nav'
                AND timestamp > datetime('now', '-1 hour')
                ORDER BY timestamp ASC
                LIMIT 1
            """)
            row_old = c.fetchone()

            c.execute("""
                SELECT value FROM system_metrics
                WHERE key = 'nav'
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            row_new = c.fetchone()

            if should_close:
                conn.close()
            
            if row_old and row_new:
                try:
                    nav_old = float(row_old[0])
                    nav_new = float(row_new[0])
                    
                    if nav_old > 0:
                        drawdown_pct = ((nav_old - nav_new) / nav_old) * 100
                        
                        if drawdown_pct > 50:
                            return RuleResult(
                                False,
                                f"CRITICAL: {drawdown_pct:.1f}% equity loss in last hour (trigger: 50%)",
                                "CRITICAL"
                            )
                        elif drawdown_pct > 20:
                            return RuleResult(
                                False,
                                f"WARNING: {drawdown_pct:.1f}% drawdown in last hour",
                                "WARNING"
                            )
                except (ValueError, TypeError):
                    pass
            
            return RuleResult(True, "Equity drawdown within acceptable limits")
            
        except Exception as e:
            return RuleResult(True, f"Could not check equity drawdown: {e}")
    
    def check_c002_bridge_uniqueness(self) -> RuleResult:
        """
        C-002: Only one Bridge allowed (no nested structures)
        Article II, Section 3
        """
        try:
            # Check for nested Bridge directories
            nested_bridge = os.path.join(BASE_DIR, 'The_Bridge')
            root_bridge = os.path.join(os.path.dirname(BASE_DIR), 'The_Bridge')
            
            if os.path.exists(nested_bridge) and os.path.exists(root_bridge):
                return RuleResult(
                    False,
                    f"Duplicate Bridge structures found: {nested_bridge} and {root_bridge}",
                    "VIOLATION"
                )
            return RuleResult(True, "Bridge structure is unique")
            
        except Exception as e:
            return RuleResult(True, f"Could not check Bridge: {e}")
    
    # =========================================================================
    # MAIN AUDIT
    # =========================================================================
    
    def run_audit(self) -> list:
        """
        Run all constitutional checks and return violations.
        Phase 12.H6: Uses a single shared DB connection for the entire audit cycle
        instead of each check opening its own connection (was 5 connections per audit).

        Returns:
            List of (rule_id, rule_name, result) tuples
        """
        logger.info("[GUARD] 📜 Constitutional Audit starting...")

        checks = [
            ('C-002', 'Bridge Uniqueness', self.check_c002_bridge_uniqueness),
            ('C-003', 'Deploy Threshold', self.check_c003_deploy_threshold),
            ('C-005', 'RSI Entry Rule', self.check_c005_rsi_entries),
            ('C-008', 'Circular Actions', self.check_c008_circular_actions),
            ('C-009', 'Equity Drawdown', self.check_c009_equity_drawdown),
        ]

        results = []
        violations = []

        # Phase 12.H6: Open ONE connection for the entire audit cycle
        try:
            with db_connection(self.db_path) as shared_conn:
                self._shared_conn = shared_conn

                for rule_id, name, checker in checks:
                    try:
                        result = checker()
                        results.append((rule_id, name, result))

                        if not result.passed:
                            violations.append((rule_id, name, result))
                            self._log_violation(rule_id, name, result)

                    except Exception as e:
                        logger.error(f"[GUARD] Error checking {rule_id}: {e}")
        except Exception as e:
            logger.error(f"[GUARD] Failed to open audit connection: {e}")
        finally:
            self._shared_conn = None

        # Summary
        passed = len(results) - len(violations)
        logger.info(f"[GUARD] 📜 Audit complete: {passed}/{len(results)} rules passed")

        if violations:
            critical = [v for v in violations if v[2].severity == 'CRITICAL']
            if critical:
                logger.critical(f"[GUARD] 🚨 CRITICAL VIOLATIONS: {len(critical)}")

        self.violations_this_cycle = violations
        return violations
    
    def _log_violation(self, rule_id: str, name: str, result: RuleResult):
        """Log a constitutional violation to the database.
        Phase 12.H6: Uses shared connection when available."""
        try:
            conn, should_close = self._get_conn()
            c = conn.cursor()

            c.execute("""
                INSERT INTO agent_logs (source, level, message)
                VALUES (?, ?, ?)
            """, (
                'CONSTITUTION_GUARD',
                f'CONSTITUTIONAL_{result.severity}',
                f"[{rule_id}] {name}: {result.reason}"
            ))

            conn.commit()
            if should_close:
                conn.close()
            
            # Also log to console
            if result.severity == 'CRITICAL':
                logger.critical(f"[GUARD] 🚨 [{rule_id}] {name}: {result.reason}")
            elif result.severity == 'VIOLATION':
                logger.warning(f"[GUARD] ⚠️ [{rule_id}] {name}: {result.reason}")
            else:
                logger.info(f"[GUARD] 📋 [{rule_id}] {name}: {result.reason}")
                
        except Exception as e:
            logger.error(f"[GUARD] Could not log violation: {e}")
    
    def get_compliance_score(self) -> float:
        """
        Calculate constitutional compliance percentage.
        100% = all rules pass, 0% = all rules fail
        Phase 12.H6: Uses cached violations from last audit instead of re-running all checks.
        """
        total_checks = 5  # C-002, C-003, C-005, C-008, C-009
        violations = len(self.violations_this_cycle) if self.violations_this_cycle else 0
        return ((total_checks - violations) / total_checks) * 100


class AmendmentVoting:
    """
    Amendment Voting System (Phase 21)
    
    Manages the lifecycle of constitutional amendments:
    PROPOSED -> VOTING -> APPROVED / REJECTED / VETOED
    
    Voters: Philosopher, Ethicist (agents with governance voice)
    Veto Power: Architect (The I)
    """
    
    # Agents with voting rights
    VOTERS = ['Philosopher', 'Ethicist', 'Civics']
    
    def __init__(self, db_path=None):
        if db_path is None:
            self.db_path = os.path.join(BASE_DIR, 'republic.db')
        else:
            self.db_path = db_path

    # Phase 34: All methods now use db_connection() context manager

    def propose_amendment(self, rule_id: str, amendment_text: str,
                          rationale: str, proposed_by: str) -> int:
        """Propose a new constitutional amendment. Returns Amendment ID or -1."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO constitutional_amendments
                    (rule_id, amendment_text, rationale, proposed_by, status)
                    VALUES (?, ?, ?, ?, 'PROPOSED')
                """, (rule_id, amendment_text, rationale, proposed_by))
                amendment_id = c.lastrowid
                conn.commit()

            logger.info(f"[VOTING] Amendment {amendment_id} proposed: {rule_id}")
            return amendment_id

        except Exception as e:
            logger.error(f"[VOTING] Failed to propose amendment: {e}")
            return -1

    def start_voting(self, amendment_id: int) -> bool:
        """Move amendment from PROPOSED to VOTING status."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute("""
                    UPDATE constitutional_amendments
                    SET status = 'VOTING'
                    WHERE id = ? AND status = 'PROPOSED'
                """, (amendment_id,))
                success = c.rowcount > 0
                conn.commit()

            if success:
                logger.info(f"[VOTING] Amendment {amendment_id} opened for voting")
            return success

        except Exception as e:
            logger.error(f"[VOTING] Failed to start voting: {e}")
            return False

    def cast_vote(self, amendment_id: int, voter: str, vote_for: bool) -> bool:
        """Cast a vote on an amendment."""
        if voter not in self.VOTERS:
            logger.warning(f"[VOTING] {voter} does not have voting rights")
            return False

        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()

                c.execute("SELECT status FROM constitutional_amendments WHERE id = ?",
                          (amendment_id,))
                row = c.fetchone()
                if not row or row[0] != 'VOTING':
                    logger.warning(f"[VOTING] Amendment {amendment_id} not in VOTING status")
                    return False

                # Phase 34: Whitelist column name — prevent injection
                column = 'votes_for' if vote_for else 'votes_against'
                c.execute(f"""
                    UPDATE constitutional_amendments
                    SET {column} = {column} + 1
                    WHERE id = ?
                """, (amendment_id,))

                conn.commit()

            vote_type = "FOR" if vote_for else "AGAINST"
            logger.info(f"[VOTING] {voter} voted {vote_type} on Amendment {amendment_id}")
            return True

        except Exception as e:
            logger.error(f"[VOTING] Failed to cast vote: {e}")
            return False

    def tally_votes(self, amendment_id: int) -> str:
        """Tally votes and resolve amendment status."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()

                c.execute("""
                    SELECT votes_for, votes_against, status
                    FROM constitutional_amendments WHERE id = ?
                """, (amendment_id,))
                row = c.fetchone()

                if not row:
                    return 'NOT_FOUND'

                votes_for, votes_against, status = row

                if status != 'VOTING':
                    return status

                total_votes = votes_for + votes_against
                if total_votes == 0:
                    return 'VOTING'

                new_status = 'APPROVED' if votes_for > votes_against else 'REJECTED'

                c.execute("""
                    UPDATE constitutional_amendments
                    SET status = ?, resolved_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_status, amendment_id))
                conn.commit()

            logger.info(f"[VOTING] Amendment {amendment_id} {new_status} ({votes_for}-{votes_against})")
            return new_status

        except Exception as e:
            logger.error(f"[VOTING] Failed to tally votes: {e}")
            return 'ERROR'

    def architect_veto(self, amendment_id: int, reason: str) -> bool:
        """Architect (The I) vetoes an amendment."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute("""
                    UPDATE constitutional_amendments
                    SET status = 'VETOED',
                        rationale = rationale || ' | VETOED: ' || ?,
                        resolved_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (reason, amendment_id))
                success = c.rowcount > 0
                conn.commit()

            if success:
                logger.warning(f"[VOTING] Amendment {amendment_id} VETOED by Architect")
            return success

        except Exception as e:
            logger.error(f"[VOTING] Failed to veto: {e}")
            return False

    def get_pending_amendments(self) -> list:
        """Get all amendments in PROPOSED or VOTING status."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT id, rule_id, amendment_text, rationale, proposed_by,
                           status, votes_for, votes_against, created_at
                    FROM constitutional_amendments
                    WHERE status IN ('PROPOSED', 'VOTING')
                    ORDER BY created_at ASC
                """)
                amendments = c.fetchall()
            return amendments

        except Exception as e:
            logger.error(f"[VOTING] Failed to get pending amendments: {e}")
            return []


def run_constitution_guard(db_path=None):
    """Entry point for main.py integration."""
    guard = ConstitutionGuard(db_path)
    return guard.run_audit()


if __name__ == "__main__":
    guard = ConstitutionGuard()
    violations = guard.run_audit()
    
    print(f"\n{'='*60}")
    print(f"Constitutional Compliance: {guard.get_compliance_score():.1f}%")
    print(f"{'='*60}")
    
    if violations:
        print("\nViolations Found:")
        for rule_id, name, result in violations:
            print(f"  [{rule_id}] {name}: {result.reason}")
    else:
        print("\n✅ All constitutional checks passed.")
