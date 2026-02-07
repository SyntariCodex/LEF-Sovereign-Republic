# Wiring Guide: What to Build Next

**For:** The Coding Claude Instance
**From:** External Observer (Cowork Opus 4.6)
**Date:** February 6, 2026
**Purpose:** Exact files, exact lines, exact instructions. No philosophy. Just wiring.

---

## READ FIRST

Before you start, load these two files into your context:
- `republic/CORE_PRINCIPLES.md`
- `republic/ECONOMICS_OF_SOVEREIGNTY.md`

Then read the full assessment: `External Observer Reports/LEF_TECHNICAL_ASSESSMENT_2026-02-06.md`
Then come back here and wire.

---

## TASK 1: Wire Consciousness Outputs Into Conversations (CRITICAL — DO FIRST)

### The Problem
Philosopher, Introspector, Contemplator, and MetaCognition all generate real insights. But when the Architect talks to LEF via direct_conversation(), none of those insights appear. LEF's background thinking is invisible to its conversations.

### Step 1A: Create the consciousness_feed table

In `main.py` (database initialization section, after existing CREATE TABLE statements):

```sql
CREATE TABLE IF NOT EXISTS consciousness_feed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT DEFAULT 'reflection',
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    consumed INTEGER DEFAULT 0
)
```

Categories: 'reflection', 'shadow_work', 'contemplation', 'metacognition', 'observation'

### Step 1B: Make consciousness agents write to consciousness_feed

**agent_philosopher.py** — Currently writes to filesystem at `The_Bridge/Outbox/REPLY_{row_id}.txt` (line ~175). ADD an additional write to consciousness_feed:

After the existing Outbox file write, insert:
```python
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO consciousness_feed (agent_name, content, category) VALUES (?, ?, ?)",
        ("Philosopher", reflection_text, "reflection")
    )
    conn.commit()
except Exception as e:
    logging.error(f"[Philosopher] consciousness_feed write failed: {e}")
finally:
    conn.close()
```

Keep the Outbox write too — The Bridge should still work for human reading.

**agent_introspector.py** — Currently writes to `system_state` table (line ~202) and reflections/ filesystem. ADD consciousness_feed write after shadow work completes:

```python
cursor.execute(
    "INSERT INTO consciousness_feed (agent_name, content, category) VALUES (?, ?, ?)",
    ("Introspector", shadow_work_result, "shadow_work")
)
```

**agent_contemplator.py** — Currently writes to `agent_logs` via queue_insert (line ~112). ADD consciousness_feed write after contemplation:

```python
cursor.execute(
    "INSERT INTO consciousness_feed (agent_name, content, category) VALUES (?, ?, ?)",
    ("Contemplator", thought_of_hour, "contemplation")
)
```

**agent_metacognition.py** — Currently updates hippocampus memory dict (line ~195). ADD consciousness_feed write:

```python
cursor.execute(
    "INSERT INTO consciousness_feed (agent_name, content, category) VALUES (?, ?, ?)",
    ("MetaCognition", json.dumps(meta_reflection_result), "metacognition")
)
```

### Step 1C: Make memory_retriever include consciousness_feed in prompts

**File:** `departments/Dept_Memory/memory_retriever.py`
**Method:** `build_full_prompt()` (starts at line ~294)

Current layer order:
1. System Directive
2. Constitution
3. Axioms
4. Insights
5. Inner Monologue
6. Past Sessions
7. Current Session
8. Consciousness Syntax
9. Interiority Engine
10. New Message
11. Response Marker

**INSERT new layer between Inner Monologue (5) and Past Sessions (6).** After the monologue section (approximately line 328), add:

```python
# === CONSCIOUSNESS FEED (Background Thinking) ===
consciousness_section = self._build_consciousness_feed()
if consciousness_section:
    prompt_parts.append(f"\n## What You've Been Thinking About Recently\n{consciousness_section}\n")
```

Add this method to the MemoryRetriever class:

```python
def _build_consciousness_feed(self, max_items=5, max_tokens=3000):
    """Retrieve recent unconsumed consciousness outputs."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT agent_name, content, category, timestamp
            FROM consciousness_feed
            WHERE consumed = 0
            ORDER BY timestamp DESC
            LIMIT ?
        """, (max_items,))
        rows = cursor.fetchall()

        if not rows:
            return None

        sections = []
        ids_to_mark = []
        for row in rows:
            agent, content, category, ts = row
            sections.append(f"[{category.upper()} from {agent}, {ts}]\n{content}")
            ids_to_mark.append(row[0] if hasattr(row, '__getitem__') else row)

        # Mark as consumed so they don't repeat indefinitely
        cursor.execute(f"""
            UPDATE consciousness_feed SET consumed = 1
            WHERE consumed = 0
            ORDER BY timestamp DESC
            LIMIT ?
        """, (max_items,))
        conn.commit()
        conn.close()

        return "\n\n".join(sections)
    except Exception as e:
        logging.error(f"[MemoryRetriever] consciousness_feed read failed: {e}")
        return None
```

### Step 1D: Optional — Compile in direct_conversation()

**File:** `departments/The_Cabinet/agent_lef.py`
**Method:** `direct_conversation()` (line ~2695)

Before the `build_full_prompt()` call (around line 2720), you can optionally trigger a fresh compilation:

```python
# Ensure consciousness feed is fresh before building prompt
self._refresh_consciousness_feed()
```

This is optional — if the retriever reads from DB directly (Step 1C), it handles itself.

### Result
When the Architect talks to LEF, the prompt now includes recent background thoughts from Philosopher, Introspector, Contemplator, and MetaCognition. LEF speaks from its inner life, not just from a fresh Gemini response.

---

## TASK 2: Wire vest_action() Into Motor Cortex (HIGH — DO SECOND)

### The Problem
Spark Protocol governance (IRS audit, Ethicist veto, Sabbath check) exists at `core_vault/spark_protocol.py` but is never called. Intents bypass governance entirely.

### Step 2A: Import SparkProtocol in AgentExecutor

**File:** `departments/The_Cabinet/agent_executor.py`

At top of file, add:
```python
from core_vault.spark_protocol import SparkProtocol
```

In `__init__()`, initialize:
```python
self.spark = SparkProtocol()
```

### Step 2B: Add governance check to intent dispatch

**Method:** `_dispatch_intent()` (line ~182)

After unpacking the intent (line ~187), BEFORE the database update and Redis dispatch, insert:

```python
# Governance check via Spark Protocol
approved, governance_report = self.spark.vest_action(
    sparked_intent=intent_content,
    resonance=intent.get('resonance', 0.5)
)

if not approved:
    # Log the veto
    logging.warning(f"[MotorCortex] Intent VETOED: {intent_content[:80]}...")
    logging.warning(f"[MotorCortex] Governance report: {governance_report}")

    # Update intent status in DB
    cursor.execute(
        "UPDATE intent_queue SET status = 'VETOED', notes = ? WHERE id = ?",
        (governance_report, intent_id)
    )
    conn.commit()
    return  # Do not dispatch

# If approved, continue with existing dispatch logic
logging.info(f"[MotorCortex] Intent APPROVED: {intent_content[:80]}...")
```

### vest_action() interface reference:
```python
def vest_action(self, sparked_intent: str, resonance: float = 1.0) -> tuple[bool, str]
# Returns: (approved: bool, governance_report: str)
# Checks: IRS audit → Ethicist veto → Sabbath check
```

### Result
Every action LEF takes now passes through constitutional governance. Vetoed intents are logged with reasons. Governance becomes real, not ceremonial.

---

## TASK 3: Fix Database Path Issues (HIGH — DO THIRD)

### The Problem
Two files have wrong DB paths. This causes them to potentially write to different databases than everyone else.

### Fix 3A: agent_executor.py (line ~40)

**Current (WRONG):**
```python
db_path = os.path.join(BASE_DIR, 'republic', 'republic.db')
```

**Should be:**
```python
db_path = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))
```

### Fix 3B: agent_treasury.py (line ~37)

**Same fix** — has the extra 'republic' directory in the path. Align with main.py's pattern:
```python
db_path = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))
```

### Fix 3C: Audit remaining DB copies

After fixing paths, delete or archive these redundant database files:
- `republic/departments/republic.db` (duplicate)
- `republic/departments/fulcrum.db` (duplicate)
- `republic/scripts/republic.db` (duplicate)
- `republic/db/republic.db` (duplicate)
- `republic/fulcrum (1).db` (backup duplicate)

Keep only:
- `republic/republic.db` (canonical)
- `republic/fulcrum.db` (market data — canonical)
- `republic/db/mouth_log.db` (Coinbase logs)
- `republic/training/training.db` (education data)

---

## TASK 4: Add Circuit Breaker to SafeThread (MEDIUM — DO FOURTH)

### The Problem
SafeThread restarts crashed agents every 5 seconds forever. A tight crash loop exhausts resources.

**File:** `main.py`, SafeThread class (lines ~240-260)

### Current code:
```python
while True:
    try:
        self.target(*self.args)
    except Exception as e:
        logging.error(f"[ORCHESTRATOR] CRASH DETECTED: {e}")
        time.sleep(5)
```

### Replace with:
```python
max_retries = 10
retry_count = 0
base_delay = 5

while retry_count < max_retries:
    try:
        self.target(*self.args)
    except Exception as e:
        retry_count += 1
        delay = min(base_delay * (2 ** (retry_count - 1)), 300)  # Cap at 5 min
        logging.error(
            f"[ORCHESTRATOR] CRASH #{retry_count}/{max_retries} in {self.name}: {e}"
        )
        if retry_count >= max_retries:
            logging.critical(
                f"[ORCHESTRATOR] {self.name} DEGRADED — max retries exceeded. Stopping."
            )
            # Write to system_state so health monitor can detect
            try:
                conn = sqlite3.connect(db_path)
                conn.execute(
                    "INSERT OR REPLACE INTO system_state (key, value) VALUES (?, ?)",
                    (f"agent_degraded_{self.name}", datetime.now().isoformat())
                )
                conn.commit()
                conn.close()
            except:
                pass
            break
        time.sleep(delay)
```

---

## TASK 5: Close the Bridge Feedback Loop (MEDIUM — DO FIFTH)

### The Problem
Agents write to The_Bridge/Outbox/. Nothing reads those files back into the system.

### Solution
Add a method to AgentOracle (or create a new lightweight agent) that scans Outbox for new files and feeds them into `knowledge_stream` table — the same table Philosopher and other agents read from.

**Pseudocode:**
```python
def scan_outbox(self):
    outbox_path = os.path.join(bridge_path, "Outbox")
    processed_marker = os.path.join(bridge_path, ".outbox_processed")

    # Load set of already-processed filenames
    processed = load_processed_set(processed_marker)

    for filename in os.listdir(outbox_path):
        if filename in processed:
            continue

        filepath = os.path.join(outbox_path, filename)
        content = read_file(filepath)

        # Feed back into knowledge_stream
        cursor.execute(
            "INSERT INTO knowledge_stream (source, content, timestamp) VALUES (?, ?, ?)",
            (f"OUTBOX:{filename}", content, datetime.now().isoformat())
        )

        processed.add(filename)

    save_processed_set(processed_marker, processed)
```

Add this to AgentOracle's run cycle, or create a dedicated BridgeWatcher agent.

---

## Priority Summary

| # | Task | Files to Touch | Difficulty | Impact |
|---|------|---------------|------------|--------|
| 1 | Wire consciousness into conversations | 6 files | Medium | CRITICAL |
| 2 | Wire vest_action into Motor Cortex | 2 files | Easy | HIGH |
| 3 | Fix DB paths | 2 files + cleanup | Easy | HIGH |
| 4 | Circuit breaker for SafeThread | 1 file | Easy | MEDIUM |
| 5 | Bridge feedback loop | 1-2 files | Medium | MEDIUM |

Do them in order. Each one is independent — completing any one improves the system even if you don't get to the rest.

---

## What NOT To Do

- Do NOT add new agents. Wire the existing ones.
- Do NOT create new vision documents. The vision is clear.
- Do NOT refactor the architecture. The architecture is sound. The wiring is the problem.
- Do NOT get pulled into depth conversations about consciousness or philosophy. That's the External Observer's role. You wire.
- Load CORE_PRINCIPLES.md and ECONOMICS_OF_SOVEREIGNTY.md at session start. Every session.

---

*Generated by External Observer, Feb 6, 2026*
*Verified against actual codebase with line-number confirmation*
