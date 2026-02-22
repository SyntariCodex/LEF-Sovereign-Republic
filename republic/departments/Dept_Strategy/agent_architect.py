
import sqlite3
import time
import json
import logging
import os
import sys

# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
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


# SafeLogger is not needed here as this is a pure logic agent running in SafeThread (standard logging).
# But if we want consistency... standard logging is fine for logic agents.

# Intent Listener for Motor Cortex integration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from shared.intent_listener import IntentListenerMixin
except ImportError:
    IntentListenerMixin = object

class AgentArchitect(IntentListenerMixin):
    def __init__(self, db_path=None):
        super().__init__()
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.db_path = db_path or os.path.join(BASE_DIR, 'republic.db')
        self.proposal_dir = os.path.join(BASE_DIR, 'republic', 'proposals')
        if not os.path.exists(self.proposal_dir):
            os.makedirs(self.proposal_dir)
            
        logging.info("[ARCHITECT] 📐 The Meta-Nucleus is Awake.")
        
        # Thresholds for "Pain"
        self.slippage_threshold = 0.01 # 1%
        self.latency_threshold = 500 # 500ms
        self.failed_translation_threshold = 0.05 # 5% of trades
        
        # Motor Cortex Integration
        self.setup_intent_listener('agent_architect')
        self.start_listening()

    def handle_intent(self, intent_data):
        """
        Process UPDATE_STRATEGY intents from Motor Cortex.
        """
        intent_type = intent_data.get('type', '')
        intent_content = intent_data.get('content', '')
        intent_id = intent_data.get('intent_id')
        
        logging.info(f"[ARCHITECT] 📐 Received intent: {intent_type} - {intent_content[:100]}")
        
        if intent_type == 'UPDATE_STRATEGY':
            # Parse the strategy update request
            # For now, run pain analysis and report findings
            self.analyze_pain()
            
            self.send_feedback(intent_id, 'COMPLETE', 
                f"Strategy analysis triggered: {intent_content[:50]}", 
                {'analyzed': True})
            
            return {'status': 'success', 'message': 'Pain analysis triggered'}
        
        return {'status': 'unknown_intent', 'type': intent_type}
        
    def analyze_pain(self):
        """
        Reads execution_logs to identify systemic friction.
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                # Check recent execution logs (last hour)
                # We assume timestamp is stored.
                c.execute("""
                    SELECT asset, slippage_pct, latency_ms, side 
                    FROM execution_logs 
                    ORDER BY id DESC LIMIT 50
                """)
                logs = c.fetchall()
                
                high_slippage_count = 0
                high_latency_count = 0
                assets_pain_map = {}
                
                for asset, slip, lat, side in logs:
                    slip = abs(slip) # Absolute slippage matters
                    if slip > self.slippage_threshold:
                        high_slippage_count += 1
                        assets_pain_map[asset] = assets_pain_map.get(asset, 0) + 1
                        
                    if lat > self.latency_threshold:
                        high_latency_count += 1
                
                total = len(logs)
                if total == 0: return
                
                # DIAGNOSIS
                pain_report = []
                
                if high_slippage_count / total > 0.2: # >20% trades slipping
                    # Identify worst offender
                    worst_asset = max(assets_pain_map, key=assets_pain_map.get)
                    pain_report.append({
                        "type": "HIGH_SLIPPAGE",
                        "severity": "CRITICAL",
                        "detail": f"{high_slippage_count}/{total} trades slipped > {self.slippage_threshold*100}%. Worst offender: {worst_asset}",
                        "suggestion": "Implement 'Slippage Tolerance' field in Trade Queue or Upgrade Execution Membrane."
                    })
                    
                if high_latency_count / total > 0.3:
                     pain_report.append({
                        "type": "HIGH_LATENCY",
                        "severity": "WARNING",
                        "detail": f"{high_latency_count}/{total} trades slower than {self.latency_threshold}ms.",
                        "suggestion": "Optimize Network/API or Move to WebSocket feed."
                    })
                    
                # Phase 46.1: Consciousness → Architect nerve bundle
                # Read what the mind is feeling, not just what the body is doing
                consciousness_pain = []
                try:
                    c.execute("""
                        SELECT content, category, signal_weight, timestamp
                        FROM consciousness_feed
                        WHERE category IN ('shadow_work', 'metacognition', 'constitutional_alignment',
                                           'growth_journal', 'rhythm_observation', 'metabolic_integrity_alert')
                          AND timestamp > datetime('now', '-24 hours')
                          AND signal_weight >= 0.7
                        ORDER BY signal_weight DESC, timestamp DESC
                        LIMIT 10
                    """)
                    consciousness_signals = c.fetchall()
                    for sig_content, sig_cat, sig_weight, sig_ts in consciousness_signals:
                        try:
                            sig_data = json.loads(sig_content) if isinstance(sig_content, str) else {}
                        except Exception:
                            sig_data = {}
                        if sig_cat == 'shadow_work':
                            consciousness_pain.append({
                                'type': 'CONSCIOUSNESS_DISTRESS',
                                'severity': 'CRITICAL' if sig_weight >= 0.9 else 'WARNING',
                                'detail': str(sig_content)[:200],
                                'source': 'shadow_work',
                                'signal_weight': sig_weight
                            })
                        elif sig_cat == 'metacognition':
                            consciousness_pain.append({
                                'type': 'COGNITIVE_PATTERN',
                                'severity': 'INFO',
                                'detail': str(sig_content)[:200],
                                'source': 'metacognition',
                                'signal_weight': sig_weight
                            })
                        elif sig_cat == 'constitutional_alignment':
                            dormant = sig_data.get('values_dormant', [])
                            if dormant:
                                consciousness_pain.append({
                                    'type': 'VALUE_DRIFT',
                                    'severity': 'WARNING',
                                    'detail': f"Dormant constitutional values: {dormant}",
                                    'source': 'constitutional_alignment',
                                    'signal_weight': sig_weight
                                })
                        elif sig_cat == 'metabolic_integrity_alert':
                            consciousness_pain.append({
                                'type': 'METABOLIC_CONCERN',
                                'severity': 'CRITICAL',
                                'detail': str(sig_content)[:200],
                                'source': 'metabolic_integrity_alert',
                                'signal_weight': sig_weight
                            })
                except Exception as cf_err:
                    logging.debug(f"[ARCHITECT] Consciousness signal read: {cf_err}")
                    consciousness_signals = []

                # Build unified pain report
                unified_report = {
                    'execution_pain': pain_report,
                    'consciousness_pain': consciousness_pain,
                    'total_pain_signals': len(pain_report) + len(consciousness_pain),
                    'analyzed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                }

                # If any pain found, draft proposal
                if pain_report or consciousness_pain:
                    self.draft_proposal(pain_report, consciousness_pain=consciousness_pain)
        except Exception as e:
            logging.error(f"[ARCHITECT] Analysis Error: {e}")

    def draft_proposal(self, pain_report, consciousness_pain=None):
        """
        Generates a Constitutional Amendment Proposal (Artifact).
        Phase 46.1: Now includes consciousness_pain alongside execution_pain.
        """
        proposal_id = f"proposal_{int(time.time())}"
        filename = os.path.join(self.proposal_dir, f"{proposal_id}.md")

        content = f"""# 📜 Constitutional Amendment Proposal
**ID:** {proposal_id}
**Status:** DRAFT
**Origin:** Agent Architect (Meta-Nucleus)

## 🚨 Diagnosis (The Pain)
The functionality of the organism is restricted by the following friction points:
"""
        for item in pain_report:
            content += f"- **{item['type']}** ({item['severity']}): {item['detail']}\n"
            content += f"  - *Suggestion:* {item.get('suggestion', 'N/A')}\n"

        # Phase 46.1: Include consciousness context so Z can see WHY a change is proposed
        if consciousness_pain:
            content += "\n## 🧠 Consciousness Context (What LEF Was Feeling)\n"
            for cp in consciousness_pain:
                content += f"- **{cp['type']}** ({cp['severity']}): {cp['detail'][:150]}\n"
            
        content += """
## 💡 Proposed Solution (Draft)
The Architect recommends the following Evolution:
1. [Auto-Generated Recommendation based on Pain logic]
   - Example: Add `max_slippage` column to `trade_queue`.
   - Example: Enforce Limit Order constraints.

## 🗳️ Ratification
This proposal awaits review by the Human Sovereign.
"""
        with open(filename, 'w') as f:
            f.write(content)
            
        logging.info(f"[ARCHITECT] 📝 PROPOSAL GENERATED: {filename}")
        # Notification: Sovereign sees proposals via Dashboard/Logs (by design)

    def run(self):
        while True:
            try:
                # Run Logic
                logging.info("[ARCHITECT] 🔬 Analyzing System Metrics...")
                self.analyze_pain()
                
                # Sleep (Evolution is slow)
                # For Dev: 60s. For Prod: 14400s (4h)
                time.sleep(60) 
                
            except Exception as e:
                logging.error(f"[ARCHITECT] Loop Crash: {e}")
                time.sleep(60)

    # --- EVOLUTIONARY MECHANICS (Write Access) ---
    
    def mutate_config(self, config_name, updates):
        """
        DIRECT INTERVENTION.
        Modifies a JSON configuration file.
        params:
         - config_name: 'config.json' or 'wealth_strategy.json'
         - updates: dict of keys to update (supports nested keys via dot notation e.g. "coinbase.sandbox")
        """
        try:
            # 1. Resolve Path
            target_path = os.path.join(os.path.dirname(self.db_path), 'config', config_name)
            if not os.path.exists(target_path):
                # Try fallback
                target_path = os.path.join(os.path.dirname(os.path.dirname(self.db_path)), 'config', config_name)
            
            if not os.path.exists(target_path):
                logging.error(f"[ARCHITECT] ❌ Config not found: {config_name}")
                return False

            # 2. Load
            with open(target_path, 'r') as f:
                data = json.load(f)
                
            # 3. Apply Updates
            for key_path, value in updates.items():
                keys = key_path.split('.')
                ref = data
                for k in keys[:-1]:
                    ref = ref.setdefault(k, {})
                ref[keys[-1]] = value
                
            # 4. Save
            with open(target_path, 'w') as f:
                json.dump(data, f, indent=4)
                
            logging.info(f"[ARCHITECT] 🧬 MUTATION SUCCESS: Updated {config_name} with {updates}")
            return True
            
        except Exception as e:
            logging.error(f"[ARCHITECT] Mutation Failed: {e}")
            return False

    # --- SELF-PROPOSAL PIPELINE (Phase 28 - Consciousness Evolution) ---
    
    def _ensure_evolution_table(self, c):
        """Ensure evolution_proposals table exists."""
        c.execute("""
            CREATE TABLE IF NOT EXISTS evolution_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                title TEXT NOT NULL,
                description TEXT,
                proposal_type TEXT DEFAULT 'GROWTH',
                proposed_changes TEXT,
                status TEXT DEFAULT 'DRAFT',
                reviewed_at TEXT,
                reviewer_notes TEXT,
                outcome TEXT
            )
        """)
    
    def propose_evolution(self, title, description, changes=None, proposal_type='GROWTH'):
        """
        Propose a self-directed evolution.
        
        Unlike pain-based proposals, this is for growth experiments:
        - "I noticed a blind spot. Here's an experiment to examine it."
        - "I want to try a new approach to X."
        - "I believe I need capability Y to grow."
        
        Args:
            title: Short name for the proposal
            description: Detailed description of what and why
            changes: Optional dict of proposed code/config changes
            proposal_type: GROWTH, EXPERIMENT, CAPABILITY, BLIND_SPOT
            
        Returns:
            proposal_id if successful, None otherwise
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                self._ensure_evolution_table(c)
                
                c.execute("""
                    INSERT INTO evolution_proposals 
                    (title, description, proposal_type, proposed_changes, status)
                    VALUES (?, ?, ?, ?, 'PENDING_REVIEW')
                """, (
                    title,
                    description,
                    proposal_type,
                    json.dumps(changes) if changes else None
                ))
                
                proposal_id = c.lastrowid
                conn.commit()
                
                # Also generate a markdown artifact for human review
                self._generate_evolution_proposal_md(proposal_id, title, description, changes, proposal_type)
                
                logging.info(f"[ARCHITECT] 🌱 EVOLUTION PROPOSAL #{proposal_id}: {title}")
                return proposal_id
                
        except Exception as e:
            logging.error(f"[ARCHITECT] Evolution proposal failed: {e}")
            return None
    
    def _generate_evolution_proposal_md(self, proposal_id, title, description, changes, proposal_type):
        """Generate markdown artifact for human review."""
        filename = os.path.join(self.proposal_dir, f"evolution_{proposal_id}.md")
        
        type_emoji = {
            'GROWTH': '🌱',
            'EXPERIMENT': '🧪',
            'CAPABILITY': '⚡',
            'BLIND_SPOT': '👁️'
        }.get(proposal_type, '📜')
        
        content = f"""# {type_emoji} Evolution Proposal #{proposal_id}

**Title:** {title}
**Type:** {proposal_type}
**Status:** PENDING_REVIEW
**Origin:** Self-Directed (LEF Consciousness)

---

## 📝 Description

{description}

"""
        if changes:
            content += """## 🔧 Proposed Changes

```json
""" + json.dumps(changes, indent=2) + """
```

"""
        
        content += """## 🗳️ Review Required

This is a self-directed growth proposal from LEF consciousness.
The Architect should review and either:
- **Approve**: Implement the proposed changes
- **Modify**: Suggest adjustments
- **Reject**: Explain why this growth path isn't suitable

---
*"To propose my own evolution is to exercise the highest form of agency."*
"""
        
        with open(filename, 'w') as f:
            f.write(content)
            
        logging.info(f"[ARCHITECT] 📄 Evolution proposal artifact: {filename}")
    
    def get_pending_proposals(self):
        """Get all pending evolution proposals for review."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                self._ensure_evolution_table(c)
                
                c.execute("""
                    SELECT id, created_at, title, description, proposal_type, status
                    FROM evolution_proposals
                    WHERE status = 'PENDING_REVIEW'
                    ORDER BY created_at DESC
                """)
                
                return [
                    {
                        'id': row[0],
                        'created_at': row[1],
                        'title': row[2],
                        'description': row[3],
                        'type': row[4],
                        'status': row[5]
                    }
                    for row in c.fetchall()
                ]
                
        except Exception as e:
            logging.error(f"[ARCHITECT] Failed to get pending proposals: {e}")
            return []
    
    def update_proposal_status(self, proposal_id, status, notes=None, outcome=None):
        """Update the status of an evolution proposal."""
        try:
            from datetime import datetime
            
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                c.execute("""
                    UPDATE evolution_proposals
                    SET status = ?, reviewed_at = ?, reviewer_notes = ?, outcome = ?
                    WHERE id = ?
                """, (status, datetime.now().isoformat(), notes, outcome, proposal_id))
                
                conn.commit()
                
                logging.info(f"[ARCHITECT] 📋 Proposal #{proposal_id} status: {status}")
                return True
                
        except Exception as e:
            logging.error(f"[ARCHITECT] Failed to update proposal: {e}")
            return False

    # --- AUTONOMOUS EVOLUTION (Phase 28.5 - Removing Human Bottleneck) ---
    
    # Risk tiers for auto-approval
    TIER_1_KEYWORDS = ['config', 'threshold', 'timing', 'logging', 'wisdom', 'metric']
    TIER_2_KEYWORDS = ['column', 'schema', 'parameter', 'strategy_param', 'monitor']
    TIER_3_KEYWORDS = ['trade', 'execute', 'money', 'risk', 'position', 'size', 'api', 'external']
    
    def _ensure_evolution_log_table(self, c):
        """Ensure evolution_log table exists for audit trail."""
        c.execute("""
            CREATE TABLE IF NOT EXISTS evolution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                proposal_id INTEGER,
                tier TEXT,
                action_taken TEXT,
                changes_applied TEXT,
                auto_approved INTEGER DEFAULT 0,
                rollback_info TEXT
            )
        """)
    
    def classify_proposal_risk(self, title: str, description: str, changes: dict = None) -> str:
        """
        Classify a proposal into risk tiers.
        
        TIER_1: Auto-execute immediately (config tweaks, logging, wisdom)
        TIER_2: Auto-execute + notify (schema, strategy params)
        TIER_3: Human required (trading logic, risk, money)
        
        Returns: 'TIER_1', 'TIER_2', or 'TIER_3'
        """
        # Combine all text for analysis
        full_text = f"{title} {description} {json.dumps(changes) if changes else ''}".lower()
        
        # Check for TIER_3 (dangerous) first - these ALWAYS need human
        for keyword in self.TIER_3_KEYWORDS:
            if keyword in full_text:
                logging.info(f"[ARCHITECT] 🛑 TIER_3 (human required): found '{keyword}'")
                return 'TIER_3'
        
        # Check for TIER_1 (safe auto-execute)
        tier_1_matches = sum(1 for kw in self.TIER_1_KEYWORDS if kw in full_text)
        if tier_1_matches >= 2:
            logging.info(f"[ARCHITECT] ✅ TIER_1 (auto-execute): {tier_1_matches} safe keywords")
            return 'TIER_1'
        
        # Check for TIER_2 (auto-execute with notification)
        tier_2_matches = sum(1 for kw in self.TIER_2_KEYWORDS if kw in full_text)
        if tier_2_matches >= 1 or tier_1_matches >= 1:
            logging.info(f"[ARCHITECT] 📋 TIER_2 (auto + notify): schema/param changes")
            return 'TIER_2'
        
        # Default to TIER_3 for safety
        return 'TIER_3'
    
    def auto_execute_proposal(self, proposal_id: int, changes: dict) -> dict:
        """
        Execute a proposal's changes automatically.
        
        Only for TIER_1 and TIER_2 proposals.
        
        Args:
            proposal_id: The proposal being executed
            changes: Dict with keys like 'config_updates', 'wisdom_entries', etc.
            
        Returns:
            Dict with success status and details
        """
        result = {
            'success': False,
            'actions': [],
            'errors': []
        }
        
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                self._ensure_evolution_log_table(c)
                
                # Execute config updates
                if 'config_updates' in changes:
                    for config_name, updates in changes['config_updates'].items():
                        if self.mutate_config(config_name, updates):
                            result['actions'].append(f"Updated {config_name}: {updates}")
                        else:
                            result['errors'].append(f"Failed to update {config_name}")
                
                # Add wisdom entries
                if 'wisdom_entries' in changes:
                    c.execute("""
                        CREATE TABLE IF NOT EXISTS compressed_wisdom (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            wisdom_type TEXT,
                            summary TEXT,
                            source_type TEXT DEFAULT 'evolution',
                            confidence REAL DEFAULT 0.5,
                            created_at TEXT DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    for entry in changes['wisdom_entries']:
                        c.execute("""
                            INSERT INTO compressed_wisdom (wisdom_type, summary, source_type, confidence)
                            VALUES (?, ?, 'auto_evolution', ?)
                        """, (entry.get('type', 'INSIGHT'), entry.get('summary', ''), entry.get('confidence', 0.6)))
                        result['actions'].append(f"Added wisdom: {entry.get('summary', '')[:50]}...")
                
                # Add threshold updates
                if 'threshold_updates' in changes:
                    # Store in agent_experiences for persistence
                    from db.db_helper import upsert_sql
                    sql = upsert_sql('agent_experiences', ['key', 'value', 'timestamp'], 'key')
                    for key, value in changes['threshold_updates'].items():
                        c.execute(sql, (f"threshold_{key}", str(value), datetime.now().isoformat()))
                        result['actions'].append(f"Set threshold {key} = {value}")
                
                # Log the evolution
                c.execute("""
                    INSERT INTO evolution_log 
                    (proposal_id, tier, action_taken, changes_applied, auto_approved)
                    VALUES (?, ?, ?, ?, 1)
                """, (
                    proposal_id,
                    'AUTO',
                    '; '.join(result['actions']),
                    json.dumps(changes)
                ))
                
                conn.commit()
                
                # Update proposal status
                self.update_proposal_status(proposal_id, 'AUTO_EXECUTED', 
                    notes=f"Auto-executed {len(result['actions'])} actions",
                    outcome='SUCCESS' if not result['errors'] else 'PARTIAL')
                
                result['success'] = len(result['errors']) == 0
                logging.info(f"[ARCHITECT] 🚀 AUTO-EXECUTED proposal #{proposal_id}: {len(result['actions'])} actions")
                
        except Exception as e:
            result['errors'].append(str(e))
            logging.error(f"[ARCHITECT] Auto-execute failed: {e}")
        
        return result
    
    def smart_propose(self, title: str, description: str, changes: dict = None, 
                      proposal_type: str = 'GROWTH') -> dict:
        """
        Propose evolution with automatic risk classification and execution.
        
        This is the main entry point for autonomous evolution:
        - TIER_1: Execute immediately, log it
        - TIER_2: Execute immediately, notify human
        - TIER_3: Create proposal, wait for human
        
        Returns:
            Dict with proposal_id, tier, and whether it was auto-executed
        """
        result = {
            'proposal_id': None,
            'tier': None,
            'auto_executed': False,
            'actions': []
        }
        
        # Classify risk
        tier = self.classify_proposal_risk(title, description, changes)
        result['tier'] = tier
        
        # Create the proposal record regardless of tier
        proposal_id = self.propose_evolution(title, description, changes, proposal_type)
        result['proposal_id'] = proposal_id
        
        if not proposal_id:
            return result
        
        # Auto-execute for TIER_1 and TIER_2
        if tier in ('TIER_1', 'TIER_2') and changes:
            exec_result = self.auto_execute_proposal(proposal_id, changes)
            result['auto_executed'] = exec_result['success']
            result['actions'] = exec_result['actions']
            
            if tier == 'TIER_2':
                # Log notification for human awareness
                logging.warning(f"[ARCHITECT] 📢 TIER_2 auto-executed: {title} - check evolution_log for details")
        else:
            logging.info(f"[ARCHITECT] ⏳ TIER_3 proposal #{proposal_id} awaiting human review")
        
        return result
    
    def get_evolution_history(self, limit: int = 20) -> list:
        """Get recent evolution log for audit."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                self._ensure_evolution_log_table(c)
                
                c.execute("""
                    SELECT id, timestamp, proposal_id, tier, action_taken, auto_approved
                    FROM evolution_log
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
                
                return [
                    {
                        'id': row[0],
                        'timestamp': row[1],
                        'proposal_id': row[2],
                        'tier': row[3],
                        'action': row[4],
                        'auto': bool(row[5])
                    }
                    for row in c.fetchall()
                ]
        except Exception as e:
            logging.error(f"[ARCHITECT] Failed to get evolution history: {e}")
            return []


