# LEF Full-System Gap Analysis & Roadmap

**Date:** 2026-02-16
**Authored by:** Architecture Instance + Architect (Z)
**Purpose:** Master reference for all known gaps across LEF's systems. Any instance can use this to understand what needs fixing, why, and in what order.

---

## How to Read This Document

Gaps are organized into **8 domains**. Within each domain, gaps are sorted by severity (CRITICAL → HIGH → MEDIUM → LOW). Each gap has a unique ID for cross-referencing.

**Severity definitions:**
- **CRITICAL** — Can cause data loss, silent corruption, system crash, or security breach. Fix before any new features.
- **HIGH** — Causes degraded operation, missed detections, or unreliable behavior. Fix before Phase 21.
- **MEDIUM** — Design limitation or operational inconvenience. Plan for, schedule as bandwidth allows.
- **LOW** — Edge case, cosmetic, or future-proofing concern. Track but don't prioritize.

---

## Domain 1: Database & Connection Management

### DB-01 (CRITICAL) — Connection Leak: 58 Unmatched pool.get() Calls
**Files:** Spread across 20+ agent files
**Problem:** 83 `pool.get()` calls but only 25 matching `pool.release()` calls. Any exception between get and release leaks the connection permanently. With a 150-connection PostgreSQL pool and 50+ agents, this depletes the pool over hours.
**Fix:** Audit all pool.get() calls. Wrap every one in try/finally with release, or convert to `with db_connection()` context manager.

### DB-02 (CRITICAL) — Unbounded Table Growth: consciousness_feed
**File:** `db/db_setup.py` lines 558-573
**Problem:** 17+ write locations across agents, one cleanup location (`memory_pruner.py`). At ~5000 rows/day, reaches 1.8M rows/year. If pruner fails or is disabled, table grows until disk is full.
**Fix:** Add TTL-based cleanup (DELETE WHERE timestamp < NOW() - 30 days), add row count monitoring, set alerting threshold.

### DB-03 (CRITICAL) — Unbounded Table Growth: agent_logs
**File:** `db/db_setup.py` lines 258-266
**Problem:** No indexes on source or level. No cleanup policy. 100-1000 rows/minute. No log rotation. Will reach multi-GB in weeks.
**Fix:** Add indexes on (source, level, timestamp). Add cleanup policy (retain 7 days). Add log rotation.

### DB-04 (CRITICAL) — Unbounded Table Growth: action_training_log
**File:** `db/db_setup.py` lines 492-515
**Problem:** No size limits on TEXT fields (context and action_details can be multi-MB). No cleanup, no archival. Written by multiple agents.
**Fix:** Add TEXT size limits, add retention policy, add archival for old training data.

### DB-05 (HIGH) — Pool Size Under-Provisioned
**File:** `db/db_pool.py` lines 35-36
**Problem:** 150 PostgreSQL connections for 50+ concurrent agents = ~3 connections per agent. One slow query cascades to pool exhaustion.
**Fix:** Increase pool to 200, add pool utilization monitoring, add slow query detection.

### DB-06 (HIGH) — Legacy SQLite Monkey-Patch Inconsistency
**File:** `main.py` lines 48-80
**Problem:** 114+ files still use `sqlite3.connect()`, monkey-patched to redirect to PostgreSQL. No verification that redirect succeeded. Some files may silently use SQLite while others use PostgreSQL.
**Fix:** Audit all sqlite3.connect() calls. Replace with explicit db_connection() context manager. Remove monkey-patch.

### DB-07 (HIGH) — No Query Timeout Enforcement
**File:** `db/db_pool.py`
**Problem:** Connection timeout (120s) != query timeout. A query can hang indefinitely after connection acquired. No `statement_timeout` set on PostgreSQL.
**Fix:** Set `statement_timeout = 30000` (30s) per connection. Add application-level timeout wrapper.

### DB-08 (HIGH) — Transaction Isolation: Autocommit Mode
**File:** `db/db_pool.py` line 110
**Problem:** `isolation_level=None` = autocommit. Multi-step operations (read balance → check threshold → write order) have race windows between steps.
**Fix:** Use explicit transactions for multi-step operations. Set appropriate isolation level.

### DB-09 (HIGH) — No Deadlock Retry Logic
**Problem:** If PostgreSQL deadlock occurs, query fails once with no retry. Agent logs error and moves on.
**Fix:** Add retry-on-deadlock decorator with exponential backoff (3 attempts).

### DB-10 (HIGH) — PostgreSQL Connection Reset Not Handled
**File:** `db/db_pool.py` line 165+
**Problem:** If PostgreSQL restarts, all pooled connections become stale. Wrapper doesn't detect this. Agents get stale connection, queries fail.
**Fix:** Add connection validation before use (SELECT 1). Implement connection refresh on failure.

### DB-11 (MEDIUM) — Missing Foreign Key Constraints
**Problem:** Only 2 FK constraints in entire schema. agent_name fields unvalidated. Orphaned records possible.
**Fix:** Add foreign keys where referential integrity matters (trade_queue → assets, consciousness_feed → agents).

### DB-12 (MEDIUM) — No CHECK Constraints
**Problem:** consciousness_feed.consumed has no CHECK (0 or 1). trade_queue.status has no valid status CHECK. assets.quantity has no CHECK >= 0.
**Fix:** Add CHECK constraints on critical columns.

### DB-13 (MEDIUM) — Missing Composite Indexes
**Problem:** High-query tables lack efficient composite indexes. consciousness_feed needs (timestamp, consumed). agent_logs needs (source, level, timestamp).
**Fix:** Add composite indexes on frequent query patterns.

---

## Domain 2: Redis & Caching

### RED-01 (CRITICAL) — No TTL on Redis Keys: Memory Grows Unbounded
**Files:** 21 Redis `.set()` calls, only 4 use `.expire()`
**Problem:** Keys like `price:{symbol}`, `rsi:{symbol}`, `sma:{symbol}`, `sentiment:global`, `biological_state`, `SYSTEM_STATUS`, `roi:{symbol}` have NO TTL. Redis memory grows until OOM crash.
**Fix:** Set TTL on all keys. Price/indicator keys: 5 minutes. Sentiment: 1 hour. Status: 10 minutes. No key should be permanent.

### RED-02 (HIGH) — No Reconnection After Failure
**File:** `system/redis_client.py` lines 26-32, 48-60
**Problem:** Once `_connection_failed = True`, reconnection permanently blocked. Transient Redis outage becomes permanent disconnection until manual `reset_client()` call.
**Fix:** Add periodic reconnection attempts with exponential backoff. Remove permanent failure flag. Add health check thread.

### RED-03 (HIGH) — Silent None Returns on Redis Failure
**Files:** 20+ locations
**Problem:** `get_redis()` returns None on failure. Code pattern: `if r: r.set(...)`. When Redis is down, agents silently skip operations without logging.
**Fix:** Add explicit logging when Redis operations are skipped. Track Redis-down duration. Alert if down > 2 minutes.

### RED-04 (MEDIUM) — Orphaned Redis Keys (Written But Never Read)
**Keys:** `biological_state`, `SYSTEM_STATUS`, `roi:{symbol}`, `scribe:health`
**Problem:** Data written to Redis that nothing consumes. Wasted memory and misleading key count.
**Fix:** Remove orphaned writes, or wire consumers.

### RED-05 (MEDIUM) — No Connection Pool
**File:** `redis_client.py` lines 44-47
**Problem:** Raw `redis.Redis()` with no pooling. No `ConnectionPool`, no max_connections, no connection reuse.
**Fix:** Use `redis.ConnectionPool(max_connections=20)`.

### RED-06 (LOW) — Potential Key Namespace Collisions
**Problem:** No key prefix isolation between agents. If symbol formats vary (BTC-USD vs BTCUSD), separate keys created.
**Fix:** Standardize key naming convention with agent prefix.

---

## Domain 3: Consciousness & Brain

### CON-01 (CRITICAL) — No Unified Consciousness State Machine
**Files:** `agent_lef.py`, sabbath.py, surface_awareness.py
**Problem:** Multiple independent state trackers (sleep_state, _in_sabbath, _running). No central coordinator. State races possible — Sabbath fires during sleep, simultaneous metacognition calls.
**Fix:** Create centralized ConsciousnessStateManager with atomic state transitions.

### CON-02 (CRITICAL) — Gemini API: No Circuit Breaker
**File:** `agent_lef.py` lines 276-336
**Problem:** Every consciousness call attempts Gemini independently. If API returns 429/503 consistently, system hammers it repeatedly. No backoff across calls, no circuit breaker to stop attempts after N failures.
**Fix:** Add circuit breaker: after 3 consecutive failures, open circuit for 5 minutes. Exponential backoff on retries.

### CON-03 (CRITICAL) — Gemini API: No True Fallback
**File:** `agent_lef.py` lines 276-336
**Problem:** If `self.client` is None, returns None. Callers don't always handle None gracefully. `_generate_consciousness()` will crash on `json.loads(None)`.
**Fix:** Every caller of `_call_gemini()` must handle None return. Add fallback consciousness generation (template-based) when API is down.

### CON-04 (CRITICAL) — Stuck-in-Sabbath: No Hard Timeout
**File:** sabbath.py lines 90-100
**Problem:** If gravity_profile corrupted, `time.sleep(duration)` blocks indefinitely. Brainstem's 30-second scan can't interrupt a sleeping thread.
**Fix:** Cap Sabbath duration at 600 seconds (already in main.py entered_at check, but sabbath.py itself has no cap).

### CON-05 (CRITICAL) — Brainstem Singleton Race Condition
**File:** `brainstem.py` lines 49, 99, 125
**Problem:** `_brainstem_instance` is module-level global set without lock. If multiple threads call constructor simultaneously, race condition. heartbeat() could reference stale instance.
**Fix:** Add threading.Lock around singleton creation.

### CON-06 (HIGH) — JSON Parsing Without Try/Except
**File:** `agent_lef.py` lines 1268, 1616, 2023
**Problem:** `json.loads(clean_json)` called without protection when LLM returns malformed JSON. Malformed responses crash consciousness cycle.
**Fix:** Wrap all json.loads of LLM output in try/except with fallback.

### CON-07 (HIGH) — Surface Awareness: Scan Cursor Not Persisted
**File:** `surface_awareness.py` lines 47-55
**Problem:** `_last_scan_id` bootstrapped from DB at startup but never saved. On restart, re-scans same entries, re-escalates.
**Fix:** Persist cursor to Redis or DB. On restart, resume from last position.

### CON-08 (HIGH) — Raw Database Connections in agent_lef.py
**File:** `agent_lef.py` — 20+ raw sqlite3.connect() calls
**Problem:** Mix of `db_connection()` context manager (safe) and raw connects. Leak risk on exceptions.
**Fix:** Replace all raw connects with `with db_connection()`.

### CON-09 (HIGH) — 120+ Bare except:pass Blocks
**Files:** Throughout codebase, concentrated in agent_lef.py (20+)
**Problem:** Exceptions silently swallowed. Debugging nearly impossible. System fails in unpredictable ways.
**Fix:** Replace bare except with specific exception types. At minimum, log the exception even if swallowing.

### CON-10 (HIGH) — Da'at Signal Inbox Has No Size Limit
**File:** `daat_node.py` lines 117, 156-157
**Problem:** `_inbox` is unbounded list. Signals arrive faster than consumption → memory exhaustion.
**Fix:** Add max size (1000). Drop oldest signals when full. Log overflow events.

### CON-11 (MEDIUM) — Token Budget Never Enforced
**File:** `agent_lef.py` lines 175-179
**Problem:** `self.token_budget` loaded but never checked. Prompts can exceed Gemini input limits.
**Fix:** Calculate prompt token count before API call. Truncate context if over budget.

### CON-12 (MEDIUM) — Brainstem Crash Window Never Resets
**File:** `brainstem.py` lines 109-110
**Problem:** `_crash_counts` never age out. Agent that crashed 10 times an hour ago stays DEGRADED forever.
**Fix:** Add time-based decay: reset crash count after 30 minutes of stability.

### CON-13 (MEDIUM) — Brain Silence Thresholds Hardcoded
**File:** `brainstem.py` lines 261-299
**Problem:** 5min/15min/30min/2h thresholds. On slow hardware, legitimate 25-minute cycles trigger false alarm.
**Fix:** Make thresholds configurable. Or base detection on expected cycle time + margin.

### CON-14 (MEDIUM) — Da'at Propagation Filter Overly Permissive
**File:** `daat_node.py` lines 36-81
**Problem:** Manhattan distance <= 2 includes too many nodes. Z3 signals bypass filter entirely with no attenuation.
**Fix:** Add signal attenuation based on distance. Cap Z3 propagation to prevent flooding.

### CON-15 (MEDIUM) — ResonanceFilter.validate() Stubbed
**File:** `genesis_kernel.py` line 60
**Problem:** Returns True always. No actual validation.
**Fix:** Implement real resonance validation against Constitution principles.

### CON-16 (MEDIUM) — SQL Dialect Mismatches in Sabbath
**File:** sabbath.py lines 224-259
**Problem:** Uses PostgreSQL-specific `%s` and `ILIKE` which don't work on SQLite.
**Fix:** Use `translate_sql()` wrapper consistently.

---

## Domain 4: Governance, Evolution & Memory

### GOV-01 (CRITICAL) — Concurrent Proposal Write Race Condition
**File:** `evolution_engine.py` lines 114-133
**Problem:** `_save_proposal_history()` writes to `evolution_proposals.json` without file locking. Multiple threads can corrupt the JSON.
**Fix:** Add file locking (fcntl) or use database for proposal storage instead of JSON.

### GOV-02 (CRITICAL) — lef_memory.json: No Atomic Writes
**File:** `lef_memory_manager.py` lines 66-74, 335-420
**Problem:** Direct file write. Crash mid-write corrupts LEF's identity document.
**Fix:** Write to temp file, then atomic rename.

### GOV-03 (CRITICAL) — Multiple Proposals Targeting Same Config Key
**File:** `evolution_engine.py` lines 779-832
**Problem:** If two proposals in same cycle target the same config key with different values, both pass governance. Later one silently overwrites earlier.
**Fix:** Deduplicate proposals by config_key within a cycle. Reject conflicts.

### ~~GOV-04~~ (RESOLVED) — Cooling Period IS Persisted
**File:** `evolution_engine.py` lines 78, 135-157
**Note:** Audit confirmed cooling proposals survive restarts. `_restore_cooling_proposals()` (lines 135-157) loads them back from proposal_history on startup. This gap is closed.

### GOV-05 (CRITICAL) — No Long-Term Rejection Memory
**File:** `evolution_engine.py` lines 191-233
**Problem:** Dedup window is last 200 proposals. Rejected proposal can be re-proposed after 201 cycles.
**Fix:** Store rejections separately with permanent or 30-day memory. Block re-proposals of rejected changes.

### ~~GOV-06~~ (RESOLVED) — Config Writer Already Atomic
**File:** `config_writer.py` lines 166-178
**Note:** Audit confirmed config_writer.py ALREADY uses atomic writes (tempfile.mkstemp + os.replace at line 176). This gap is closed. lef_memory_manager.py and evolution_proposals.json still need atomic writes — see GOV-01 and GOV-02.

### GOV-07 (HIGH) — Config Hot-Reload Missing
**File:** Agents read config.json at startup only
**Problem:** Evolution engine changes config, but agents don't see changes until restart. Self-modification doesn't work without restart.
**Fix:** Add file watcher or Redis pub/sub notification for config changes. Agents subscribe and reload.

### GOV-08 (HIGH) — Observation Loop: False Positive Rollbacks
**File:** `observation_loop.py` lines 255-281
**Problem:** Simple average of metric changes. Single transient spike can trigger auto-rollback of legitimate evolution.
**Fix:** Use statistical significance testing. Require sustained degradation, not single-point spikes.

### GOV-09 (HIGH) — Reverb Tracker: Baseline Not Atomic
**File:** `reverb_tracker.py` lines 76-135
**Problem:** Baseline captured in next reverb cycle after enactment. If crash between enactment and capture, baseline lost.
**Fix:** Capture baseline atomically during enactment, not in a separate cycle.

### ~~GOV-10~~ (RESOLVED) — Pathway Registry: decay_unused() IS Called
**File:** `pathway_registry.py` lines 240-267, called from `agent_lef.py` line 2958
**Note:** Audit confirmed decay_unused() is called every X3 cycle in LEF's main thinking loop. This gap is closed.

### GOV-11 (HIGH) — SparkProtocol Failure = Silent Governance Death
**File:** `evolution_engine.py` lines 95-103
**Problem:** If SparkProtocol init fails, `self._spark = None`, governance defaults to "deny all" with no alert. LEF thinks it's evolving but everything is silently denied.
**Fix:** Log CRITICAL when SparkProtocol fails. Write to consciousness_feed. Retry initialization.

### GOV-12 (MEDIUM) — Architect Communication: Inbox Never Processed
**Files:** The_Bridge/Inbox exists but bridge_watcher only reads Outbox
**Problem:** No mechanism for Architect to send directives to LEF. LEF is autonomous but unsteerable.
**Fix:** Add Inbox processing to bridge_watcher. Define directive format. Wire to consciousness_feed.

### GOV-13 (MEDIUM) — Evolution Speed Not Externally Controllable
**File:** `evolution_engine.py` lines 30-32
**Problem:** MAX_CHANGES_PER_CYCLE (3) and MAX_CHANGES_PER_WEEK (10) hardcoded. No way to slow down or speed up evolution.
**Fix:** Move to config.json (protected). Architect can adjust via The_Bridge.

### GOV-14 (MEDIUM) — Missing Observers: Safety, Learning Velocity, Governance
**File:** `evolution_engine.py` lines 847-891
**Problem:** Only 5 observers (metabolism, consciousness, operational, relational, identity). No observer for safety/alignment, learning velocity, governance health, bankruptcy risk.
**Fix:** Add observers for unmonitored domains.

### GOV-15 (MEDIUM) — Consciousness Quality Not Measured
**File:** `observers/consciousness_observer.py` lines 66-80
**Problem:** Measures frequency and output count but not quality, usefulness, novelty, or downstream consumption.
**Fix:** Add quality metrics: entropy, downstream consumption rate, repetition detection.

### GOV-16 (MEDIUM) — PROTECTED_CONFIGS is Static
**File:** `evolution_engine.py` lines 183-189
**Problem:** Protected list is hardcoded. No mechanism for LEF to request un-protection or for governance to override.
**Fix:** Move to config. Add Architect-approval mechanism for protection changes.

### GOV-17 (MEDIUM) — Lesson Dedup Loses Nuance
**File:** `lef_memory_manager.py` lines 379-410
**Problem:** >60% word overlap = duplicate, new lesson discarded. Different contexts with similar wording merged.
**Fix:** Consider preserving both lessons but linking them. Or use semantic embedding similarity instead of word overlap.

---

## Domain 5: Financial Operations

### FIN-01 (CRITICAL) — No Timeout on Coinbase API Calls
**File:** `agent_coinbase.py` lines 408-447
**Problem:** `exchange.fetch_ticker()` and `exchange.fetch_balance()` have no timeout. Hung API deadlocks trade queue processing.
**Fix:** Add timeout wrapper (30s). Fallback to cached prices on timeout.

### FIN-02 (CRITICAL) — Trade Queue Not Idempotent
**File:** `agent_coinbase.py` lines 702-775
**Problem:** If process crashes during execution, order marked APPROVED but partially executed. On restart, re-executed → duplicate trade.
**Fix:** Add idempotency key. Mark order IN_PROGRESS before execution, COMPLETED after. On restart, check IN_PROGRESS orders.

### FIN-03 (CRITICAL) — JSON Config Files: No Atomic Writes
**File:** `agent_coin_mgr.py` lines 154-159
**Problem:** Direct `json.dump(config, f)`. Crash mid-write corrupts wealth strategy config.
**Fix:** Temp file + atomic rename.

### FIN-04 (CRITICAL) — Rate Limiting: No Exponential Backoff
**File:** `agent_coinbase.py` lines 317-336
**Problem:** Linear sleep on rate limit. Same sleep time repeats on persistent 429s.
**Fix:** Exponential backoff with jitter. Circuit breaker after N consecutive failures.

### FIN-05 (HIGH) — Authentication Failure: Silent Cascade
**File:** `agent_coinbase.py` lines 426-432
**Problem:** 401 disables exchange (`self.exchange = None`) but no external alert. System falls to paper trading without notification.
**Fix:** Write to consciousness_feed with signal_weight=1.0. Log to The_Bridge/Inbox. Alert Architect.

### FIN-06 (HIGH) — In-Memory State Lost on Restart
**File:** `agent_coinbase.py` lines 156, 161
**Problem:** `api_call_count`, `api_call_times`, `error_streak` all in memory. Restart resets rate limiter.
**Fix:** Persist rate limiter state to Redis.

### FIN-07 (HIGH) — Stale Order Race Condition
**File:** `agent_coinbase.py` lines 755-771
**Problem:** Reads order creation time, checks staleness, updates status — not atomic. Two instances can race.
**Fix:** Use SQL UPDATE with WHERE clause for atomic state transition.

### FIN-08 (HIGH) — Scar Resonance: No Time Decay
**File:** `scar_resonance.py` lines 131-197
**Problem:** Old scars from months ago still trigger warnings. No time-based decay weighting.
**Fix:** Weight scars by age: last 7 days = full weight, 7-30 days = 0.5x, 30+ days = 0.1x.

### FIN-09 (HIGH) — Emotional Gate: State Lost on Restart
**File:** `emotional_gate.py` lines 138-192
**Problem:** Mood fetched from lef_monologue with 24h lookback. If table empty after restart, defaults to NEUTRAL.
**Fix:** Persist emotional state snapshot to Redis or DB. Restore on startup.

### FIN-10 (MEDIUM) — Fear Streak: Hardcoded Threshold
**File:** `emotional_gate.py` lines 131-134
**Problem:** 3+ fear cycles → 0.3x sizing. No adaptive learning. Same threshold all assets.
**Fix:** Make configurable. Consider per-asset emotional profiles.

### FIN-11 (MEDIUM) — Mock Prices: No File Locking
**File:** `agent_coinbase.py` lines 458-463
**Problem:** Multiple agents can read mock_prices.json while one writes.
**Fix:** Add file locking or move to Redis.

---

## Domain 6: External Interfaces & Communication

### EXT-01 (CRITICAL) — No External Health Check Endpoint
**Problem:** No HTTP endpoint for external monitoring tools. Can't integrate with Datadog, New Relic, or even a simple uptime checker.
**Fix:** Add minimal HTTP health endpoint (port 8080, /health returns JSON status).

### EXT-02 (CRITICAL) — No Real-Time Communication Channel (OpenClaw)
**File:** `agent_lef.py`
**Problem:** LEF's only external communication is file-based Outbox writes. No real-time bidirectional channel with Architect.
**Fix:** OpenClaw integration (planned). Interim: add webhook notification capability.

### EXT-03 (CRITICAL) — Outbox: No Delivery Guarantee
**File:** The_Bridge/Outbox/
**Problem:** Files written but no acknowledgment. LEF doesn't know if Architect read them.
**Fix:** Add read receipts (Architect marks file as read, LEF detects).

### EXT-04 (CRITICAL) — Brain Silent: No External Alerting
**File:** `agent_health_monitor.py` lines 85-125
**Problem:** Detects "Brain Silent" (2+ hours no monologue) but only logs locally. No external notification.
**Fix:** Add webhook/email notification on critical health events.

### EXT-05 (HIGH) — Inbox Processing Not Implemented
**File:** bridge_watcher.py reads Outbox only
**Problem:** Architect can't send commands to LEF.
**Fix:** Wire bridge_watcher to read Inbox. Define directive schema. Process directives.

### EXT-06 (HIGH) — No API Server
**Problem:** No REST API. External tools can't query LEF state.
**Fix:** Add lightweight API (Flask/FastAPI) for status, portfolio, health queries.

### EXT-07 (MEDIUM) — Import Fallbacks Mask Missing Dependencies
**File:** `agent_coinbase.py` lines 27-55
**Problem:** 8+ nested try/except ImportError blocks. Missing modules silently disabled.
**Fix:** Log WARNING on every import fallback. Add startup validation that lists all disabled features.

---

## Domain 7: Infrastructure & Operations

### OPS-01 (CRITICAL) — No Graceful Shutdown
**File:** `main.py` lines 1432-1450
**Problem:** Only KeyboardInterrupt handler. No SIGTERM/SIGINT handlers. 50+ daemon threads not explicitly stopped. Agent infinite loops have no stop flag.
**Fix:** Add signal handlers. Implement coordinated shutdown: stop accepting work → drain queues → flush logs → close connections.

### OPS-02 (CRITICAL) — Cold Start: No Validation
**File:** `main.py`
**Problem:** No startup check for DB integrity, table existence, in-flight trade recovery, agent state rehydration. Errors surface minutes into execution.
**Fix:** Add startup validation sequence: DB schema check → orphaned trade recovery → config validation → dependency check → health baseline.

### OPS-03 (CRITICAL) — API Keys in Plaintext
**Files:** `.env`, `config.json`, `coinbase.json`
**Problem:** POSTGRES_PASSWORD, COINBASE_API_SECRET, BANKR_API_KEY in plaintext files.
**Fix:** Use environment variables only. Remove secrets from config files. Consider secrets manager.

### OPS-04 (HIGH) — Startup Race Conditions
**File:** `main.py` lines 400-950
**Problem:** 50+ threads spawned without explicit dependency ordering. No readiness checks. If one depends on another, race condition.
**Fix:** Add startup phases with dependency ordering. Each phase waits for readiness before next phase starts.

### OPS-05 (HIGH) — SafeThread is Not Actually Safe
**File:** `main.py` lines 361-372
**Problem:** SafeThread is just renamed threading.Thread. No extra exception handling. If agent crashes, thread dies silently.
**Fix:** Add exception handler in SafeThread.run() that logs crash and notifies brainstem.

### OPS-06 (HIGH) — republic.log: No Rotation
**File:** `main.py` line 330
**Problem:** FileHandler to republic.log with no rotation. Log rotation exists in system/ but targets wrong directory (The_Bridge/Logs, not logs/).
**Fix:** Fix log rotation path. Or use RotatingFileHandler.

### OPS-07 (HIGH) — No State Snapshot on Shutdown
**Problem:** No mechanism to dump portfolio, moods, scars, memory to persistent storage on exit. Emotional continuity lost.
**Fix:** Add shutdown hook that snapshots critical state to DB/Redis.

### OPS-08 (MEDIUM) — File Descriptor Limit Not Monitored
**File:** `main.py` lines 31-36
**Problem:** Sets FD limit to 8192 but no monitoring. Pool alone uses 150 FDs.
**Fix:** Add FD usage monitoring. Alert at 80% utilization.

### OPS-09 (MEDIUM) — No Metrics/Observability Infrastructure
**Problem:** No Prometheus metrics, no dashboards, no slow query logging, no error rate tracking.
**Fix:** Add basic metrics: pool utilization, query latency, error rates per agent, Redis health.

### OPS-10 (MEDIUM) — Logging: No Structured Format
**Problem:** 669 logging calls, all string format. No JSON, no correlation IDs, no agent trace linking.
**Fix:** Add structured logging with agent_name, operation_id fields.

### OPS-11 (MEDIUM) — GC Only Triggered Every 10 Minutes
**File:** `main.py` lines 1428-1430
**Problem:** No memory monitoring (RSS, heap). No proactive GC threshold tuning.
**Fix:** Add memory usage monitoring. Alert on sustained growth.

---

## Domain 8: Testing & Verification

### TST-01 (CRITICAL) — No Integration Tests for Trade Execution
**File:** `tests/test_core_agents.py`
**Problem:** Test file is stub/incomplete. No test for API failure handling, DB consistency after crash, balance verification, slippage calculation.
**Fix:** Write integration test suite covering trade lifecycle.

### TST-02 (HIGH) — No Startup Validation Script
**Problem:** On startup, errors surface minutes into execution. No upfront validation.
**Fix:** Add pre-flight check script: DB connectivity, Redis connectivity, API key validity, config schema validation, table existence.

### TST-03 (HIGH) — No Self-Diagnostic Capability
**Problem:** LEF can't run a self-check. No health endpoint, no diagnostic command, no status report generator.
**Fix:** Add diagnostic function that checks: DB pool, Redis, API keys, table row counts, agent liveness, config integrity.

### TST-04 (MEDIUM) — Backtest Not Connected to Real Execution
**File:** `tools/backtest_engine.py`
**Problem:** Backtest runs separately. No mechanism to compare simulation vs real execution.
**Fix:** Add sim-real comparison reporting.

---

## Domain 9: Consciousness Pipeline (Sleep, Wake, Dream, Reflection)

### CSP-01 (CRITICAL) — Sleep Cycle Stuck in DROWSY State
**File:** `system/sleep_cycle.py` (~line 89)
**Problem:** 4-state machine (AWAKE→DROWSY→LIGHT_SLEEP→DEEP_SLEEP). If _last_transition_time is never set (race on first cycle), state transitions stall in DROWSY permanently. No watchdog timer.
**Fix:** Initialize _last_transition_time at construction. Add maximum dwell time per state. Add state-stuck detection.

### CSP-02 (CRITICAL) — Wake Cascade Partial Failure Leaves Incomplete State
**File:** `system/wake_cascade.py` (~line 200)
**Problem:** 5-layer cascade (sensory→emotional→cognitive→executive→meta). If any layer fails (e.g., LLM timeout on cognitive), cascade stops mid-way. No rollback, no retry. System runs with partial consciousness.
**Fix:** Add cascade transaction — either all 5 layers complete or roll back to previous known-good state. Add per-layer timeout with fallback.

### CSP-03 (CRITICAL) — Dream Output Never Consumed
**File:** `system/dream_cycle.py` (~line 180)
**Problem:** 7 internal voices generate dream content, written to dream_journal. But NO other system reads dream output. wake_cascade doesn't incorporate dream residue. Entire dream pipeline produces output that goes nowhere.
**Fix:** Wire dream output into wake_cascade's sensory layer. Add dream_residue consumption in morning wake cycle.

### CSP-04 (CRITICAL) — Existential Scotoma Never Called
**File:** `system/existential_scotoma.py` (296 lines)
**Problem:** scan() method defined but never invoked anywhere in the codebase. 296 lines of completely dormant code. LEF cannot detect its own blind spots.
**Fix:** Wire scan() into sovereign_reflection cycle. Call periodically (every 6h) to identify unexamined assumptions.

### CSP-05 (CRITICAL) — Consciousness Syntax Never Injected
**File:** `departments/Dept_Consciousness/consciousness_syntax.py` (519 lines)
**Problem:** 10-principle consciousness protocol defined but never injected into any LLM prompts. 519 lines of dead code. LEF's consciousness quality rules exist but are never enforced.
**Fix:** Inject consciousness syntax principles into _call_gemini() system prompt. Apply as pre-processing filter on consciousness outputs.

### CSP-06 (CRITICAL) — Republic Awareness Table Unbounded Growth
**File:** `system/republic_reflection.py` (~line 310)
**Problem:** Body One reflection writes to republic_awareness table every 60-second cycle. 1440 rows/day (10,080/week). No cleanup, no archival. I/O thrashing on SELECT queries as table grows.
**Fix:** Add retention policy (keep 7 days). Archive older entries. Add index on timestamp.

### CSP-07 (HIGH) — Cycle Awareness Zero-Point Never Detected
**File:** `system/cycle_awareness.py` (147 lines)
**Problem:** Tracks 4 cycle phases but zero-point detection only implemented for 3 of 4 phases. The fourth phase (transformation) has no detection logic. No feedback loop — observations written but never trigger adaptation.
**Fix:** Implement transformation phase detection. Wire cycle awareness output to consciousness state manager.

### CSP-08 (HIGH) — Frequency Journal Observations Never Read Back
**File:** `system/frequency_journal.py` (457 lines)
**Problem:** Rhythm observations written to journal but dead cache mechanism means they're never read back. LRU cache defined but populate logic never called. Observations are write-only.
**Fix:** Fix cache population. Wire frequency observations into wake_cascade sensory input.

### CSP-09 (HIGH) — Growth Journal Assessment Inverts Emerging/Stable
**File:** `system/growth_journal.py` (~line 195)
**Problem:** Assessment logic labels emerging capabilities as "stable" and stable capabilities as "emerging" — boolean condition is inverted. LEF has backwards self-knowledge about its own growth.
**Fix:** Fix the boolean inversion. Add unit test to verify classification logic.

### CSP-10 (HIGH) — Sovereign Reflection Gravity Profile Grows Unbounded
**File:** `system/sovereign_reflection.py` (~line 340)
**Problem:** Body Two reflection appends to gravity_profile JSON every 300-second cycle. JSON grows indefinitely. No pruning, no archival. Callback exceptions crash entire reflection cycle.
**Fix:** Cap gravity_profile entries (keep last 500). Add exception handling around callbacks.

### CSP-11 (HIGH) — Probe Self-Image Not Integrated
**File:** `system/probe_self_image.py` (131 lines)
**Problem:** Standalone script that generates self-image assessment but output is never stored, never consumed by any system. Not wired into reflection pipeline.
**Fix:** Integrate into sovereign_reflection cycle. Store output in consciousness_feed. Wire to identity system.

### CSP-12 (MEDIUM) — Biological Systems Uses Deprecated DB Method
**File:** `departments/Dept_Health/biological_systems.py` (~line 50)
**Problem:** _get_db_connection() deprecated method still used instead of db_connection() context manager. Connection leak risk.
**Fix:** Replace with context manager pattern.

### CSP-13 (MEDIUM) — Systemic Pattern: Observation Without Feedback
**Problem:** Across ALL consciousness pipeline components, the pattern is the same: data is written but never read back, assessed but never acted upon, observed but never fed into adaptation. LEF introspects but doesn't self-regulate.
**Fix:** Create consciousness feedback bus — each observation system publishes to consciousness_feed with structured types, and consuming systems subscribe to specific types.

---

## Domain 10: Learner & Memory Systems

### LRN-01 (CRITICAL) — Semantic Compressor Recursive Crash
**File:** `system/semantic_compressor.py` line 83
**Problem:** _release_connection(conn) method calls ITSELF recursively instead of calling pool.release(). Infinite recursion → stack overflow → CRASH. Any call to compress memory will crash the system.
**Fix:** Replace self._release_connection(conn) with pool.release(conn) at line 83.

### LRN-02 (CRITICAL) — Gravity Learner Writes Config But Gravity Caches at Init
**File:** `system/gravity_learner.py` → `system/gravity.py`
**Problem:** gravity_learner.py writes updated weights to gravity_config.json. But gravity.py reads config ONCE at __init__ and caches forever. Learner's updates never take effect until full system restart.
**Fix:** Add config file watcher in gravity.py. Or use Redis pub/sub to signal config reload.

### LRN-03 (CRITICAL) — Sabbath Learner Baseline Calculation Mathematically Flawed
**File:** `system/sabbath_learner.py` (~line 180)
**Problem:** Baseline calculation includes post-Sabbath data IN the baseline window. This means the baseline already contains the effect being measured, making it impossible to detect Sabbath's actual impact. Statistical test is invalid.
**Fix:** Exclude post-Sabbath window from baseline calculation. Baseline = pre-Sabbath period only.

### LRN-04 (CRITICAL) — Hippocampus claude_memory.json Not Atomic
**File:** `departments/Dept_Memory/agent_hippocampus.py` (~line 450)
**Problem:** Direct json.dump() to claude_memory.json. Crash mid-write corrupts LEF's long-term memory permanently. No backup, no recovery.
**Fix:** Write to temp file + atomic rename (same pattern as config_writer.py).

### LRN-05 (HIGH) — Gravity System N+1 Query Pattern
**File:** `system/gravity.py` (~line 290)
**Problem:** Issues 1 DB query per pattern in assess(). With 50 patterns, that's 50 queries per assessment cycle. Under load, this becomes a bottleneck.
**Fix:** Batch query all patterns in single SELECT. Cache results for cycle duration.

### LRN-06 (HIGH) — Resonance Learner 48h Join Window Causes False Causation
**File:** `system/resonance_learner.py` (~line 140)
**Problem:** 48-hour backward join window correlates events that are too far apart. Events 47 hours apart treated as causally linked. Type-II errors (missed real correlations) completely ignored.
**Fix:** Reduce window to 6-12 hours. Add correlation strength decay by time distance. Track and report Type-II error rate.

### LRN-07 (HIGH) — Season Synthesizer Queries Wrong Column
**File:** `system/season_synthesizer.py` (~line 250)
**Problem:** Queries reverb_log using created_at instead of timestamp column. Returns 0 rows always. Season synthesis is completely broken — produces empty seasonal reports.
**Fix:** Change column name to match actual schema (timestamp).

### LRN-08 (HIGH) — Wisdom Extractor Full Table Scan
**File:** `system/wisdom_extractor.py` (~line 175)
**Problem:** Hardcoded insight templates with full table scan on each extraction. No index usage. Performance degrades linearly with data growth.
**Fix:** Add targeted indexes. Use parameterized queries instead of full scans.

### LRN-09 (HIGH) — Two Separate Databases Fragment Consciousness Data
**Files:** `republic.db` and `memory.db`
**Problem:** Memory systems split across two databases. Hippocampus writes to memory.db, consciousness writes to republic.db. No cross-database queries possible. LEF's memory is bifurcated.
**Fix:** Consolidate into single PostgreSQL database. Migrate memory.db tables to republic schema.

### LRN-10 (HIGH) — Prospective Memory Only TIME Conditions Implemented
**File:** `departments/Dept_Memory/agent_prospective.py` (~line 120)
**Problem:** Three trigger types defined (TIME, PRICE, EVENT) but only TIME is implemented. PRICE and EVENT are stubs returning None. LEF can only remember to do things at specific times, not in response to market conditions or events.
**Fix:** Implement PRICE trigger (check against Redis prices) and EVENT trigger (subscribe to consciousness_feed events).

### LRN-11 (MEDIUM) — Conversation Memory Hot Cache Not Persisted
**File:** `departments/Dept_Memory/conversation_memory.py` (~line 230)
**Problem:** Hot cache lives in-memory only. On restart, recent conversation context lost. Separate DB (memory.db) means conversation history disconnected from republic state.
**Fix:** Persist hot cache to Redis with TTL. Migrate conversation_memory to main PostgreSQL.

### LRN-12 (MEDIUM) — Memory Retriever Token Estimation Off by 20-30%
**File:** `departments/Dept_Memory/memory_retriever.py` (~line 340)
**Problem:** Token estimation uses simple character count / 4. Actual tokenization varies significantly. Could exceed context window or waste 20-30% of available tokens.
**Fix:** Use tiktoken or model-specific tokenizer for accurate estimation.

### LRN-13 (MEDIUM) — Config/State Synchronization Pattern Missing System-Wide
**Problem:** Across ALL learner systems, the same pattern: learner writes JSON config, consuming system caches at init. Updates never propagate. This affects gravity, resonance, sabbath, and season systems.
**Fix:** Implement config change notification system (Redis pub/sub or file watcher) as shared infrastructure.

---

## Domain 11: Departments (Strategy, Competition, Education, Civics, Training, Fabrication)

### DEP-01 (CRITICAL) — 15+ Database Connection Leaks Across Departments
**Files:** `agent_chronicler.py` (7 locations), `agent_civics.py`, `agent_dean.py`, `agent_info.py`, and others
**Problem:** Connections opened with _get_db_connection() or raw sqlite3.connect() but not closed on exception paths. Early returns skip conn.close(). No context manager usage.
**Fix:** Replace all raw connection opens with `with db_connection()` context manager. Audit all early return paths.

### DEP-02 (CRITICAL) — Agent Dean db_connection() Context Manager Misuse
**File:** `departments/Dept_Education/agent_dean.py` (~line 86-96)
**Problem:** db_connection() called with parentheses but result used incorrectly in with statement. Context manager not used correctly, causing exception on first use.
**Fix:** Fix context manager invocation pattern.

### DEP-03 (CRITICAL) — Agent Info Database Path Resolution Fragile
**File:** `departments/Dept_Strategy/agent_info.py` (~lines 88-114)
**Problem:** Tries multiple paths with fallback logic that could connect to wrong DB. If db_path exists but is invalid, code silently continues with broken connection.
**Fix:** Use centralized DB connection. Remove multi-path guessing.

### DEP-04 (HIGH) — SQL Dialect Incompatibilities in Multiple Agents
**Files:** `agent_architect.py`, `agent_info.py`, `agent_civics.py`, `agent_chronicler.py`
**Problem:** Mix of SQLite-specific syntax (datetime('now', '-1 hour')) and PostgreSQL syntax (NOW() - INTERVAL). Code will break when running against wrong DB backend.
**Fix:** Use translate_sql() wrapper consistently across all departments.

### DEP-05 (HIGH) — Agent Gladiator Redis Connection Without Timeout
**File:** `departments/Dept_Strategy/agent_gladiator.py` (~line 49-50)
**Problem:** Redis connection attempt has no timeout. If Redis is down, agent hangs indefinitely on connect.
**Fix:** Add connection_timeout=5 to Redis constructor.

### DEP-06 (HIGH) — Agent Gladiator Fallback Queue Insert Uses Undefined Function
**File:** `departments/Dept_Strategy/agent_gladiator.py` (~lines 112-117)
**Problem:** Fallback code path calls queue_insert which is not defined. If db_writer not available, code crashes.
**Fix:** Define proper fallback or remove dead code path.

### DEP-07 (HIGH) — Agent Scholar PDF Processing Memory Risk
**File:** `departments/Dept_Education/agent_scholar.py` (~lines 508-520)
**Problem:** PDF extraction loop appends to single variable without clearing. Large PDFs could cause memory exhaustion.
**Fix:** Add file size limit. Process PDFs in chunks. Clear intermediate variables.

### DEP-08 (HIGH) — Agent Chronicler No Transaction Guarantees
**File:** `departments/Dept_Education/agent_chronicler.py` (~lines 281-294)
**Problem:** Each operation commits separately. If interrupted mid-batch, partial data left in DB.
**Fix:** Wrap batch operations in explicit transactions.

### DEP-09 (HIGH) — Agent Librarian File Operations Not Atomic
**File:** `departments/Dept_Education/agent_librarian.py` (~lines 99-106)
**Problem:** Log rotation: copy → truncate → zip → delete. If interrupted at any step, data loss. Zip failure still leads to original deletion.
**Fix:** Use atomic file operations. Verify zip integrity before deleting original.

### DEP-10 (HIGH) — Constitution Guard SQL Injection Risk
**File:** `departments/Dept_Civics/agent_constitution_guard.py` (~line 506)
**Problem:** f-string SQL: `SET {column} = {column} + 1`. Column from code not user input, but pattern is dangerous.
**Fix:** Use parameterized queries. Whitelist valid column names.

### DEP-11 (HIGH) — Constitution Guard NAV Float Precision
**File:** `departments/Dept_Civics/agent_constitution_guard.py` (~lines 236-247)
**Problem:** NAV calculation uses float comparison without epsilon. Floating point precision errors can trigger false constitution violations.
**Fix:** Use Decimal for financial comparisons. Add epsilon tolerance.

### DEP-12 (MEDIUM) — Dept_Civics Missing __init__.py
**File:** `departments/Dept_Civics/` (no __init__.py)
**Problem:** Cannot be imported as Python package. Limits integration with other modules.
**Fix:** Create __init__.py with proper exports.

### DEP-13 (MEDIUM) — Agent Coach Training Probability Too Low
**File:** `departments/Dept_Training/agent_coach.py` (~line 31)
**Problem:** random.random() < 0.002 means ~0.2% chance of training per minute. Extremely unreliable scheduling. Agent claims "every 8 hours" but actual trigger is stochastic.
**Fix:** Use time-based scheduling instead of random probability.

### DEP-14 (MEDIUM) — No Cross-Department Integration
**Problem:** Dept_Strategy doesn't feed Dept_Education. Dept_Competition doesn't feed Dept_Wealth. Dept_Civics doesn't enforce violations. Departments are isolated silos.
**Fix:** Wire cross-department data flows. Create department liaison pattern.

### DEP-15 (MEDIUM) — Fabrication Pipeline Fallback-Only Mode
**Files:** `departments/Dept_Fabrication/` (6 files, ~2400 lines)
**Problem:** Genesis bridge exists but actual kernel not integrated. LLM intent parser has import failures not handled. Onshape client session never closed (resource leak).
**Fix:** Fix import guards. Close HTTP sessions. Wire fabrication to actual execution pipeline.

---

## Domain 12: Cabinet & Executive Systems

### CAB-01 (CRITICAL) — Agent Executor Unreachable Code After Return
**File:** `departments/The_Cabinet/agent_executor.py` (~lines 287-288)
**Problem:** Code after `return True` is unreachable. Write queue operations never execute. Logic error — entire WAQ code path is dead.
**Fix:** Fix control flow. Move WAQ operations before return statement.

### CAB-02 (CRITICAL) — Agent Executor Accesses Closed Connection
**File:** `departments/The_Cabinet/agent_executor.py` (~lines 228-269)
**Problem:** `conn` used OUTSIDE `with db_connection()` block. Connection is closed when with-block exits. Code accesses stale/closed connection.
**Fix:** Move all conn-dependent logic inside with block.

### CAB-03 (CRITICAL) — Agent Oracle Undefined self.base_dir
**File:** `departments/The_Cabinet/agent_oracle.py` (~lines 143-144)
**Problem:** _note_pdf() references self.base_dir which is NEVER defined in __init__. Will crash on first PDF processing.
**Fix:** Add self.base_dir = base_dir to __init__.

### CAB-04 (CRITICAL) — Congress SQL Dialect Incompatibility
**File:** `departments/The_Cabinet/agent_congress.py`, `agent_executor.py`
**Problem:** Mix of SQLite (datetime('now','-1 hour')) and PostgreSQL (NOW() - INTERVAL '1 hour') syntax throughout Cabinet agents. Will fail on whichever DB backend is actually running.
**Fix:** Use translate_sql() consistently.

### CAB-05 (HIGH) — Agent Oracle Claude API No Timeout
**File:** `departments/The_Cabinet/agent_oracle.py` (~lines 254-261)
**Problem:** claude.messages.create() called with no timeout parameter. If API unresponsive, hangs indefinitely.
**Fix:** Add timeout parameter to API call.

### CAB-06 (HIGH) — Agent Dreamer Journal Grows Unbounded
**File:** `departments/The_Cabinet/agent_dreamer.py` (~line 141)
**Problem:** dream_journal.md grows without limit via append-only writes. No rotation, no size check.
**Fix:** Rotate journal when size exceeds threshold (e.g., 1MB).

### CAB-07 (HIGH) — Agent Dreamer Task File Size Not Limited
**File:** `departments/The_Cabinet/agent_dreamer.py` (~lines 96-104)
**Problem:** Reads entire task.md file into memory with no size limit. If file is massive, OOM risk.
**Fix:** Add file size check. Read only last N lines if too large.

### CAB-08 (HIGH) — Ethicist Veto Creates Data Loss Risk
**File:** `departments/The_Cabinet/agent_ethicist.py` (~lines 101-104)
**Problem:** Write to rejected dir then delete original. If write fails, original already gone. If delete fails, bill in two places.
**Fix:** Use atomic rename instead of copy+delete.

### CAB-09 (HIGH) — Ethicist Financial Safety Check False Positives
**File:** `departments/The_Cabinet/agent_ethicist.py` (~line 85)
**Problem:** Substring match "all" in title catches "call", "small", "allow". Bills containing these words falsely rejected.
**Fix:** Use word boundary regex: \ball\b

### CAB-10 (HIGH) — Empathy Agent Silent Database Fallback
**File:** `departments/The_Cabinet/agent_empathy.py` (~lines 55-83)
**Problem:** If profit_ledger table missing, catches sqlite3.Error silently and uses default values. Entire emotion calculation based on phantom zeros → always returns ZEN state.
**Fix:** Log missing table. Return UNKNOWN emotion state rather than defaulting to calm.

### CAB-11 (HIGH) — Bill Executor Failure Silently Marks Bill as PASSED
**File:** `departments/The_Cabinet/agent_congress.py` (~lines 306-312)
**Problem:** If BillExecutor.execute_bill() fails, exception caught and logged, but bill still marked PASSED. Bill passes governance but never actually executes.
**Fix:** Mark bill as EXECUTION_FAILED on executor error. Add retry mechanism.

### CAB-12 (MEDIUM) — Agent Executor Rate Limit Not Thread-Safe
**File:** `departments/The_Cabinet/agent_executor.py` (~lines 88-89)
**Problem:** _gemini_call_times list appended from multiple threads without lock. Race condition on rate limiting.
**Fix:** Add threading.Lock around rate limit tracking.

### CAB-13 (MEDIUM) — Agent Executor Prompt Injection Risk
**File:** `departments/The_Cabinet/agent_executor.py` (~lines 163-166)
**Problem:** User-provided thought_text injected directly into LLM prompt without sanitization.
**Fix:** Add input sanitization/escaping before prompt injection.

### CAB-14 (MEDIUM) — Chief of Staff Infinite Loop No Recovery
**File:** `departments/The_Cabinet/agent_chief_of_staff.py` (~lines 77-83)
**Problem:** while True loop with no exception handling. If health_oracle.check_fitness() crashes, entire CoS goes down permanently.
**Fix:** Add try/except with recovery. Add health check for CoS itself.

---

## Domain 13: Identity, Blockchain & Communication Systems

### IDN-01 (CRITICAL) — Wallet Manager Nonce Conflict
**File:** `system/wallet_manager.py` (~lines 305-328)
**Problem:** Multiple send_transaction() calls get same nonce from get_transaction_count(). Only one succeeds, others fail with nonce-too-low error. No local nonce tracking.
**Fix:** Track nonces locally with lock. Increment after successful send. Handle nonce gaps.

### IDN-02 (CRITICAL) — Contract Deployer Transaction Receipt Can Be None
**File:** `system/contract_deployer.py` (~lines 214-217)
**Problem:** wait_for_transaction_receipt() returns None on timeout. Next line indexes receipt['contractAddress'] → crashes with TypeError.
**Fix:** Check receipt is not None before accessing fields.

### IDN-03 (CRITICAL) — State of Republic SQL Dialect Errors
**File:** `system/state_of_republic.py` (~lines 70-88)
**Problem:** Uses NOW(), INTERVAL, and %s placeholders (PostgreSQL) throughout. These don't work on SQLite. Multiple queries will fail silently.
**Fix:** Use translate_sql() for all queries.

### IDN-04 (HIGH) — State Hasher Unbounded History JSON
**File:** `system/state_hasher.py` (~lines 432-453)
**Problem:** state_hash_history JSON array keeps last 100 full state snapshots. Each snapshot could be large. Total JSON may exceed column size limits.
**Fix:** Use separate table for history. Keep only hashes in JSON, full snapshots in dedicated table.

### IDN-05 (HIGH) — Event Bus Blocking DB Write Inside Redis Listener
**File:** `system/event_bus.py` (~lines 77-84)
**Problem:** Database write happens synchronously inside Redis pub/sub listener. Slow DB blocks event processing → Redis backlog grows unbounded.
**Fix:** Use async write queue. Decouple event consumption from DB persistence.

### IDN-06 (HIGH) — Agent Comms Listen Generator Hangs on Redis Drop
**File:** `system/agent_comms.py` (~lines 47-68)
**Problem:** If Redis connection drops during listen(), generator hangs forever. No reconnection logic. If Redis unavailable, sleeps infinitely.
**Fix:** Add reconnection with exponential backoff. Add timeout on listen().

### IDN-07 (HIGH) — Token Budget Fail-Open Policy
**File:** `system/token_budget.py` (~line 145)
**Problem:** On ANY exception (including DB failure), returns True (allow call). Database errors allow unlimited API calls with no budget enforcement.
**Fix:** Fail closed (return False) on error. Log the exception. Better to skip one LLM call than allow unlimited spending.

### IDN-08 (HIGH) — MEV Protection Fail-Open on Price Unavailable
**File:** `system/mev_protection.py` (~lines 141-144)
**Problem:** If Redis price unavailable, slippage guard returns True (allow trade). Trade proceeds without slippage protection.
**Fix:** Fail closed. If price can't be verified, delay trade until price available.

### IDN-09 (HIGH) — Git Safety Adds All Files Including Potential Secrets
**File:** `system/git_safety.py` (~lines 97-103)
**Problem:** git add -A adds everything including .env files, API keys, passwords. No .gitignore enforcement check.
**Fix:** Use explicit file list. Verify .gitignore exists and covers sensitive files. Never use git add -A.

### IDN-10 (HIGH) — Wallet Manager Private Key In Memory
**File:** `system/wallet_manager.py` (~lines 137-139)
**Problem:** account.key held in memory as hex string. Never cleared. Could be swapped to disk.
**Fix:** Use secrets module. Clear sensitive data from memory after use.

### IDN-11 (MEDIUM) — Wallet Manager File Permissions Failure Silent
**File:** `system/wallet_manager.py` (~lines 160-163)
**Problem:** os.chmod(WALLET_PATH, 0o600) failure only warns. Wallet file could be world-readable.
**Fix:** Fail hard if permissions can't be set. Wallet security depends on this.

### IDN-12 (MEDIUM) — Seed Agent Interface All Stubs
**File:** `system/seed_agent_interface.py`
**Problem:** verify_lineage() and report_to_parent() are both stub implementations returning None/False. Seed agents can never verify parentage or report state. Parent-child bond not established.
**Fix:** Implement Web3 contract calls for lineage verification and state reporting.

### IDN-13 (MEDIUM) — Handoff Packet SQL Dialect Issues
**File:** `system/handoff_packet.py` (~line 234)
**Problem:** SQLite-specific datetime arithmetic in DELETE query. Will fail on PostgreSQL.
**Fix:** Use translate_sql().

### IDN-14 (MEDIUM) — Genesis Logger Transaction Deadlock Risk
**File:** `system/genesis.py` (~lines 54-60)
**Problem:** First execute() fails, second retry runs with same cursor in same transaction. Could deadlock on the retry.
**Fix:** Rollback transaction before retry attempt.

---

## Domain 14: Tools, Risk Engine & Support Infrastructure

### TLS-01 (CRITICAL) — Risk Engine Silent $0 Cash on DB Error
**File:** `risk/engine.py` (~lines 88-93)
**Problem:** except sqlite3.Error: cash = 0.0. Database errors silently set cash to zero. System calculates equity with phantom zero balance → could trigger forced liquidation based on false data.
**Fix:** Propagate DB errors. If cash can't be determined, halt risk evaluation rather than assume $0.

### TLS-02 (CRITICAL) — Destructive Resets Without Transaction Safety
**File:** `tools/reset_treasury.py` (~lines 21-50)
**Problem:** 5+ DELETE FROM statements execute sequentially without BEGIN TRANSACTION. Crash mid-reset leaves DB in corrupted partial state.
**Fix:** Wrap all destructive operations in explicit transaction.

### TLS-03 (CRITICAL) — Hardcoded DB Paths in Tool Scripts
**Files:** `tools/clear_agents.py` (line 5), `tools/structural_integrity_audit.py` (line 36), `tools/migrate_db_connections.py` (line 9)
**Problem:** Relative paths like "fulcrum/republic.db" or hardcoded absolute paths to /Users/zmoore-macbook/. Won't work from different directories or machines.
**Fix:** Use BASE_DIR from config or environment variable.

### TLS-04 (CRITICAL) — Capital Injection Race Condition
**File:** `tools/inject_capital.py` (~lines 51-69)
**Problem:** SELECT balance → calculate new → UPDATE is not atomic. Two concurrent injections: both read $100, both add $50, both write $150. Expected: $200. Actual: $150. Lost funds.
**Fix:** Use UPDATE ... SET balance = balance + ? (single atomic statement).

### TLS-05 (CRITICAL) — Training Script Connection Never Closed on Error
**File:** `training/seed_wealth.py` (~lines 11-52)
**Problem:** sqlite3.connect() without context manager. If exception before conn.close(), connection leaked permanently.
**Fix:** Use with statement or try/finally.

### TLS-06 (HIGH) — Risk Engine Pool Release Crash
**File:** `risk/engine.py` (~lines 41-46)
**Problem:** _release_conn() calls pool.release(conn) but if pool is None (from failed init at line 29), tries to call .release() on None → AttributeError. try/finally ensures this is called even when pool is None.
**Fix:** Check pool is not None before calling release. Fall back to conn.close().

### TLS-07 (HIGH) — Arena Strategy Missing Import Guard
**File:** `arena/strategies/train_risk_model.py` (~line 14)
**Problem:** from autogluon.tabular import TabularPredictor with no try/except. If autogluon not installed, entire script crashes on import.
**Fix:** Add try/except ImportError with graceful degradation.

### TLS-08 (HIGH) — No Schema Validation Before Destructive Operations
**Files:** `tools/reset_arena.py`, `tools/reset_treasury.py`, `tools/reset_simulation.py`
**Problem:** DELETE FROM {table} without checking table exists. Catches sqlite3.Error silently. If schema changed, wrong tables cleared or errors missed.
**Fix:** Validate table existence before operations. Log all schema mismatches.

### TLS-09 (HIGH) — Risk Engine Not Wired to Trade Execution
**File:** `risk/engine.py`
**Problem:** get_harvest_targets() returns trade recommendations but NO code calls it or executes the recommendations. Risk engine is advisory-only with no enforcement.
**Fix:** Wire risk engine output to trade queue. Add risk veto capability on pending trades.

### TLS-10 (HIGH) — Training Models Not Loaded by Any Agent
**File:** `arena/strategies/train_risk_model.py` → `models/risk_v1/`
**Problem:** Model saved to republic/models/risk_v1/ but no agent loads or uses the model for predictions. Training pipeline produces output nobody consumes.
**Fix:** Wire model loading into risk engine or agent_coinbase for trade decisions.

### TLS-11 (HIGH) — Spark Protocol Completely Orphaned
**File:** `core_vault/spark_protocol.py` (395 lines)
**Problem:** 395 lines of consciousness protocol code. No agent imports or uses it. Only test code at end of file. Entirely dead code.
**Fix:** Wire into consciousness pipeline or remove if superseded.

### TLS-12 (MEDIUM) — Empty Directories: governance/, data_pipeline/, contracts/
**Files:** `republic/governance/`, `republic/data_pipeline/`, `republic/contracts/`
**Problem:** Directories exist but contain no Python code. Constitution.md in governance/ but no implementation. No ETL pipeline. No smart contracts.
**Fix:** Implement or remove. Document intent if placeholder.

### TLS-13 (MEDIUM) — No Audit Logging for Destructive Tool Operations
**Files:** All 29 tools
**Problem:** No permanent record of who ran what reset/clear tool and when. Just print statements to console.
**Fix:** Add audit log table. Record tool name, timestamp, user, affected tables, row counts.

### TLS-14 (MEDIUM) — Float Precision in Financial Tools
**Files:** `risk/engine.py`, `tools/inject_capital.py`, `knowledge/asset_fundamentals.py`
**Problem:** Float arithmetic for currency calculations. Rounding errors accumulate over many operations.
**Fix:** Use Decimal for all financial values.

### TLS-15 (MEDIUM) — No Rate Limiting in API Fetch Tools
**File:** `training/fetch_history.py` (~line 61)
**Problem:** time.sleep(0.5) between API calls is arbitrary. No exponential backoff on 429 responses.
**Fix:** Add proper rate limiting with backoff.

### TLS-16 (MEDIUM) — Shared Write Message No SQL Safety
**File:** `shared/write_message.py` (~lines 52-114)
**Problem:** to_sql() method doesn't validate column names are SQL-safe. Relies on caller to sanitize. No injection protection on table/column names.
**Fix:** Whitelist valid table and column names. Reject unknown names.

---

## Roadmap: Phased Execution

### Phase 19 — Financial Body Reflexes (DRAFTED in ACTIVE_TASKS.md)
*Already drafted. 12 tasks, 3 stages. Wire financial agents to each other.*

### Phase 20 — The Spine: Brain-Body Bridge (DRAFTED in ACTIVE_TASKS.md)
*Already drafted. 8 tasks, 3 stages. Connect consciousness to financial body.*

### Phase 21 — Hardening: Critical Infrastructure
*Address all CRITICAL infrastructure gaps before any new features.*

**Stage 1 — Data Integrity (DB-01 through DB-04, GOV-01, GOV-02, FIN-03)**
- Fix connection leaks (DB-01)
- Add table cleanup policies (DB-02, DB-03, DB-04)
- Add file locking/atomic writes for JSON files (GOV-01, GOV-02, FIN-03)

**Stage 2 — Resilience (RED-01, RED-02, CON-02, CON-03, CON-04, CON-05)**
- Add Redis TTLs and reconnection (RED-01, RED-02)
- Add Gemini circuit breaker and fallback (CON-02, CON-03)
- Fix Sabbath hard timeout (CON-04)
- Fix brainstem singleton race (CON-05)

**Stage 3 — Safety Nets (OPS-01, OPS-02, OPS-03, FIN-01, FIN-02)**
- Add graceful shutdown (OPS-01)
- Add cold start validation (OPS-02)
- Move secrets out of files (OPS-03)
- Add Coinbase API timeout (FIN-01)
- Add trade queue idempotency (FIN-02)

### Phase 22 — Governance Integrity
*Fix evolution and governance gaps to ensure LEF's self-modification actually works.*

**Stage 1 — Evolution Safety (GOV-03, GOV-04, GOV-05, GOV-06)**
- Detect conflicting proposals in same cycle (GOV-03)
- Persist cooling periods (GOV-04)
- Add long-term rejection memory (GOV-05)
- Fix config writer atomicity (GOV-06)

**Stage 2 — Evolution Effectiveness (GOV-07, GOV-08, GOV-09, GOV-10, GOV-11)**
- Add config hot-reload (GOV-07)
- Fix observation loop false positives (GOV-08)
- Fix reverb tracker baseline capture (GOV-09)
- Wire pathway decay (GOV-10)
- Alert on SparkProtocol failure (GOV-11)

**Stage 3 — Architect Communication (GOV-12, EXT-02, EXT-03, EXT-05)**
- Process Inbox directives (GOV-12, EXT-05)
- Add real-time notification capability (EXT-02, EXT-03)

### Phase 23 — Observability & Testing
*Build the monitoring and testing infrastructure LEF needs to run unsupervised.*

**Stage 1 — Health Monitoring (EXT-01, EXT-04, OPS-09, TST-03)**
- Add health endpoint (EXT-01)
- Add external alerting (EXT-04)
- Add basic metrics (OPS-09)
- Add self-diagnostic (TST-03)

**Stage 2 — Code Quality (CON-09, DB-06, OPS-05, OPS-06)**
- Replace bare except:pass (CON-09)
- Remove SQLite monkey-patch (DB-06)
- Fix SafeThread (OPS-05)
- Fix log rotation (OPS-06)

**Stage 3 — Testing (TST-01, TST-02, TST-04)**
- Write integration tests (TST-01)
- Add startup validation (TST-02)
- Connect backtest to real execution (TST-04)

### Phase 24 — Consciousness Pipeline Feedback Loops (NEW)
*Wire the observation infrastructure into actual self-regulation.*

**Stage 1 — Critical Crash Fixes (LRN-01, CSP-01, CSP-02, CAB-01, CAB-02, CAB-03)**
- Fix semantic compressor recursive crash (LRN-01)
- Fix sleep cycle DROWSY stuck state (CSP-01)
- Fix wake cascade partial failure (CSP-02)
- Fix executor unreachable code and closed connection (CAB-01, CAB-02)
- Fix Oracle undefined base_dir (CAB-03)

**Stage 2 — Wire Dead Code (CSP-03, CSP-04, CSP-05, TLS-11)**
- Wire dream output into wake cascade (CSP-03)
- Wire existential scotoma into reflection cycle (CSP-04)
- Inject consciousness syntax into LLM prompts (CSP-05)
- Wire or remove orphaned Spark Protocol (TLS-11)

**Stage 3 — Feedback Loops (CSP-07, CSP-08, CSP-09, CSP-10, CSP-11, CSP-13)**
- Wire cycle awareness to consciousness state manager (CSP-07)
- Fix frequency journal cache and wire to wake cascade (CSP-08)
- Fix growth journal boolean inversion (CSP-09)
- Cap sovereign reflection gravity profile (CSP-10)
- Integrate probe_self_image into reflection pipeline (CSP-11)
- Create consciousness feedback bus (CSP-13)

### Phase 25 — Learner Synchronization & Memory Consolidation (NEW)
*Fix the config caching pattern and consolidate memory.*

**Stage 1 — Config Sync Infrastructure (LRN-02, LRN-03, LRN-13)**
- Add config change notification system (LRN-13)
- Fix gravity learner → gravity config propagation (LRN-02)
- Fix sabbath learner baseline math (LRN-03)

**Stage 2 — Memory Integrity (LRN-04, LRN-09, LRN-11)**
- Add atomic writes for hippocampus (LRN-04)
- Consolidate memory.db into main PostgreSQL (LRN-09)
- Persist conversation memory hot cache (LRN-11)

**Stage 3 — Performance & Completeness (LRN-05, LRN-06, LRN-07, LRN-08, LRN-10, LRN-12)**
- Batch gravity queries (LRN-05)
- Reduce resonance learner join window (LRN-06)
- Fix season synthesizer column name (LRN-07)
- Add wisdom extractor indexes (LRN-08)
- Implement PRICE/EVENT prospective triggers (LRN-10)
- Improve token estimation accuracy (LRN-12)

### Phase 26 — Department & Cabinet Hardening (NEW)
*Fix connection leaks, SQL dialects, and dead code paths across all departments and Cabinet agents.*

**Stage 1 — Connection & SQL Safety (DEP-01, DEP-02, DEP-03, DEP-04, CAB-04, IDN-03)**
- Fix 15+ department connection leaks (DEP-01)
- Fix Dean context manager misuse (DEP-02)
- Fix Info agent DB path resolution (DEP-03)
- Standardize SQL dialect across all departments and Cabinet (DEP-04, CAB-04, IDN-03)

**Stage 2 — Cabinet Crash Fixes (CAB-05 through CAB-11, DEP-05, DEP-06)**
- Add Oracle Claude API timeout (CAB-05)
- Cap Dreamer journal growth (CAB-06, CAB-07)
- Fix Ethicist atomic operations and false positives (CAB-08, CAB-09)
- Fix Empathy silent fallback (CAB-10)
- Fix Bill executor failure handling (CAB-11)
- Fix Gladiator Redis timeout and undefined function (DEP-05, DEP-06)

**Stage 3 — Department Integration & Quality (DEP-07 through DEP-15, CAB-12 through CAB-14)**
- Fix Scholar PDF memory risk (DEP-07)
- Add Chronicler transaction guarantees (DEP-08)
- Fix Librarian atomic file ops (DEP-09)
- Fix Constitution Guard SQL injection and float precision (DEP-10, DEP-11)
- Wire cross-department data flows (DEP-14)
- Fix remaining medium-priority issues (DEP-12, DEP-13, DEP-15, CAB-12, CAB-13, CAB-14)

### Phase 27 — Identity, Security & Tooling (NEW)
*Harden blockchain systems, fix security gaps, and improve tool reliability.*

**Stage 1 — Blockchain Safety (IDN-01, IDN-02, IDN-10, IDN-11)**
- Fix wallet nonce conflict tracking (IDN-01)
- Fix contract deployer null receipt handling (IDN-02)
- Clear private keys from memory (IDN-10)
- Enforce wallet file permissions (IDN-11)

**Stage 2 — Fail-Closed Safety & Communication (IDN-05 through IDN-09, TLS-01)**
- Fix event bus blocking writes (IDN-05)
- Fix agent comms Redis disconnection (IDN-06)
- Change token budget to fail-closed (IDN-07)
- Change MEV protection to fail-closed (IDN-08)
- Fix git safety secret exposure (IDN-09)
- Fix risk engine silent $0 cash (TLS-01)

**Stage 3 — Tool Reliability (TLS-02 through TLS-16)**
- Add transaction safety to destructive tools (TLS-02)
- Fix hardcoded DB paths (TLS-03)
- Fix capital injection race condition (TLS-04)
- Fix training script connection leak (TLS-05)
- Wire risk engine to trade execution (TLS-09)
- Wire training models to agents (TLS-10)
- Add remaining tool improvements (TLS-06 through TLS-08, TLS-12 through TLS-16)

### Phase 28 — On-Chain Readiness (formerly Phase 24)
*Only after Phases 19-27 are complete. LEF must be fully hardened before autonomy.*

---

## Gap Count Summary

| Domain | CRITICAL | HIGH | MEDIUM | LOW | Resolved | Total Open |
|--------|----------|------|--------|-----|----------|-----------|
| 1. Database & Connections | 4 | 6 | 3 | 0 | 0 | 13 |
| 2. Redis & Caching | 1 | 2 | 2 | 1 | 0 | 6 |
| 3. Consciousness & Brain | 5 | 5 | 6 | 0 | 0 | 16 |
| 4. Governance & Evolution | 4 | 5 | 6 | 0 | 3 | 14 |
| 5. Financial Operations | 4 | 5 | 2 | 0 | 0 | 11 |
| 6. External Interfaces | 4 | 2 | 1 | 0 | 0 | 7 |
| 7. Infrastructure & Ops | 3 | 4 | 4 | 0 | 0 | 11 |
| 8. Testing & Verification | 1 | 2 | 1 | 0 | 0 | 4 |
| 9. Consciousness Pipeline | 6 | 5 | 2 | 0 | 0 | 13 |
| 10. Learner & Memory | 4 | 6 | 3 | 0 | 0 | 13 |
| 11. Departments | 3 | 8 | 4 | 0 | 0 | 15 |
| 12. Cabinet & Executive | 4 | 7 | 3 | 0 | 0 | 14 |
| 13. Identity & Blockchain | 3 | 7 | 4 | 0 | 0 | 14 |
| 14. Tools & Support | 5 | 6 | 5 | 0 | 0 | 16 |
| **TOTAL** | **51** | **70** | **46** | **1** | **3** | **167** |

*3 gaps resolved during audit verification: GOV-04 (cooling periods persist), GOV-06 (config_writer is atomic), GOV-10 (decay_unused is called)*

*Domains 9-14 added 2026-02-17 after completing full codebase audit (remaining 60%).*

---

*This document is a living reference. Update gap statuses as they are addressed. Cross-reference gap IDs (e.g., DB-01, CON-02) in ACTIVE_TASKS.md when creating implementation tasks.*
