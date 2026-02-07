# Runtime Issues Registry

**Date:** 2026-02-05  
**Source:** republic.log analysis (92,896 lines)  
**Authority:** Structural Integrity Audit (Runtime Health: 50%)

---

## Critical Issues (Recurring Daily)

### 1. Missing `knowledge_stream` Table

**Pattern:** `[CIVICS] Calculation Error: no such table: knowledge_stream`  
**Count:** 100+ occurrences  
**Impact:** Governance macro score calculation fails, defaults to neutral policy  

**Fix:**

```sql
CREATE TABLE IF NOT EXISTS knowledge_stream (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    content TEXT,
    implication_bullish REAL,
    implication_bearish REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### 2. Missing `implication_bullish` Column

**Pattern:** `[CIVICS] Calculation Error: no such column: implication_bullish`  
**Count:** 10+ occurrences  
**Impact:** Market sentiment calculation fails  

**Fix:** Same as above (column is part of knowledge_stream)

---

### 3. "AgentCoinbase Crashes" — MISDIAGNOSIS

**Pattern:** `[SURGEON] 🚑 CHRONIC FAILURE DETECTED in AgentCoinbase (55 crashes/5m)`  
**Count:** 1000+ occurrences  

**Root Cause Analysis:**  
These are NOT actual AgentCoinbase crashes. The SURGEON monitors `agent_logs` for ERROR/CRITICAL entries. Errors from OTHER agents are being logged with source="AgentCoinbase" because they share a process or logger.

**Actual Error Sources (from agent_logs database):**

| Error | Count | Real Source |
|-------|-------|-------------|
| `AgentQuant.run` missing | 30,667 | AgentQuant |
| `AgentExecutor.run` missing | 3,743 | AgentExecutor |
| `no such table: agent_health_ledger` | 3,549 | Health Oracle |
| `AgentScholar._init_census` missing | 980 | AgentScholar |
| `database is locked` | 750+ | Multiple agents |
| `AgentDean` closed database | 41,937 | AgentDean |

**Fix Required:**

1. Add missing `run()` method to `AgentQuant`
2. Add missing `run()` method to `AgentExecutor`  
3. Create `agent_health_ledger` table
4. Create `lef_scars` table
5. Fix `AgentDean` database connection handling

**Status:** ROOT CAUSE IDENTIFIED

---

### 4. Flipsidecrypto DNS Resolution Failures

**Pattern:** `Failed to resolve 'api-v2.flipsidecrypto.com'`  
**Count:** 100+ retries  
**Impact:** Chain analytics unavailable  

**Root Cause:** Either:

- Flipside API endpoint changed
- Network connectivity issues
- API deprecated

**Status:** NEEDS INVESTIGATION

---

## Fix Priority

| Issue | Severity | Effort | Priority |
|-------|----------|--------|----------|
| knowledge_stream table | High | Low (one SQL) | 1 |
| implication_bullish column | High | Low (same fix) | 1 |
| AgentCoinbase crashes | Critical | Unknown | 2 |
| Flipsidecrypto DNS | Medium | Low (disable/replace) | 3 |

---

## Immediate Actions

1. ✅ Register issues in this document
2. [ ] Run schema migration to create knowledge_stream table
3. [ ] Review AgentCoinbase for crash root cause
4. [ ] Disable or replace Flipsidecrypto integration

---

*This registry tracks recurring runtime issues identified by the new audit layer.*
