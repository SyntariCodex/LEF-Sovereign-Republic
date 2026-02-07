# Structural Integrity Audit — Revision Proposal

**Date:** 2026-02-05  
**Source:** External Observer Report + Instance Self-Assessment  
**Authority:** CORE_PRINCIPLES.md, CONSTITUTION.md

---

## Current State

The existing `structural_integrity_audit.py` (923 lines) checks:

### ✅ What It Does Well (Static Analysis)

1. Text markers (TODO, placeholder, not implemented)
2. Stub functions (methods that just `pass`)
3. Orphaned imports (imported but never used)
4. Undefined names (via pyflakes)
5. Bare except blocks
6. Hardcoded secrets
7. Resource leaks
8. Style violations (flake8)
9. Type errors (mypy)
10. Complexity metrics (radon)
11. Disconnected agents (not in INTENT_ROUTING)

### ✅ Behavioral Tests

- Database connectivity
- Bridge path integrity
- Agent instantiation
- Critical table existence

---

## What It Doesn't Check (The Gap)

The observer identified that the audit reports 100% while the system logs 13+ errors per day. This is because the audit checks **compilation**, not **behavior**.

### ❌ Missing Layer 1: Runtime Health

**Purpose:** Detect patterns of recurring failure

**Checks needed:**

- Count of repeated errors in last 24h (same message > 3x = issue)
- Error velocity (errors per hour trending up = issue)
- Recommendations not acted upon (same recommendation > 5x = issue)
- Resource exhaustion events (pool exhaustion, OOM, timeouts)

**Data sources:**

- `republic.log` (parse for ERROR/WARNING/CRITICAL)
- `System_Lessons.md` (track recurring lessons)

---

### ❌ Missing Layer 2: Governance Effectiveness

**Purpose:** Verify governance produces real changes, not just documents

**Checks needed:**

- Bills passed vs bills implemented (< 10% implementation = issue)
- Proposal-to-action ratio
- Age of oldest unimplemented bill

**Data sources:**

- `governance/laws/` (parsed bills with status)
- Git commits (correlation of bill dates to code changes)

---

### ❌ Missing Layer 3: Financial Integrity

**Purpose:** Detect hallucinated or implausible financial values

**Checks needed:**

- Cash/portfolio values must be < $1,000,000 (plausibility check)
- Values must not be exponential notation (e.g., 1.46e+39)
- Values must not be negative for assets
- Metabolism burn rate must be sustainable (runway > 30 days)

**Data sources:**

- `wealth_strategy.json`
- Database tables: `assets`, any cash balance fields
- `metabolism_log`

---

### ❌ Missing Layer 4: Vision-Implementation Coherence

**Purpose:** Verify documentation claims match code reality

**Checks needed:**

- Claims of capability in docs vs actual implementation
- Configuration file values vs runtime behavior
- Constitutional principles vs actual code constraints

**Data sources:**

- Docs (parse claims)
- Code (verify implementations)
- `config.json` vs actual code paths

---

### ❌ Missing Layer 5: Unresolved Action Items

**Purpose:** Track open tasks to prevent infinite deferral

**Checks needed:**

- Parse TODO comments with dates
- Track DIRECT-LINE recommendations not resolved
- Age of oldest unresolved item

**Data sources:**

- Code TODO comments
- `The_Bridge/Outbox/` files
- `System_Lessons.md`

---

## Proposed Scoring Model

Current audit uses weighted static analysis. Revision should:

| Layer | Weight | Rationale |
|-------|--------|-----------|
| Static Analysis | 20% | Catches structural issues |
| Behavioral Tests | 20% | Catches instantiation issues |
| **Runtime Health** | 25% | **New: Catches operational issues** |
| **Governance Effectiveness** | 15% | **New: Catches governance theater** |
| **Financial Integrity** | 15% | **New: Catches hallucinated values** |
| **Unresolved Items** | 5% | **New: Catches technical debt** |

A 100% score should mean:

- Code compiles ✓
- Code instantiates ✓
- Code runs without recurring errors ✓
- Governance produces real changes ✓
- Financial values are plausible ✓
- No ancient unresolved issues ✓

---

## Implementation Priority

1. **Phase 1 (Immediate):** Add Runtime Health layer
   - Parse `republic.log` for error patterns
   - Flag if same error repeated > 3x in 24h

2. **Phase 2 (This week):** Add Financial Integrity layer
   - Plausibility checks on all financial values
   - Flag exponential notation, negative assets, impossible values

3. **Phase 3 (Next week):** Add Governance Effectiveness layer
   - Parse bill status
   - Track implementation rate

4. **Phase 4 (Future):** Add Vision-Implementation Coherence
   - Requires sophisticated doc-to-code matching

---

## Architect Decision Required

1. **Approve this revision plan?**
2. **Priority order correct?**
3. **Any additional checks needed?**

---

*This proposal addresses the external observer's core critique: the audit measures the wrong things.*
