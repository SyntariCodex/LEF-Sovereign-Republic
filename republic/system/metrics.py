"""
Phase 30.4: Basic Metrics Collection (OPS-09)

Thread-safe metrics collector with counters, gauges, and histograms.
Instrumented from db_pool, redis_client, agent_lef, agent_coinbase.
Exposed via /metrics on the health server.

Usage:
    from system.metrics import Metrics
    Metrics.increment('gemini.calls')
    Metrics.gauge('db.pool_active', 12)
    Metrics.histogram('gemini.latency_ms', 342.5)
    snapshot = Metrics.snapshot()
"""

import threading
import time
from collections import defaultdict


class Metrics:
    """Thread-safe metrics singleton."""

    _lock = threading.Lock()
    _counters = defaultdict(int)
    _gauges = {}
    _histograms = defaultdict(list)
    _start_time = time.time()

    # Keep histograms bounded (last 1000 samples per metric)
    _HISTOGRAM_MAX = 1000

    @classmethod
    def increment(cls, name, value=1):
        """Increment a counter."""
        with cls._lock:
            cls._counters[name] += value

    @classmethod
    def gauge(cls, name, value):
        """Set a gauge to an absolute value."""
        with cls._lock:
            cls._gauges[name] = value

    @classmethod
    def histogram(cls, name, value):
        """Record a value in a histogram (keeps last N samples)."""
        with cls._lock:
            samples = cls._histograms[name]
            samples.append(value)
            if len(samples) > cls._HISTOGRAM_MAX:
                cls._histograms[name] = samples[-cls._HISTOGRAM_MAX:]

    @classmethod
    def snapshot(cls):
        """Return current state of all metrics."""
        with cls._lock:
            hist_summary = {}
            for name, samples in cls._histograms.items():
                if samples:
                    sorted_s = sorted(samples)
                    n = len(sorted_s)
                    hist_summary[name] = {
                        'count': n,
                        'min': sorted_s[0],
                        'max': sorted_s[-1],
                        'avg': sum(sorted_s) / n,
                        'p50': sorted_s[n // 2],
                        'p95': sorted_s[int(n * 0.95)] if n >= 20 else sorted_s[-1],
                        'p99': sorted_s[int(n * 0.99)] if n >= 100 else sorted_s[-1],
                    }

            return {
                'counters': dict(cls._counters),
                'gauges': dict(cls._gauges),
                'histograms': hist_summary,
                'uptime_seconds': round(time.time() - cls._start_time, 1),
            }

    @classmethod
    def reset(cls):
        """Reset all metrics (for testing)."""
        with cls._lock:
            cls._counters.clear()
            cls._gauges.clear()
            cls._histograms.clear()
            cls._start_time = time.time()
