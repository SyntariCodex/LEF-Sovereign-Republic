"""
AgentInfo (The Narrative Radar)
Department: Dept_Strategy
Role: External Reality Verification & Sentiment Analysis
"""

import json
import redis
import sqlite3
import feedparser
import time
import requests
import os
import logging
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
# from utils.notifier import Notifier # REMOVED Phase 100
from pathlib import Path

# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection, table_exists
except ImportError:
    def table_exists(cursor, table_name):  # noqa: E306
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        return cursor.fetchone() is not None
    from contextlib import contextmanager
    import sqlite3 as _sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = _sqlite3.connect(db_path, timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()


class AgentInfo:
    def __init__(self, db_path=None):
        logging.info("[INFO] 📡 Narrative Radar Online.")
        self.db_path = db_path or os.getenv('DB_PATH', 'republic.db')
        self.analyzer = SentimentIntensityAnalyzer()
        
        # Redis - Use shared singleton
        try:
            from system.redis_client import get_redis
            self.r = get_redis()
        except ImportError:
            try:
                self.r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                self.r.ping()
            except (redis.RedisError, ConnectionError):
                self.r = None
        
        # RSS Config
        try:
            base_dir = Path(__file__).parent.parent.parent
            rss_path = base_dir / 'config' / 'rss_feeds.json'
            with open(rss_path, 'r') as f:
                self.rss_feeds = json.load(f)
        except (OSError, json.JSONDecodeError):
            self.rss_feeds = {}

    def scan_rss_feeds(self) -> float:
        """
        Scans Real-World RSS Feeds (DeFi, Crypto, Macro).
        """
        all_headlines = []
        categories = ['crypto_news', 'macro', 'defi'] 
        
        for cat in categories:
            urls = self.rss_feeds.get(cat, [])
            for url in urls:
                try:
                    headers = {'User-Agent': 'Mozilla/5.0 AgentInfo/1.0'}
                    response = requests.get(url, headers=headers, timeout=3) 
                    if response.status_code == 200:
                        feed = feedparser.parse(response.content)
                        for entry in feed.entries[:3]:
                            all_headlines.append(f"{entry.get('title', '')} {entry.get('summary', '')}")
                except (requests.RequestException, Exception):
                    pass
        
        if not all_headlines:
             # Fallback check for INTERNAL signals if external RSS fails
             # This ensures the "War Room" connection even if internet is flaky
             pass

        # === THE WAR ROOM CONNECTION ===
        # Fetch recent Gladiator Signals from DB to influence Sentiment
        try:
            db_path = os.getenv('DB_PATH', 'republic.db')
            # Handle relative path if needed, or assume AgentInfo runs with correct env
            if not os.path.exists(db_path):
                 # Try absolute path based on file location
                 base_dir = Path(__file__).parent.parent.parent.parent
                 # Check for env var again with absolute path fallback
                 db_name = os.getenv('DB_PATH', 'republic.db')
                 # If env var is just a filename, join it. If absolute, use it.
                 if not os.path.isabs(db_name):
                     db_path = base_dir / db_name
                 else:
                     db_path = Path(db_name)

            if os.path.exists(db_path):
                with db_connection(str(db_path)) as conn:
                    c = conn.cursor()
                    # Get Gladiator signals from last hour
                    c.execute("SELECT summary, sentiment_score FROM knowledge_stream WHERE source='GLADIATOR' AND timestamp > datetime('now', '-1 hour')")
                    signals = c.fetchall()
                
                if signals:
                    logging.info(f"[INFO] ⚔️ Integrating {len(signals)} War Room Signals...")
                    for summary, score in signals:
                        # Weight internal intelligence highly
                        all_headlines.append(f"INTERNAL INTELLIGENCE: {summary}")
        except Exception as e:
             logging.warning(f"[INFO] Failed to read War Room signals: {e}")

        if not all_headlines: return 50.0 # Neutral fallback

        total_score = 0.0
        count = 0
        for text in all_headlines:
            scores = self.analyzer.polarity_scores(text)
            sentiment_score = (scores['compound'] + 1) * 50
            total_score += sentiment_score
            count += 1
            
        final_score = round(total_score / count, 2)
        logging.info(f"[INFO] 📡 Sentiment Score: {final_score} (from {count} sources)")
        
        if self.r:
            self.r.set('market:sentiment', final_score)
            
        return final_score

    def monitor_strategic_targets(self):
        """
        Polls Helius for activity on 'Smart Money' wallets.
        """
        try:
            helius_key = os.getenv("HELIUS_API_KEY")
            if not helius_key: return

            # Get Targets
            with db_connection(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                if not table_exists(c, 'strategic_targets'): return  # No targets yet
                
                c.execute("SELECT address FROM strategic_targets")
                targets = [r['address'] for r in c.fetchall()]
            
            if not targets: return

            # HELIUS POLL (Simplified for MVP)
            # In production, use Webhooks. For local, we check last 10 txs.
            # Using raw requests for simplicity if SDK fails, or SDK if available.
            # Let's use requests for max reliability given dependency uncertainty.
            
            for address in targets:
                url = f"https://api.helius.xyz/v0/addresses/{address}/transactions?api-key={helius_key}"
                resp = requests.get(url)
                if resp.status_code == 200:
                    txs = resp.json()
                    # Check if any TX is very recent (< 1 min)
                    if txs and isinstance(txs, list) and len(txs) > 0:
                        last_tx = txs[0]
                        # Timestamp check (Helius uses unix timestamp)
                        if last_tx.get('timestamp', 0) > time.time() - 300: # 5 mins
                            logging.info(f"[INFO] 🚨 SMART MONEY ALERT: {address} active!")
                            self._publish_signal(address, last_tx)

        except Exception as e:
            logging.error(f"[INFO] Helius Error: {e}")

    def _publish_signal(self, address, tx_data):
        # Publish to 'trade_signals' table for Treasury
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute('''CREATE TABLE IF NOT EXISTS trade_signals 
                             (source TEXT, target TEXT, signal_type TEXT, token TEXT, timestamp REAL)''')
                
                # Simple Logic: If they swapped, we signal
                if 'SWAP' in tx_data.get('type', 'UNKNOWN'):
                    c.execute("INSERT INTO trade_signals VALUES (?, ?, ?, ?, ?)",
                              ("AGENT_INFO", address, "COPY_TRADE", "SOL", time.time()))
                    conn.commit()
                    logging.info(f"[INFO] 📡 Signal Published to Treasury.")
        except sqlite3.Error:
            pass

    def calculate_macro_regime(self, sentiment_score):
        """
        Calculate macro regime based on sentiment score.
        Updates wealth_strategy.json with current regime.
        
        Regime levels (Phase 12 - from AgentCivics migration):
        - PRESERVATION: sentiment < 35 (defensive, reduce risk)
        - ACCUMULATION: sentiment 35-65 (normal operations)
        - AGGRESSIVE: sentiment > 65 (expand positions)
        """
        # Determine regime
        if sentiment_score < 35:
            regime = "PRESERVATION"
        elif sentiment_score > 65:
            regime = "AGGRESSIVE"
        else:
            regime = "ACCUMULATION"
        
        # Update wealth_strategy.json
        try:
            base_dir = Path(__file__).parent.parent.parent
            config_path = base_dir / 'config' / 'wealth_strategy.json'
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
            
            old_regime = config.get('regime', 'UNKNOWN')
            config['regime'] = regime
            config['macro_score'] = sentiment_score
            config['regime_updated_by'] = 'AgentInfo'
            config['regime_timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%S')
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            if old_regime != regime:
                logging.info(f"[INFO] 🔄 Regime Shift: {old_regime} → {regime} (score: {sentiment_score})")
                
                # Publish regime change event
                if self.r:
                    self.r.publish('events', json.dumps({
                        'type': 'REGIME_CHANGE',
                        'source': 'AgentInfo',
                        'old_regime': old_regime,
                        'new_regime': regime,
                        'macro_score': sentiment_score
                    }))
            else:
                logging.info(f"[INFO] 📊 Regime: {regime} (score: {sentiment_score})")
                
        except Exception as e:
            logging.error(f"[INFO] Regime update error: {e}")
        
        return regime

    def run_cycle(self):
        sentiment = self.scan_rss_feeds()
        self.calculate_macro_regime(sentiment)
        self.monitor_strategic_targets()

def run_info_loop(db_path=None):
    agent = AgentInfo(db_path)
    while True:
        try:
            agent.run_cycle()
            time.sleep(15) 
        except Exception as e:
            logging.error(f"[INFO] Loop Error: {e}")
            time.sleep(15)
