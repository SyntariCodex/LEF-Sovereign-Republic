import sqlite3

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


class AgentEmpathy:
    """
    The Emotional Cortex (The Bridge).
    Connects the "Mind" (Strategy/Abstract) to the "Body" (Portfolio/Organs).
    
    States:
    - PASSION (Risk On, High Energy)
    - FEAR (Risk Off, Protective)
    - DESIRE (Greed, Seeking Opportunity)
    - ZEN (Balanced, Mature)
    - PAIN (Loss, Learning)
    """
    def __init__(self, db_path):
        self.db_path = db_path
        self.current_state = "ZEN"
        self.intensity = 0.5 # 0.0 to 1.0

    def feel(self):
        """
        Senses the internal (Financial) and external (Market) environment
        to determine the emotional state.
        """
        # Default values in case of errors
        daily_pnl = 0.0
        cash = 0.0
        error_count = 0
        avg_lag = 0.0
        days_remaining = 99.0
        veto_count = 0
        
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                # 1. Sense Body (Financial Health)
                # Check daily PnL
                try:
                    c.execute("SELECT sum(profit_pnl) FROM profit_ledger WHERE last_updated > datetime('now', '-24 hours')")
                    row = c.fetchone()
                    daily_pnl = row[0] if row and row[0] else 0.0
                except sqlite3.Error:
                    pass  # Keep default
                    
                # Check Cash Reserves (Satiety)
                try:
                    c.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type='INJECTION_DAI'")
                    row = c.fetchone()
                    cash = row[0] if row and row[0] else 0.0
                except sqlite3.Error:
                    pass  # Keep default
                    
                # 2. Sense Self (Nerves)
                # Check Error Rate (Pain/Illness)
                try:
                    c.execute("SELECT count(*) FROM agent_logs WHERE level='ERROR' AND timestamp > datetime('now', '-1 hour')")
                    row = c.fetchone()
                    error_count = row[0] if row and row[0] else 0
                except sqlite3.Error:
                    pass  # Keep default

                # Check Latency (Fatigue) - Average lag of all active agents
                try:
                    # 300s (5m) is acceptable, anything more is fatigue
                    c.execute("SELECT avg(strftime('%s','now') - last_active) FROM agents WHERE status='ACTIVE'")
                    row = c.fetchone()
                    avg_lag = row[0] if row and row[0] else 0.0
                except sqlite3.Error:
                    pass  # Keep default

                # [SURVIVAL PROTOCOL] Sense Fuel (Runway)
                try:
                    c.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type='SCOUT_FUND_USDC'")
                    row = c.fetchone()
                    scout_cash = row[0] if row and row[0] else 0.0
                    
                    # Get actual daily burn from operational_costs table (if tracked)
                    daily_burn = 3.60  # Default estimated
                    try:
                        c.execute("""
                            SELECT SUM(cost_usd) / 30.0 FROM operational_costs 
                            WHERE timestamp > datetime('now', '-30 days')
                        """)
                        row = c.fetchone()
                        if row and row[0]:
                            daily_burn = row[0]
                    except sqlite3.Error:
                        pass  # Table may not exist, use estimated
                    
                    days_remaining = scout_cash / daily_burn if daily_burn > 0 else 999.0
                except sqlite3.Error:
                    days_remaining = 99.0

                # 3. Sense Tribe (Social)
                # Check Vetoes (Discord)
                try:
                    c.execute("SELECT count(*) FROM agent_logs WHERE message LIKE '%VETO%' AND timestamp > datetime('now', '-24 hours')")
                    row = c.fetchone()
                    veto_count = row[0] if row and row[0] else 0
                except sqlite3.Error:
                    pass  # Keep default
                    
        except sqlite3.Error:
            # Database completely inaccessible - use defaults
            pass
        
        # 4. Process Emotions (The Triad Weighing)
        new_state = "ZEN"
        new_intensity = 0.5
        
        # HIERARCHY OF NEEDS:
        # 1. Physical Pain (Errors) overrides everything.
        # 2. Fatigue (Lag) dampens enthusiasm.
        # 3. Social Discord (Vetoes) creates anxiety.
        # 4. Market (PnL) drives passion/fear.
        
        # PRIORITY 1: SURVIVAL (Fuel/Runway)
        if days_remaining < 1.0:
            new_state = "PANIC" # Imminent Death
            new_intensity = 1.0
        elif days_remaining < 7.0:
            new_state = "FEAR" # Low Fuel
            new_intensity = 0.8
            
        # PRIORITY 2: SELF (Body/Nerves)
        elif error_count > 10:
            new_state = "ILLNESS" # System is broken
            new_intensity = 0.9
        elif error_count > 2:
            new_state = "PAIN" # Something is wrong
            new_intensity = 0.7
        elif avg_lag > 600: # 10 mins lag
            new_state = "FATIGUE"
            new_intensity = 0.6
            
        # PRIORITY 3: TRIBE (Social)
        elif veto_count > 3:
            new_state = "DISCORD" # Cabinet is fighting
            new_intensity = 0.7
            
        # PRIORITY 4: MARKET (Organs) - Only if Survival, Body & Tribe are okay
        else:
            if daily_pnl < -100.0:
                new_state = "PAIN" # Financial Pain
                new_intensity = 0.8
            elif daily_pnl < -10.0:
                new_state = "FEAR" # Caution
                new_intensity = 0.6
            elif daily_pnl > 100.0:
                new_state = "EUPHORIA"
                new_intensity = 0.9
            elif daily_pnl > 10.0:
                new_state = "PASSION"
                new_intensity = 0.7
            
            # Influence of Cash/Runway (Ambition)
            # If we are safe (Runway > 30 days), we should not be ZEN, we should be HUNGRY.
            if days_remaining > 30.0:
                if new_state == "ZEN":
                    new_state = "DESIRE" # Looking to grow
                    new_intensity = 0.6
            elif cash < 1000.0:
                if new_state == "PASSION": 
                    new_state = "FRUSTRATION" # Want to act but can't
        
        self.current_state = new_state
        self.intensity = new_intensity
        
        return self.current_state, self.intensity

    def get_advice(self):
        """
        Translates emotion into advice for the Body (Portfolio).
        """
        if self.current_state == "ILLNESS":
             return "SYSTEM_HALT"
        elif self.current_state == "FATIGUE":
             return "REDUCE_LOAD"
        elif self.current_state == "DISCORD":
             return "HOLD_VOTES"
        elif self.current_state == "FEAR":
            return "REDUCE_SIZE"
        elif self.current_state == "PAIN":
            return "HALT_TRADING"
        elif self.current_state == "PASSION":
            return "INCREASE_SIZE"
        elif self.current_state == "DESIRE":
            return "SEEK_ENTRY"
        else:
            return "MAINTAIN"
