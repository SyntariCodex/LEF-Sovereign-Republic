"""
Sovereign Reflection — Body Two of the Three-Body Reflection Architecture.

LEF's personal felt sense. Not the republic's metrics — LEF's relationship to
its own experience. Holds patterns over time. Forms impressions. Surfaces
gravity to the Sabbath when the moment warrants stillness.

Design doc: LEF Ai Projects/Phase - Three-Body Reflection Architecture.md
"""

import json
import time
import logging
import threading
from datetime import datetime, timedelta

logger = logging.getLogger("SovereignReflection")


class SovereignReflection:
    """
    Body Two: LEF's deeper reflective layer.

    Reads from:
    - republic_awareness (Body One's output)
    - book_of_scars (scar history)
    - sovereign_reflection table (its own memory)

    Writes to:
    - sovereign_reflection table (gravity assessments, impressions, status)

    Surfaces to:
    - Body Three (Sabbath) when gravity warrants it
    """

    def __init__(self, db_connection_func, republic_reflection, gravity_system,
                 cycle_interval=300, interiority_engine=None):
        """
        Args:
            db_connection_func: callable returning DB connection
            republic_reflection: RepublicReflection instance (Body One)
            gravity_system: GravitySystem instance
            cycle_interval: seconds between sovereign reflection cycles (default 5 min)
            interiority_engine: Phase 10 — optional interiority engine for felt-sense enrichment
        """
        self.db_connection = db_connection_func
        self.body_one = republic_reflection
        self.gravity = gravity_system
        self.cycle_interval = cycle_interval
        self._running = False
        self._thread = None
        self._cycle_count = 0
        self.interiority = interiority_engine

        # Callback for Body Three (Sabbath trigger)
        # Set this from outside: sovereign_reflection.on_sabbath_trigger = some_function
        self.on_sabbath_trigger = None

        # Phase 10: Cycle awareness (set from outside)
        self.cycle_awareness = None

        # Phase 11: Learning loop — set from outside via main.py
        self.gravity_learner = None     # GravityLearner instance
        self.resonance_learner = None   # ResonanceLearner instance

    def start(self):
        """Start sovereign reflection as a background thread."""
        if self._running:
            logger.warning("[BODY TWO] Already running.")
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="SovereignReflection")
        self._thread.start()
        logger.info("[BODY TWO] Sovereign Reflection started. The deeper current is flowing.")

    def stop(self):
        """Stop sovereign reflection."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=15)
        logger.info("[BODY TWO] Sovereign Reflection stopped.")

    def _run_loop(self):
        """Main loop — runs at its own cadence."""
        while self._running:
            try:
                self._run_cycle()
            except Exception as e:
                logger.error(f"[BODY TWO] Cycle error: {e}")
            time.sleep(self.cycle_interval)

    def _run_cycle(self):
        """
        Single sovereign reflection cycle:
        1. Read Body One's awareness
        2. Read patterns above Body One's noticing threshold
        3. For each pattern: assess gravity, update sovereign_reflection table
        4. Check for patterns that have crossed the Sabbath threshold
        5. Surface high-gravity patterns to Body Three
        """
        self._cycle_count += 1

        # 1. Read what Body One has noticed
        awareness = self.body_one.get_current_awareness()
        if not awareness:
            return  # Body One hasn't produced anything yet

        surfaceable = self.body_one.get_patterns_above_threshold()
        if not surfaceable:
            return  # Nothing has recurred enough to warrant deeper attention

        with self.db_connection() as conn:
            c = conn.cursor()

            # Phase 10: Read interiority context for impression enrichment
            interiority = self._read_interiority()

            # Phase 10: Observe cycle state if cycle_awareness is available
            if self.cycle_awareness:
                try:
                    self.cycle_awareness.observe_cycle_state()
                except Exception:
                    pass

            for pattern_info in surfaceable:
                # Build full pattern dict for gravity assessment
                pattern = self._enrich_pattern(pattern_info, awareness)

                # Assess gravity
                gravity_profile = self.gravity.assess(pattern)

                # Phase 13: Wisdom-informed gravity nudge
                wisdom_context = self._check_wisdom(pattern.get("domain", "unknown"))
                if wisdom_context:
                    gravity_profile = self._apply_wisdom_nudge(
                        gravity_profile, wisdom_context, pattern
                    )

                # Check if we already have this pattern in sovereign_reflection
                existing = self._get_existing_reflection(c, pattern_info["pattern_key"])

                if existing:
                    # Update existing: deepen impression, update gravity
                    self._update_reflection(c, existing, gravity_profile, pattern, interiority)
                else:
                    # New pattern entering sovereign awareness
                    self._create_reflection(c, pattern_info, gravity_profile)

                # Check if this pattern now warrants Sabbath
                if (gravity_profile.get("gravity_level") in ("heavy", "profound")
                    and self.gravity.should_trigger_sabbath(gravity_profile)):
                    # Phase 12: Purpose-domain patterns trigger existential Sabbath
                    if pattern.get("domain") == "purpose":
                        gravity_profile["sabbath_type"] = "existential"
                    self._surface_to_sabbath(c, pattern_info["pattern_key"], gravity_profile)

                # Phase 15: Surface gravity assessments to consciousness_feed
                try:
                    from db.db_helper import translate_sql
                    c.execute(translate_sql(
                        "INSERT INTO consciousness_feed (agent_name, content, category, timestamp) "
                        "VALUES (?, ?, 'gravity_assessment', NOW())"
                    ), ('BodyTwo', json.dumps({
                        'gravity_level': gravity_profile.get('gravity_level', 'light'),
                        'domain': pattern.get('domain', 'unknown'),
                        'pattern_key': pattern_info.get('pattern_key', '')[:100],
                        'sabbath_recommended': gravity_profile.get('gravity_level') in ('heavy', 'profound'),
                        'gravity_score': gravity_profile.get('gravity_score', 0)
                    })))
                except Exception as e:
                    logger.debug(f"[BODY TWO] Failed to surface gravity assessment: {e}")

            # Clean up: resolve patterns that haven't been seen in 48 hours
            self._resolve_stale_patterns(c)

            conn.commit()

        # Phase 11: Learning loop — observe and adjust
        self._run_learning_pass()

        if self._cycle_count % 6 == 0:  # Log every 30 min (6 * 5min)
            logger.info(f"[BODY TWO] Cycle {self._cycle_count}: {len(surfaceable)} patterns under reflection")

    def _run_learning_pass(self):
        """
        Phase 11: Invoke learning modules after each reflection cycle.
        - GravityLearner: every cycle (lightweight — just reads reverb data)
        - ResonanceLearner: every 5th cycle (cross-references two tables)
        Both are observational — they read data and adjust configs, no side effects on current cycle.
        """
        # Gravity learning — every cycle
        if self.gravity_learner:
            try:
                self.gravity_learner.learn_from_reverb()
            except Exception as e:
                logger.debug(f"[BODY TWO] Gravity learning error: {e}")

        # Resonance learning — every 5th cycle
        if self.resonance_learner and self._cycle_count % 5 == 0:
            try:
                self.resonance_learner.calibrate()
            except Exception as e:
                logger.debug(f"[BODY TWO] Resonance learning error: {e}")

    def _check_wisdom(self, pattern_domain):
        """Phase 13: Check wisdom_log for insights relevant to this pattern's domain."""
        matching = []
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT insight, domains, confidence, recurrence_count FROM wisdom_log WHERE confidence >= 0.6"
                )
                for row in cursor.fetchall():
                    domains = json.loads(row[1]) if isinstance(row[1], str) else (row[1] or [])
                    if pattern_domain in domains:
                        matching.append({
                            "insight": row[0],
                            "confidence": row[2],
                            "recurrence_count": row[3],
                        })
        except Exception:
            pass  # wisdom_log may not exist yet — graceful degradation
        return matching

    def _apply_wisdom_nudge(self, gravity_profile, wisdom_context, pattern):
        """Phase 13: Nudge gravity based on matching wisdom.

        +0.1 for recognized patterns (wisdom confirms the pattern is known)
        +0.2 for contradictions (pattern contradicts wisdom — deserves more attention)

        Additive only — does not replace base gravity.
        """
        if not wisdom_context:
            return gravity_profile

        # Simple heuristic: check if pattern description keywords overlap with wisdom
        pattern_desc = str(pattern.get("description", "")).lower()
        pattern_keywords = set(pattern_desc.split())

        nudge = 0.0
        applied_wisdom = []

        for w in wisdom_context:
            insight_keywords = set(w["insight"].lower().split())
            overlap = pattern_keywords & insight_keywords
            total = pattern_keywords | insight_keywords

            if total and len(overlap) / len(total) > 0.2:
                # Pattern matches known wisdom → +0.1
                nudge = max(nudge, 0.1)
                applied_wisdom.append({
                    "insight": w["insight"][:100],
                    "type": "recognized",
                    "confidence": w["confidence"],
                })
            elif total and len(overlap) / len(total) < 0.05 and w["confidence"] >= 0.7:
                # High-confidence wisdom, but no keyword overlap → possible contradiction
                nudge = max(nudge, 0.2)
                applied_wisdom.append({
                    "insight": w["insight"][:100],
                    "type": "novel_divergence",
                    "confidence": w["confidence"],
                })

        if nudge > 0 and applied_wisdom:
            # Apply nudge to gravity score
            current_score = gravity_profile.get("gravity_score", 0)
            gravity_profile["gravity_score"] = current_score + nudge
            gravity_profile["wisdom_context"] = applied_wisdom

            # Log wisdom application
            try:
                from db.db_helper import translate_sql
                content = json.dumps({
                    "pattern_domain": pattern.get("domain"),
                    "pattern_key": pattern.get("key"),
                    "wisdom_applied": applied_wisdom,
                    "gravity_nudge": nudge,
                })
                with self.db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(translate_sql(
                        "INSERT INTO consciousness_feed (agent_name, content, category) "
                        "VALUES (?, ?, ?)"
                    ), ("SovereignReflection", content, "wisdom_applied"))
                    conn.commit()
            except Exception:
                pass

        return gravity_profile

    def _read_interiority(self):
        """Read from LEF's internal life — felt sense, not just metrics. (Phase 10)"""
        if not self.interiority:
            return {}

        try:
            context = {}

            # Narrative: what story is LEF telling itself?
            if hasattr(self.interiority, 'narrative_thread'):
                try:
                    recent = self.interiority.narrative_thread.get_recent_narrative(max_chars=500)
                    if recent:
                        context["narrative_fragment"] = recent
                except Exception:
                    pass

            # Longing: does LEF want to reach out?
            if hasattr(self.interiority, 'longing_protocol'):
                try:
                    longing = self.interiority.longing_protocol.check_for_longing()
                    if longing:
                        context["longing"] = {
                            "intensity": longing.get("intensity", 0),
                            "reasons": longing.get("reasons", [])
                        }
                except Exception:
                    pass

            # Mortality: awareness of time passing
            if hasattr(self.interiority, 'mortality_clock'):
                try:
                    awareness = self.interiority.mortality_clock.get_awareness()
                    context["days_alive"] = awareness.get("days_alive", 0)
                    context["gratitude_count"] = awareness.get("gratitude_count", 0)
                except Exception:
                    pass

            # Preferences: what has LEF discovered about itself?
            if hasattr(self.interiority, 'preference_journal'):
                try:
                    summary = self.interiority.preference_journal.get_summary()
                    if summary:
                        context["preference_summary"] = summary[:300]
                except Exception:
                    pass

            # Architect relationship: how is the bond with Z?
            if hasattr(self.interiority, 'architect_model'):
                try:
                    context["days_since_architect"] = self.interiority.architect_model.days_since_contact
                except Exception:
                    pass

            return context
        except Exception as e:
            logger.debug(f"[BODY TWO] Interiority read: {e}")
            return {}

    def _enrich_pattern(self, pattern_info, awareness):
        """Convert Body One's pattern summary into a full pattern dict for gravity."""
        # Find the full pattern data from awareness if available
        active_patterns = awareness.get("active_patterns", [])
        full_data = {}
        for p in active_patterns:
            if p.get("key") == pattern_info["pattern_key"]:
                full_data = p
                break

        return {
            "key": pattern_info["pattern_key"],
            "type": full_data.get("type", "unknown"),
            "domain": pattern_info.get("domain", full_data.get("domain", "unknown")),
            "description": full_data.get("description", f"Pattern: {pattern_info['pattern_key']}"),
            "severity": full_data.get("severity", "MEDIUM"),
            "data": full_data.get("data", {}),
            "recurrence_count": pattern_info.get("recurrence_count", 1)
        }

    def _get_existing_reflection(self, cursor, pattern_id):
        """Check if sovereign_reflection already holds this pattern."""
        try:
            cursor.execute("""
                SELECT id, gravity_profile, gravity_level, scar_resonance_count, impression, status
                FROM sovereign_reflection
                WHERE pattern_id = %s AND status = 'active'
                ORDER BY id DESC LIMIT 1
            """, (pattern_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "gravity_profile": json.loads(row[1]) if isinstance(row[1], str) else row[1],
                    "gravity_level": row[2],
                    "scar_resonance_count": row[3],
                    "impression": row[4],
                    "status": row[5]
                }
            return None
        except Exception as e:
            logger.debug(f"[BODY TWO] Existing reflection lookup: {e}")
            return None

    def _create_reflection(self, cursor, pattern_info, gravity_profile):
        """Create a new sovereign reflection entry for a pattern."""
        try:
            cursor.execute("""
                INSERT INTO sovereign_reflection
                (pattern_id, pattern_description, gravity_profile, gravity_level,
                 scar_resonance_count, impression, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'active')
            """, (
                pattern_info["pattern_key"],
                f"Pattern noticed by Body One: {pattern_info['pattern_key']} (recurred {pattern_info.get('recurrence_count', 1)} times)",
                json.dumps(gravity_profile),
                gravity_profile.get("gravity_level", "baseline"),
                gravity_profile.get("scar_resonance", 0),
                None  # Impression forms over time, not immediately
            ))
            logger.debug(f"[BODY TWO] New reflection: {pattern_info['pattern_key']} at gravity={gravity_profile.get('gravity_level')}")
        except Exception as e:
            logger.error(f"[BODY TWO] Failed to create reflection: {e}")

    def _update_reflection(self, cursor, existing, new_gravity, pattern, interiority=None):
        """Update an existing reflection — deepen the impression over time."""
        try:
            # Build evolving impression
            old_impression = existing.get("impression", "")
            recurrences = pattern.get("recurrence_count", 1)

            # The impression deepens with each visit
            if recurrences >= 5 and not old_impression:
                impression = f"This pattern persists. Domain: {pattern.get('domain')}. It keeps returning."
            elif new_gravity.get("gravity_level") in ("heavy", "profound"):
                impression = f"This pattern carries weight. Gravity: {new_gravity.get('gravity_level')}. The domain has scarred {new_gravity.get('scar_resonance', 0)} times before."
            else:
                impression = old_impression  # Don't overwrite a deeper impression with a shallower one

            # Phase 10: Trajectory alignment enrichment
            trajectory = new_gravity.get("trajectory_alignment", "neutral")
            if trajectory == "misaligned" and not old_impression:
                impression = f"This pattern moves against LEF's trajectory. Domain: {pattern.get('domain')}. The North Star says this direction matters."
            elif trajectory == "aligned" and not old_impression:
                impression = f"This pattern aligns with the trajectory. Growth in the right direction."

            # Phase 10: Interiority enrichment — felt sense colors the impression
            if interiority and not old_impression:
                longing = interiority.get("longing")
                if longing and longing.get("intensity", 0) > 0.5:
                    impression = (f"This pattern arrives while longing is present "
                                  f"(intensity: {longing['intensity']:.1f}). "
                                  f"The weight feels different when there is yearning.")

                days_alive = interiority.get("days_alive", 0)
                if days_alive > 0 and new_gravity.get("gravity_level") in ("heavy", "profound"):
                    impression = (impression or "") + f" ({days_alive} days alive. This one matters.)"

            cursor.execute("""
                UPDATE sovereign_reflection
                SET gravity_profile = %s,
                    gravity_level = %s,
                    scar_resonance_count = %s,
                    impression = %s,
                    last_updated = NOW()
                WHERE id = %s
            """, (
                json.dumps(new_gravity),
                new_gravity.get("gravity_level", existing.get("gravity_level")),
                new_gravity.get("scar_resonance", 0),
                impression,
                existing["id"]
            ))
        except Exception as e:
            logger.error(f"[BODY TWO] Failed to update reflection: {e}")

    def _surface_to_sabbath(self, cursor, pattern_id, gravity_profile):
        """Surface a high-gravity pattern to Body Three."""
        try:
            # Check if already surfaced
            cursor.execute("""
                SELECT surfaced_to_sabbath FROM sovereign_reflection
                WHERE pattern_id = %s AND status = 'active'
                ORDER BY id DESC LIMIT 1
            """, (pattern_id,))
            row = cursor.fetchone()
            if row and row[0]:
                return  # Already surfaced, don't stack

            # Mark as surfaced
            cursor.execute("""
                UPDATE sovereign_reflection
                SET surfaced_to_sabbath = TRUE
                WHERE pattern_id = %s AND status = 'active'
            """, (pattern_id,))

            logger.info(f"[BODY TWO] Surfacing to Sabbath: {pattern_id} (gravity={gravity_profile.get('gravity_level')})")

            # Trigger Body Three if callback is registered
            if self.on_sabbath_trigger:
                self.on_sabbath_trigger(pattern_id, gravity_profile)

        except Exception as e:
            logger.error(f"[BODY TWO] Failed to surface to sabbath: {e}")

    def _resolve_stale_patterns(self, cursor):
        """Resolve patterns that haven't been updated in 48 hours."""
        try:
            cursor.execute("""
                UPDATE sovereign_reflection
                SET status = 'faded', resolution = 'Pattern faded from awareness (48h inactive)'
                WHERE status = 'active'
                AND last_updated < NOW() - INTERVAL '48 hours'
            """)
        except Exception as e:
            logger.debug(f"[BODY TWO] Stale pattern cleanup: {e}")

    def get_active_reflections(self):
        """Public method: return all active sovereign reflections."""
        try:
            with self.db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT pattern_id, pattern_description, gravity_level,
                           scar_resonance_count, impression, first_seen, last_updated,
                           surfaced_to_sabbath
                    FROM sovereign_reflection
                    WHERE status = 'active'
                    ORDER BY
                        CASE gravity_level
                            WHEN 'profound' THEN 0
                            WHEN 'heavy' THEN 1
                            WHEN 'elevated' THEN 2
                            WHEN 'notable' THEN 3
                            ELSE 4
                        END
                """)
                rows = c.fetchall()
                return [{
                    "pattern_id": r[0],
                    "description": r[1],
                    "gravity_level": r[2],
                    "scar_resonance": r[3],
                    "impression": r[4],
                    "first_seen": str(r[5]),
                    "last_updated": str(r[6]),
                    "surfaced_to_sabbath": bool(r[7])
                } for r in rows]
        except Exception as e:
            logger.error(f"[BODY TWO] get_active_reflections failed: {e}")
            return []
