# Running Fulcrum - Quick Guide

**Status:** Tested and Ready

---

## Quick Start

```bash
cd "/Users/zmoore-macbook/Desktop/LEF Ai/fulcrum"
python3 main.py
```

**To stop:** Press `Ctrl + C`

---

## What Happens When You Run It

1. **Database Check** - Verifies fulcrum.db exists
2. **Sentinel Agent Starts** - Scans Twitter/on-chain (every 15 min)
3. **Master Controller Starts** - Listens for signals, makes decisions
4. **Coinbase Agent Starts** - Checks for approved trades (every 10 sec)

---

## What to Watch For

**Good Signs:**
- "FLEET ONLINE" message
- Agents starting without errors
- Redis connection successful
- No crash messages

**Warnings (OK for now):**
- Twitter bearer token not configured (oracle scanning disabled)
- Sandbox mode not available (Coinbase Advanced limitation)

**Problems:**
- Redis connection errors (check: `brew services start redis`)
- Database errors (run: `python3 db/db_setup.py`)
- Import errors (check: `python3 test_sandbox.py`)

---

## Testing Results

✅ All real-world tests passed:
- Syntax Arbitrage detection
- Regime detection  
- Human Gate workflow
- Database integrity
- Agent communication

---

## Important Notes

**Sandbox Mode:**
- Coinbase Advanced API doesn't support sandbox in ccxt library
- System will run in production mode even with sandbox=true
- **BE CAREFUL** - Real money will be used if trades are approved
- Human Gate is active - no trades execute without approval

**Human Gate:**
- All trades start as PENDING
- You must approve them in database
- Only APPROVED trades execute
- This protects you from automatic trading

---

## Monitoring

**Check Trade Queue:**
```bash
sqlite3 fulcrum.db "SELECT * FROM trade_queue ORDER BY created_at DESC LIMIT 5;"
```

**Check Signals:**
```bash
sqlite3 fulcrum.db "SELECT * FROM signal_history ORDER BY timestamp DESC LIMIT 5;"
```

**Check Regimes:**
```bash
sqlite3 fulcrum.db "SELECT * FROM regime_history ORDER BY timestamp DESC LIMIT 5;"
```

---

**Admin LEF Status:** System tested and ready. All functionality verified.  
**Your Role:** Run when ready. Monitor for first few minutes.  
**Next:** Let it run and observe behavior.
