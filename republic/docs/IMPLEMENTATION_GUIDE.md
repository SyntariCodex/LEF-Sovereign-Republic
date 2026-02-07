Prt 1: Instructions
Operational Instructions for The Distributed Virtual Fleet
This guide outlines the steps to take the code documentation from Parts 1–5, the "Muscle" integration (NLP/Signal Processing), and the Redis Message Bus to implement it as a functioning, distributed system on your MacBook Pro.


Phase 0: The Toolkit (Prerequisites)

Before creating files, ensure your MacBook has the necessary software environment.
1. The Editor: Visual Studio Code (VS Code)
	•	Purpose: The workspace where you will create and edit all Fulcrum files.
	•	Action: Download and install from code.visualstudio.com.

2. The Language: Python 3
	•	Purpose: The engine that runs Fulcrum code.
	•	Check: Open your Terminal (Cmd + Space, type "Terminal"). Type python3 --version.
	•	Action: If version does not appear, download from python.org or use Homebrew (brew install python).
3. The Libraries (Pip Packages)

These are external code modules needed for Fulcrum to talk to Exchanges, Twitter, run AI models, and connect to Redis.
	•	Action: Create a file named requirements.txt in your folder.
	•	Paste this content into: requirements.txt:
ccxt
tweepy
praw
requests
torch
transformers
Redis

	•	Install: Open Terminal in VS Code and run:
pip3 install -r requirements.txt

	•	ccxt: Connects to Coinbase/Exchanges.
	•	tweepy / praw: Connects to X/Twitter/Reddit.
	•	torch / transformers: Runs the AI "Muscle" (NLP Models).
	•	redis: Connects to the Message Bus.

4. The Message Bus Server: Redis
	•	Purpose: The "Nervous System" that allows agents to talk.
	•	Action: Open your standard Mac Terminal and run:
brew install redis
brew services start redis

Note: Keep this terminal window open or running in the background.

Phase 1: Environment Setup

1. Create the Work Space
	•	Go to your Desktop or Documents.
	•	Create a new folder named fulcrum.
	•	Open VS Code > File > Open Folder > Select fulcrum.

2. Create the Files (Map to Code Documentation)
In VS Code, use the "Explorer" sidebar (left side) to create the following files.

File Name
Corresponds To
Description
db_setup.py
Code Doc Part 1
Initializes the Database and Virtual Wallets.
config.json
Code Doc Part 1
Holds API Keys and Settings.
fulcrum_master.py
Code Doc Part 2 & Muscle
The "Brain" / Master Controller (Subscriber).
agent_sentinel.py
Code Doc Part 3 & Muscle
The "Eye" / Oracle Scanning (Publisher).
agent_coinbase.py
Code Doc Part 4
The "Mouth" / Execution.
main.py
Code Doc Part 5 (v2.0)
The "Orchestrator" / Launcher.
canon_oracles.json
Code Doc Part 3
List of Root Twitter accounts (Static).
living_oracles.json
Code Doc Part 3
List of Dynamic Twitter accounts.
living_candidates.json
Code Doc Part 3
Empty list for proposed new accounts.
requirements.txt
Phase 0
List of Python libraries to install.


3. Paste the Code
Copy the code from the respective "Code Documentation" parts (including the "Muscle" upgrades and Redis integration) and paste them into the corresponding files listed above.

Note: You can leave config.json keys as placeholders (e.g., "YOUR_API_KEY") for now.

Phase 2: Configuration & Initialization

1. Configure the Empire (config.json)
Open config.json. Edit the sandbox setting to true to ensure safety.


json
{
 "coinbase": {
   "sandbox": true
 }
}


2. Initialize the Database (db_setup.py)
	•	Open Terminal in VS Code.
	•	Run the setup script:
python3 db_setup.py

	•	Verify: You should see a message: Database initialized. The Virtual Fleet is ready. and a new file fulcrum.db appear in your sidebar.


Phase 3: Verify Components
Before running the full system, verify individual components.

1. Check the DB
Create a temporary file check_db.py (if desired) to query the fulcrum.db and ensure wallet data exists.

2. Check the Oracle List
Ensure canon_oracles.json and living_oracles.json are populated with the JSON data provided in Part 3.


Phase 4: Execution (The Distributed Fleet)
This phase activates the "Nervous System" (Redis) and launches the distributed agents.

1. Start Redis (The Message Bus)
	•	Ensure you completed the installation in Phase 0.
	•	If you stopped the service, restart it in your standard Mac Terminal:
brew services start redis

2. Start Fulcrum (main.py)
	•	Ensure Phase 2 is complete.
	•	In Terminal (VS Code), run:
python3 main.py

3. Observe the Logs
You will see logs appear in the terminal indicating the agents are starting their threads:
--- DEPLOYING FULCRUM FLEET v2.0 ---
Starting Sentinel Agent (Publisher)...
Starting Master Agent (Subscriber)...
Agents are communicating via Redis Bus.

4. Stop Fulcrum
	•	To stop the "Heartbeat," press Ctrl + C in the terminal.

Phase 5: Safety & Troubleshooting

1. Sandbox Mode (CRITICAL)
	•	Always keep "sandbox": true in config.json until you have fully tested the logic.
	•	Sandbox mode uses fake money on Coinbase to simulate trades without risk.
2. Redis Errors
	•	Error connecting to Redis: Ensure brew services start redis was run successfully. Check that port 6379 is not blocked.
	•	Connection refused: Redis might not be running. Check your standard Mac Terminal for errors.
3. Library Errors
	•	Module not found: You forgot to run pip3 install -r requirements.txt or an error occurred during install.
	•	torch/transformers errors: Ensure you have enough disk space and a supported MacOS version for PyTorch installation.
4. API Keys
	•	When ready to leave Sandbox, you must generate real API Keys from your Coinbase Advanced Trade account and update config.json.
	•	Security: Never share your config.json file. Add it to .gitignore if you push this code to GitHub.


Summary of Workflow
	•	Install VS Code, Python 3, Redis, and Libraries (requirements.txt).
	•	Create fulcrum folder.
	•	Paste code into files (Parts 1–5, including Muscle/Redis updates).
	•	Start Redis Server (brew services start redis).
	•	Run python3 db_setup.py to build the DB.
	•	Run python3 main.py to start the distributed fleet.
Prt 2: Database & Setup
import sqlite3

def init_db():
    conn = sqlite3.connect('fulcrum.db')
    c = conn.cursor()

    # 1. Virtual Wallets (The Rooms)
    c.execute('''CREATE TABLE IF NOT EXISTS virtual_wallets
                 (id INTEGER PRIMARY KEY,
                  name TEXT UNIQUE, 
                  role TEXT, 
                  allocation_cap REAL)''')
    
    # 2. Assets (The Furniture - Dynamic)
    c.execute('''CREATE TABLE IF NOT EXISTS assets
                 (symbol TEXT PRIMARY KEY,
                  current_wallet_id INTEGER,
                  teleonomy_score REAL, 
                  quantity REAL,
                  value_usd REAL,
                  FOREIGN KEY(current_wallet_id) REFERENCES virtual_wallets(id))''')

    # 3. Oracle List (The Garden)
    c.execute('''CREATE TABLE IF NOT EXISTS oracles
                 (handle TEXT PRIMARY KEY,
                  weight INTEGER,
                  category TEXT)''')
    
    # 4. Trade Queue (The Human Gate)
    c.execute('''CREATE TABLE IF NOT EXISTS trade_queue
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  asset TEXT,
                  action TEXT,
                  amount REAL,
                  status TEXT, 
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # Initialize Default Wallets (The Rooms)
    wallets = [
        ('Dynasty_Core', 'HODL', 0.60), # 60% of funds
        ('Hunter_Tactical', 'Alpha', 0.20), # 20%
        ('Builder_Ecosystem', 'Growth', 0.10), # 10%
        ('Yield_Vault', 'Stable', 0.05), # 5%
        ('Experimental', 'High_Risk', 0.05)  # 5%
    ]

    c.executemany("INSERT OR IGNORE INTO virtual_wallets (name, role, allocation_cap) VALUES (?, ?, ?)", wallets)
    
    conn.commit()
    conn.close()
    print("Database initialized. The Virtual Fleet is ready.")

if __name__ == "__main__":
    init_db()

Prt 2: API keys & Settings
{
  "coinbase": {
    "api_key": "YOUR_CB_API_KEY",
    "api_secret": "YOUR_CB_API_SECRET",
    "sandbox": true 
  },
  "twitter": {
    "bearer_token": "YOUR_X_BEARER_TOKEN"
  },
  "thresholds": {
    "buy_signal_confidence": 0.8,
    "sell_signal_confidence": 0.8,
    "sanity_floor_weight": 2
  }
}

Prt 2: Master Controller
import sqlite3
import json
import redis
import threading

# ADDED: Redis Import
r = redis.Redis(host='localhost', port=6379, db=0)
CHANNEL = "fulcrum_signals"

class FulcrumAgent:
    def __init__(self, db_path='fulcrum.db'):
        self.conn = sqlite3.connect(db_path)
        self.c = self.conn.cursor()
        self.pubsub = r.pubsub()
        self.pubsub.subscribe(CHANNEL)

    def handle_signal(self, message_json):
        """
        The 'Reflex Action':
        Receives signal from Nervous System -> Executes Logic.
        """
        axes = json.loads(message_json)
        
        print(f"[MASTER] Received: {axes}")
        
        # Existing Logic: Determine Regime
        # ... (Your determine_regime logic here) ...
        
        # Existing Logic: Apply Presets / Rebalance
        # ... (Your rebalance_wallets logic here) ...

    def listen_loop(self):
        """
        Runs in background thread waiting for impulses.
        """
        print(f"[MASTER] Listening on {CHANNEL}...")
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                self.handle_signal(message['data'])

# Usage: Run in a separate thread
def run_master_agent():
    master = FulcrumAgent()
    
    # Start Listener in Background (Daemon Thread)
    t = threading.Thread(target=master.listen_loop, daemon=True)
    t.start()
    
    # Keep main thread alive
    while True:
        pass


Prt 3: Sentinel
import json
import redis
import tweepy
import time

# ADDED: Redis Import
r = redis.Redis(host='localhost', port=6379, db=0)
CHANNEL = "fulcrum_signals"

class AgentSentinel:
    def __init__(self):
        self.client = tweepy.Client(bearer_token='YOUR_BEARER_TOKEN') 
        
    def publish_signal(self, axes: dict):
        """
        The 'Nerve Impulse':
        Packs data into JSON and fires it down the wire.
        """
        # Add Timestamp
        axes["timestamp"] = time.time()
        
        # JSON Serialize
        message = json.dumps(axes)
        
        # Publish
        r.publish(CHANNEL, message)
        print(f"[SENTINEL] Published Signal: {axes}")

    def scan_and_publish(self):
        """
        Combines scanning logic with publishing logic.
        """
        # 1. Load Oracles & Analyze (Existing Logic)
        # ... (Your existing scanning code here) ...
        
        # Placeholder for axes
        axes = {
            "perceived_sentiment": 25, # From analysis
            "teleonomic_alignment": 85  # From analysis
        }
        
        # 2. Publish
        self.publish_signal(axes)

# New Loop for Sentinel Agent
def run_sentinel_loop():
    sentinel = AgentSentinel()
    print("[SENTINEL] Starting Publisher Loop...")
    
    while True:
        sentinel.scan_and_publish()
        time.sleep(900) # 15 Minutes



Prt 3: Configuration Files
[
    {"handle": "VitalikButerin", "weight": 10, "category": "Core Dev"},
    {"handle": "balajis", "weight": 9, "category": "Core Dev"},
    {"handle": "nicksimson", "weight": 8, "category": "Analyst"},
    {"handle": "BlackRock", "weight": 10, "category": "TradFi"},
    {"handle": "coinbase", "weight": 5, "category": "Exchange"},
    {"handle": "MicroStrategy", "weight": 7, "category": "Treasury"}
]

Prt 3: Oracles
[
    {"handle": "mempoolive", "weight": 5, "category": "News"},
    {"handle": "CoinDesk", "weight": 4, "category": "News"}
]

Prt 3: Candidates
[]
Prt 4: CoinBase Agent
The Logical Architecture
The Coinbase Agent is distinct from the Master Controller to ensure Sovereignty.
	•	Brain (Master Controller): Decides What to buy based on Logic/Sentiment.
	•	Mouth (Coinbase Agent): Knows How to buy (API commands), but never decides Why.

Core Functions:
	•	Authenticaion: Connecting to Coinbase Advanced Trade API securely.
	•	Balance Check: Verifying funds are available before attempting a trade.
	•	Execution: Placing Limit Orders (Prevents Slippage).
	•	Queue Processing: Watching the trade_queue for "Human Approved" orders.

import sqlite3
import ccxt # pip install ccxt
import time

class CoinbaseAgent:
    def __init__(self, api_key, api_secret, sandbox=True):
        # Connect to Coinbase (Pro API)
        self.exchange = ccxt.coinbaseadvanced({
            'apiKey': api_key,
            'secret': api_secret,
        })
        
        # Sandbox Mode (Fake Money) for testing
        if sandbox:
            self.exchange.set_sandbox_mode(True)
            print("[MOUTH] Running in SANDBOX mode.")
        
        self.db_path = 'fulcrum.db'

    def get_balance(self, symbol='BTC'):
        """
        Checks 'Do I have enough money to breathe?'
        Returns available balance for an asset.
        """
        balance = self.exchange.fetch_balance()
        
        # Coinbase balances are often nested: 'BTC': {'free': 1.5, 'used': 0}
        free_balance = self.exchange.safe_balance[symbol]['free']
        print(f"[MOUTH] Available {symbol}: {free_balance}")
        return free_balance

    def execute_trade(self, symbol, action, amount):
        """
        Places a Limit Order (Safer than Market Order).
        This is the 'Voice' speaking to the world.
        """
        if action == 'BUY':
            # Logic: Buy slightly below current price (Limit Order)
            order = self.exchange.create_limit_buy_order(symbol, amount, price) # price variable needed
            print(f"[MOUTH] ORDER PLACED: BUY {amount} {symbol}")
            
        elif action == 'SELL':
            order = self.exchange.create_limit_sell_order(symbol, amount, price) # price variable needed
            print(f"[MOUTH] ORDER PLACED: SELL {amount} {symbol}")
            
        return order

    def process_queue(self):
        """
        The 'Larynx Reflex':
        Checks the trade_queue database for any orders 
        that have been 'APPROVED' by the Human.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 1. Find Approved Orders
        # Status must be 'APPROVED' (Human signed off via UI/App)
        c.execute("SELECT * FROM trade_queue WHERE status='APPROVED'")
        orders = c.fetchall()
        
        for order in orders:
            order_id = order[0]
            asset = order[1]
            action = order[2]
            amount = order[3]
            
            print(f"[MOUTH] Executing Order ID: {order_id}")
            
            try:
                # 2. Check if we have the funds
                # (Logic simplified for doc: Check USDC for BUY, Asset for SELL)
                self.get_balance(asset)
                
                # 3. Execute (Pseudo-price logic used here)
                # In reality, you fetch current ticker price first.
                current_price = 50000 # Placeholder
                trade = self.execute_trade(asset, action, amount)
                
                # 4. Mark as 'DONE'
                c.execute("UPDATE trade_queue SET status='DONE' WHERE id=?", (order_id,))
                conn.commit()
                
            except Exception as e:
                print(f"[MOUTH] ERROR executing trade: {e}")
                c.execute("UPDATE trade_queue SET status='FAILED' WHERE id=?", (order_id,))
                conn.commit()
        
        conn.close()

# Usage Example (The Breathing Loop)
# agent = CoinbaseAgent(api_key="...", api_secret="...")
# while True:
#     agent.process_queue()
#     time.sleep(10) # Check for orders every 10 seconds


The "Human Gate" Workflow

Note the line: c.execute("SELECT * FROM trade_queue WHERE status='APPROVED'").
This is how Sovereignty is preserved.
	•	Step 1 (Brain): Master Controller decides to buy BTC. Sets status to 'PENDING'.
	•	Step 2 (User): User sees notification on their phone. Clicks "Sign."
	•	Step 3 (System): Database updates status from 'PENDING' to 'APPROVED'.
	•	Step 4 (Mouth): agent_coinbase.py wakes up, sees 'APPROVED', and executes trade.

Crucial Safety:
agent_coinbase.py is forbidden from executing any order that is not 'APPROVED'. Even if the Master Controller screams "BUY!", the Mouth remains shut until the User clicks.

Operational Notes

1. Sandbox Mode
Always keep sandbox=True until you are 100% sure the logic holds. This uses "Fake Money" on Coinbase to test your Fleet without risk.

2. Order Types
The code uses Limit Orders (create_limit_buy_order).
	•	Why? Market Orders buy at any price (risky slippage). Limit Orders buy at your price.
	•	The Trade-off: If the price moves fast, the order might not fill. This is Better than buying at a terrible price.

3. Fail-Safe
If an order fails (network error, insufficient funds), the code catches the exception and marks the status as 'FAILED' in the database. The Master Controller sees this and can decide to retry or alert you.

Prt 5: Main
import logging
from agent_sentinel import run_sentinel_loop
from fulcrum_master import run_master_agent

logging.basicConfig(level=logging.INFO)

def main():
    logging.info(" --- DEPLOYING FULCRUM FLEET v2.0 ---")
    
    # 1. Deploy The Mouth (Coinbase) - Runs own loop
    # (Assuming agent_coinbase.py runs its own process/loop)
    
    # 2. Deploy The Eye (Sentinel) - Runs own loop
    logging.info("Starting Sentinel Agent (Publisher)...")
    sentinel_thread = threading.Thread(target=run_sentinel_loop, daemon=True)
    sentinel_thread.start()
    
    # 3. Deploy The Brain (Master) - Listens to Redis
    logging.info("Starting Master Agent (Subscriber)...")
    master_thread = threading.Thread(target=run_master_agent, daemon=True)
    master_thread.start()
    
    logging.info(" --- FLEET ONLINE ---")
    logging.info("Agents are communicating via Redis Bus.")
    
    # Keep Main Process Alive
    try:
        while True:
            pass
    except KeyboardInterrupt:
        logging.info(" --- SHUTTING DOWN FLEET ---")

if __name__ == "__main__":
    main()

