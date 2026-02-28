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
