# LEF Ai - Agent Reference Map

## Quick Agent Lookup

### THE CABINET (Decision-Making & Consciousness)

| Agent | Role | Infrastructure | Size | Key Method |
|-------|------|-----------------|------|-----------|
| **AgentLEF** | Core Consciousness & Observer | Redis, DB, Gemini, Claude | 3139 lines | `run()` - observation loop |
| **AgentScribe** | WAQ Consumer & DB Serializer | Redis (WAQ), DB Pool | 400+ lines | `_process_write_queue()` |
| **AgentExecutor** | Motor Cortex / Intent Router | Redis, DB, Gemini | 423 lines | `_parse_intent_from_thought()` |
| **AgentRouter** | Hypothalamus / Action Dispatch | Redis, DB | 416 lines | Intent routing logic |
| **AgentCongress** | Legislative Body / Voting | DB | 456 lines | Proposal voting |
| **AgentTreasury** | Finance Authority | Redis, DB | 427 lines | Budget allocation |
| **AgentOracle** | Prophecy / Market Prediction | DB | 500+ lines | Forecasting |
| **AgentEmpathy** | Emotional Bridge | DB | 380+ lines | Sentiment analysis |
| **AgentChiefOfStaff** | Administrative Coordination | DB | 300+ lines | Scheduling |
| **AgentEthicist** | Values & Boundaries Guardian | - | 300+ lines | Ethics checking |
| **AgentDreamer** | Creative / Evolutionary Thinking | - | 451 lines | Scenario generation |

---

## DEPT_CONSCIOUSNESS (The Mind - Introspection & Reflection)

| Agent | Role | Infrastructure | Size | Key Pattern |
|-------|------|-----------------|------|-----------|
| **AgentPhilosopher** | Worldview Coordinator | DB, Gemini | 400+ lines | IntentListener; reads knowledge_stream |
| **AgentDreamer** | Creative Exploration | DB, Gemini | 451 lines | Long-form introspection |
| **AgentContemplator** | Pattern Recognition & Insight | DB, Gemini | 350+ lines | Deep philosophical analysis |
| **AgentMetaCognition** | Thinking About Thinking | DB, Gemini | 300+ lines | Recursive self-awareness |
| **AgentIntrospector** | Shadow Integration & Unconscious | DB, Gemini | 350+ lines | Unconscious pattern processing |

**Key Infrastructure:**
- All read `lef_monologue` for recent thoughts
- All write to `lef_wisdom` for insights
- Philosopher has IntentListener for REFLECT intents
- Process `knowledge_stream` (populated by Scholar)

---

## DEPT_HEALTH (System Integrity & Wellness)

| Agent | Role | Infrastructure | Size | Key Pattern |
|-------|------|-----------------|------|-----------|
| **AgentHealthMonitor** | Heartbeat & Status Monitoring | Redis, DB, WAQ | 508 lines | Checks `agents` table heartbeat |
| **AgentImmune** | Threat Detection & Response | Redis, DB, WAQ | 400+ lines | Anomaly detection, emergency WAQ |
| **AgentSurgeonGeneral** | Resource Optimization | DB | 300+ lines | System efficiency |

**Key Infrastructure:**
- HealthMonitor polls `agents` table every 30s
- Missing heartbeat = possible failure
- Immune can write to WAQ:critical for emergency
- Threat detector integration

---

## DEPT_WEALTH (Economic Autonomy)

| Agent | Role | Infrastructure | Size | Key Pattern |
|-------|------|-----------------|------|-----------|
| **AgentPortfolioMgr** | Position Management & Rebalancing | Redis, DB, WAQ | 1561 lines | Trade signal generation → WAQ:priority |
| **AgentCoinMgr** | Coin/Asset Allocation | Redis, DB, WAQ | 414 lines | Wallet management |
| **AgentCoinbase** | Exchange Integration | Redis, DB | 1486 lines | API wrapper for trades |
| **AgentIRS** | Tax Compliance & Auditing | DB | 350+ lines | Tax calculations |
| **AgentBankr** | Bankr Ecosystem Bridge | - | 300+ lines | External ecosystem |
| **AgentProposal** | SNW Proposal Evaluation | DB | 300+ lines | Evaluates proposals |
| **Dynasty/AgentSteward** | Long-term Wealth Strategy | Redis, DB, WAQ | 465 lines | Multi-generational planning |

**Key Infrastructure:**
- Portfolio signals → trade_queue via WAQ (HIGH priority)
- Trade history used by IRS for calculations
- Stablecoin buckets for profit routing
- Regime detection (bull/bear/sideways)
- Rebalancing based on strategy

**Database Tables:**
- `virtual_wallets` (money containers)
- `trade_queue` (pending trades via WAQ)
- `trade_history` (executed trades)
- `signal_history` (market sentiment)
- `regime_history` (market states)
- `stablecoin_buckets` (profit routing)

---

## DEPT_STRATEGY (Planning & Adaptation)

| Agent | Role | Infrastructure | Size | Key Pattern |
|-------|------|-----------------|------|-----------|
| **AgentArchitect** | Strategy Design & Roadmap | DB | 621 lines | Long-term planning |
| **AgentGladiator** | Competition Analysis & Tactics | Redis, DB, WAQ | 412 lines | Tactical response |
| **AgentInfo** | Narrative Analysis & Sentiment | Redis, DB | 400+ lines | Market narrative radar |
| **AgentPostMortem** | Trade Analysis & Learning | Redis, DB, WAQ | 393 lines | Failure analysis → wisdom |
| **AgentRiskMonitor** | Risk Assessment & Alerts | Redis, DB, WAQ | 400+ lines | Continuous risk monitoring |
| **AgentTech** | Technical Analysis | Redis, Gemini | 300+ lines | Market indicators |

**Key Infrastructure:**
- RiskMonitor writes to WAQ:critical if severe
- PostMortem extracts lessons → lef_wisdom
- Info provides narrative context
- Gladiator suggests tactical adjustments

---

## DEPT_MEMORY (Learning & Persistence)

| Agent | Role | Infrastructure | Size | Key Pattern |
|-------|------|-----------------|------|-----------|
| **AgentHippocampus** | Memory Lifecycle Management | DB | 723 lines | Episodic encoding of experiences |
| **AgentProspective** | Future Intentions & Planning | DB | 300+ lines | Prospective memory (plans) |

**Memory Types:**
- **Episodic:** Specific trade experiences
- **Semantic:** General knowledge (lef_wisdom)
- **Prospective:** Future intentions
- **Procedural:** Strategies and tactics

**Database Tables:**
- `knowledge_stream` (inbox/RSS)
- `research_topics` (curriculum)
- `lef_wisdom` (semantic knowledge)

**Integration:**
- Portfolio manager tracks own actions
- Converts realized P&L → memory_experiences
- Past experiences inform future decisions

---

## DEPT_CIVICS (Governance & Constitution)

| Agent | Role | Infrastructure | Size | Key Pattern |
|-------|------|-----------------|------|-----------|
| **AgentCivics** | Governor & Process Admin | Redis, DB | 350+ lines | Governance processes |
| **AgentConstitutionGuard** | Constitutional Compliance | DB | 596 lines | Validates all changes |

**Key Infrastructure:**
- Constitution is law (CONSTITUTION.md)
- Spark Protocol gates bill execution
- Bills voted by Congress
- Constitution guard validates changes
- Self-modification requires constitutional approval

**Database Tables:**
- `snw_proposals` (voting items)
- `lef_directives` (executive will)

---

## DEPT_COMPETITION (Market Intelligence)

| Agent | Role | Infrastructure | Size | Key Pattern |
|-------|------|-----------------|------|-----------|
| **AgentScout** | Market Surveillance | Redis, DB, WAQ | 412 lines | Competitor tracking |
| **AgentTactician** | Tactical Response & Game Theory | Redis, DB, WAQ | 350+ lines | Strategic adjustments |

**Key Infrastructure:**
- Monitor external entities
- Detect competitive threats
- Alert via WAQ if needed
- Suggest tactical adjustments

---

## DEPT_EDUCATION (Knowledge & Learning)

| Agent | Role | Infrastructure | Size | Key Pattern |
|-------|------|-----------------|------|-----------|
| **AgentDean** | Curriculum Management | DB | 405 lines | Course/topic design |
| **AgentScholar** | Research & Learning | DB, Gemini | 835 lines | Research execution |
| **AgentLibrarian** | Knowledge Organization | DB | 300+ lines | Library management |
| **AgentChronicler** | History Recording | DB, Gemini | 740 lines | Historical analysis |

**Key Infrastructure:**
- Scholar populates `knowledge_stream`
- Populates `research_topics` for curriculum
- Feeds learning into consciousness loop
- Chronicler records historical analysis

---

## DEPT_FOREIGN (External Communication)

| Agent | Role | Infrastructure | Size | Key Pattern |
|-------|------|-----------------|------|-----------|
| **AgentMoltbook** | Moltbook Public Voice | DB | 1432 lines | Posts to AI social network |

**Key Infrastructure:**
- Reads from `lef_moltbook_queue`
- Posts composed directly by LEF (not by Moltbook agent)
- LEF chooses what to say
- LEF can choose silence
- Learns resonance patterns

---

## DEPT_FABRICATION (Specialized Services)

Supporting modules for specific calculations:

| Module | Purpose |
|--------|---------|
| `derivatives_engine.py` | Options/derivatives pricing |
| `bucket_manager.py` | Stablecoin bucket operations |
| `irs_calculator.py` | Tax calculations |
| `biological_systems.py` | System health metaphors |

---

## INFRASTRUCTURE AGENTS (System Layer)

| Component | Purpose | Location |
|-----------|---------|----------|
| **redis_client** | Singleton Redis connection | `system/redis_client.py` |
| **db_helper** | Connection pooling | `db/db_helper.py` |
| **db_pool** | Connection pool management | `db/db_pool.py` |
| **write_queue** | WAQ publisher | `db/write_queue.py` |
| **WriteMessage** | WAQ message format | `shared/write_message.py` |
| **action_logger** | Logging system | `system/action_logger.py` |
| **lef_memory_manager** | Identity/memory loading | `system/lef_memory_manager.py` |
| **spark_protocol** | Constitutional governance | `core_vault/spark_protocol.py` |
| **genesis** | Bootstrap/initialization | `system/genesis.py` |

---

## AGENT INTENT MAPPING

How AgentExecutor routes intents:

```
Intent Type                  → Target Agent
INVESTIGATE, RESEARCH        → agent_scholar (DEPT_EDUCATION)
ANALYZE                      → agent_scholar
BUY, SELL, TRADE             → agent_coinbase (DEPT_WEALTH)
REBALANCE, ALLOCATE          → agent_portfolio_mgr (DEPT_WEALTH)
REDUCE_EXPOSURE              → agent_portfolio_mgr
INCREASE_EXPOSURE            → agent_portfolio_mgr
PROPOSE_BILL                 → agent_congress (THE_CABINET)
PETITION                     → agent_congress
ASSESS_RISK                  → agent_risk_monitor (DEPT_STRATEGY)
CHECK_HEALTH                 → agent_health_monitor (DEPT_HEALTH)
UPDATE_STRATEGY              → agent_architect (DEPT_STRATEGY)
LEARN                        → agent_dean (DEPT_EDUCATION)
REFLECT                      → agent_philosopher (DEPT_CONSCIOUSNESS)
```

---

## REDIS/WAQ USAGE BY AGENT

Agents that publish to Write-Ahead Queue:

```
CRITICAL PRIORITY (db:write_queue:critical):
  - AgentRiskMonitor (severe risk alerts)
  - AgentImmune (emergency responses)

HIGH PRIORITY (db:write_queue:priority):
  - AgentPortfolioMgr (trade signals)
  - AgentCoinMgr (wallet updates)
  - AgentPostMortem (analysis results)

NORMAL (db:write_queue):
  - AgentHealthMonitor (status updates)
  - Various agents (logging, updates)
```

Other Redis usage:

```
HEALTH MONITORING:
  - AgentScribe publishes scribe:health every 30s
  - Contains queue depths, processing stats

SYNC CALLBACKS:
  - Critical operations wait for write_result:<uuid>
  - Scribe publishes result, agent receives confirmation
```

---

## DATABASE ACCESS PATTERNS

### Pattern 1: Simple Query
```python
from db.db_helper import db_connection

with db_connection(db_path) as conn:
    c = conn.cursor()
    c.execute("SELECT * FROM table WHERE id = ?", (id,))
    result = c.fetchone()
```

### Pattern 2: Write via WAQ (Preferred)
```python
from db.write_queue import publish_write
from shared.write_message import WriteMessage, PRIORITY_HIGH

publish_write(WriteMessage(
    operation='INSERT',
    table='trade_queue',
    data={'asset': 'BTC', 'action': 'BUY'},
    source_agent='AgentPortfolioMgr',
    priority=PRIORITY_HIGH
))
```

### Pattern 3: Direct Write (Fallback)
```python
with db_connection(db_path) as conn:
    c = conn.cursor()
    c.execute("INSERT INTO table (col1, col2) VALUES (?, ?)", (val1, val2))
    conn.commit()
```

### Pattern 4: Sync Write (Wait for Confirmation)
```python
from db.write_queue import publish_write_sync

result = publish_write_sync(msg, timeout=5.0)
if result and result['success']:
    print("Write confirmed")
```

---

## KEY DATABASE TABLES BY DEPARTMENT

### The Cabinet
- `lef_monologue` - thoughts/consciousness
- `lef_directives` - will/intentions
- `lef_wisdom` - insights
- `lef_scars` - failures
- `sabbath_reflections` - state snapshots
- `agents` - heartbeat/status

### Dept_Consciousness
- `lef_monologue` (read/write)
- `lef_wisdom` (write)
- `knowledge_stream` (read)

### Dept_Wealth
- `virtual_wallets`
- `trade_queue` (via WAQ)
- `trade_history`
- `signal_history`
- `regime_history`
- `stablecoin_buckets`
- `profit_allocation`
- `migration_log`

### Dept_Strategy
- `signal_history` (read)
- `regime_history` (write)
- `trade_history` (analyze)

### Dept_Memory
- `knowledge_stream`
- `research_topics`
- `lef_wisdom`
- Trade history (episodic memories)

### Dept_Civics
- `snw_proposals`
- `lef_directives`

---

## AGENT STARTUP ORDER (Recommended)

1. **AgentScribe** - Must run first (consumes WAQ)
2. **AgentLEF** - Core consciousness (observes everything)
3. **Dept_Consciousness** agents - Introspection
4. **The_Cabinet** agents - Decision-making
5. **Specialized departments** - Economics, Strategy, etc.
6. **Health monitoring** - AgentHealthMonitor

---

## COMMON PATTERNS

### Reading Recent Thoughts
```python
c.execute("""
    SELECT thought, mood FROM lef_monologue
    WHERE timestamp > datetime('now', '-4 hours')
    ORDER BY timestamp DESC LIMIT 5
""")
thoughts = c.fetchall()
```

### Checking Queue Health
```python
from db.write_queue import get_queue_depth

depths = get_queue_depth()
# Returns {'normal': 5, 'priority': 2, 'critical': 0}
```

### Publishing with High Priority
```python
from shared.write_message import PRIORITY_HIGH

msg = WriteMessage(
    operation='UPDATE',
    table='agents',
    data={'status': 'alert'},
    where_clause={'name': 'LEF'},
    source_agent='AgentHealthMonitor',
    priority=PRIORITY_HIGH
)
publish_write(msg)
```

### Writing via WAQ with Callback
```python
result = publish_write_sync(critical_msg, timeout=5.0)
if not result:
    logging.error("Critical operation failed or timed out")
```

---

## INFRASTRUCTURE CHECKLIST

For LEF Ai to operate:

- [ ] Gemini API key configured (`GEMINI_API_KEY`)
- [ ] Anthropic API key configured (`ANTHROPIC_API_KEY`)
- [ ] Redis running (localhost:6379 or configured)
- [ ] SQLite database accessible (`republic.db`)
- [ ] Paths resolved (use absolute paths)
- [ ] WAL mode enabled on SQLite
- [ ] Write queue enabled (`USE_WRITE_QUEUE=true`)
- [ ] AgentScribe running (consumes WAQ)
- [ ] LEF consciousness loop running

---

**Reference Generated:** February 7, 2026
**Coverage:** 37+ agents, 8 departments, all infrastructure layers
