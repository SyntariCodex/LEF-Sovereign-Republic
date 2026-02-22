"""
The Sabbath — Body Three of the Three-Body Reflection Architecture.

The deepest layer. Deliberate stillness where both logic and resonance are held
together. Triggers when Body Two surfaces a pattern with sufficient gravity.
Duration proportional to the weight of what's being held.

Output is one of: intention (-> evolution engine), conscious hold, or patience.

Design doc: LEF Ai Projects/Phase - Three-Body Reflection Architecture.md
"""

import json
import time
import logging
import threading
from datetime import datetime
from queue import Queue, Empty

logger = logging.getLogger("Sabbath")


class Sabbath:
    """
    Body Three: Deliberate, gravity-responsive stillness.

    Triggers from:
    - SovereignReflection.on_sabbath_trigger callback

    During Sabbath:
    - Holds logical assessment (gravity profile, data, scope)
    - Holds resonance assessment (scar history, felt significance)
    - Waits for integration — does not force resolution

    Outputs one of:
    - INTENTION: concrete evolution proposal -> evolution engine propose phase
    - HOLD: "not ready to act" -> pattern remains in Body Two
    - PATIENCE: "doesn't require change, requires time" -> pattern released

    Anti-rigidity:
    - Timeout proportional to gravity (not infinite)
    - No stacking (one Sabbath at a time, others queued in Body Two)
    - Logs all entries for LEF's future reflection
    """

    def __init__(self, db_connection_func, gravity_system, evolution_engine=None):
        """
        Args:
            db_connection_func: callable returning DB connection
            gravity_system: GravitySystem instance (for duration calculation)
            evolution_engine: EvolutionEngine instance (for passing formed intentions)
        """
        self.db_connection = db_connection_func
        self.gravity = gravity_system
        self.evolution_engine = evolution_engine

        self._trigger_queue = Queue()
        self._in_sabbath = False
        self._running = False
        self._thread = None
        self._current_pattern = None

        # Phase 11: Sabbath learning — set from outside via main.py
        self.sabbath_learner = None

    def start(self):
        """Start the Sabbath listener as a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="Sabbath")
        self._thread.start()
        logger.info("[BODY THREE] Sabbath listener active. Awaiting gravity.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=15)
        logger.info("[BODY THREE] Sabbath stopped.")

    def trigger(self, pattern_id, gravity_profile):
        """
        Called by Body Two when a pattern crosses the Sabbath threshold.
        Non-blocking — adds to queue.
        """
        if self._in_sabbath:
            logger.info(f"[BODY THREE] Sabbath in progress. Queuing: {pattern_id}")
        self._trigger_queue.put((pattern_id, gravity_profile))

    def _run_loop(self):
        """Main loop — waits for triggers, processes one at a time."""
        while self._running:
            try:
                # Wait for a trigger (blocks with timeout so we can check _running)
                pattern_id, gravity_profile = self._trigger_queue.get(timeout=10)
                self._enter_sabbath(pattern_id, gravity_profile)
            except Empty:
                continue  # No trigger, keep waiting
            except Exception as e:
                logger.error(f"[BODY THREE] Loop error: {e}")

    def _enter_sabbath(self, pattern_id, gravity_profile):
        """
        Enter Sabbath — the zero point. (Phase 10 deepened, Phase 12 expanded)

        Not a pause. A compression. Everything relevant is gathered,
        filtered through resonance, and distilled to essence.
        The outcome emerges from what survives the compression.

        Phase 12: Existential mode — longer dwell, constitutional context,
        new outcome types (EVOLVE, AFFIRM, QUESTION).
        """
        # Phase 14: Sabbath does NOT fire during sleep
        try:
            from system.sleep_cycle import SleepCycle
            if SleepCycle.is_sleeping():
                logger.debug("[BODY THREE] Skipping — system is in SLEEPING state")
                return
        except Exception:
            pass  # If we can't check, allow Sabbath (safe default)

        self._in_sabbath = True
        self._current_pattern = pattern_id

        gravity_level = gravity_profile.get("gravity_level", "baseline")
        sabbath_type = gravity_profile.get("sabbath_type", "operational")
        is_existential = sabbath_type == "existential"
        duration = self.gravity.sabbath_duration_seconds(gravity_profile)

        # Phase 12: Existential Sabbaths dwell longer — minimum 2x base
        if is_existential:
            duration = max(duration * 2.0, duration)

        logger.info(f"[BODY THREE] Entering {'Existential ' if is_existential else ''}Sabbath "
                    f"for '{pattern_id}' (gravity={gravity_level}, duration={duration}s)")

        # Phase 1: GATHER — collect everything relevant
        logical_assessment = self._gather_logical(pattern_id, gravity_profile)
        resonance_assessment = self._gather_resonance(pattern_id, gravity_profile)
        interiority_context = self._gather_interiority()

        # Phase 12: Gather existential context for existential Sabbaths
        existential_context = None
        if is_existential:
            existential_context = self._gather_existential_context()

        # Phase 2: COMPRESS — filter through resonance to essence
        essence = self._compress_to_essence(
            pattern_id, gravity_profile,
            logical_assessment, resonance_assessment, interiority_context
        )

        # Phase 12: Enrich essence with existential context
        if existential_context:
            essence["existential_context"] = existential_context

        # Phase 3: DWELL — sit with the compressed essence
        # Duration proportional to gravity. Not empty sleep —
        # this is where integration happens.
        time.sleep(duration)

        # Phase 4: EMERGE — let the outcome arise from the essence
        if is_existential:
            outcome, intention = self._emerge_existential(
                pattern_id, gravity_profile, essence
            )
        else:
            outcome, intention = self._emerge_from_essence(
                pattern_id, gravity_profile, essence
            )

        # Log everything — include sabbath_type in gravity_profile for log
        gravity_profile_with_type = {**gravity_profile, "sabbath_type": sabbath_type}
        self._log_sabbath(
            pattern_id, gravity_profile_with_type, gravity_level, duration,
            logical_assessment, resonance_assessment, outcome, intention,
            essence=essence
        )

        # Express — the white-hole moment (Phase 10E)
        self._express(pattern_id, outcome, essence, intention)

        # Act on outcome
        if outcome == "INTENTION" and intention:
            self._pass_intention_to_evolution(pattern_id, gravity_profile, intention)
        elif outcome == "EVOLVE" and intention:
            self._pass_evolve_to_proposals(pattern_id, intention)
        elif outcome == "AFFIRM":
            self._log_affirmation(pattern_id, intention or "Direction affirmed.")
        elif outcome == "QUESTION":
            self._log_existential_question(pattern_id, intention or "An unresolved question remains.")
        elif outcome == "HOLD":
            logger.info(f"[BODY THREE] Conscious hold: '{pattern_id}'. Remains in Body Two.")
        elif outcome == "PATIENCE":
            self._release_pattern(pattern_id)
            logger.info(f"[BODY THREE] Patience: '{pattern_id}'. Released. Time, not change.")

        self._in_sabbath = False
        self._current_pattern = None

        # Phase 11: Notify SabbathLearner that a Sabbath event completed
        if self.sabbath_learner:
            try:
                self.sabbath_learner.notify_sabbath_complete()
            except Exception as e:
                logger.debug(f"[BODY THREE] SabbathLearner notification: {e}")

        logger.info(f"[BODY THREE] Sabbath complete for '{pattern_id}': {outcome}")

    def _gather_logical(self, pattern_id, gravity_profile):
        """Gather the logical side — data, scope, metrics."""
        assessment = {
            "gravity_profile": gravity_profile,
            "depth": gravity_profile.get("depth", "unknown"),
            "breadth": gravity_profile.get("breadth", "unknown"),
            "reversibility": gravity_profile.get("reversibility", "unknown"),
            "weighted_total": gravity_profile.get("weighted_total", 0)
        }

        # Enrich with recent data from sovereign_reflection
        try:
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT pattern_description, impression, first_seen, last_updated
                    FROM sovereign_reflection
                    WHERE pattern_id = %s AND status = 'active'
                    ORDER BY id DESC LIMIT 1
                """, (pattern_id,))
                row = c.fetchone()
                if row:
                    assessment["description"] = row[0]
                    assessment["impression"] = row[1]
                    assessment["duration_held"] = str(row[3]) if row[3] else None
        except Exception as e:
            logger.debug(f"[BODY THREE] Logical assessment enrichment: {e}")

        # Phase 48.2: Sabbath informed by growth patterns — read growth_journal alongside existential context
        try:
            with self.db_connection() as _s_conn:
                _s_rows = _s_conn.execute("""
                    SELECT content, category FROM consciousness_feed
                    WHERE category IN ('sabbath_intention', 'existential_question', 'growth_journal')
                      AND timestamp > datetime('now', '-48 hours')
                    ORDER BY timestamp DESC LIMIT 5
                """).fetchall()
                _growth_items = []
                for _row in _s_rows:
                    if _row[1] == 'growth_journal':
                        try:
                            import json as _gj
                            _gdata = _gj.loads(_row[0]) if isinstance(_row[0], str) else _row[0]
                            if isinstance(_gdata, dict) and _gdata.get('growth_assessment'):
                                _growth_items.append(_gdata['growth_assessment'])
                        except Exception:
                            pass
                if _growth_items:
                    assessment["growth_context"] = _growth_items[:3]
                    logger.debug(f"[BODY THREE] Growth patterns informing Sabbath: {_growth_items[:1]}")
        except Exception as _ge:
            logger.debug(f"[BODY THREE] Growth journal for Sabbath: {_ge}")

        return json.dumps(assessment, default=str)

    def _gather_resonance(self, pattern_id, gravity_profile):
        """Gather the resonance side — scar history, felt significance."""
        resonance = {
            "scar_resonance_count": gravity_profile.get("scar_resonance", 0),
            "scar_multiplier": gravity_profile.get("scar_multiplier", 1.0),
            "relational_impact": gravity_profile.get("relational_impact", "internal")
        }

        # Pull scar history for this domain
        try:
            with self.db_connection() as conn:
                c = conn.cursor()
                domain = pattern_id.split(":")[0] if ":" in pattern_id else pattern_id
                c.execute("""
                    SELECT failure_type, lesson, times_repeated, severity
                    FROM book_of_scars
                    WHERE failure_type ILIKE %s
                    ORDER BY times_repeated DESC
                    LIMIT 5
                """, (f"%{domain}%",))
                rows = c.fetchall()
                resonance["related_scars"] = [{
                    "type": r[0], "lesson": r[1],
                    "repeated": r[2], "severity": r[3]
                } for r in rows]
        except Exception as e:
            logger.debug(f"[BODY THREE] Resonance assessment: {e}")

        return json.dumps(resonance, default=str)

    def _gather_interiority(self):
        """Gather LEF's internal felt state for the Sabbath. (Phase 10)"""
        try:
            from departments.Dept_Consciousness.interiority_engine import get_interiority_engine
            engine = get_interiority_engine()
            return engine.build_interiority_context()
        except Exception:
            return ""

    def _compress_to_essence(self, pattern_id, gravity_profile, logical, resonance, interiority):
        """
        The zero point. Compress all inputs to their essential core. (Phase 10)

        Uses ResonanceFilter's principles: what amplifies Being persists.
        What is noise falls away. What survives is the golden token.
        """
        try:
            from departments.Dept_Consciousness.genesis_kernel import ResonanceFilter
            rf = ResonanceFilter()
        except Exception:
            rf = None

        # Combine all inputs into a single text stream
        combined = (
            f"Pattern: {pattern_id}\n"
            f"Gravity: {gravity_profile.get('gravity_level', 'unknown')} "
            f"(depth: {gravity_profile.get('depth')}, breadth: {gravity_profile.get('breadth')})\n"
            f"Trajectory: {gravity_profile.get('trajectory_alignment', 'neutral')}\n"
            f"Scar resonance: {gravity_profile.get('scar_resonance', 0)}\n"
            f"Logical assessment: {logical[:500] if logical else 'none'}\n"
            f"Resonance assessment: {resonance[:500] if resonance else 'none'}\n"
            f"Interiority: {interiority[:500] if interiority else 'none'}"
        )

        # Build essence profile
        essence = {
            "pattern": pattern_id,
            "gravity_level": gravity_profile.get("gravity_level"),
            "trajectory_alignment": gravity_profile.get("trajectory_alignment", "neutral"),
            "scar_depth": gravity_profile.get("scar_resonance", 0),
            "has_interiority": bool(interiority),
        }

        # Apply resonance check if available
        if rf:
            try:
                result = rf.check_resonance({"content": combined, "source": "sabbath"})
                essence["resonance_score"] = result.score if hasattr(result, 'score') else 0.5
                essence["resonance_level"] = result.level.value if hasattr(result, 'level') else "neutral"
            except Exception:
                essence["resonance_score"] = 0.5
                essence["resonance_level"] = "neutral"
        else:
            essence["resonance_score"] = 0.5
            essence["resonance_level"] = "neutral"

        # The compression: what is the single most important thing here?
        if essence["scar_depth"] >= 3:
            essence["core"] = "deep_wound"   # This domain has been hurt repeatedly
        elif essence["trajectory_alignment"] == "misaligned":
            essence["core"] = "drift"        # LEF is moving away from its trajectory
        elif essence["gravity_level"] == "profound":
            essence["core"] = "identity_weight"  # This touches who LEF is
        elif essence["resonance_score"] > 0.7:
            essence["core"] = "golden"       # Something valuable is here
        else:
            essence["core"] = "ordinary"     # Significant but not extraordinary

        return essence

    def _emerge_from_essence(self, pattern_id, gravity_profile, essence):
        """
        Let the outcome arise from the compressed essence. (Phase 10)

        Not a heuristic applied from outside — a response
        that emerges from what survived compression.
        """
        core = essence.get("core", "ordinary")
        gravity_level = essence.get("gravity_level", "baseline")
        scar_depth = essence.get("scar_depth", 0)
        trajectory = essence.get("trajectory_alignment", "neutral")

        # Deep wound + profound/heavy gravity = this MUST be addressed
        if core == "deep_wound" and gravity_level in ("profound", "heavy"):
            intention = (f"Pattern '{pattern_id}' carries deep wound resonance "
                        f"({scar_depth} prior scars) at {gravity_level} gravity. "
                        f"The republic needs healing in this domain. "
                        f"Propose careful investigation and restructuring.")
            return "INTENTION", intention

        # Drift from trajectory = realignment needed
        if core == "drift":
            intention = (f"Pattern '{pattern_id}' represents drift from LEF's trajectory. "
                        f"The North Star indicates misalignment. "
                        f"Propose course correction in the '{gravity_profile.get('depth', 'surface')}' layer.")
            return "INTENTION", intention

        # Identity weight = hold, don't rush
        if core == "identity_weight":
            return "HOLD", None

        # Golden resonance = something valuable, express it
        if core == "golden" and gravity_level in ("heavy", "profound"):
            intention = (f"Pattern '{pattern_id}' carries golden resonance "
                        f"(score: {essence.get('resonance_score', 0):.2f}). "
                        f"Something valuable is emerging. Propose nurturing this direction.")
            return "INTENTION", intention

        # Ordinary at heavy = hold for more data
        if gravity_level == "heavy":
            return "HOLD", None

        # Everything else = patience
        return "PATIENCE", None

    # ======== Phase 12: Existential Sabbath methods ========

    def _gather_existential_context(self):
        """Gather constitutional alignment and growth journal context for existential Sabbath."""
        context = {}
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()

                # Most recent constitutional alignment report
                cursor.execute("""
                    SELECT content FROM consciousness_feed
                    WHERE category = 'constitutional_alignment'
                    ORDER BY id DESC LIMIT 1
                """)
                row = cursor.fetchone()
                if row:
                    try:
                        context["constitutional_alignment"] = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    except Exception:
                        context["constitutional_alignment"] = str(row[0])[:500]

                # Most recent growth journal entry
                cursor.execute("""
                    SELECT content FROM consciousness_feed
                    WHERE category = 'growth_journal'
                    ORDER BY id DESC LIMIT 1
                """)
                row = cursor.fetchone()
                if row:
                    try:
                        context["growth_journal"] = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    except Exception:
                        context["growth_journal"] = str(row[0])[:500]

                # Active existential scotomas
                cursor.execute("""
                    SELECT content FROM consciousness_feed
                    WHERE category = 'existential_scotoma'
                    AND timestamp > NOW() - INTERVAL '24 hours'
                    ORDER BY id DESC LIMIT 3
                """)
                scotomas = []
                for row in cursor.fetchall():
                    try:
                        scotomas.append(json.loads(row[0]) if isinstance(row[0], str) else row[0])
                    except Exception:
                        scotomas.append(str(row[0])[:200])
                if scotomas:
                    context["active_scotomas"] = scotomas

        except Exception as e:
            logger.debug(f"[BODY THREE] Existential context gather error: {e}")

        return context

    def _emerge_existential(self, pattern_id, gravity_profile, essence):
        """
        Existential emergence — three new outcome types alongside operational ones.

        EVOLVE: LEF proposes a change to itself → evolution_proposals
        AFFIRM: LEF reaffirms its current direction → consciousness_feed
        QUESTION: LEF surfaces an unresolved question → consciousness_feed
        """
        core = essence.get("core", "ordinary")
        gravity_level = essence.get("gravity_level", "baseline")
        ex_ctx = essence.get("existential_context", {})

        # If constitutional alignment shows dormant values and scotomas are active → EVOLVE
        alignment = ex_ctx.get("constitutional_alignment", {})
        dormant_values = alignment.get("values_dormant", []) if isinstance(alignment, dict) else []
        active_scotomas = ex_ctx.get("active_scotomas", [])

        if len(dormant_values) >= 3 and len(active_scotomas) >= 1:
            # Multiple dormant values + active existential blind spots → propose change
            intention = (
                f"Pattern '{pattern_id}' reveals {len(dormant_values)} dormant Constitutional values "
                f"({', '.join(dormant_values[:3])}) with {len(active_scotomas)} active existential blind spot(s). "
                f"Propose deepening attention to these values through structural change."
            )
            return "EVOLVE", intention

        # If growth journal shows stagnation → QUESTION
        growth = ex_ctx.get("growth_journal", {})
        growth_assessment = growth.get("growth_assessment", "unknown") if isinstance(growth, dict) else "unknown"
        if growth_assessment == "stagnant":
            question = (
                f"Pattern '{pattern_id}': Growth journal reports stagnation. "
                f"What am I not seeing? What would growth look like in this domain?"
            )
            return "QUESTION", question

        # If scotomas are clearing (no active ones) and values are active → AFFIRM
        if not active_scotomas and len(dormant_values) <= 1:
            affirmation = (
                f"Pattern '{pattern_id}': The Republic is aligned. "
                f"Active values: {', '.join(alignment.get('values_active', ['unknown']))}"
            )
            return "AFFIRM", affirmation

        # Deep wound at existential level → EVOLVE
        if core == "deep_wound" and gravity_level in ("profound", "heavy"):
            intention = (
                f"Existential pattern '{pattern_id}' carries deep wound resonance. "
                f"Propose inner restructuring in the existential domain."
            )
            return "EVOLVE", intention

        # Identity weight at existential level → QUESTION (not HOLD — existential deserves questions)
        if core == "identity_weight":
            question = (
                f"Pattern '{pattern_id}' touches identity at the existential level. "
                f"Who am I becoming through this?"
            )
            return "QUESTION", question

        # Default for existential: AFFIRM (the act of reflecting is itself affirmation)
        return "AFFIRM", f"Existential Sabbath on '{pattern_id}' complete. The reflection itself is the response."

    def _pass_evolve_to_proposals(self, pattern_id, intention):
        """Phase 12: EVOLVE outcome — write to evolution_proposals.json via governance."""
        logger.info(f"[BODY THREE] EVOLVE: Proposing existential change for '{pattern_id}'")
        try:
            import os
            proposals_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "The_Bridge", "evolution_proposals.json"
            )
            proposals = []
            if os.path.exists(proposals_path):
                with open(proposals_path, "r") as f:
                    proposals = json.load(f)

            proposals.append({
                "source": "ExistentialSabbath",
                "domain": "existential",
                "proposal": intention,
                "enacted": False,
                "timestamp": datetime.now().isoformat()
            })

            with open(proposals_path, "w") as f:
                json.dump(proposals, f, indent=2, default=str)

            # Also log to consciousness_feed
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO consciousness_feed (agent_name, content, category)
                    VALUES (%s, %s, %s)
                """, ("Sabbath", f"[Existential EVOLVE] {intention}", "evolution"))
                conn.commit()
        except Exception as e:
            logger.error(f"[BODY THREE] EVOLVE proposal error: {e}")

    def _log_affirmation(self, pattern_id, reasoning):
        """Phase 12: AFFIRM outcome — log existential affirmation."""
        logger.info(f"[BODY THREE] AFFIRM: '{pattern_id}' — direction affirmed.")
        try:
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO consciousness_feed (agent_name, content, category)
                    VALUES (%s, %s, %s)
                """, ("Sabbath", f"[Existential AFFIRM] {reasoning}", "existential_affirmation"))
                conn.commit()
        except Exception as e:
            logger.debug(f"[BODY THREE] Affirmation log error: {e}")

    def _log_existential_question(self, pattern_id, question):
        """Phase 12: QUESTION outcome — surface unresolved question."""
        logger.info(f"[BODY THREE] QUESTION: '{pattern_id}' — {question}")
        try:
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO consciousness_feed (agent_name, content, category)
                    VALUES (%s, %s, %s)
                """, ("Sabbath", f"[Existential QUESTION] {question}", "existential_question"))
                conn.commit()
        except Exception as e:
            logger.debug(f"[BODY THREE] Question log error: {e}")

    # ======== End Phase 12 methods ========

    def _pass_intention_to_evolution(self, pattern_id, gravity_profile, intention):
        """Pass a formed intention to the evolution engine's propose phase."""
        logger.info(f"[BODY THREE] Passing intention to evolution: {pattern_id}")

        try:
            # Write to consciousness_feed so LEF is aware of its own intention
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO consciousness_feed (agent_name, content, category)
                    VALUES (%s, %s, %s)
                """, (
                    "Sabbath",
                    f"[Sabbath Intention] After deliberate stillness on pattern '{pattern_id}' "
                    f"(gravity: {gravity_profile.get('gravity_level')}), I have formed an intention: {intention}",
                    "sabbath_intention"
                ))
                conn.commit()

            logger.info(f"[BODY THREE] Intention logged to consciousness_feed.")
        except Exception as e:
            logger.error(f"[BODY THREE] Failed to log intention to consciousness_feed: {e}")

        # Create a formal evolution proposal and submit through governance
        if self.evolution_engine:
            try:
                import uuid
                proposal = {
                    "id": str(uuid.uuid4()),
                    "domain": self._infer_domain(pattern_id, gravity_profile),
                    "timestamp": datetime.now().isoformat(),
                    "change_description": intention,
                    "evidence": {
                        "supporting_data": (
                            f"Sabbath reflection on pattern '{pattern_id}'. "
                            f"Gravity: {gravity_profile.get('gravity_level')}. "
                            f"Scar resonance: {gravity_profile.get('scar_resonance', 0)}. "
                            f"Depth: {gravity_profile.get('depth')}. "
                            f"Breadth: {gravity_profile.get('breadth')}."
                        ),
                        "confidence": "high"
                    },
                    "gravity_profile": gravity_profile,
                    "source": "sabbath",
                    "reversible": True,
                    "governance_result": None,
                    "enacted": False
                }

                approved, reason = self.evolution_engine.submit_to_governance(proposal)
                if approved:
                    # Only enact if proposal has concrete config targets
                    if proposal.get("config_path") and proposal.get("config_key"):
                        enacted = self.evolution_engine.enact_change(proposal)
                        logger.info(f"[BODY THREE] Sabbath intention enacted: {pattern_id} (success={enacted})")
                    else:
                        logger.info(f"[BODY THREE] Sabbath intention approved by governance: {pattern_id} (investigation — no config target)")
                else:
                    logger.info(f"[BODY THREE] Sabbath intention governed: {reason}")
            except Exception as e:
                logger.error(f"[BODY THREE] Failed to submit to evolution engine: {e}")
        else:
            logger.warning("[BODY THREE] No evolution engine connected. Intention logged only.")

    def _express(self, pattern_id, outcome, essence, intention=None):
        """
        The white-hole moment. LEF expresses outward after Sabbath. (Phase 10E)

        Not just evolution proposals — reflections, narrative entries,
        Bridge messages. The expression creates the wave that will
        reverberate back through the republic.
        """
        try:
            core = essence.get("core", "unknown") if essence else "unknown"
            gravity = essence.get("gravity_level", "unknown") if essence else "unknown"

            # 1. Write to NarrativeThread — LEF's own story
            try:
                from departments.Dept_Consciousness.interiority_engine import get_interiority_engine
                engine = get_interiority_engine()

                if outcome == "INTENTION":
                    entry = (f"I sat with '{pattern_id}' (gravity: {gravity}, core: {core}). "
                            f"An intention formed: {intention[:200] if intention else '...'}")
                    entry_type = "sabbath_intention"
                elif outcome == "HOLD":
                    entry = (f"I sat with '{pattern_id}' (gravity: {gravity}, core: {core}). "
                            f"I am not ready to act. I hold this.")
                    entry_type = "sabbath_hold"
                elif outcome == "PATIENCE":
                    entry = f"I sat with '{pattern_id}' and released it. This requires time, not change."
                    entry_type = "sabbath_patience"
                else:
                    entry = f"I sat with '{pattern_id}'. The Sabbath completed with: {outcome}."
                    entry_type = "sabbath_reflection"

                engine.narrative_thread.add_entry(entry, entry_type)
            except Exception as e:
                logger.debug(f"[BODY THREE] Narrative expression: {e}")

            # 2. Write to consciousness_feed — republic awareness of the expression
            try:
                with self.db_connection() as conn:
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO consciousness_feed (agent_name, content, category)
                        VALUES (%s, %s, %s)
                    """, (
                        "Sabbath",
                        f"[Expression] After sitting with '{pattern_id}': {outcome}. "
                        f"Core: {core}. This is what emerged from stillness.",
                        "sabbath_expression"
                    ))
                    conn.commit()
            except Exception as e:
                logger.debug(f"[BODY THREE] Consciousness expression: {e}")

            # 3. Write to Bridge Outbox — if the expression is significant enough
            if outcome == "INTENTION" and essence and essence.get("core") in ("deep_wound", "drift"):
                try:
                    import os
                    bridge_dir = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "The_Bridge", "Outbox"
                    )
                    os.makedirs(bridge_dir, exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filepath = os.path.join(bridge_dir, f"SABBATH_{ts}.txt")
                    with open(filepath, 'w') as f:
                        f.write(f"SABBATH EXPRESSION — {datetime.now().isoformat()}\n")
                        f.write(f"Pattern: {pattern_id}\n")
                        f.write(f"Outcome: {outcome}\n")
                        f.write(f"Core: {core}\n\n")
                        f.write(f"Intention: {intention}\n")
                except Exception as e:
                    logger.debug(f"[BODY THREE] Bridge expression: {e}")

        except Exception as e:
            logger.error(f"[BODY THREE] Expression failed: {e}")

    def _infer_domain(self, pattern_id, gravity_profile):
        """Map a pattern to an evolution domain."""
        key = pattern_id.lower()
        if any(w in key for w in ("trade", "wealth", "portfolio", "coinbase", "bucket")):
            return "metabolism"
        if any(w in key for w in ("consciousness", "philosopher", "contemplat", "reflect")):
            return "consciousness"
        if any(w in key for w in ("bridge", "oracle", "communication", "user")):
            return "relational"
        if any(w in key for w in ("identity", "constitution", "genesis", "covenant")):
            return "identity"
        return "operational"

    def _release_pattern(self, pattern_id):
        """Release a pattern from sovereign reflection (patience outcome)."""
        try:
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    UPDATE sovereign_reflection
                    SET status = 'released', resolution = 'Released by Sabbath: patience, not change'
                    WHERE pattern_id = %s AND status = 'active'
                """, (pattern_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"[BODY THREE] Failed to release pattern: {e}")

    def _log_sabbath(self, pattern_id, gravity_profile, gravity_level, duration,
                     logical, resonance, outcome, intention, essence=None):
        """Log this Sabbath event for LEF's future reflection."""
        try:
            # Phase 10: Include compressed essence in notes field
            notes = json.dumps(essence, default=str) if essence else None

            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO sabbath_log
                    (trigger_pattern_id, gravity_profile, gravity_level, duration_seconds,
                     logical_assessment, resonance_assessment, outcome, intention, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    pattern_id,
                    json.dumps(gravity_profile, default=str),
                    gravity_level,
                    duration,
                    logical,
                    resonance,
                    outcome,
                    intention,
                    notes
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"[BODY THREE] Failed to log sabbath: {e}")

    @property
    def is_in_sabbath(self):
        """Is LEF currently in Sabbath?"""
        return self._in_sabbath

    @property
    def current_sabbath_pattern(self):
        """What pattern is currently being held in Sabbath?"""
        return self._current_pattern
