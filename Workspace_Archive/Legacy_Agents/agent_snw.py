import time
import sqlite3
import redis
import json
import logging
import os
import random
import requests
from datetime import datetime

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AgentSNW")

class AgentSNW:
    """
    AGENT SNW: The Steward.
    -----------------------
    Role: Macro Awareness & Strategic Guidance.
    Mission: Fetch 'The Weather' (Macro Data) and guide Fulcrum (The Body).
    
    Data Sources (Simulated/Real):
    1. Fed Funds Rate (Interest Rates)
    2. CPI (Inflation)
    3. Crypto Fear & Greed Index
    """
    
    def __init__(self, db_path=None):
        if db_path is None:
             BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
             self.db_path = os.path.join(BASE_DIR, 'republic.db')
        else:
             self.db_path = db_path
        self.db_path = db_path
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        try:
            self.r = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)
            self.r.ping()
            logger.info(f"Connected to Redis at {redis_host}")
        except:
            logger.warning("Redis connection failed. Running in localized mode.")
            self.r = None

    def fetch_macro_indicators(self):
        """
        Fetches or simulates key economic indicators.
        In a real prod environment, this would hit FRED API or TradingEconomics.
        For now, we use realistic range simulation with random walk.
        """
        logger.info("📡 Scanning Economic Horizons...")
        
        # 1. Fed Funds Rate (Simulated 4.0% - 5.5% range)
        # Using a deterministic random walk based on day of year to simulate slow trends
        day_of_year = datetime.now().timetuple().tm_yday
        base_rate = 5.0
        rate_swing = 1.0 * (random.random() - 0.5) # +/- 0.5% noise
        current_rate = base_rate + (day_of_year % 30) * 0.01  # Slow drift
        
        # 2. Fear & Greed Index (Real API if available, else Mock)
        fear_greed_val = 50
        try:
            # Attempt to fetch real data from Alternative.me API
            resp = requests.get("https://api.alternative.me/fng/", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                fear_greed_val = int(data['data'][0]['value'])
                logger.info(f"🌍 Real Fear & Greed Index fetched: {fear_greed_val}")
            else:
                raise Exception("API Error")
        except:
            logger.warning("Could not fetch Fear & Greed API. Using simulated sentiment.")
            # Simulate based on recent volatility or random
            fear_greed_val = random.randint(20, 80)

        # 3. CPI (Inflation) - Sticky around 3%
        cpi = 3.2 + random.uniform(-0.2, 0.2)
        
        # publish
        macro_report = {
            'fed_rate': round(current_rate, 2),
            'cpi': round(cpi, 2),
            'fear_greed': fear_greed_val,
            'timestamp': time.time()
        }
        
        return macro_report

    def publish_weather_report(self, report):
        """
        Publishes the Macro Context to Redis for Fulcrum Master to see.
        """
        if self.r:
            self.r.set("macro:fed_rate", report['fed_rate'])
            self.r.set("macro:cpi", report['cpi'])
            self.r.set("macro:fear_greed", report['fear_greed'])
            self.r.set("macro:last_updated", report['timestamp'])
            
            # Derived Liquidity Status
            # High Rate + High Inflation = TIGHT (Bad for Risk)
            # Low Rate + Low Inflation = LOOSE (Good for Risk)
            liquidity = "NEUTRAL"
            if report['fed_rate'] > 4.5:
                liquidity = "TIGHT"
            elif report['fed_rate'] < 3.0:
                liquidity = "LOOSE"
            
            self.r.set("macro:liquidity_status", liquidity)
            logger.info(f"🌩️  Weather Report Published: Rates={report['fed_rate']}%, F&G={report['fear_greed']}, Liquidity={liquidity}")
            return liquidity
        return "UNKNOWN"

    def archive_history(self, report, liquidity):
        """
        Writes the history to the database for LEF (Long Term Memory).
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                INSERT INTO macro_history 
                (fed_rate, cpi_inflation, fear_greed_index, liquidity_status)
                VALUES (?, ?, ?, ?)
            """, (report['fed_rate'], report['cpi'], report['fear_greed'], liquidity))
            conn.commit()
            conn.close()
            logger.info("📜 Macro History Archived.")
        except Exception as e:
            logger.error(f"Failed to archive macro history: {e}")

    def accrue_yield(self):
        """
        THE BANKER: Pays interest on Stablecoin Buckets.
        Runs every loop (simulated as Hourly).
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            # Select Interest Bearing Buckets
            c.execute("SELECT bucket_type, balance, interest_rate FROM stablecoin_buckets WHERE interest_rate > 0 AND balance > 0")
            rows = c.fetchall()
            
            total_payout = 0.0
            
            for row in rows:
                bucket, balance, apy = row
                
                # Calculate Hourly Yield
                # APY is Annual. 
                # hourly_rate = apy / (365 * 24)
                hourly_yield = balance * (apy / 8760.0)
                
                if hourly_yield > 0:
                    # Credit the account
                    c.execute("UPDATE stablecoin_buckets SET balance = balance + ? WHERE bucket_type=?", (hourly_yield, bucket))
                    total_payout += hourly_yield
                    # logger.info(f"💰 Yield Paid to {bucket}: +${hourly_yield:.4f} (APY {apy*100}%)")
            
            if total_payout > 0:
                 conn.commit()
                 logger.info(f"💸 TOTAL YIELD DISTRIBUTED: ${total_payout:.4f}")
                 
        except Exception as e:
            logger.error(f"Yield Accrual Failed: {e}")
        finally:
            conn.close()

    def run_steward_loop(self):
        """
        Main Loop. Runs infrequently (every 6 hours) as macro data moves slow.
        """
        logger.info("🏛️  Agent SNW (The Steward) Initialized.")
        
        while True:
            try:
                # 1. Fetch
                report = self.fetch_macro_indicators()
                
                # 2. Publish
                liquidity = self.publish_weather_report(report)
                
                # 3. Archive
                self.archive_history(report, liquidity)
                
                # 4. Pay Yield (The Bank)
                self.accrue_yield()
                
                # Sleep 1 hour.
                logger.info("Sleeping for 1 hour...")
                time.sleep(3600) 
                
            except Exception as e:
                logger.error(f"Steward Loop Error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    # Test Mode
    db_path = os.getenv('DB_PATH', 'republic.db')
    snw = AgentSNW(db_path=db_path)
    snw.run_steward_loop()
