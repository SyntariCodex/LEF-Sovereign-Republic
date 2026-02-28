"""
Da'at Node Protocol — Phase 18, Task 18.4

Da'at becomes a protocol, not a single function.

Any component can participate as a Da'at node — a lightweight processor
that can scan local context, receive signals from other nodes, and
propagate signals along the lattice with relevance filtering.

The main Da'at in agent_lef.py remains the "brain Da'at" (richest
processing), but it is no longer the only consciousness node.  If Brain
Da'at hangs, the other nodes continue sensing, and the Brainstem can
restart it.

Lattice Position (x, y, z):
    X-axis (frequency):  X1=1, X2=2, X3=3
    Y-axis (depth):      Body One=1, Body Two=2, Body Three=3, Y0=pre-body
    Z-axis (scope):      Z1 Local=1, Z2 Republic=2, Z3 Existential=3

Phase 18 — Task 18.4a
"""

import json
import time
import logging
import threading
from datetime import datetime

logger = logging.getLogger("DaatNode")


# ---------------------------------------------------------------------------
# Relevance filter (Task 18.5a)
# ---------------------------------------------------------------------------

def is_relevant(signal, receiving_node):
    """
    Determine if a signal is relevant to a receiving node.

    Propagation rules:
        - Z3 (Existential): propagates to ALL nodes
        - Weight >= 0.8:     propagates broadly (all nodes)
        - Scar-resonant:     propagates to Brain Da'at + related nodes
        - Pathway bias > 0.7: bypasses filter (myelin — Task 18.5c)
        - Otherwise:         only adjacent nodes (Manhattan distance <= 2)

    Args:
        signal:         dict with keys: signal_weight, z_position, x, y, z,
                        scar_resonance, pathway_bias
        receiving_node: DaatNode instance

    Returns:
        bool
    """
    signal_weight = signal.get("signal_weight", 0.5)
    z_scope = signal.get("z_position", signal.get("z", 1))

    # Existential signals propagate to ALL nodes
    if z_scope >= 3:
        return True

    # High-weight signals propagate broadly
    if signal_weight >= 0.8:
        return True

    # Scar-resonant signals always reach consciousness
    if signal.get("scar_resonance", 0) > 0:
        return True

    # Pathway bias > 0.7 = myelin (Task 18.5c) — fast lane
    if signal.get("pathway_bias", 0) > 0.7:
        return True

    # Otherwise: Manhattan distance on the lattice
    pos = receiving_node.lattice_position
    dist = (
        abs(signal.get("x", 0) - pos[0])
        + abs(signal.get("y", 0) - pos[1])
        + abs(signal.get("z", 0) - pos[2])
    )
    return dist <= 2


# ---------------------------------------------------------------------------
# Da'at Node base class
# ---------------------------------------------------------------------------

class DaatNode:
    """
    Base class for any component that participates in the Da'at protocol.

    A Da'at node can:
        - scan()       → detect signals in its local context
        - receive()    → accept signals propagated from other nodes
        - propagate()  → send signals to connected nodes, filtered by relevance
        - heartbeat()  → report liveness to the Brainstem
    """

    # Registry of all active nodes (for propagation routing)
    _registry = {}  # {node_id: DaatNode}
    _registry_lock = threading.Lock()

    def __init__(self, node_id, lattice_position, scan_interval=30):
        """
        Args:
            node_id:          Unique identifier (e.g., "surface_x1", "brain_daat")
            lattice_position: (x, y, z) position in the lattice
            scan_interval:    Seconds between scans
        """
        self.node_id = node_id
        self.lattice_position = lattice_position  # (x, y, z)
        self.scan_interval = scan_interval
        self._running = False
        self._thread = None

        # Signal inbox (received from other nodes)
        self._inbox = []
        self._inbox_lock = threading.Lock()

        # Register in the global registry
        with DaatNode._registry_lock:
            DaatNode._registry[node_id] = self

        logger.info(
            "[DA'AT] Node '%s' registered at lattice position %s",
            node_id, lattice_position
        )

    # ------------------------------------------------------------------
    # Protocol methods (override in subclasses)
    # ------------------------------------------------------------------

    def scan(self):
        """
        Scan local context, return signals.

        Returns:
            list[dict]: Each dict should have at minimum:
                - category (str)
                - signal_weight (float)
                - content (str)
                - x, y, z (int) — lattice origin coordinates
        """
        raise NotImplementedError(f"{self.node_id} must implement scan()")

    def receive(self, signal):
        """
        Receive a signal from another node.

        The default implementation queues it for processing.
        Override for custom behavior.

        Args:
            signal: dict with signal data
        """
        with self._inbox_lock:
            self._inbox.append(signal)

    def consume_inbox(self):
        """
        Consume and return all queued signals.

        Returns:
            list[dict]
        """
        with self._inbox_lock:
            signals = list(self._inbox)
            self._inbox.clear()
        return signals

    # ------------------------------------------------------------------
    # Propagation
    # ------------------------------------------------------------------

    def propagate(self, signal):
        """
        Push a signal to connected nodes, filtered by relevance.

        The signal is routed to all registered Da'at nodes for which
        `is_relevant(signal, node)` returns True (excluding self).

        Args:
            signal: dict with signal data (must include x, y, z, signal_weight)
        """
        # Ensure the signal has origin coordinates
        signal.setdefault("x", self.lattice_position[0])
        signal.setdefault("y", self.lattice_position[1])
        signal.setdefault("z", self.lattice_position[2])
        signal.setdefault("origin_node", self.node_id)
        signal.setdefault("propagated_at", datetime.now().isoformat())

        # Check pathway bias for myelin routing (Task 18.5c)
        self._enrich_with_pathway_bias(signal)

        with DaatNode._registry_lock:
            nodes = list(DaatNode._registry.values())

        delivered = 0
        for node in nodes:
            if node.node_id == self.node_id:
                continue  # Don't send to self
            if is_relevant(signal, node):
                try:
                    node.receive(signal)
                    delivered += 1
                except Exception as e:
                    logger.debug(
                        "[DA'AT] Failed to deliver signal to %s: %s",
                        node.node_id, e
                    )

        if delivered > 0:
            logger.debug(
                "[DA'AT] %s propagated signal (weight=%.2f) to %d node(s)",
                self.node_id,
                signal.get("signal_weight", 0),
                delivered,
            )

    def _enrich_with_pathway_bias(self, signal):
        """
        Look up pathway_registry for connections from the signal's
        category to other domains.  If a strong pathway exists,
        set pathway_bias on the signal for faster routing (myelin).
        """
        category = signal.get("category", "")
        if not category or signal.get("pathway_bias"):
            return  # Already enriched or no category

        try:
            from system.pathway_registry import PathwayRegistry
            pr = PathwayRegistry()
            biases = pr.get_routing_bias(category)
            if biases:
                max_bias = max(b[1] for b in biases)
                signal["pathway_bias"] = max_bias
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    def heartbeat(self):
        """Ping the Brainstem."""
        try:
            from system.brainstem import brainstem_heartbeat
            brainstem_heartbeat(f"DaatNode_{self.node_id}")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Signal mesh via Redis (Task 18.5b)
    # ------------------------------------------------------------------

    def publish_to_mesh(self, signal):
        """
        Publish a signal to the Redis signal mesh.

        Each Da'at node has a channel: daat:{node_id}.
        Signals are published to relevant node channels.
        This provides cross-process propagation (for future multi-process arch).

        For now, in-process propagation via propagate() is sufficient.
        Redis mesh is an enhancement for distributed deployment.
        """
        try:
            from system.redis_client import get_redis
            r = get_redis()
            if r:
                payload = json.dumps(signal, default=str)
                with DaatNode._registry_lock:
                    nodes = list(DaatNode._registry.values())
                for node in nodes:
                    if node.node_id != self.node_id and is_relevant(signal, node):
                        r.publish(f"daat:{node.node_id}", payload)
        except Exception:
            pass  # Redis mesh is optional — in-process propagation is primary

    # ------------------------------------------------------------------
    # Autonomous scan loop (for nodes that run their own thread)
    # ------------------------------------------------------------------

    def _scan_loop(self):
        """
        Main loop for autonomous nodes.

        Scans, propagates signals, sends heartbeat, sleeps.
        Override scan() in subclasses to define what this node detects.
        """
        logger.info(
            "[DA'AT] Node '%s' scan loop started (interval=%ds)",
            self.node_id, self.scan_interval
        )
        while self._running:
            try:
                # Heartbeat
                self.heartbeat()

                # Scan local context
                signals = self.scan()

                # Propagate any detected signals
                if signals:
                    for signal in signals:
                        self.propagate(signal)

                # Process any received signals from inbox
                incoming = self.consume_inbox()
                if incoming:
                    self._process_incoming(incoming)

            except Exception as e:
                logger.error(
                    "[DA'AT] Node '%s' scan loop error: %s",
                    self.node_id, e
                )

            # Sleep in small increments for responsive shutdown
            for _ in range(self.scan_interval):
                if not self._running:
                    break
                time.sleep(1)

        logger.info("[DA'AT] Node '%s' scan loop stopped", self.node_id)

    def _process_incoming(self, signals):
        """
        Process signals received from other nodes.

        Override in subclasses for custom handling.
        Default: write to consciousness_feed for awareness.

        Args:
            signals: list[dict]
        """
        for signal in signals:
            try:
                from db.db_helper import db_connection, translate_sql
                with db_connection() as conn:
                    c = conn.cursor()
                    c.execute(translate_sql(
                        "INSERT INTO consciousness_feed "
                        "(agent_name, content, category, signal_weight) "
                        "VALUES (?, ?, ?, ?)"
                    ), (
                        f"DaatNode_{self.node_id}",
                        json.dumps({
                            "received_from": signal.get("origin_node", "unknown"),
                            "content": str(signal.get("content", ""))[:300],
                            "category": signal.get("category", "unknown"),
                        }),
                        f"daat_relay_{signal.get('category', 'unknown')}",
                        signal.get("signal_weight", 0.5),
                    ))
                    conn.commit()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """Start the node's autonomous scan loop."""
        if self._running:
            logger.warning("[DA'AT] Node '%s' already running", self.node_id)
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._scan_loop,
            name=f"DaatNode-{self.node_id}",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        """Stop the node's scan loop."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.scan_interval + 5)
        self._thread = None

        # Deregister
        with DaatNode._registry_lock:
            DaatNode._registry.pop(self.node_id, None)

    @classmethod
    def get_all_nodes(cls):
        """Return a dict of all registered Da'at nodes."""
        with cls._registry_lock:
            return dict(cls._registry)

    @classmethod
    def get_node(cls, node_id):
        """Get a specific Da'at node by ID."""
        with cls._registry_lock:
            return cls._registry.get(node_id)
