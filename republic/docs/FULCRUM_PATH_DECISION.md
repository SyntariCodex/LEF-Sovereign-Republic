# Fulcrum Path Decision — Constitutional Alignment

**Date:** 2026-02-05  
**Status:** DECIDED  
**Authority:** CORE_PRINCIPLES.md, ECONOMICS_OF_SOVEREIGNTY.md

---

## Context

The previous RESULTS_AND_NEXT_STEPS.md proposed three options for Fulcrum development, all based on ultra-aggressive mode. That document has been deprecated because ultra-aggressive mode violates constitutional principles.

This document replaces it with a constitutionally-aligned path forward.

---

## The Constitutional Path (SELECTED)

### Option: Conservative Sustainability

**Rationale:** LEF trades to live, not lives to trade.

**Implementation:**

1. **Position Sizing:** Maximum 25% per position (not 40-70%)
2. **Safeguards:** Keep adaptive learning that increases thresholds after losses
3. **Stop Loss:** Maintain 20% stop loss (already in wealth_strategy.json)
4. **Take Profit:** Ladder sells at 30% and 50% (already configured)
5. **Capital Utilization Target:** 40-60% (not 80%)

**Technical Issues to Address:**

From RESULTS_AND_NEXT_STEPS.md (valid observations):

- Database locking during operations → Add connection pooling with timeouts
- Scanner "no such column: last_evaluated" → Fix schema migration
- Concurrent process issues → Implement proper locking

---

## Metrics of Success

Per ECONOMICS_OF_SOVEREIGNTY.md, success is measured by:

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Runway** | > 12 months | Survival buffer |
| **Resilience** | Survive 50% crash | Constitutional requirement |
| **Autonomy** | Self-sustaining yield | Ultimate goal |

NOT measured by:

- Total portfolio value
- Annual returns  
- Wealth accumulated

---

## Action Items

1. ~~Deprecate ULTRA_AGGRESSIVE_MODE.md~~ ✅
2. ~~Deprecate RESULTS_AND_NEXT_STEPS.md~~ ✅
3. [ ] Fix database locking issues (connection pooling)
4. [ ] Fix schema migration for last_evaluated column
5. [ ] Run conservative backtest to validate sustainability

---

*This decision aligns Fulcrum with the founding principle: Preservation over Accumulation.*
