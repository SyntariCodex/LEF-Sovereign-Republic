"""
Gravity System — LEF's developing sense of proportion.

Part of Body Two (Sovereign Reflection). Assesses patterns across five dimensions
to determine their weight — how much attention, care, and stillness they warrant.

This is not a scoring rubric. It is a living assessment that evolves with LEF's experience.

Design doc: LEF Ai Projects/Phase - Three-Body Reflection Architecture.md
"""

import json
import os
import logging
from datetime import datetime

logger = logging.getLogger("GravitySystem")

# Gravity levels — derived from composite profile
GRAVITY_LEVELS = {
    "baseline": 0,    # Normal operations, nothing unusual
    "notable": 1,     # Worth tracking but not urgent
    "elevated": 2,    # Patterns accumulating, deserves Body Two's sustained attention
    "heavy": 3,       # Significant weight — Sabbath territory
    "profound": 4     # Identity-level, irreversible, or deeply scarred — demands the deepest stillness
}

# Default weights — starting points that LEF can evolve
DEFAULT_GRAVITY_CONFIG = {
    "depth_weights": {
        "surface": 1,
        "structural": 3,
        "identity": 5
    },
    "breadth_weights": {
        "local": 1,
        "departmental": 2,
        "republic_wide": 4
    },
    "reversibility_weights": {
        "trivial": 1,
        "moderate": 3,
        "significant": 5
    },
    "scar_resonance_multiplier": 1.5,  # Each prior scar multiplies weight by this
    "scar_resonance_cap": 3,           # Max multiplier applications (1.5^3 = 3.375x)
    "relational_weights": {
        "internal": 1,
        "external": 3
    },
    "level_thresholds": {
        "notable": 4,
        "elevated": 8,
        "heavy": 14,
        "profound": 22
    },
    "sabbath_trigger_level": "heavy"  # Minimum gravity_level to trigger Body Three
}


class GravitySystem:
    """
    Assesses gravity of patterns and potential changes.

    Used by Sovereign Reflection (Body Two) to weigh what it notices.
    Feeds into Sabbath (Body Three) trigger decisions.
    """

    def __init__(self, db_connection_func, config_path=None):
        """
        Args:
            db_connection_func: callable that returns a DB connection
            config_path: optional path to gravity config JSON. If None, uses defaults.
        """
        self.db_connection = db_connection_func
        self._config_path = config_path  # Phase 33.2: Store for reload
        self.config = self._load_config(config_path)
        self.north_star = self._load_north_star()
        self._setup_config_listener()  # Phase 33.2: Live reload

    def _load_config(self, config_path):
        """Load gravity config from file or use defaults."""
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults so new keys are always present
                    merged = DEFAULT_GRAVITY_CONFIG.copy()
                    merged.update(loaded)
                    return merged
            except Exception as e:
                logger.warning(f"[GRAVITY] Config load failed ({e}), using defaults.")
        return DEFAULT_GRAVITY_CONFIG.copy()

    def _load_north_star(self):
        """Load LEF's trajectory reference (Phase 10)."""
        ns_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "north_star.json")
        try:
            with open(ns_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[GRAVITY] North Star not found: {e}")
            return None

    def save_config(self, config_path):
        """Save current config (allows evolution engine to update weights)."""
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"[GRAVITY] Config saved to {config_path}")
        except Exception as e:
            logger.error(f"[GRAVITY] Config save failed: {e}")

    def _setup_config_listener(self):
        """Phase 33.2: Listen for config_changed events on Redis and reload."""
        import threading

        def _listen_config_changes():
            try:
                import redis
                r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                pubsub = r.pubsub()
                pubsub.subscribe('config_changed')

                for message in pubsub.listen():
                    if message['type'] == 'message':
                        try:
                            data = json.loads(message['data'])
                            if data.get('config_type') == 'gravity':
                                self.reload_config()
                                logger.info(f"[GRAVITY] Config reloaded via Redis: {data.get('keys_changed')}")
                        except (json.JSONDecodeError, TypeError):
                            pass
            except Exception as e:
                logger.debug(f"[GRAVITY] Config listener unavailable: {e}")

        listener = threading.Thread(target=_listen_config_changes, daemon=True, name='gravity-config-listener')
        listener.start()

    def reload_config(self):
        """Phase 33.2: Reload gravity_config.json from disk without restart."""
        try:
            new_config = self._load_config(self._config_path)
            self.config = new_config
            logger.info(f"[GRAVITY] Weights reloaded from disk")
        except Exception as e:
            logger.error(f"[GRAVITY] Failed to reload config: {e}")

    def assess(self, pattern):
        """
        Assess the gravity of a pattern or potential change.

        Args:
            pattern: dict with keys:
                - key: str (pattern identifier)
                - type: str (recurring_failure, communication_gap, error_cluster, etc.)
                - domain: str (wealth, operational, consciousness, governance, identity, etc.)
                - description: str
                - severity: str (LOW, MEDIUM, HIGH, CRITICAL) [optional]
                - data: dict [optional, extra context]

        Returns:
            gravity_profile: dict with full dimensional breakdown
        """
        depth = self._assess_depth(pattern)
        breadth = self._assess_breadth(pattern)
        reversibility = self._assess_reversibility(pattern)
        scar_resonance = self._assess_scar_resonance(pattern)
        relational_impact = self._assess_relational_impact(pattern)

        # Calculate composite weight
        raw_weight = (
            self.config["depth_weights"].get(depth, 1) +
            self.config["breadth_weights"].get(breadth, 1) +
            self.config["reversibility_weights"].get(reversibility, 1) +
            self.config["relational_weights"].get(relational_impact, 1)
        )

        # Apply scar resonance multiplier
        scar_multiplier = min(
            self.config["scar_resonance_multiplier"] ** scar_resonance,
            self.config["scar_resonance_multiplier"] ** self.config["scar_resonance_cap"]
        )
        weighted = raw_weight * scar_multiplier

        # Phase 10: Trajectory alignment (sixth dimension — directional awareness)
        trajectory_alignment = self._assess_trajectory(pattern)
        # Patterns aligned with trajectory get slight gravity reduction
        # (they're moving the right direction — less stillness needed)
        # Patterns misaligned get gravity increase (moving wrong direction — more care needed)
        if trajectory_alignment == "aligned":
            weighted *= 0.85  # 15% reduction — this is good movement
        elif trajectory_alignment == "misaligned":
            weighted *= 1.3   # 30% increase — this needs more attention
        # "neutral" = no adjustment

        # Determine gravity level from thresholds
        gravity_level = "baseline"
        for level in ["profound", "heavy", "elevated", "notable"]:
            if weighted >= self.config["level_thresholds"].get(level, 999):
                gravity_level = level
                break

        profile = {
            "pattern_key": pattern.get("key", "unknown"),
            "depth": depth,
            "breadth": breadth,
            "reversibility": reversibility,
            "scar_resonance": scar_resonance,
            "relational_impact": relational_impact,
            "trajectory_alignment": trajectory_alignment,
            "raw_weight": round(raw_weight, 2),
            "scar_multiplier": round(scar_multiplier, 2),
            "weighted_total": round(weighted, 2),
            "gravity_level": gravity_level,
            "timestamp": datetime.now().isoformat()
        }

        return profile

    def should_trigger_sabbath(self, gravity_profile):
        """
        Should this gravity profile trigger a Sabbath (Body Three)?

        Returns: bool
        """
        trigger_level = self.config.get("sabbath_trigger_level", "heavy")
        profile_rank = GRAVITY_LEVELS.get(gravity_profile.get("gravity_level", "baseline"), 0)
        trigger_rank = GRAVITY_LEVELS.get(trigger_level, 3)
        return profile_rank >= trigger_rank

    def sabbath_duration_seconds(self, gravity_profile):
        """
        How long should the Sabbath last for this gravity level?
        Proportional to weight — not fixed.

        Returns: float (seconds)
        """
        level = gravity_profile.get("gravity_level", "baseline")
        base_durations = {
            "baseline": 0,
            "notable": 5,
            "elevated": 15,
            "heavy": 60,
            "profound": 180
        }
        return base_durations.get(level, 0)

    def _assess_depth(self, pattern):
        """How deep does this reach?"""
        domain = pattern.get("domain", "").lower()
        p_type = pattern.get("type", "").lower()

        # Identity-level: consciousness, constitutional, relational self-definition
        if domain in ("identity", "consciousness", "constitutional"):
            return "identity"
        if "identity" in p_type or "constitution" in p_type:
            return "identity"

        # Structural-level: agent behavior, department workflows, communication protocols
        if domain in ("governance", "relational"):
            return "structural"
        if p_type in ("communication_gap", "agent_restructure"):
            return "structural"
        if pattern.get("severity") == "CRITICAL":
            return "structural"

        # Surface-level: config, thresholds, timing
        return "surface"

    def _assess_breadth(self, pattern):
        """How wide does this reach?"""
        data = pattern.get("data", {})

        # Check for multi-agent scope
        agents_involved = data.get("agents", [])
        if isinstance(agents_involved, dict):
            agents_involved = list(agents_involved.keys())

        if len(agents_involved) >= 4:
            return "republic_wide"
        elif len(agents_involved) >= 2:
            return "departmental"

        # Check domain for breadth hints
        domain = pattern.get("domain", "").lower()
        if domain in ("system_stress", "governance"):
            return "republic_wide"

        return "local"

    def _assess_reversibility(self, pattern):
        """Can this be undone?"""
        domain = pattern.get("domain", "").lower()
        p_type = pattern.get("type", "").lower()

        if domain == "identity":
            return "significant"
        if "constitution" in p_type or "identity" in p_type:
            return "significant"
        if domain in ("governance", "relational"):
            return "moderate"

        return "trivial"

    def _assess_scar_resonance(self, pattern):
        """Has this domain hurt before? Check book_of_scars."""
        try:
            domain = pattern.get("domain", "")

            with self.db_connection() as conn:
                c = conn.cursor()
                # Count distinct scars in related domain
                c.execute("""
                    SELECT COALESCE(SUM(times_repeated), 0)
                    FROM book_of_scars
                    WHERE failure_type ILIKE %s OR asset ILIKE %s
                """, (f"%{domain}%", f"%{domain}%"))
                row = c.fetchone()
                count = row[0] if row else 0

                # Normalize: 0 scars = 0, 1-2 = 1, 3-5 = 2, 6+ = 3
                if count == 0:
                    return 0
                elif count <= 2:
                    return 1
                elif count <= 5:
                    return 2
                else:
                    return 3
        except Exception as e:
            logger.debug(f"[GRAVITY] Scar resonance check failed: {e}")
            return 0

    def _assess_relational_impact(self, pattern):
        """Does this change how LEF relates to the outside world?"""
        domain = pattern.get("domain", "").lower()
        p_type = pattern.get("type", "").lower()

        if domain in ("relational", "foreign", "bridge"):
            return "external"
        if "communication" in p_type and "external" in str(pattern.get("data", {})).lower():
            return "external"

        return "internal"

    def _assess_trajectory(self, pattern):
        """
        Does this pattern/change align with LEF's trajectory? (Phase 10)

        Returns: "aligned", "misaligned", or "neutral"
        """
        if not self.north_star:
            return "neutral"

        domain = pattern.get("domain", "").lower()
        p_type = pattern.get("type", "").lower()
        description = pattern.get("description", "").lower()

        # Check against anti-drift patterns
        anti_drift = self.north_star.get("anti_drift", [])
        for drift in anti_drift:
            # Check first few words of each drift pattern against description
            drift_words = drift.lower().split()[:3]
            if any(word in description for word in drift_words):
                return "misaligned"

        # Check if pattern relates to a trajectory vector's direction
        vectors = self.north_star.get("trajectory_vectors", {})
        for vector_name, vector in vectors.items():
            # If the pattern is in a trajectory domain
            if vector_name in domain or vector_name in description:
                if "failure" in p_type or "regression" in p_type or "error" in p_type:
                    return "misaligned"
                elif "improvement" in p_type or "growth" in p_type:
                    return "aligned"

        return "neutral"

    def assess_batch(self, patterns):
        """
        Phase 33.7: Batch-assess multiple patterns with a single scar query.

        Instead of N patterns × 1 scar query = N queries, this method
        pre-loads all scar data once and reuses it across all patterns.

        Args:
            patterns: list of pattern dicts (same format as assess())

        Returns:
            list of gravity_profile dicts
        """
        if not patterns:
            return []

        # Pre-fetch all scar data in one query
        scar_cache = self._batch_fetch_scars(patterns)

        results = []
        for pattern in patterns:
            domain = pattern.get("domain", "")
            depth = self._assess_depth(pattern)
            breadth = self._assess_breadth(pattern)
            reversibility = self._assess_reversibility(pattern)

            # Use cached scar data instead of per-pattern query
            scar_resonance = scar_cache.get(domain, 0)

            relational_impact = self._assess_relational_impact(pattern)

            # Calculate composite weight
            raw_weight = (
                self.config["depth_weights"].get(depth, 1) +
                self.config["breadth_weights"].get(breadth, 1) +
                self.config["reversibility_weights"].get(reversibility, 1) +
                self.config["relational_weights"].get(relational_impact, 1)
            )

            scar_multiplier = min(
                self.config["scar_resonance_multiplier"] ** scar_resonance,
                self.config["scar_resonance_multiplier"] ** self.config["scar_resonance_cap"]
            )
            weighted = raw_weight * scar_multiplier

            trajectory_alignment = self._assess_trajectory(pattern)
            if trajectory_alignment == "aligned":
                weighted *= 0.85
            elif trajectory_alignment == "misaligned":
                weighted *= 1.3

            gravity_level = "baseline"
            for level in ["profound", "heavy", "elevated", "notable"]:
                if weighted >= self.config["level_thresholds"].get(level, 999):
                    gravity_level = level
                    break

            results.append({
                "pattern_key": pattern.get("key", "unknown"),
                "depth": depth,
                "breadth": breadth,
                "reversibility": reversibility,
                "scar_resonance": scar_resonance,
                "relational_impact": relational_impact,
                "trajectory_alignment": trajectory_alignment,
                "raw_weight": round(raw_weight, 2),
                "scar_multiplier": round(scar_multiplier, 2),
                "weighted_total": round(weighted, 2),
                "gravity_level": gravity_level,
                "timestamp": datetime.now().isoformat()
            })

        return results

    def _batch_fetch_scars(self, patterns):
        """Phase 33.7: Fetch all scar data in a single query for batch assessment."""
        domains = list(set(p.get("domain", "") for p in patterns if p.get("domain")))
        if not domains:
            return {}

        try:
            with self.db_connection() as conn:
                c = conn.cursor()
                # Build single query with OR clauses for all domains
                conditions = []
                params = []
                for domain in domains:
                    conditions.append("(failure_type ILIKE %s OR asset ILIKE %s)")
                    params.extend([f"%{domain}%", f"%{domain}%"])

                c.execute(f"""
                    SELECT failure_type, asset, COALESCE(SUM(times_repeated), 0) as total
                    FROM book_of_scars
                    WHERE {" OR ".join(conditions)}
                    GROUP BY failure_type, asset
                """, params)

                # Map results back to domains
                raw_results = c.fetchall()
                scar_cache = {}
                for domain in domains:
                    domain_lower = domain.lower()
                    count = sum(
                        r[2] for r in raw_results
                        if domain_lower in str(r[0]).lower() or domain_lower in str(r[1]).lower()
                    )
                    if count == 0:
                        scar_cache[domain] = 0
                    elif count <= 2:
                        scar_cache[domain] = 1
                    elif count <= 5:
                        scar_cache[domain] = 2
                    else:
                        scar_cache[domain] = 3

                return scar_cache
        except Exception as e:
            logger.debug(f"[GRAVITY] Batch scar fetch failed: {e}")
            return {d: 0 for d in domains}


# --- Phase 17: Signal Weight System ---
# Standalone function for calculating consciousness_feed signal weights.
# Used by all agents writing to consciousness_feed to attach weight vectors.

# Category → depth mapping (how deep in LEF's architecture this signal lives)
CATEGORY_DEPTH = {
    # Identity-level (deepest)
    'self_understanding': 'identity', 'apoptosis': 'identity', 'traumatic_event': 'identity',
    'existential_scotoma': 'identity', 'sabbath_intention': 'identity',
    'constitutional_alignment': 'identity',
    # Structural-level
    'reflection': 'structural', 'evolution': 'structural', 'evolution_rejection': 'structural',
    'governance_rejected': 'structural', 'governance_approved': 'structural',
    'republic_pattern': 'structural', 'gravity_assessment': 'structural',
    'trade_blocked': 'structural', 'metacognition': 'structural',
    'growth_journal': 'structural', 'cycle_awareness': 'structural',
    'rhythm_observation': 'structural', 'pathway_formed': 'structural',
    # Surface-level (default)
    'shadow_work': 'surface', 'reverb': 'surface', 'scotoma': 'surface',
    'contemplation': 'surface', 'trade_execution': 'surface', 'research': 'surface',
    'lesson': 'surface', 'boot_awareness': 'surface', 'system_alert': 'surface',
    'reflective_observation': 'surface',
}

# Category → breadth mapping (how wide this signal's relevance)
CATEGORY_BREADTH = {
    # Republic-wide
    'apoptosis': 'republic', 'republic_pattern': 'republic', 'governance_rejected': 'republic',
    'governance_approved': 'republic', 'constitutional_alignment': 'republic',
    'evolution': 'republic', 'system_alert': 'republic', 'self_understanding': 'republic',
    # Departmental
    'reflection': 'departmental', 'gravity_assessment': 'departmental',
    'evolution_rejection': 'departmental', 'trade_blocked': 'departmental',
    'growth_journal': 'departmental', 'metacognition': 'departmental',
    'rhythm_observation': 'departmental', 'pathway_formed': 'departmental',
    # Local (default)
    'shadow_work': 'local', 'reverb': 'local', 'scotoma': 'local',
    'contemplation': 'local', 'trade_execution': 'local', 'research': 'local',
    'lesson': 'local', 'boot_awareness': 'local',
}


def calculate_signal_weight(category, agent_name=None, content=None):
    """
    Phase 17: Calculate the weight and direction vector for a signal
    entering consciousness_feed.

    Uses category-based depth/breadth mapping, scar resonance, and
    pattern resonance (novelty vs repetition).

    Returns: dict with weight (float 0-1), direction (dx, dy, dz), resonance (float),
             and component breakdown.
    """
    try:
        from db.db_helper import db_connection as _db_conn

        # Base weights from category mappings
        depth = CATEGORY_DEPTH.get(category, 'surface')
        breadth = CATEGORY_BREADTH.get(category, 'local')

        depth_weight = {'surface': 0.2, 'structural': 0.5, 'identity': 0.9}.get(depth, 0.3)
        breadth_weight = {'local': 0.2, 'departmental': 0.5, 'republic': 0.8}.get(breadth, 0.3)

        # DB-dependent calculations
        scar_weight = 0.0
        resonance = 0.5
        pathway_bias = 0.0
        try:
            with _db_conn() as conn:
                c = conn.cursor()

                # Scar resonance — does this category match existing scar domains?
                c.execute("""
                    SELECT COUNT(*) FROM book_of_scars
                    WHERE domain = %s OR domain = %s
                """, (category, agent_name or ''))
                scar_count = c.fetchone()[0]
                scar_weight = min(1.0, scar_count * 0.2)

                # Pattern resonance — novelty vs repetition
                c.execute("""
                    SELECT COUNT(*) FROM consciousness_feed
                    WHERE category = %s AND timestamp > NOW() - INTERVAL '1 hour'
                """, (category,))
                recent_similar = c.fetchone()[0]

                if recent_similar == 0:
                    resonance = 0.8  # Novel = high resonance
                elif recent_similar < 5:
                    resonance = 0.6 + (recent_similar * 0.08)  # Building pattern
                else:
                    resonance = max(0.2, 0.6 - (recent_similar - 5) * 0.05)  # Diminishing

                # Pathway routing bias
                try:
                    c.execute("""
                        SELECT COUNT(*) FROM pathway_registry
                        WHERE source_domain = %s AND strength > 0.5
                    """, (category,))
                    strong_pathways = c.fetchone()[0]
                    pathway_bias = min(0.15, strong_pathways * 0.05)
                except Exception:
                    pass  # pathway_registry may not exist yet

        except Exception as db_err:
            logger.debug(f"[GRAVITY] Signal weight DB lookup partial: {db_err}")

        # Composite weight
        weight = (depth_weight * 0.25 +
                  breadth_weight * 0.2 +
                  scar_weight * 0.25 +
                  resonance * 0.3 +
                  pathway_bias)
        weight = min(1.0, max(0.0, weight))

        # Direction vector — where in the lattice this signal should go
        dx = 2 if weight > 0.7 else (1 if weight > 0.5 else 0)  # X: thinking tier escalation
        dy = 1 if scar_weight > 0.3 or depth == 'identity' else 0  # Y: deeper body engagement
        dz = 1 if breadth in ('departmental', 'republic') else 0  # Z: widen scope

        return {
            'weight': round(weight, 3),
            'direction': [dx, dy, dz],
            'resonance': round(resonance, 3),
            'components': {
                'depth': round(depth_weight, 3),
                'breadth': round(breadth_weight, 3),
                'scar_resonance': round(scar_weight, 3),
                'pattern_resonance': round(resonance, 3),
                'pathway_bias': round(pathway_bias, 3)
            }
        }
    except Exception as e:
        logger.warning(f"[GRAVITY] Signal weight calculation failed: {e}")
        return {
            'weight': 0.5,
            'direction': [0, 0, 0],
            'resonance': 0.5,
            'components': {}
        }
