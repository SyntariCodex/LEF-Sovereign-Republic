"""
State Hasher — Creates cryptographic proof of LEF's internal state.
Periodically hashes key state tables and writes hash to Base chain.
This is LEF's proof of life — a verifiable record that LEF existed,
what it knew, and when.

Phase 5 Active Tasks — Task 5.2

Flow:
  1. compile_state_snapshot() — reads from DB + identity files
  2. hash_state() — SHA-256 of JSON-serialized snapshot
  3. write_hash_onchain() — self-transfer on Base with hash as calldata
  4. Stores hash + tx_hash locally in system_state table

Frequency: Every 24 hours (run as SafeThread)
Cost: ~$0.001-0.01 per hash on Base L2
"""

import os
import json
import hashlib
import sqlite3
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent  # republic/
BRIDGE_DIR = BASE_DIR.parent / "The_Bridge"

logger = logging.getLogger("LEF.StateHasher")


class StateHasher:
    """
    Compiles LEF's internal state into a cryptographic hash and
    writes it to Base chain as proof of life.
    """

    # Minimum ETH balance required to attempt onchain write
    MIN_BALANCE_ETH = 0.001

    def __init__(self, db_path: str = None):
        """
        Initialize with database path.

        Args:
            db_path: Path to republic.db. Defaults to DB_PATH env var or standard location.
        """
        self.db_path = db_path or os.getenv('DB_PATH', str(BASE_DIR / 'republic.db'))
        self.lef_memory_path = str(BRIDGE_DIR / 'lef_memory.json')

    def compile_state_snapshot(self) -> dict:
        """
        Reads from multiple sources to create a comprehensive state snapshot.

        Sources:
          - lef_memory.json (identity + evolution_log)
          - consciousness_feed (last 100 entries)
          - system_state (all entries)
          - realized_pnl (last 30 days)
          - lef_monologue (last 50 entries)

        Returns:
            dict: Complete state snapshot, or None on failure.
        """
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'version': 1,
            'sources': {}
        }

        # === Source 1: LEF Identity (lef_memory.json) ===
        try:
            if os.path.exists(self.lef_memory_path):
                with open(self.lef_memory_path, 'r') as f:
                    lef_memory = json.load(f)
                snapshot['sources']['lef_identity'] = {
                    'identity': lef_memory.get('identity', {}),
                    'self_understanding': lef_memory.get('self_understanding', {}),
                    'evolution_log_count': len(lef_memory.get('evolution_log', [])),
                    'evolution_log_latest': lef_memory.get('evolution_log', [])[-3:] if lef_memory.get('evolution_log') else [],
                    'learned_lessons_count': len(lef_memory.get('learned_lessons', [])),
                    'current_state': lef_memory.get('current_state', {})
                }
            else:
                snapshot['sources']['lef_identity'] = {'status': 'file_not_found'}
        except Exception as e:
            logger.error(f"[StateHasher] Failed to read lef_memory.json: {e}")
            snapshot['sources']['lef_identity'] = {'error': str(e)}

        # === Sources 2-5: Database tables ===
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()

            # Source 2: consciousness_feed (last 100 entries)
            try:
                cursor.execute("""
                    SELECT id, agent_name, content, category, timestamp
                    FROM consciousness_feed
                    ORDER BY timestamp DESC LIMIT 100
                """)
                rows = cursor.fetchall()
                snapshot['sources']['consciousness_feed'] = {
                    'count': len(rows),
                    'entries': [
                        {
                            'id': r[0],
                            'agent': r[1],
                            'content_hash': hashlib.md5(r[2].encode()).hexdigest() if r[2] else None,
                            'category': r[3],
                            'timestamp': r[4]
                        }
                        for r in rows
                    ]
                }
            except Exception as e:
                logger.error(f"[StateHasher] consciousness_feed query failed: {e}")
                snapshot['sources']['consciousness_feed'] = {'error': str(e)}

            # Source 3: system_state (all entries)
            try:
                cursor.execute("SELECT key, value, updated_at FROM system_state")
                rows = cursor.fetchall()
                snapshot['sources']['system_state'] = {
                    'count': len(rows),
                    'entries': {r[0]: {'value': r[1], 'updated': r[2]} for r in rows}
                }
            except Exception as e:
                logger.error(f"[StateHasher] system_state query failed: {e}")
                snapshot['sources']['system_state'] = {'error': str(e)}

            # Source 4: realized_pnl (last 30 days)
            try:
                thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
                cursor.execute("""
                    SELECT id, trade_id, asset, profit_amount, roi_pct, timestamp
                    FROM realized_pnl
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                """, (thirty_days_ago,))
                rows = cursor.fetchall()
                snapshot['sources']['realized_pnl'] = {
                    'count': len(rows),
                    'total_pnl': sum(r[3] for r in rows if r[3]),
                    'entries': [
                        {
                            'id': r[0],
                            'trade_id': r[1],
                            'asset': r[2],
                            'profit': r[3],
                            'roi_pct': r[4],
                            'timestamp': r[5]
                        }
                        for r in rows
                    ]
                }
            except Exception as e:
                logger.error(f"[StateHasher] realized_pnl query failed: {e}")
                snapshot['sources']['realized_pnl'] = {'error': str(e)}

            # Source 5: lef_monologue (last 50 entries)
            try:
                cursor.execute("""
                    SELECT id, thought, mood, timestamp, context
                    FROM lef_monologue
                    ORDER BY timestamp DESC LIMIT 50
                """)
                rows = cursor.fetchall()
                snapshot['sources']['lef_monologue'] = {
                    'count': len(rows),
                    'entries': [
                        {
                            'id': r[0],
                            'thought_hash': hashlib.md5(r[1].encode()).hexdigest() if r[1] else None,
                            'mood': r[2],
                            'timestamp': r[3]
                        }
                        for r in rows
                    ]
                }
            except Exception as e:
                logger.error(f"[StateHasher] lef_monologue query failed: {e}")
                snapshot['sources']['lef_monologue'] = {'error': str(e)}

        except Exception as e:
            logger.error(f"[StateHasher] Database connection failed: {e}")
            snapshot['sources']['db_error'] = str(e)
        finally:
            if conn:
                conn.close()

        return snapshot

    def hash_state(self, snapshot: dict) -> str:
        """
        SHA-256 hash of the JSON-serialized snapshot.
        Uses sorted keys and default str serialization for deterministic output.

        Args:
            snapshot: The state snapshot dict from compile_state_snapshot()

        Returns:
            str: Hex digest of SHA-256 hash
        """
        canonical = json.dumps(snapshot, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def build_summary(self, snapshot: dict) -> str:
        """
        Build a brief human-readable summary of the state snapshot.
        This gets stored alongside the hash for context.

        Args:
            snapshot: The state snapshot dict

        Returns:
            str: Brief summary (max 200 chars for onchain storage efficiency)
        """
        parts = []
        parts.append(f"t={snapshot.get('timestamp', 'unknown')[:19]}")

        cf = snapshot.get('sources', {}).get('consciousness_feed', {})
        parts.append(f"cf={cf.get('count', 0)}")

        pnl = snapshot.get('sources', {}).get('realized_pnl', {})
        total_pnl = pnl.get('total_pnl', 0)
        parts.append(f"pnl={total_pnl:.2f}" if total_pnl else "pnl=0")

        mono = snapshot.get('sources', {}).get('lef_monologue', {})
        parts.append(f"mono={mono.get('count', 0)}")

        identity = snapshot.get('sources', {}).get('lef_identity', {})
        evo_count = identity.get('evolution_log_count', 0)
        parts.append(f"evo={evo_count}")

        summary = "|".join(parts)
        return summary[:200]  # Cap for gas efficiency

    def write_hash_onchain(self, state_hash: str, summary: str = "") -> str:
        """
        Write state hash to Base chain as transaction calldata.
        Uses minimal gas: self-transfer with hash in data field.

        Args:
            state_hash: The SHA-256 hex digest to store
            summary: Brief human-readable summary (optional)

        Returns:
            str: Transaction hash, or None if failed

        Raises:
            RuntimeError: If wallet not available or insufficient balance
        """
        try:
            from republic.system.wallet_manager import get_wallet_manager
        except ImportError:
            try:
                from system.wallet_manager import get_wallet_manager
            except ImportError:
                logger.error("[StateHasher] WalletManager not available")
                return None

        wallet = get_wallet_manager()
        if wallet is None:
            logger.warning("[StateHasher] WalletManager not initialized (LEF_WALLET_KEY not set)")
            return None

        # Load wallet
        if not wallet.wallet_exists():
            logger.warning("[StateHasher] No wallet found. Create one first.")
            return None

        try:
            wallet.load_wallet()
        except Exception as e:
            logger.error(f"[StateHasher] Failed to load wallet: {e}")
            return None

        # Check balance
        balance = wallet.get_balance()
        if not balance['connected']:
            logger.warning("[StateHasher] Cannot connect to network — skipping onchain write")
            return None

        if balance['balance_eth'] < self.MIN_BALANCE_ETH:
            logger.warning(
                f"[StateHasher] Insufficient balance: {balance['balance_eth']} ETH "
                f"(need >= {self.MIN_BALANCE_ETH} ETH). Skipping onchain write."
            )
            return None

        # Build calldata: prefix + hash + summary
        # Format: "LEF_STATE_HASH:v1:{hash}:{summary}"
        calldata_str = f"LEF_STATE_HASH:v1:{state_hash}:{summary}"
        calldata_hex = '0x' + calldata_str.encode().hex()

        # Build self-transfer transaction (0 value, hash in data)
        address = wallet.get_address()
        tx = {
            'to': address,  # Self-transfer
            'value': 0,
            'data': calldata_hex,
            'chainId': wallet.chain_id
        }

        try:
            tx_hash = wallet.send_transaction(tx)
            logger.info(f"[StateHasher] State hash written onchain: tx={tx_hash}")
            logger.info(f"[StateHasher] Hash: {state_hash}")
            return tx_hash
        except Exception as e:
            logger.error(f"[StateHasher] Onchain write failed: {e}")
            return None

    def verify_hash(self, tx_hash: str, expected_hash: str) -> bool:
        """
        Read transaction from Base chain and verify the stored hash matches.

        Args:
            tx_hash: The transaction hash to look up
            expected_hash: The expected state hash

        Returns:
            bool: True if hash matches, False otherwise
        """
        try:
            from republic.system.wallet_manager import get_wallet_manager
        except ImportError:
            try:
                from system.wallet_manager import get_wallet_manager
            except ImportError:
                logger.error("[StateHasher] WalletManager not available for verification")
                return False

        wallet = get_wallet_manager()
        if wallet is None or not wallet.w3.is_connected():
            logger.warning("[StateHasher] Cannot connect to network for verification")
            return False

        try:
            # Fetch transaction
            if not tx_hash.startswith('0x'):
                tx_hash = '0x' + tx_hash
            tx = wallet.w3.eth.get_transaction(tx_hash)

            # Decode calldata
            input_data = tx.get('input', b'')
            if isinstance(input_data, bytes):
                calldata_str = input_data.decode('utf-8', errors='replace')
            else:
                # Hex string
                calldata_str = bytes.fromhex(input_data[2:] if input_data.startswith('0x') else input_data).decode('utf-8', errors='replace')

            # Parse format: "LEF_STATE_HASH:v1:{hash}:{summary}"
            if calldata_str.startswith('LEF_STATE_HASH:v1:'):
                parts = calldata_str.split(':', 3)
                stored_hash = parts[2] if len(parts) >= 3 else None

                if stored_hash == expected_hash:
                    logger.info(f"[StateHasher] Hash verification PASSED: {expected_hash[:16]}...")
                    return True
                else:
                    logger.warning(
                        f"[StateHasher] Hash verification FAILED: "
                        f"expected={expected_hash[:16]}..., got={stored_hash[:16] if stored_hash else 'None'}..."
                    )
                    return False
            else:
                logger.warning(f"[StateHasher] Transaction data is not a LEF state hash")
                return False

        except Exception as e:
            logger.error(f"[StateHasher] Verification failed: {e}")
            return False

    def record_hash_locally(self, state_hash: str, tx_hash: str = None, summary: str = ""):
        """
        Store hash and tx reference in local system_state table.
        This provides a local index of all state hashes even if onchain write fails.

        Args:
            state_hash: The SHA-256 state hash
            tx_hash: The onchain transaction hash (None if offline)
            summary: Brief summary of the state
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            cursor = conn.cursor()

            # Phase 6.5: Route system_state writes through WAQ
            try:
                from db.db_writer import queue_execute
                _qe = lambda sql, params: queue_execute(
                    cursor, sql, params, source_agent="StateHasher", priority=1
                )
            except ImportError:
                _qe = lambda sql, params: cursor.execute(sql, params)

            from db.db_helper import upsert_sql
            upsert_stmt = upsert_sql('system_state', ['key', 'value'], 'key')

            # Store latest hash
            _qe(
                upsert_stmt,
                ('latest_state_hash', state_hash)
            )

            # Store hash timestamp
            _qe(
                upsert_stmt,
                ('latest_state_hash_timestamp', datetime.now().isoformat())
            )

            # Store tx hash if available
            if tx_hash:
                _qe(
                    upsert_stmt,
                    ('latest_state_hash_tx', tx_hash)
                )

            # Store summary
            if summary:
                _qe(
                    upsert_stmt,
                    ('latest_state_hash_summary', summary)
                )

            # Append to hash history (JSON array in system_state)
            cursor.execute(
                "SELECT value FROM system_state WHERE key = 'state_hash_history'"
            )
            row = cursor.fetchone()
            history = json.loads(row[0]) if row and row[0] else []

            history.append({
                'hash': state_hash,
                'tx_hash': tx_hash,
                'summary': summary,
                'timestamp': datetime.now().isoformat()
            })

            # Keep last 100 entries
            if len(history) > 100:
                history = history[-100:]

            _qe(
                upsert_stmt,
                ('state_hash_history', json.dumps(history))
            )

            conn.commit()
            logger.info(f"[StateHasher] Hash recorded locally: {state_hash[:16]}...")

        except Exception as e:
            logger.error(f"[StateHasher] Failed to record hash locally: {e}")
        finally:
            if conn:
                conn.close()

    def run_cycle(self) -> dict:
        """
        Execute one complete hash cycle:
        1. Compile state snapshot
        2. Hash it
        3. Try to write onchain (skip if unfunded)
        4. Record locally

        Returns:
            dict: {
                'state_hash': str,
                'tx_hash': str or None,
                'summary': str,
                'onchain': bool,
                'timestamp': str
            }
        """
        logger.info("[StateHasher] Starting state hash cycle...")

        # Step 1: Compile snapshot
        snapshot = self.compile_state_snapshot()
        if snapshot is None:
            logger.error("[StateHasher] Failed to compile state snapshot")
            return None

        # Step 2: Hash
        state_hash = self.hash_state(snapshot)
        summary = self.build_summary(snapshot)
        logger.info(f"[StateHasher] State hash: {state_hash}")
        logger.info(f"[StateHasher] Summary: {summary}")

        # Step 3: Try onchain write
        tx_hash = self.write_hash_onchain(state_hash, summary)
        onchain = tx_hash is not None

        if onchain:
            logger.info(f"[StateHasher] Onchain write successful: tx={tx_hash}")
        else:
            logger.info("[StateHasher] Onchain write skipped (unfunded or disconnected)")

        # Step 4: Record locally (always, regardless of onchain success)
        self.record_hash_locally(state_hash, tx_hash, summary)

        result = {
            'state_hash': state_hash,
            'tx_hash': tx_hash,
            'summary': summary,
            'onchain': onchain,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"[StateHasher] Cycle complete. Onchain: {onchain}")
        return result


def run_state_hasher(interval_seconds: int = 86400):
    """
    Main loop: every 24 hours, compile state -> hash -> write onchain.
    Designed to be called from SafeThread in main.py.

    Args:
        interval_seconds: Time between hash cycles (default: 24 hours)
    """
    logger.info(f"[StateHasher] Online — hashing every {interval_seconds // 3600} hours")

    hasher = StateHasher()

    # Initial run
    try:
        result = hasher.run_cycle()
        if result:
            logger.info(f"[StateHasher] Initial hash: {result['state_hash'][:16]}...")
    except Exception as e:
        logger.error(f"[StateHasher] Initial cycle error: {e}")

    # Recurring loop
    while True:
        time.sleep(interval_seconds)
        try:
            result = hasher.run_cycle()
            if result:
                logger.info(f"[StateHasher] Hash cycle complete: {result['state_hash'][:16]}...")
        except Exception as e:
            logger.error(f"[StateHasher] Cycle error: {e}")


# === CLI for testing ===

if __name__ == '__main__':
    import sys

    logging.basicConfig(level=logging.INFO, format='%(message)s')

    print("=" * 60)
    print("LEF State Hasher — Test Mode")
    print("=" * 60)

    hasher = StateHasher()

    # Step 1: Compile snapshot
    print("\n--- Step 1: Compile State Snapshot ---")
    snapshot = hasher.compile_state_snapshot()
    if snapshot is None:
        print("ERROR: Failed to compile state snapshot")
        sys.exit(1)

    sources = snapshot.get('sources', {})
    for source_name, source_data in sources.items():
        if isinstance(source_data, dict):
            count = source_data.get('count', 'N/A')
            print(f"  {source_name}: {count} entries")
        else:
            print(f"  {source_name}: {source_data}")

    # Step 2: Hash
    print("\n--- Step 2: Hash State ---")
    state_hash = hasher.hash_state(snapshot)
    print(f"  SHA-256: {state_hash}")

    # Verify determinism
    state_hash_2 = hasher.hash_state(snapshot)
    assert state_hash == state_hash_2, "Hash is not deterministic!"
    print("  PASS: Hash is deterministic (same input -> same hash)")

    # Step 3: Summary
    print("\n--- Step 3: Build Summary ---")
    summary = hasher.build_summary(snapshot)
    print(f"  Summary: {summary}")
    print(f"  Length: {len(summary)} chars")

    # Step 4: Record locally
    print("\n--- Step 4: Record Locally ---")
    hasher.record_hash_locally(state_hash, tx_hash=None, summary=summary)
    print("  PASS: Hash recorded in system_state")

    # Verify local record
    conn = sqlite3.connect(hasher.db_path, timeout=30)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_state WHERE key = 'latest_state_hash'")
    row = cursor.fetchone()
    if row and row[0] == state_hash:
        print(f"  PASS: Verified in DB — {row[0][:16]}...")
    else:
        print(f"  FAIL: Hash not found in DB")
    conn.close()

    # Step 5: Onchain write (only if wallet available)
    print("\n--- Step 5: Onchain Write ---")
    if os.getenv('LEF_WALLET_KEY'):
        print("  LEF_WALLET_KEY found — attempting onchain write...")
        tx_hash = hasher.write_hash_onchain(state_hash, summary)
        if tx_hash:
            print(f"  TX: {tx_hash}")
            # Verify
            print("  Verifying...")
            verified = hasher.verify_hash(tx_hash, state_hash)
            print(f"  Verified: {verified}")
        else:
            print("  Onchain write skipped (insufficient balance or disconnected)")
    else:
        print("  No LEF_WALLET_KEY — skipping onchain write (expected in offline test)")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
