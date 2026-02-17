"""
AgentChronicler (The Keeper of Histories)
Department: Dept_Education
Role: Longitudinal coin analysis, lifecycle tracking, pattern recognition.

Philosophy:
    "To understand where a coin is going, you must know where it has been."
    
    AgentChronicler studies the biography of coins - not just their current
    metrics, but their evolution over time. It correlates price movements
    with news narratives, GitHub activity, and governance events to identify
    patterns that distinguish legitimate infrastructure from moonshots.

Responsibilities:
    1. Track coin lifecycle stages (CONCEPT → INSTITUTION)
    2. Calculate Governance Health Score
    3. Correlate historical price with news/sentiment
    4. Feed maturity classifications to CoinMgr
    5. Identify pattern shifts (growth → stagnation, etc.)

Data Sources:
    - Historical price/volume (CoinGecko, CoinMarketCap)
    - GitHub activity (commits, PRs, issues)
    - News/sentiment archives (knowledge_stream)
    - Governance proposals (on-chain when available)
"""

import os
import sys
import time
import json
import logging
import redis
import requests
from datetime import datetime

# Path setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))

# Use centralized db_helper for connection pooling
try:
    from db.db_helper import db_connection
except ImportError:
    from contextlib import contextmanager
    import sqlite3
    @contextmanager
    def db_connection(db_path=None, timeout=120.0):
        conn = sqlite3.connect(db_path or DB_PATH, timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()

try:
    from utils.agent_registry import register_agent, heartbeat
except ImportError:
    register_agent = lambda *a, **k: None
    heartbeat = lambda *a, **k: None

logging.basicConfig(level=logging.INFO)


class AgentChronicler:
    """
    The Keeper of Histories: Longitudinal coin analysis.
    
    Tracks the biography of each coin:
    - Where did it start?
    - What promises did it make (whitepaper)?
    - Did it deliver?
    - How has governance evolved?
    - What stage of maturity is it in?
    """
    
    # Maturity stages
    STAGES = ['CONCEPT', 'LAUNCH', 'TRACTION', 'INFRASTRUCTURE', 'INSTITUTION', 'DECLINING', 'ZOMBIE']
    
    # Stage indicators
    STAGE_CRITERIA = {
        'CONCEPT': {'has_token': False},
        'LAUNCH': {'age_days': (0, 90), 'volume_24h': (0, 1_000_000)},
        'TRACTION': {'age_days': (90, 365), 'volume_24h': (1_000_000, 50_000_000)},
        'INFRASTRUCTURE': {'age_days': (365, None), 'volume_24h': (50_000_000, None), 'ecosystem_projects': 10},
        'INSTITUTION': {'age_days': (730, None), 'governance_score': 70},
    }
    
    # Governance health weights
    GOV_WEIGHTS = {
        'github_activity': 0.25,
        'whitepaper_delivery': 0.20,
        'team_transparency': 0.15,
        'governance_health': 0.20,
        'fork_stability': 0.10,
        'sentiment_trajectory': 0.10
    }
    
    # Known GitHub repos for major coins (can be expanded)
    GITHUB_REPOS = {
        'BTC': 'bitcoin/bitcoin',
        'ETH': 'ethereum/go-ethereum',
        'SOL': 'solana-labs/solana',
        'AVAX': 'ava-labs/avalanchego',
        'ATOM': 'cosmos/cosmos-sdk',
        'DOT': 'paritytech/polkadot',
        'ADA': 'input-output-hk/cardano-node',
        'LINK': 'smartcontractkit/chainlink',
        'UNI': 'Uniswap/v3-core',
        'AAVE': 'aave/aave-v3-core',
        'MATIC': 'maticnetwork/bor',
        'XRP': 'ripple/rippled',
        'NEAR': 'near/nearcore',
        'APT': 'aptos-labs/aptos-core',
        'SUI': 'MystenLabs/sui',
        'ARB': 'OffchainLabs/nitro',
        'OP': 'ethereum-optimism/optimism',
    }
    
    # Known attributes for major coins (bootstrap data)
    COIN_ATTRIBUTES = {
        'BTC': {'team_doxxed': True, 'whitepaper_delivered': True, 'has_governance': False},
        'ETH': {'team_doxxed': True, 'whitepaper_delivered': True, 'has_governance': True},
        'SOL': {'team_doxxed': True, 'whitepaper_delivered': True, 'has_governance': True},
        'AVAX': {'team_doxxed': True, 'whitepaper_delivered': True, 'has_governance': True},
        'ATOM': {'team_doxxed': True, 'whitepaper_delivered': True, 'has_governance': True},
        'DOT': {'team_doxxed': True, 'whitepaper_delivered': True, 'has_governance': True},
        'LINK': {'team_doxxed': True, 'whitepaper_delivered': True, 'has_governance': False},
        'XRP': {'team_doxxed': True, 'whitepaper_delivered': True, 'has_governance': False},
    }
    
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.name = "AgentChronicler"
        logging.info(f"[CHRONICLER] 📚 The Keeper of Histories is Online.")
        
        self._ensure_tables()
        
        # Register with matrix
        register_agent(self.name, "EDUCATION", self.db_path)
        
        # Redis - Use shared singleton
        try:
            from system.redis_client import get_redis
            self.redis = get_redis()
        except ImportError:
            try:
                self.redis = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'),
                                          port=6379, db=0, decode_responses=True)
                self.redis.ping()
            except (redis.RedisError, ConnectionError):
                self.redis = None

    # Phase 34: _get_db_connection() removed — all callers converted to db_connection() context manager

    
    def _ensure_tables(self):
        """Create chronicles tables if they don't exist."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()

                # Coin chronicles - longitudinal data
                c.execute("""
                    CREATE TABLE IF NOT EXISTS coin_chronicles (
                        symbol TEXT PRIMARY KEY,
                        name TEXT,
                        first_seen TIMESTAMP,
                        maturity_stage TEXT DEFAULT 'UNKNOWN',
                        governance_score REAL,
                        github_url TEXT,
                        github_commits_30d INTEGER,
                        github_last_commit TIMESTAMP,
                        whitepaper_delivered BOOLEAN DEFAULT 0,
                        team_doxxed BOOLEAN DEFAULT 0,
                        has_governance BOOLEAN DEFAULT 0,
                        fork_count INTEGER DEFAULT 0,
                        sentiment_trend TEXT,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Price history snapshots
                c.execute("""
                    CREATE TABLE IF NOT EXISTS coin_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT,
                        snapshot_date DATE,
                        price_usd REAL,
                        volume_24h REAL,
                        market_cap REAL,
                        sentiment_score REAL,
                        news_count INTEGER,
                        UNIQUE(symbol, snapshot_date)
                    )
                """)

                conn.commit()
            logging.info("[CHRONICLER] Chronicle tables ready.")
        except Exception as e:
            logging.error(f"[CHRONICLER] Table creation error: {e}")
    
    # =========================================================================
    # COIN LIFECYCLE ANALYSIS
    # =========================================================================
    
    def classify_maturity_stage(self, symbol, data):
        """
        Determine which lifecycle stage a coin is in.
        
        Stages:
        CONCEPT → LAUNCH → TRACTION → INFRASTRUCTURE → INSTITUTION
        (or DECLINING → ZOMBIE if degrading)
        """
        age_days = data.get('age_days', 0)
        volume = data.get('volume_24h', 0)
        market_cap = data.get('market_cap', 0)
        gov_score = data.get('governance_score', 0)
        ecosystem = data.get('ecosystem_projects', 0)
        
        # Check for zombie (declining with no recovery)
        if data.get('volume_trend') == 'DECLINING' and age_days > 365:
            return 'DECLINING'
        
        if volume < 10000 and age_days > 180:
            return 'ZOMBIE'
        
        # Check stages from highest to lowest
        if age_days >= 730 and gov_score >= 70:
            return 'INSTITUTION'
        
        if age_days >= 365 and volume >= 50_000_000:
            return 'INFRASTRUCTURE'
        
        if age_days >= 90 and volume >= 1_000_000:
            return 'TRACTION'
        
        if age_days < 90:
            return 'LAUNCH'
        
        return 'UNKNOWN'
    
    # =========================================================================
    # GOVERNANCE HEALTH SCORING
    # =========================================================================
    
    def calculate_governance_score(self, symbol):
        """
        Calculate Governance Health Score (0-100).
        
        Components:
        - GitHub activity (25%)
        - Whitepaper delivery (20%)
        - Team transparency (15%)
        - Governance health (20%)
        - Fork stability (10%)
        - Sentiment trajectory (10%)
        """
        scores = {}

        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()

                c.execute("SELECT * FROM coin_chronicles WHERE symbol = ?", (symbol,))
                row = c.fetchone()

                if not row:
                    return None

                # Convert to dict
                columns = [desc[0] for desc in c.description]
                data = dict(zip(columns, row))

            # GitHub activity score
            commits = data.get('github_commits_30d') or 0  # Handle None
            if commits >= 50:
                scores['github_activity'] = 100
            elif commits >= 20:
                scores['github_activity'] = 75
            elif commits >= 5:
                scores['github_activity'] = 50
            else:
                scores['github_activity'] = 25

            # Whitepaper delivery
            scores['whitepaper_delivery'] = 100 if data.get('whitepaper_delivered') else 30

            # Team transparency
            scores['team_transparency'] = 100 if data.get('team_doxxed') else 40

            # Governance health
            scores['governance_health'] = 80 if data.get('has_governance') else 30

            # Fork stability (fewer forks = more stable)
            forks = data.get('fork_count') or 0  # Handle None
            if forks == 0:
                scores['fork_stability'] = 100
            elif forks <= 2:
                scores['fork_stability'] = 70
            else:
                scores['fork_stability'] = 40

            # Sentiment trajectory
            trend = data.get('sentiment_trend', 'NEUTRAL')
            if trend == 'IMPROVING':
                scores['sentiment_trajectory'] = 90
            elif trend == 'STABLE':
                scores['sentiment_trajectory'] = 70
            elif trend == 'DECLINING':
                scores['sentiment_trajectory'] = 30
            else:
                scores['sentiment_trajectory'] = 50

            # Weighted average
            total = sum(scores[k] * self.GOV_WEIGHTS[k] for k in scores)

            return round(total, 1)
            
        except Exception as e:
            logging.error(f"[CHRONICLER] Governance scoring error for {symbol}: {e}")
            return None
    
    # =========================================================================
    # DATA COLLECTION
    # =========================================================================
    
    def chronicle_coin(self, symbol, name=None):
        """
        Create or update chronicle entry for a coin.
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()

                # Check if exists
                c.execute("SELECT symbol FROM coin_chronicles WHERE symbol = ?", (symbol,))
                exists = c.fetchone()

                # --- PHASE 30: USE WRITE QUEUE ---
                try:
                    from db.db_writer import queue_insert, queue_update

                    if not exists:
                        queue_insert(
                            c, 'coin_chronicles',
                            {'symbol': symbol, 'name': name or symbol},
                            source_agent='AgentChronicler'
                        )
                        logging.info(f"[CHRONICLER] New chronicle started: {symbol}")
                    else:
                        queue_update(
                            c, 'coin_chronicles',
                            {'last_updated': 'CURRENT_TIMESTAMP'},
                            {'symbol': symbol},
                            source_agent='AgentChronicler'
                        )
                except ImportError:
                    if not exists:
                        c.execute("""
                            INSERT INTO coin_chronicles (symbol, name, first_seen, last_updated)
                            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """, (symbol, name or symbol))
                        logging.info(f"[CHRONICLER] New chronicle started: {symbol}")
                    else:
                        c.execute("""
                            UPDATE coin_chronicles SET last_updated = CURRENT_TIMESTAMP WHERE symbol = ?
                        """, (symbol,))

                conn.commit()
            return True

        except Exception as e:
            logging.error(f"[CHRONICLER] Chronicle error for {symbol}: {e}")
            return False
    
    def update_chronicle_metrics(self, symbol, metrics):
        """
        Update chronicle with new metrics.
        """
        # Phase 34: Whitelist columns to prevent injection via dynamic keys
        ALLOWED_COLUMNS = {'github_commits_30d', 'whitepaper_delivered', 'team_doxxed',
                           'has_governance', 'fork_count', 'sentiment_trend', 'github_url'}
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()

                # Build dynamic update
                updates = []
                values = []
                for key, value in metrics.items():
                    if key in ALLOWED_COLUMNS:
                        updates.append(f"{key} = ?")
                        values.append(value)

                if updates:
                    values.append(symbol)
                    sql = f"UPDATE coin_chronicles SET {', '.join(updates)}, last_updated = CURRENT_TIMESTAMP WHERE symbol = ?"
                    try:
                        from db.db_writer import queue_execute
                        queue_execute(c, sql, tuple(values), source_agent='AgentChronicler', priority=0)
                    except ImportError:
                        c.execute(sql, values)
                        conn.commit()

            return True

        except Exception as e:
            logging.error(f"[CHRONICLER] Metrics update error for {symbol}: {e}")
            return False
    
    def update_maturity_and_score(self, symbol):
        """
        Recalculate maturity stage and governance score for a coin.
        Phase 34: Uses context manager — no leaked connections.
        """
        try:
            # Step 1: Read current data (acquire+release)
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM coin_chronicles WHERE symbol = ?", (symbol,))
                row = c.fetchone()

                if not row:
                    return False

                columns = [desc[0] for desc in c.description]
                data = dict(zip(columns, row))

                c.execute("""
                    SELECT market_cap, volume_24h, first_seen
                    FROM market_universe WHERE symbol = ?
                """, (symbol,))
                market_data = c.fetchone()

                if market_data:
                    market_cap, volume, first_seen = market_data
                    try:
                        first_date = datetime.fromisoformat(str(first_seen).replace('Z', ''))
                        age_days = (datetime.now() - first_date).days
                    except (ValueError, TypeError):
                        age_days = 0
                    data['age_days'] = age_days
                    data['volume_24h'] = volume or 0
                    data['market_cap'] = market_cap or 0

            # Step 2: Calculate scores (no DB held)
            gov_score = self.calculate_governance_score(symbol)
            data['governance_score'] = gov_score or 0
            stage = self.classify_maturity_stage(symbol, data)

            # Step 3: Write update (acquire+release)
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                try:
                    from db.db_writer import queue_execute
                    queue_execute(
                        c,
                        "UPDATE coin_chronicles SET maturity_stage = ?, governance_score = ?, last_updated = CURRENT_TIMESTAMP WHERE symbol = ?",
                        (stage, gov_score, symbol),
                        source_agent='AgentChronicler', priority=0
                    )
                except ImportError:
                    c.execute("""
                        UPDATE coin_chronicles
                        SET maturity_stage = ?, governance_score = ?, last_updated = CURRENT_TIMESTAMP
                        WHERE symbol = ?
                    """, (stage, gov_score, symbol))
                    conn.commit()

            logging.debug(f"[CHRONICLER] {symbol}: Stage={stage}, Gov={gov_score}")
            return True

        except Exception as e:
            logging.error(f"[CHRONICLER] Update error for {symbol}: {e}")
            return False
    
    # =========================================================================
    # SYNC WITH MARKET UNIVERSE
    # =========================================================================
    
    def sync_from_universe(self):
        """
        Ensure all coins in market_universe have chronicle entries.
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute("SELECT symbol, name FROM market_universe")
                coins = c.fetchall()

            for symbol, name in coins:
                self.chronicle_coin(symbol, name)
                self.update_maturity_and_score(symbol)

            logging.info(f"[CHRONICLER] Synced {len(coins)} coins from market_universe")
            return len(coins)

        except Exception as e:
            logging.error(f"[CHRONICLER] Sync error: {e}")
            return 0
    
    # =========================================================================
    # GITHUB DATA FETCHING
    # =========================================================================
    
    def fetch_github_activity(self, symbol):
        """
        Fetch GitHub commit activity for a coin's main repo.
        Uses public GitHub API (no auth needed for basic stats).
        """
        if symbol not in self.GITHUB_REPOS:
            return None
        
        repo = self.GITHUB_REPOS[symbol]
        
        try:
            # Get commit activity for last 4 weeks
            url = f"https://api.github.com/repos/{repo}/stats/commit_activity"
            headers = {'Accept': 'application/vnd.github.v3+json'}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                weeks = response.json()
                if weeks and isinstance(weeks, list):
                    # Sum commits from last 4 weeks (approximately 30 days)
                    recent_weeks = weeks[-4:] if len(weeks) >= 4 else weeks
                    commits_30d = sum(w.get('total', 0) for w in recent_weeks)
                    
                    logging.info(f"[CHRONICLER] 🔧 {symbol} GitHub: {commits_30d} commits in 30 days")
                    
                    # Update chronicle
                    self.update_chronicle_metrics(symbol, {
                        'github_url': f"https://github.com/{repo}",
                        'github_commits_30d': commits_30d
                    })
                    
                    return commits_30d
            elif response.status_code == 202:
                # GitHub is computing stats, try again later
                logging.info(f"[CHRONICLER] ⏳ GitHub computing stats for {symbol}")
                
        except Exception as e:
            logging.error(f"[CHRONICLER] GitHub fetch error for {symbol}: {e}")
        
        return None
    
    def enrich_known_coins(self):
        """
        Apply known attributes for major coins and fetch GitHub data.
        This bootstraps governance data for coins we have info about.
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute("SELECT symbol FROM coin_chronicles")
                chronicle_coins = [r[0] for r in c.fetchall()]

            enriched = 0

            for symbol in chronicle_coins:
                # Apply known attributes
                if symbol in self.COIN_ATTRIBUTES:
                    self.update_chronicle_metrics(symbol, self.COIN_ATTRIBUTES[symbol])
                    enriched += 1
                
                # Fetch GitHub data (rate limit: be gentle)
                if symbol in self.GITHUB_REPOS:
                    self.fetch_github_activity(symbol)
                    time.sleep(1)  # Rate limit: 1 request per second
            
            if enriched > 0:
                logging.info(f"[CHRONICLER] ✨ Enriched {enriched} coins with known data")
            
            return enriched
            
        except Exception as e:
            logging.error(f"[CHRONICLER] Enrichment error: {e}")
            return 0
    
    # =========================================================================
    # NEWS/SENTIMENT CORRELATION
    # =========================================================================
    
    def correlate_with_news(self, symbol, days=30):
        """
        Analyze correlation between news sentiment and price movement.
        Uses price history from coin_history and sentiment from knowledge_stream.
        """
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()

                # Get price changes over the period
                c.execute("""
                    SELECT DATE(timestamp) as date,
                           (MAX(price) - MIN(price)) / MIN(price) * 100 as price_change
                    FROM coin_history
                    WHERE symbol = ?
                      AND timestamp > datetime('now', ?)
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                """, (symbol, f'-{days} days'))
                prices = {row[0]: row[1] for row in c.fetchall()}

                if not prices:
                    return {'symbol': symbol, 'correlation': None, 'reason': 'No price data'}

                # Get news sentiment scores using weighted word analysis
                c.execute("""
                    SELECT DATE(created_at) as date,
                           AVG(
                               CASE WHEN summary LIKE '%bullish%' THEN 1.0 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%surge%' THEN 0.8 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%rally%' THEN 0.8 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%moon%' THEN 0.6 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%breakout%' THEN 0.7 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%growth%' THEN 0.5 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%adoption%' THEN 0.6 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%partnership%' THEN 0.5 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%upgrade%' THEN 0.4 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%bullrun%' THEN 0.9 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%accumulation%' THEN 0.5 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%buy signal%' THEN 0.8 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%bearish%' THEN -1.0 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%crash%' THEN -0.9 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%dump%' THEN -0.8 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%sell%' THEN -0.3 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%fear%' THEN -0.6 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%panic%' THEN -0.8 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%hack%' THEN -0.9 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%rug%' THEN -1.0 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%scam%' THEN -1.0 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%bankrupt%' THEN -1.0 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%regulation%' THEN -0.3 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%lawsuit%' THEN -0.6 ELSE 0.0 END +
                               CASE WHEN summary LIKE '%decline%' THEN -0.5 ELSE 0.0 END
                           ) as sentiment
                    FROM knowledge_stream
                    WHERE (title LIKE ? OR summary LIKE ?)
                      AND created_at > datetime('now', ?)
                    GROUP BY DATE(created_at)
                """, (f'%{symbol}%', f'%{symbol}%', f'-{days} days'))
                sentiments = {row[0]: row[1] for row in c.fetchall()}

            if not sentiments:
                return {'symbol': symbol, 'correlation': None, 'reason': 'No news data'}
            
            # Calculate simple correlation (matching dates)
            matching_dates = set(prices.keys()) & set(sentiments.keys())
            if len(matching_dates) < 5:
                return {'symbol': symbol, 'correlation': None, 'reason': 'Insufficient overlap'}
            
            # Simple correlation: count agreements
            agreements = 0
            for date in matching_dates:
                if (prices[date] > 0 and sentiments[date] > 0) or \
                   (prices[date] < 0 and sentiments[date] < 0):
                    agreements += 1
            
            correlation = agreements / len(matching_dates)
            
            logging.info(f"[CHRONICLER] 📰 News correlation for {symbol}: {correlation:.1%}")
            return {
                'symbol': symbol,
                'correlation': correlation,
                'sample_size': len(matching_dates),
                'status': 'COMPLETE'
            }
            
        except Exception as e:
            logging.error(f"[CHRONICLER] Correlation error: {e}")
            return {'symbol': symbol, 'correlation': None, 'reason': str(e)}
    
    # =========================================================================
    # MAIN CYCLE
    # =========================================================================
    
    def run_cycle(self):
        """
        Chronicler cycle (runs every 2 hours).
        
        Focus:
        1. Sync with market universe
        2. Enrich with GitHub/known data
        3. Update maturity stages
        4. Calculate governance scores
        """
        logging.info("[CHRONICLER] 📚 Historical Analysis Cycle Starting...")
        
        while True:
            try:
                # Sync and update all tracked coins
                self.sync_from_universe()
                
                # Enrich with GitHub data and known attributes
                self.enrich_known_coins()
                
                time.sleep(7200)  # 2 hour cycle
                
            except Exception as e:
                logging.error(f"[CHRONICLER] Cycle error: {e}")
                time.sleep(600)


def run_chronicler_loop(db_path=None):
    """Entry point for main.py"""
    agent = AgentChronicler(db_path)
    agent.run_cycle()


if __name__ == "__main__":
    agent = AgentChronicler()
    agent.run_cycle()
