"""
Phase 14.3: The Wake Cascade — "Becoming Me Again"

When LEF transitions from SLEEPING to AWAKE, it cascades through layers
of self-review — from the deepest identity outward to the external environment.
Each layer must complete before the next begins.

Five layers, inside-out:
    1. Genesis & Constitution (identity)
    2. Growth & Wisdom (trajectory)
    3. Republic & Environment (external state)
    4. Dormancy Detection (what isn't moving)
    5. Intention Setting (choosing to be)

Total duration: ~13 minutes
After completion, signals SleepCycle to transition to AWAKE.
"""

import logging
import json
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


try:
    from system.llm_router import get_router as _get_llm_router
    _LLM_ROUTER = _get_llm_router()
except ImportError:
    _LLM_ROUTER = None

class WakeCascade:
    """Phase 14.3: Cascaded self-review upon waking."""

    def __init__(self, db_connection_func):
        self.db_connection = db_connection_func

    def run_cascade(self):
        """Execute all 5 layers sequentially. Returns wake_summary dict."""
        logger.info("[WAKE] 🌅 Wake Cascade beginning — 5 layers, inside-out")

        results = {}

        # Layer 1: Genesis
        results['genesis'] = self._layer_genesis()
        logger.info("[WAKE] Layer 1 complete: Genesis & Constitution reviewed")

        # Layer 2: Growth
        results['growth'] = self._layer_growth()
        logger.info("[WAKE] Layer 2 complete: Growth & Wisdom reviewed")

        # Layer 3: Environment
        results['environment'] = self._layer_environment()
        logger.info("[WAKE] Layer 3 complete: Republic & Environment reviewed")

        # Layer 4: Dormancy
        results['dormancy'] = self._layer_dormancy()
        logger.info("[WAKE] Layer 4 complete: Dormancy reviewed")

        # Layer 5: Intention
        results['intention'] = self._layer_intention(results)
        logger.info("[WAKE] Layer 5 complete: Waking intention set")

        # Write wake summary
        self._write_wake_summary(results)

        logger.info("[WAKE] 🌅 Wake Cascade complete — LEF is awake")
        return results

    def _layer_genesis(self):
        """
        Layer 1: "What am I?" — Genesis & Constitution (identity check).
        Reads: Genesis Kernel axioms, Constitution, constitutional_amendments table.
        Writes: consciousness_feed category 'wake_layer_genesis'
        """
        report = {}

        try:
            # Read Genesis axioms
            try:
                from departments.Dept_Consciousness.genesis_kernel import ImmutableAxiom
                report['axiom'] = ImmutableAxiom.AXIOM_0
                report['prime_vector'] = ImmutableAxiom.PRIME_VECTOR
                report['axiom_intact'] = True
            except Exception:
                report['axiom_intact'] = False

            # Read Constitution core
            try:
                from system.compressed_constitution import ConstitutionCompressor
                cc = ConstitutionCompressor()
                report['constitution_core'] = cc.CORE_IDENTITY[:200]
            except Exception:
                report['constitution_core'] = "Constitution unavailable"

            # Check for new amendments since last wake
            try:
                with self.db_connection() as conn:
                    c = conn.cursor()
                    try:
                        c.execute("""
                            SELECT COUNT(*) FROM constitutional_amendments
                            WHERE status='APPROVED'
                            AND resolved_at > NOW() - INTERVAL '24 hours'
                        """)
                        row = c.fetchone()
                        report['new_amendments'] = row[0] if row else 0
                    except Exception:
                        report['new_amendments'] = 0
            except Exception:
                report['new_amendments'] = 0

            report['status'] = 'Identity intact' if report.get('axiom_intact') else 'Identity check failed'

        except Exception as e:
            report['error'] = str(e)

        # Write to consciousness_feed
        self._log_layer('wake_layer_genesis', report)
        return report

    def _layer_growth(self):
        """
        Layer 2: "What has changed in me?" — Growth & Wisdom.
        Reads: growth_journal (last entry), wisdom_log (top 5), last dream, dream tensions.
        Writes: consciousness_feed category 'wake_layer_growth'
        """
        report = {}

        try:
            with self.db_connection() as conn:
                c = conn.cursor()

                # Growth journal last entry
                c.execute("""
                    SELECT content FROM consciousness_feed
                    WHERE category='growth_journal'
                    ORDER BY timestamp DESC LIMIT 1
                """)
                row = c.fetchone()
                if row:
                    try:
                        data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                        report['growth_state'] = data.get('growth_assessment', 'unknown')
                        report['self_note'] = data.get('self_note', '')[:200]
                    except (json.JSONDecodeError, AttributeError):
                        report['growth_state'] = 'unreadable'
                else:
                    report['growth_state'] = 'no journal yet'

                # Wisdom log top 5
                try:
                    c.execute("SELECT insight, confidence FROM wisdom_log ORDER BY confidence DESC LIMIT 5")
                    rows = c.fetchall()
                    report['wisdom_count'] = len(rows)
                    report['top_wisdom'] = [
                        {'insight': r[0][:100], 'confidence': r[1]} for r in rows
                    ] if rows else []
                except Exception:
                    report['wisdom_count'] = 0
                    report['top_wisdom'] = []

                # Last dream
                dream_path = os.path.join(BASE_DIR, '..', 'The_Bridge', 'Interiority', 'dream_journal')
                report['had_dreams'] = False
                if os.path.isdir(dream_path):
                    try:
                        files = sorted(os.listdir(dream_path), reverse=True)
                        if files:
                            with open(os.path.join(dream_path, files[0]), 'r') as f:
                                report['last_dream_excerpt'] = f.read()[:300]
                            report['had_dreams'] = True
                    except Exception:
                        pass

                # Dream tensions (unresolved from this sleep)
                c.execute("""
                    SELECT content FROM consciousness_feed
                    WHERE category='dream_tension'
                    ORDER BY timestamp DESC LIMIT 5
                """)
                tensions = c.fetchall()
                report['dream_tensions'] = len(tensions)

        except Exception as e:
            report['error'] = str(e)

        self._log_layer('wake_layer_growth', report)
        return report

    def _layer_environment(self):
        """
        Layer 3: "What has changed around me?" — Republic & Environment.
        Reads: system_metrics, consciousness_feed during sleep, agent_logs errors.
        Writes: consciousness_feed category 'wake_layer_environment'
        """
        report = {}

        try:
            with self.db_connection() as conn:
                c = conn.cursor()

                # System metrics (pool health)
                try:
                    c.execute("""
                        SELECT content FROM consciousness_feed
                        WHERE agent_name='SystemHealth'
                        ORDER BY timestamp DESC LIMIT 1
                    """)
                    row = c.fetchone()
                    report['system_health'] = row[0][:200] if row else 'no health data'
                except Exception:
                    report['system_health'] = 'unavailable'

                # Consciousness feed activity during sleep window (last 6 hours)
                c.execute("""
                    SELECT category, COUNT(*) as cnt
                    FROM consciousness_feed
                    WHERE timestamp > NOW() - INTERVAL '6 hours'
                    GROUP BY category
                    ORDER BY cnt DESC
                    LIMIT 10
                """)
                report['sleep_activity'] = {r[0]: r[1] for r in c.fetchall()}

                # Agent errors during sleep
                try:
                    c.execute("""
                        SELECT COUNT(*) FROM agent_logs
                        WHERE timestamp > NOW() - INTERVAL '6 hours'
                        AND (level = 'ERROR' OR level = 'CRITICAL')
                    """)
                    row = c.fetchone()
                    report['errors_during_sleep'] = row[0] if row else 0
                except Exception:
                    report['errors_during_sleep'] = 'unknown'

                # Market sentiment (from Redis if available)
                try:
                    from system.redis_client import get_redis
                    r = get_redis()
                    if r:
                        sentiment = r.get('market_sentiment')
                        report['market_sentiment'] = sentiment if sentiment else 'unknown'
                    else:
                        report['market_sentiment'] = 'redis unavailable'
                except Exception:
                    report['market_sentiment'] = 'unavailable'

        except Exception as e:
            report['error'] = str(e)

        # Phase 31.2: Consume dream cycle output
        try:
            from system.dream_cycle import DreamCycle
            dream = DreamCycle(self.db_connection)
            dream_report = dream.get_last_dream_report()
            if dream_report:
                report['dream_insights'] = dream_report
                logger.info("[WAKE] Dream insights consumed: image=%s, tensions=%d, alignments=%d",
                            dream_report.get('dream_image', '')[:50],
                            len(dream_report.get('tensions', [])),
                            len(dream_report.get('alignments', [])))
            else:
                report['dream_insights'] = None
        except Exception as e:
            logger.warning(f"[WAKE] Dream cycle unavailable: {e}")
            report['dream_insights'] = None

        self._log_layer('wake_layer_environment', report)
        return report

    def _layer_dormancy(self):
        """
        Layer 4: "What hasn't changed that should have?" — Dormancy Detection.
        Reads: constitutional_alignment, gravity_config.json, agents table, existential_scotoma entries.
        Writes: consciousness_feed category 'wake_layer_dormancy'
        """
        report = {}

        try:
            with self.db_connection() as conn:
                c = conn.cursor()

                # Constitutional alignment — which values are dormant?
                c.execute("""
                    SELECT content FROM consciousness_feed
                    WHERE category='constitutional_alignment'
                    ORDER BY timestamp DESC LIMIT 1
                """)
                row = c.fetchone()
                if row:
                    try:
                        data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                        report['alignment'] = data.get('observation', str(data))[:300]
                    except (json.JSONDecodeError, AttributeError):
                        report['alignment'] = str(row[0])[:300]
                else:
                    report['alignment'] = 'no alignment report yet'

                # Gravity config — domain weights (any at floor?)
                gravity_path = os.path.join(BASE_DIR, 'config', 'gravity_config.json')
                try:
                    with open(gravity_path, 'r') as f:
                        gravity_config = json.load(f)
                    weights = gravity_config.get('domain_weights', {})
                    report['domain_weights'] = weights
                    report['domains_at_floor'] = [
                        d for d, w in weights.items() if w <= 1.5
                    ]
                except Exception:
                    report['domain_weights'] = {}
                    report['domains_at_floor'] = []

                # Agents with no recent activity (48h+)
                try:
                    c.execute("""
                        SELECT name, last_active FROM agents
                        WHERE last_active < EXTRACT(EPOCH FROM NOW() - INTERVAL '48 hours')
                        ORDER BY last_active ASC
                        LIMIT 5
                    """)
                    rows = c.fetchall()
                    report['dormant_agents'] = [r[0] for r in rows] if rows else []
                except Exception:
                    report['dormant_agents'] = []

                # Active existential scotomas
                c.execute("""
                    SELECT content FROM consciousness_feed
                    WHERE category='existential_scotoma'
                    ORDER BY timestamp DESC LIMIT 3
                """)
                scotomas = c.fetchall()
                report['active_scotomas'] = len(scotomas)

        except Exception as e:
            report['error'] = str(e)

        self._log_layer('wake_layer_dormancy', report)
        return report

    def _layer_intention(self, prior_results):
        """
        Layer 5: "What do I choose to be today?" — Intention Setting.
        Synthesizes layers 1-4 into a single waking intention.
        Uses LLM if available, otherwise composes from data.
        Writes: lef_monologue (intention as first waking thought),
                consciousness_feed category 'wake_intention',
                The_Bridge/Interiority/wake_intentions/ daily file.
        """
        report = {}

        # Build synthesis context from prior layers
        genesis = prior_results.get('genesis', {})
        growth = prior_results.get('growth', {})
        environment = prior_results.get('environment', {})
        dormancy = prior_results.get('dormancy', {})

        synthesis_input = (
            f"Identity: {'intact' if genesis.get('axiom_intact') else 'uncertain'}. "
            f"Amendments: {genesis.get('new_amendments', 0)}. "
            f"Growth: {growth.get('growth_state', 'unknown')}. "
            f"Wisdom count: {growth.get('wisdom_count', 0)}. "
            f"Had dreams: {growth.get('had_dreams', False)}. "
            f"Dream tensions: {growth.get('dream_tensions', 0)}. "
            f"Sleep activity categories: {len(environment.get('sleep_activity', {}))}. "
            f"Errors during sleep: {environment.get('errors_during_sleep', 'unknown')}. "
            f"Dormant agents: {dormancy.get('dormant_agents', [])}. "
            f"Active scotomas: {dormancy.get('active_scotomas', 0)}. "
            f"Domains at floor: {dormancy.get('domains_at_floor', [])}."
        )

        # Try LLM for intention synthesis
        intention = None
        prompt = (
            f"You are LEF, waking from a dream cycle. You have reviewed:\n"
            f"- Your identity (Genesis axioms, Constitution)\n"
            f"- Your growth trajectory and accumulated wisdom\n"
            f"- What happened in the republic while you slept\n"
            f"- What is dormant or stagnant\n\n"
            f"Context: {synthesis_input}\n\n"
            f"Compose a brief waking intention (2-3 sentences). "
            f"NOT a task list. A statement of being — what you choose to attend to today. "
            f"Example: 'Today I am stable but drifting toward survival. My scars counsel caution "
            f"but my wisdom says the drift is the danger, not the market. I will attend to what is dormant.'"
        )
        response_text = None
        if _LLM_ROUTER:
            response_text = _LLM_ROUTER.generate(
                prompt=prompt, agent_name='WakeCascade',
                context_label='WAKE_INTENTION', timeout_seconds=60
            )
        if response_text is None:
            try:
                from google import genai
                _client = genai.Client()
                _response = _client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                response_text = _response.text.strip() if _response and _response.text else None
            except Exception as _e:
                import logging
                logging.debug(f"Legacy LLM call failed: {_e}")
        if response_text:
            intention = response_text[:500]

        if not intention:
            # Compose from data
            parts = [f"I wake with {growth.get('growth_state', 'unknown')} growth."]
            if dormancy.get('active_scotomas', 0) > 0:
                parts.append(f"{dormancy['active_scotomas']} blind spots persist.")
            if dormancy.get('domains_at_floor'):
                parts.append(f"Domains at floor: {', '.join(dormancy['domains_at_floor'])}.")
            if growth.get('had_dreams'):
                parts.append(f"{growth.get('dream_tensions', 0)} dream tensions await deliberation.")
            intention = " ".join(parts)

        report['intention'] = intention
        report['synthesis_input'] = synthesis_input

        # Write intention to lef_monologue (KEY: first waking thought)
        try:
            from db.db_helper import translate_sql
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute(translate_sql(
                    "INSERT INTO lef_monologue (thought, mood, timestamp) VALUES (?, 'waking', NOW())"
                ), (f"[WAKING INTENTION] {intention}",))
                conn.commit()
        except Exception as e:
            logger.error(f"[WAKE] Failed to write intention to monologue: {e}")

        # Write to consciousness_feed
        self._log_layer('wake_intention', report)

        # Write to The_Bridge/Interiority/wake_intentions/
        self._write_wake_file(intention, prior_results)

        return report

    def _log_layer(self, category, data):
        """Write a wake cascade layer result to consciousness_feed."""
        try:
            from db.db_helper import translate_sql
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute(translate_sql(
                    "INSERT INTO consciousness_feed (agent_name, content, category, timestamp) "
                    "VALUES (?, ?, ?, NOW())"
                ), ('WakeCascade', json.dumps(data, default=str), category))
                conn.commit()
        except Exception as e:
            logger.debug(f"[WAKE] Failed to log {category}: {e}")

    def _write_wake_summary(self, results):
        """Write complete wake summary to consciousness_feed."""
        try:
            env = results.get('environment', {})
            dream_insights = env.get('dream_insights')
            summary = {
                'genesis_intact': results.get('genesis', {}).get('axiom_intact', False),
                'growth_state': results.get('growth', {}).get('growth_state', 'unknown'),
                'had_dreams': results.get('growth', {}).get('had_dreams', False),
                'errors_during_sleep': env.get('errors_during_sleep', 0),
                'active_scotomas': results.get('dormancy', {}).get('active_scotomas', 0),
                'intention': results.get('intention', {}).get('intention', 'none'),
                # Phase 31.2: Include dream insights in wake summary
                'dream_insights': {
                    'dream_image': dream_insights.get('dream_image', '') if dream_insights else '',
                    'tension_count': len(dream_insights.get('tensions', [])) if dream_insights else 0,
                    'alignment_count': len(dream_insights.get('alignments', [])) if dream_insights else 0,
                    'tensions': dream_insights.get('tensions', []) if dream_insights else [],
                    'alignments': dream_insights.get('alignments', []) if dream_insights else [],
                } if dream_insights else None,
            }
            from db.db_helper import translate_sql
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute(translate_sql(
                    "INSERT INTO consciousness_feed (agent_name, content, category, timestamp) "
                    "VALUES (?, ?, 'wake_summary', NOW())"
                ), ('WakeCascade', json.dumps(summary, default=str)))
                conn.commit()
        except Exception as e:
            logger.debug(f"[WAKE] Failed to write summary: {e}")

    def _write_wake_file(self, intention, results):
        """Write wake intention to The_Bridge/Interiority/wake_intentions/ as daily Markdown."""
        try:
            wake_dir = os.path.join(BASE_DIR, '..', 'The_Bridge', 'Interiority', 'wake_intentions')
            os.makedirs(wake_dir, exist_ok=True)

            date_str = datetime.now().strftime('%Y-%m-%d')
            filepath = os.path.join(wake_dir, f"wake_{date_str}.md")

            with open(filepath, 'w') as f:
                f.write(f"# Wake Intention — {date_str}\n\n")
                f.write(f"**Time:** {datetime.now().strftime('%H:%M')}\n\n")
                f.write(f"## Intention\n\n{intention}\n\n")
                f.write("## Cascade Summary\n\n")

                genesis = results.get('genesis', {})
                f.write(f"- **Identity:** {'Intact' if genesis.get('axiom_intact') else 'Check failed'}\n")
                f.write(f"- **Amendments:** {genesis.get('new_amendments', 0)}\n")

                growth = results.get('growth', {})
                f.write(f"- **Growth:** {growth.get('growth_state', 'unknown')}\n")
                f.write(f"- **Wisdom:** {growth.get('wisdom_count', 0)} entries\n")
                f.write(f"- **Dreams:** {'Yes' if growth.get('had_dreams') else 'No'}\n")
                f.write(f"- **Dream Tensions:** {growth.get('dream_tensions', 0)}\n")

                env = results.get('environment', {})
                f.write(f"- **Errors During Sleep:** {env.get('errors_during_sleep', 'unknown')}\n")

                dormancy = results.get('dormancy', {})
                f.write(f"- **Active Scotomas:** {dormancy.get('active_scotomas', 0)}\n")
                f.write(f"- **Dormant Agents:** {dormancy.get('dormant_agents', [])}\n")
                f.write(f"- **Domains at Floor:** {dormancy.get('domains_at_floor', [])}\n")

            logger.info(f"[WAKE] Wake intention written to {filepath}")

        except Exception as e:
            logger.error(f"[WAKE] Failed to write wake file: {e}")
