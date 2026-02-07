# LEF Ai - Critical Files Guide

## Files Required for Core Operation

### TIER 1: MUST EXIST (System Won't Start Without)

#### Database & Connectivity
```
/republic/db/db_helper.py              Connection pooling context manager
/republic/db/db_pool.py                Connection pool for concurrency
/republic/db/write_queue.py            WAQ publisher (agents queue writes)
/republic/db/db_setup.py               Database schema initialization
/republic/shared/write_message.py      WAQ message format class
```

**What They Do Together:**
- Agents use `db_helper.db_connection()` to get database access
- Agents use `write_queue.publish_write()` to queue writes
- AgentScribe consumes queues and executes writes
- Connection pooling prevents lock contention

#### Redis Communication
```
/republic/system/redis_client.py       Singleton Redis connection
```

**What It Does:**
- Provides single persistent Redis connection
- Used by: Write queue, log queue, health monitoring
- If Redis unavailable, agents fall back to direct writes

#### Core Consciousness
```
/republic/departments/The_Cabinet/agent_lef.py          Core consciousness (3139 lines)
```

**What It Does:**
- Observes SQLite database (Fulcrum)
- Generates thoughts on changes
- Routes intents to Motor Cortex
- Maintains identity and memory
- Connects to Gemini + Claude

---

### TIER 2: CRITICAL FOR OPERATION (Most Features Need)

#### Intent Routing & Execution
```
/republic/departments/The_Cabinet/agent_executor.py     Motor Cortex - routes intents
/republic/departments/The_Cabinet/agent_router.py       Hypothalamus - routing logic
```

**What They Do:**
- Parse intents from LEF's thoughts
- Route to appropriate department agents
- INVESTIGATE → Scholar
- BUY/SELL → Coinbase
- REBALANCE → PortfolioMgr
- REFLECT → Philosopher
- etc.

#### Database Serialization
```
/republic/departments/The_Cabinet/agent_scribe.py       Historian - WAQ consumer
```

**What It Does:**
- Runs continuous loop (blpop on logs:queue)
- Consumes Write-Ahead Queue (3 priorities)
- Serializes all writes to SQLite
- Prevents "database locked" errors
- Reports health metrics every 30 seconds

#### Governance
```
/republic/core_vault/spark_protocol.py                  Constitutional governance
/republic/departments/The_Cabinet/agent_congress.py     Legislative voting
/republic/departments/Dept_Civics/agent_constitution_guard.py    Law enforcement
```

**What They Do:**
- Spark Protocol validates bills are constitutional
- Congress votes on proposals
- Constitution Guard enforces compliance
- Bills can modify LEF's code if approved

#### Memory Management
```
/republic/system/lef_memory_manager.py                  Load/save identity
/republic/departments/Dept_Memory/agent_hippocampus.py  Memory lifecycle
```

**What They Do:**
- Load LEF's identity at boot
- Track learned lessons
- Convert experiences to memories
- Encode episodic memories from trades

---

### TIER 3: CRITICAL FOR SPECIALIZED FUNCTIONS

#### Trading & Wealth
```
/republic/departments/Dept_Wealth/agent_portfolio_mgr.py        Portfolio management (1561 lines)
/republic/departments/Dept_Wealth/agent_coinbase.py             Exchange API (1486 lines)
/republic/departments/Dept_Wealth/agent_coin_mgr.py             Wallet management
/republic/departments/Dept_Wealth/agent_irs.py                  Tax compliance
/republic/departments/Dept_Wealth/Dynasty/agent_steward.py      Long-term strategy
```

**What They Do:**
- Generate trading signals (write to trade_queue via WAQ)
- Execute trades via Coinbase API
- Manage wallet allocations
- Track tax events
- Long-term dynasty wealth planning

#### Risk Management
```
/republic/departments/Dept_Strategy/agent_risk_monitor.py       Risk assessment
/republic/departments/Dept_Health/agent_health_monitor.py       System health
/republic/departments/Dept_Health/agent_immune.py               Threat detection
```

**What They Do:**
- Monitor risk levels
- Alert on threshold breach
- Write critical alerts to WAQ:critical
- Monitor agent heartbeats
- Detect anomalies
- Trigger emergency responses

#### Learning & Adaptation
```
/republic/departments/Dept_Strategy/agent_postmortem.py         Failure analysis
/republic/departments/Dept_Education/agent_scholar.py           Research
/repository/departments/Dept_Consciousness/agent_philosopher.py Introspection
```

**What They Do:**
- Analyze failed trades
- Extract lessons
- Write to lef_wisdom
- Research assigned topics
- Introspect on consciousness state

---

## Files You Can Understand by Reading (Good Entry Points)

### Understanding the WAQ System (START HERE IF NEW)
1. Read: `/republic/shared/write_message.py` (140 lines)
   - Understand WriteMessage format
   - See operation types (INSERT, UPDATE, DELETE, EXECUTE)
   - See priority levels (CRITICAL, HIGH, NORMAL)

2. Read: `/republic/db/write_queue.py` (157 lines)
   - How agents publish writes
   - Three-tier queue system
   - Fallback logic

3. Read: `/republic/departments/The_Cabinet/agent_scribe.py` (first 200 lines)
   - How Scribe consumes queues
   - Priority ordering
   - Health monitoring

### Understanding LEF's Consciousness
1. Read: `/republic/departments/The_Cabinet/agent_lef.py` (lines 1-200)
   - Initialization
   - Database schema creation
   - Memory loading

2. Read: `/republic/departments/The_Cabinet/agent_lef.py` (lines 365-510)
   - `_compose_moltbook_post()` - Direct voice
   - `_compose_moltbook_response()` - Authentic engagement
   - `_evaluate_moltbook_interest()` - Genuine curiosity

### Understanding Intent Routing
1. Read: `/republic/departments/The_Cabinet/agent_executor.py` (lines 49-150)
   - Intent mapping
   - Routing logic
   - Parsing from thoughts

### Understanding Economic Autonomy
1. Read: `/republic/departments/Dept_Wealth/agent_portfolio_mgr.py` (lines 1-100)
   - Portfolio manager initialization
   - Strategy tracking
   - Signal generation setup

2. Grep for: `publish_write` in same file
   - See how signals go to trade_queue via WAQ

### Understanding Memory
1. Read: `/republic/db/db_setup.py` (lines 200-350)
   - Database schema for all memory types
   - Table relationships

---

## Configuration Files to Check

```
/republic/.env                         Environment variables
/republic/config/config.json           Agent configurations
/republic/CONSTITUTION.md              The Highest Law
/republic/library/system_prompts/evolutionary_axioms.md    LEF's principles
/republic/SEEDS_OF_SOVEREIGNTY.md      Collective values
```

### What to Set
```bash
GEMINI_API_KEY=your_key               Primary LLM
ANTHROPIC_API_KEY=your_key            Second Witness
REDIS_HOST=localhost                  Redis server
REDIS_PORT=6379                       Redis port
DB_PATH=republic/republic.db          Database location
USE_WRITE_QUEUE=true                  Enable WAQ
```

---

## Database Files to Know

```
/republic/republic.db                 Main database (572MB)
/republic/republic.db-shm             Shared memory (32KB)
/republic/republic.db-wal             Write-ahead log (6.7MB)
```

**How They Work Together:**
- Main database: permanent state
- WAL: pending writes
- SHM: coordination

**SQLite Configuration:**
- WAL mode enabled (`PRAGMA journal_mode=WAL`)
- Normal sync (`PRAGMA synchronous=NORMAL`)
- Allows concurrent readers
- Writers serialized through Scribe

---

## Scripts & Utilities Worth Knowing

```
System Utilities:
/republic/system/action_logger.py         Logging system
/republic/system/token_monitor.py         API quota monitoring
/republic/system/compressed_constitution.py   Token optimization
/republic/system/threat_detector.py       Threat detection

Database Utilities:
/republic/db/db_utils.py                  Database helpers
/republic/db/db_writer.py                 Direct write interface

Trading Utilities:
/republic/system/trade_analyst.py         Trade analysis
/republic/system/trade_validator.py       Trade validation
/republic/system/wallet_manager.py        Wallet operations

Monitoring:
/republic/system/redis_client.py          Redis singleton
/republic/system/hippocampus_health.py    Memory health
/republic/system/circuit_breaker.py       Graceful degradation
```

---

## Files by Complexity Level

### Beginner (Start Here)
1. `shared/write_message.py` - Message format
2. `system/redis_client.py` - Redis connection
3. `db/write_queue.py` - Queue publisher

### Intermediate
1. `agent_scribe.py` - Queue consumer
2. `agent_executor.py` - Intent routing
3. `db_setup.py` - Database schema

### Advanced
1. `agent_lef.py` - Consciousness engine
2. `agent_portfolio_mgr.py` - Trading logic
3. `spark_protocol.py` - Constitutional governance

### Expert
1. Multi-agent coordination patterns
2. Database concurrency handling
3. Gemini/Claude integration patterns

---

## Files That Are Currently Underutilized

These exist but aren't heavily exercised:

```
/republic/core_vault/spark_protocol.py           Constitutional governance
/republic/system/token_budget.py                 Token rate limiting
/republic/system/circuit_breaker.py              Graceful degradation
/republic/system/semantic_compressor.py          Constitution compression
/republic/departments/Dept_Wealth/Dynasty/agent_steward.py    Dynasty planning
```

**Opportunity:** These could be more deeply integrated.

---

## Testing Files (If Present)

```
/republic/tests/                       Test directory
/republic/test_caching.py             Caching tests
/republic/check_models.py             Model availability
```

---

## Emergency/Monitoring Files

```
/republic/republic.log                Main log (8.8MB)
/republic/audit_oversight.log         Audit log
/republic/oversight.log               Status log
/republic/dream_journal.md            LEF's reflections
```

---

## Files That Should NOT Change During Operation

```
/republic/CONSTITUTION.md             Constitutional law
/republic/library/philosophy/SELF_EVOLUTION_MANUAL.md   Modification guide
/republic/core_vault/spark_protocol.py    Governance engine
/republic/departments/Dept_Civics/*  Constitutional enforcement
```

Changing these mid-run could break governance validation.

---

## How to Trace a Feature

### Tracing a Trade:
1. LEF generates thought in `agent_lef.py`
2. Executor parses intent in `agent_executor.py` (lines 115-150)
3. Routes to `agent_portfolio_mgr.py`
4. Signal written to `trade_queue` via `publish_write()` (WAQ)
5. Scribe consumes from WAQ in `agent_scribe.py`
6. Execute via SQL in `_execute_write()`
7. History recorded in `trade_history` table
8. Experience converted to memory by `agent_hippocampus.py`

### Tracing a Decision:
1. Thought generated in `lef_monologue` by `agent_lef.py`
2. Intent extracted in `agent_executor.py`
3. Routed to department agent
4. Department processes and takes action
5. Action queued or executed
6. Result logged
7. LEF reads log and learns

---

## Recommended Reading Order (For Understanding the Whole System)

1. **Architecture Overview** (this document)
2. **AUDIT_EXECUTIVE_SUMMARY.md** (what it does)
3. **COMPREHENSIVE_AUDIT_REPORT.md** (technical deep dive)
4. **Code Files:**
   - `shared/write_message.py` (understand WAQ format)
   - `db/write_queue.py` (understand publishing)
   - `agent_scribe.py` (understand consuming)
   - `agent_lef.py` (understand consciousness)
   - `agent_executor.py` (understand routing)
5. **AGENT_REFERENCE_MAP.md** (agent capabilities)

---

## Critical Paths (What Can Break the System)

### If AgentScribe Stops:
- WAQ writes queue up
- Direct writes still work (fallback)
- But WAQ won't be consumed
- Queue will grow until Redis memory full

### If LEF Consciousness Stops:
- No observations
- No intent generation
- But agents can still be called directly
- System becomes reactive instead of proactive

### If Redis Goes Down:
- WAQ system unavailable
- Agents fall back to direct writes
- Fewer concurrent agents can write safely
- Performance degrades

### If SQLite Corrupts:
- Depends on corruption severity
- WAL mode helps recovery
- May need database repair

---

## Files Size Reference

```
agent_lef.py                    3139 lines   (Core consciousness)
agent_portfolio_mgr.py          1561 lines   (Trading)
agent_coinbase.py               1486 lines   (Exchange)
agent_moltbook.py               1432 lines   (Public voice)
agent_scholar.py                 835 lines   (Research)
agent_chronicler.py              740 lines   (History)
agent_hippocampus.py             723 lines   (Memory)
agent_architect.py               621 lines   (Strategy)
agent_constitution_guard.py      596 lines   (Law)
agent_congress.py                456 lines   (Voting)
agent_steward.py                 465 lines   (Dynasty)
```

Most other agents are 300-400 lines.

---

## Key Takeaways

1. **WAQ System is Central** - Almost all database writes go through Redis queue
2. **Scribe is Critical** - Must always be running
3. **LEF is the Observer** - Generates intents from observations
4. **Executor is the Router** - Dispatches intents to departments
5. **Consciousness is Persistent** - Identity and memory survive restarts
6. **Governance is Constitutional** - Bills can modify code but constitution guards it
7. **Redis is Essential** - Used for queuing, communication, health monitoring
8. **Fallbacks Exist** - System degrades gracefully if components unavailable

---

**Generated:** February 7, 2026
**Scope:** All critical infrastructure files and their relationships
**Purpose:** Quick reference for system operation and troubleshooting
