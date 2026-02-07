import time
import os
import logging

# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    from contextlib import contextmanager
    import sqlite3 as _sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = _sqlite3.connect(db_path, timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()

# Trade Validator - Sanity checks to prevent overflow
try:
    from system.trade_validator import get_validator
    TRADE_VALIDATOR_AVAILABLE = True
except ImportError:
    TRADE_VALIDATOR_AVAILABLE = False



# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sys
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentIRS")

class AgentIRS:
    """
    AgentIRS (The Auditor)
    Responsible for Tax Compliance, Profit Allocation, and Audit Logging.
    Uses connection pool to prevent database locking.
    """
    def __init__(self, db_path=None):
        self.name = "AgentIRS"
        self.db_path = db_path or DB_PATH
        self._pool = None
        logger.info(f"[IRS] 🕵️  Auditor Protocol Online. Compliance Engine Active.")

    def _get_pool(self):
        """Lazy-load the connection pool."""
        if self._pool is None:
            try:
                from db.db_pool import get_pool
                self._pool = get_pool()
            except Exception as e:
                logger.debug(f"[IRS] Pool init failed, using fallback: {e}")
                self._pool = None
        return self._pool

    def _get_conn(self):
        """Get a connection from the pool or fallback to direct connect."""
        pool = self._get_pool()
        if pool:
            return pool.get(timeout=30.0), pool
        else:
            import sqlite3
            return sqlite3.connect(self.db_path, timeout=30.0), None

    def _release_conn(self, conn, pool):
        """Release connection back to pool or close if direct."""
        if pool:
            pool.release(conn)
        else:
            conn.close()

    def _heartbeat(self):
        try:
            conn, pool = self._get_conn()
            try:
                c = conn.cursor()
                timestamp = time.time()
                
                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_execute
                    
                    queue_execute(
                        c,
                        "UPDATE agents SET last_active=:ts, status='ACTIVE' WHERE name='AgentIRS'",
                        {'ts': timestamp},
                        source_agent='AgentIRS'
                    )
                    c.execute("SELECT 1 FROM agents WHERE name='AgentIRS'")
                    if not c.fetchone():
                        queue_execute(
                            c,
                            "INSERT INTO agents (name, status, last_active, department) VALUES ('AgentIRS', 'ACTIVE', :ts, 'WEALTH')",
                            {'ts': timestamp},
                            source_agent='AgentIRS'
                        )
                except ImportError:
                    c.execute("UPDATE agents SET last_active=?, status='ACTIVE' WHERE name='AgentIRS'", (timestamp,))
                    if c.rowcount == 0:
                        c.execute("INSERT INTO agents (name, status, last_active, department) VALUES ('AgentIRS', 'ACTIVE', ?, 'WEALTH')", (timestamp,))
                
                conn.commit()
            finally:
                self._release_conn(conn, pool)
        except Exception as e:
            logger.error(f"[IRS] Heartbeat Error: {e}")

    def execute_tax_compliance(self):
        """
        [THE TITHE]
        Scans for Realized Gains (SELL orders in trade_queue).
        Calculates 30% Tax Withholding.
        Moves funds to IRS_USDT bucket.
        Allocates remainder to SNW/Reinvest.
        """
        try:
            conn, pool = self._get_conn()
            try:
                c = conn.cursor()
                
                # Find Unprocessed Sales
                query = """
                    SELECT t.id, t.asset, t.amount, t.price, t.executed_at
                    FROM trade_queue t
                    LEFT JOIN profit_allocation p ON t.id = p.trade_id
                    WHERE t.action='SELL' AND t.status='DONE' AND p.id IS NULL
                """
                c.execute(query)
                unprocessed = c.fetchall()
                
                if not unprocessed:
                    return

                logger.info(f"[IRS] 🧾 Processing {len(unprocessed)} Taxable Events...")

                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_execute, queue_insert
                    use_waq = True
                except ImportError:
                    use_waq = False

                for trade_id, asset, amount, price, timestamp in unprocessed:
                    gross_proceeds = amount * price
                    
                    # SANITY CHECK: Validate proceeds before allocation (prevents overflow)
                    if TRADE_VALIDATOR_AVAILABLE:
                        validator = get_validator()
                        is_valid, reason = validator.validate_profit_allocation(gross_proceeds)
                        if not is_valid:
                            logger.warning(f"[IRS] 🛑 PROFIT REJECTED: Trade #{trade_id} {asset} - {reason}")
                            continue  # Skip this allocation
                    
                    # TAX LOGIC (30% Flat Rate Schema)
                    # NOTE: SNW_LLC_USDC STUBBED — reactivate when SNW funding begins
                    irs_cut = gross_proceeds * 0.30
                    snw_cut = 0  # STUBBED: Was 0.20, now dormant until SNW activated
                    scout_cut = gross_proceeds * 0.10
                    reinvest_cut = gross_proceeds * 0.60  # Was 0.40, absorbed SNW's 20%
                    
                    if use_waq:
                        queue_execute(c, "UPDATE stablecoin_buckets SET balance = balance + :amt WHERE bucket_type='IRS_USDT'", {'amt': irs_cut}, source_agent='AgentIRS')
                        # queue_execute(c, "UPDATE stablecoin_buckets SET balance = balance + :amt WHERE bucket_type='SNW_LLC_USDC'", {'amt': snw_cut}, source_agent='AgentIRS')  # STUBBED
                        queue_execute(c, "UPDATE stablecoin_buckets SET balance = balance + :amt WHERE bucket_type='SCOUT_FUND_USDC'", {'amt': scout_cut}, source_agent='AgentIRS')
                        queue_execute(c, "UPDATE stablecoin_buckets SET balance = balance + :amt WHERE bucket_type='INJECTION_DAI'", {'amt': reinvest_cut}, source_agent='AgentIRS')
                        queue_insert(c, 'profit_allocation', 
                                    {'trade_id': trade_id, 'asset': asset, 'realized_gain_usd': gross_proceeds, 
                                     'irs_allocation': irs_cut, 'snw_allocation': snw_cut, 
                                     'reinvest_allocation': reinvest_cut, 'scout_allocation': scout_cut},
                                    source_agent='AgentIRS')
                    else:
                        c.execute("UPDATE stablecoin_buckets SET balance = balance + ? WHERE bucket_type='IRS_USDT'", (irs_cut,))
                        # c.execute("UPDATE stablecoin_buckets SET balance = balance + ? WHERE bucket_type='SNW_LLC_USDC'", (snw_cut,))  # STUBBED
                        c.execute("UPDATE stablecoin_buckets SET balance = balance + ? WHERE bucket_type='SCOUT_FUND_USDC'", (scout_cut,))
                        c.execute("UPDATE stablecoin_buckets SET balance = balance + ? WHERE bucket_type='INJECTION_DAI'", (reinvest_cut,))
                        c.execute("""
                            INSERT INTO profit_allocation (trade_id, asset, realized_gain_usd, irs_allocation, snw_allocation, reinvest_allocation, scout_allocation)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (trade_id, asset, gross_proceeds, irs_cut, snw_cut, reinvest_cut, scout_cut))
                    
                    logger.info(f"[IRS] 💸 WITHHOLDING: Trade #{trade_id} (${gross_proceeds:.2f}) -> Tax: ${irs_cut:.2f} | Net: ${gross_proceeds - irs_cut:.2f}")

                conn.commit()
            finally:
                self._release_conn(conn, pool)
            
        except Exception as e:
            logger.error(f"[IRS] Compliance Error: {e}")

    def run_audit_cycle(self):
        """
        The Audit: Verifies that Treasury Waterfalls matches actual holdings.
        """
        try:
            conn, pool = self._get_conn()
            try:
                c = conn.cursor()
                
                # Check IRS Bucket Health
                c.execute("SELECT sum(irs_allocation) FROM profit_allocation")
                row = c.fetchone()
                total_tax_liability = row[0] if row and row[0] else 0.0
                
                c.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type='IRS_USDT'")
                row = c.fetchone()
                cash_on_hand = row[0] if row and row[0] else 0.0
                
                if cash_on_hand < total_tax_liability:
                    logger.warning(f"[IRS] 🚨 DEFICIT ALERT: Tax Liability ${total_tax_liability:.2f} > Cash ${cash_on_hand:.2f}")
            finally:
                self._release_conn(conn, pool)
        except Exception as e:
            logger.error(f"[IRS] Audit Error: {e}")

    def run(self):
        logger.info(f"[IRS] 🚀 Agent Active. Monitoring Trade Queue.")
        while True:
            try:
                self._heartbeat()
                self.execute_tax_compliance()
                if int(time.time()) % 3600 < 60: # Hourly Audit
                    self.run_audit_cycle()
                time.sleep(60) # Check every minute
            except Exception as e:
                logger.error(f"[IRS] Loop Error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    agent = AgentIRS()
    agent.run()

