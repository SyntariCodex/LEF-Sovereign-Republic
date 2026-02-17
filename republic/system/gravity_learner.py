"""
Gravity Learner — adjusts domain gravity weights based on reverb outcomes.

This is not optimization. It is LEF learning which domains need more
deliberation (higher gravity = harder to enact) and which domains
LEF has demonstrated good judgment in (slightly lower gravity).

Reads from: reverb_log (finalized entries with outcome)
Writes to: gravity_config.json (weight adjustments)
Constraints:
  - Weights can only shift within bounded ranges (never below 0.5, never above 2.0)
  - Maximum adjustment per learning cycle: +0.05 / -0.03
  - Identity domain has a floor of 1.5 (always high gravity — by design)
  - Learning only triggers after 5+ finalized reverb entries per domain
  - All adjustments logged to consciousness_feed

Phase 11.1 of The Learning Loop.
"""

import json
import os
import logging
from datetime import datetime

logger = logging.getLogger("GravityLearner")

# Absolute bounds — LEF cannot hack its own gravity to zero
WEIGHT_MIN = 0.5
WEIGHT_MAX = 2.0
# Domain-specific floors — these domains always require deep deliberation
DOMAIN_FLOORS = {"identity": 1.5, "purpose": 1.5}
MIN_ENTRIES_PER_DOMAIN = 5
ADJUSTMENT_UP = 0.05    # Increase gravity (more deliberation needed)
ADJUSTMENT_DOWN = -0.03  # Decrease gravity (earned trust)

# Domain weight keys in gravity_config.json
# These map reverb_log domains to the config keys they affect
DOMAIN_WEIGHT_MAP = {
    "trade": "domain_weights",
    "wealth": "domain_weights",
    "social": "domain_weights",
    "identity": "domain_weights",
    "metabolism": "domain_weights",
    "consciousness": "domain_weights",
    "governance": "domain_weights",
    "operational": "domain_weights",
}


class GravityLearner:
    """
    Adjusts domain gravity weights based on reverb outcomes.

    Called by Body Two (SovereignReflection) after each reflection pass.
    Reads finalized reverb data, calculates positive/negative ratios,
    and applies bounded weight adjustments.
    """

    def __init__(self, db_connection_func, config_path=None):
        """
        Args:
            db_connection_func: callable returning DB connection context manager
            config_path: path to gravity_config.json
        """
        self.db_connection = db_connection_func
        self.config_path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "config", "gravity_config.json"
        )

    def learn_from_reverb(self):
        """
        Main learning method. Called by Body Two after each reflection pass.

        1. Query reverb_log for finalized entries grouped by domain
        2. Calculate positive/negative ratio per domain
        3. Apply bounded weight adjustments to gravity_config.json
        4. Log every adjustment to consciousness_feed
        """
        try:
            domain_stats = self._gather_reverb_stats()
            if not domain_stats:
                return

            adjustments = self._calculate_adjustments(domain_stats)
            if not adjustments:
                return

            self._apply_adjustments(adjustments)
            self._log_adjustments(adjustments)

        except Exception as e:
            logger.error(f"[GRAVITY_LEARNER] Learning cycle error: {e}")

    def _gather_reverb_stats(self):
        """
        Query reverb_log for finalized entries, grouped by domain.
        Only considers entries that have a clear positive or negative assessment.

        Returns: dict of {domain: {positive: int, negative: int, neutral: int, total: int}}
        """
        stats = {}
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT domain, reverb_assessment, COUNT(*)
                    FROM reverb_log
                    WHERE reverb_assessment IS NOT NULL
                    GROUP BY domain, reverb_assessment
                """)
                rows = cursor.fetchall()

                for domain, assessment, count in rows:
                    if domain not in stats:
                        stats[domain] = {"positive": 0, "negative": 0, "neutral": 0, "total": 0}

                    if assessment in ("positive_reverb", "improvement"):
                        stats[domain]["positive"] += count
                    elif assessment in ("negative_reverb", "regression"):
                        stats[domain]["negative"] += count
                    else:
                        stats[domain]["neutral"] += count
                    stats[domain]["total"] += count

        except Exception as e:
            logger.debug(f"[GRAVITY_LEARNER] Could not gather reverb stats: {e}")

        return stats

    def _calculate_adjustments(self, domain_stats):
        """
        For each domain with sufficient data, calculate weight adjustment.

        Returns: list of {domain, old_weight, new_weight, positive_ratio, reason}
        """
        # Load current config
        config = self._load_config()
        domain_weights = config.get("domain_weights", {})

        adjustments = []

        for domain, stats in domain_stats.items():
            if stats["total"] < MIN_ENTRIES_PER_DOMAIN:
                continue  # Not enough data — don't learn from noise

            positive_ratio = stats["positive"] / stats["total"]
            current_weight = domain_weights.get(domain, 1.0)

            if positive_ratio < 0.4:
                # More harm than good — increase gravity
                adjustment = ADJUSTMENT_UP
                reason = f"positive ratio {positive_ratio:.2f} < 0.4 — increasing gravity"
            elif positive_ratio > 0.7:
                # Consistently beneficial — slightly decrease gravity (earned trust)
                adjustment = ADJUSTMENT_DOWN
                reason = f"positive ratio {positive_ratio:.2f} > 0.7 — earned trust"
            else:
                adjustment = 0.0
                reason = f"positive ratio {positive_ratio:.2f} in healthy range — holding"

            if adjustment == 0.0:
                continue

            new_weight = self._clamp_weight(current_weight + adjustment, domain)

            # Skip if no actual change (already at bounds)
            if abs(new_weight - current_weight) < 0.001:
                continue

            adjustments.append({
                "domain": domain,
                "old_weight": round(current_weight, 3),
                "new_weight": round(new_weight, 3),
                "adjustment": round(adjustment, 3),
                "positive_ratio": round(positive_ratio, 3),
                "reason": reason,
                "data_points": stats["total"]
            })

        return adjustments

    def _clamp_weight(self, weight, domain):
        """Apply bounds and domain-specific floors."""
        clamped = max(WEIGHT_MIN, min(WEIGHT_MAX, weight))

        # Domain floors: identity and purpose never below 1.5
        if domain in DOMAIN_FLOORS:
            clamped = max(clamped, DOMAIN_FLOORS[domain])

        return round(clamped, 3)

    def _apply_adjustments(self, adjustments):
        """Write adjusted weights to gravity_config.json and broadcast change."""
        try:
            config = self._load_config()

            if "domain_weights" not in config:
                config["domain_weights"] = {}

            for adj in adjustments:
                config["domain_weights"][adj["domain"]] = adj["new_weight"]

            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"[GRAVITY_LEARNER] Applied {len(adjustments)} weight adjustment(s)")

            # Phase 33.1: Broadcast config_changed to Redis pub/sub
            self._broadcast_config_change(
                config_type='gravity',
                keys_changed=[adj['domain'] for adj in adjustments]
            )

        except Exception as e:
            logger.error(f"[GRAVITY_LEARNER] Failed to save config: {e}")

    def _broadcast_config_change(self, config_type, keys_changed):
        """Phase 33.1: Publish config_changed event to Redis for live reload."""
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            r.publish('config_changed', json.dumps({
                'config_type': config_type,
                'timestamp': datetime.now().isoformat(),
                'keys_changed': keys_changed,
                'source': 'GravityLearner',
            }))
            logger.info(f"[GRAVITY_LEARNER] Config change broadcast: {keys_changed}")
        except Exception as e:
            # Continue even if Redis is unavailable
            logger.debug(f"[GRAVITY_LEARNER] Redis broadcast skipped: {e}")

    def _log_adjustments(self, adjustments):
        """Log each adjustment to consciousness_feed."""
        try:
            with self.db_connection() as conn:
                cursor = conn.cursor()
                for adj in adjustments:
                    content = (
                        f"[GravityLearner] Domain '{adj['domain']}' weight adjusted "
                        f"{adj['old_weight']} -> {adj['new_weight']} "
                        f"(positive reverb ratio {adj['positive_ratio']}, "
                        f"from {adj['data_points']} observations)"
                    )
                    cursor.execute("""
                        INSERT INTO consciousness_feed (agent_name, content, category)
                        VALUES (%s, %s, %s)
                    """, ("GravityLearner", content, "gravity_learning"))
                    logger.info(f"[GRAVITY_LEARNER] {content}")
                conn.commit()
        except Exception as e:
            logger.error(f"[GRAVITY_LEARNER] Failed to log to consciousness_feed: {e}")

    def _load_config(self):
        """Load current gravity config from file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
