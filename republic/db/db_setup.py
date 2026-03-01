"""
Fulcrum Database Setup
Initializes the Virtual Fleet database structure.

Based on: Fulcrum MacBook Agent Implementation Guide
"""

import sqlite3
import os


def init_db(db_path=None):
    """
    Initializes the Fulcrum database with all required tables.
    """
    if db_path is None:
        # Determine strict path to republic/republic.db
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # republic/
        if os.path.split(BASE_DIR)[-1] == 'db': # Handle if running inside republic/db/
             BASE_DIR = os.path.dirname(BASE_DIR)
             
        # If running from project root (LEF Ai/), we need to go into republic/
        current_cwd = os.getcwd()
        if os.path.exists(os.path.join(current_cwd, 'republic')):
             db_path = os.path.join(current_cwd, 'republic', 'republic.db')
        else:
             # Fallback
             db_path = 'republic.db'

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # ENABLE WAL MODE (Concurrency Fix)
    try:
        c.execute("PRAGMA journal_mode=WAL;")
        c.execute("PRAGMA synchronous=NORMAL;") # Faster writes, safe for WAL
        print("[DB] ⚡ WAL Mode Enabled (Non-Blocking Reads).")
    except Exception as e:
        print(f"[DB] ⚠️ Could not set WAL mode: {e}")

    # 1. Virtual Wallets (The Rooms)
    # -- Phase 16: Table removed (never used in production). Preserved as comment for reference.
    # c.execute('''CREATE TABLE IF NOT EXISTS virtual_wallets
    #              (id INTEGER PRIMARY KEY,
    #               name TEXT UNIQUE,
    #               role TEXT,
    #               allocation_cap REAL)''')
    
    # 2. Assets (Moved to updated definition below)

    # 3. Oracle List (The Garden)
    # -- Phase 16: Table removed (never used in production). Preserved as comment for reference.
    # c.execute('''CREATE TABLE IF NOT EXISTS oracles
    #              (handle TEXT PRIMARY KEY,
    #               weight INTEGER,
    #               category TEXT,
    #               is_canon BOOLEAN DEFAULT 0,
    #               added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 4. Trade Queue (The Human Gate)
    c.execute('''CREATE TABLE IF NOT EXISTS trade_queue
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  schema_version TEXT DEFAULT 'v1_spot',
                  asset TEXT,
                  action TEXT,
                  amount REAL,
                  price REAL,
                  status TEXT DEFAULT 'PENDING',
                  reason TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  approved_at TIMESTAMP,
                  executed_at TIMESTAMP)''')
    
    # 5. Signal History (For RDA and pattern analysis)
    c.execute('''CREATE TABLE IF NOT EXISTS signal_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  perceived_sentiment REAL,
                  teleonomic_alignment REAL,
                  source TEXT,
                  processed BOOLEAN DEFAULT 0)''')
    
    # 6. Regime Detection (Market state tracking)
    c.execute('''CREATE TABLE IF NOT EXISTS regime_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  regime TEXT,
                  confidence REAL,
                  signal_source TEXT)''')
    
    # 7. Stablecoin Buckets (Phase 1: Profit routing)
    c.execute('''CREATE TABLE IF NOT EXISTS stablecoin_buckets
                 (id INTEGER PRIMARY KEY,
                  bucket_type TEXT UNIQUE,
                  stablecoin TEXT,
                  purpose TEXT,
                  balance REAL DEFAULT 0,
                  interest_rate REAL DEFAULT 0,
                  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 8. Profit Allocation (Tracks where profits go)
    c.execute('''CREATE TABLE IF NOT EXISTS profit_allocation
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  trade_id INTEGER,
                  profit_amount REAL,
                  bucket_type TEXT,
                  allocated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(trade_id) REFERENCES trade_queue(id))''')
    
    # 9. Migration Log (Phase 3: Audit trail for coin migrations)
    c.execute('''CREATE TABLE IF NOT EXISTS migration_log
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  symbol TEXT,
                  from_wallet TEXT,
                  to_wallet TEXT,
                  old_score REAL,
                  new_score REAL,
                  reason TEXT,
                  migrated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 10. Trade History (For IRS tax calculations and analysis)
    c.execute('''CREATE TABLE IF NOT EXISTS trade_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date DATE,
                  wallet TEXT,
                  symbol TEXT,
                  action TEXT,
                  amount REAL,
                  price REAL,
                  revenue REAL,
                  cost_basis REAL,
                  profit REAL,
                  reason TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                  
    # 11. SNW Proposals (The Voting Booth)
    c.execute('''CREATE TABLE IF NOT EXISTS snw_proposals
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  project_name TEXT,
                  description TEXT,
                  amount REAL,
                  status TEXT,
                  votes_for INTEGER DEFAULT 0,
                  votes_against INTEGER DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 12. LEF Directives (The Higher Mind)
    c.execute('''CREATE TABLE IF NOT EXISTS lef_directives
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  directive_type TEXT,
                  payload TEXT,
                  status TEXT DEFAULT 'PENDING',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                  
    # 12b. LEF Monologue (The Stream of Consciousness)
    c.execute('''CREATE TABLE IF NOT EXISTS lef_monologue
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  thought TEXT,
                  mood TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 12f. Agents (The Org Chart Status) - For Health Monitoring
    c.execute('''CREATE TABLE IF NOT EXISTS agents (
                 name TEXT PRIMARY KEY,
                 status TEXT,
                 last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 current_task TEXT,
                 level INTEGER DEFAULT 1,
                 xp INTEGER DEFAULT 0,
                 department TEXT
                 )''')

    # 12c. LEF Wisdom (The Long-Term Memory)
    c.execute('''CREATE TABLE IF NOT EXISTS lef_wisdom
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  insight TEXT,
                  context TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                  
    # 12d. Research Topics (Curriculum) - Agent Scholar
    c.execute("""
        CREATE TABLE IF NOT EXISTS research_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            assigned_by TEXT,
            status TEXT DEFAULT 'PENDING',  -- PENDING, STUDYING, MASTERED
            knowledge_artifact_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 12e. Knowledge Stream (Inbox/RSS) - Agent Scholar
    c.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_stream (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            source TEXT,
            title TEXT,
            summary TEXT,
            sentiment_score REAL DEFAULT 0.0
        )
    """)

    # 2. Assets (The Furniture - Dynamic) - UPDATED with avg_buy_price
    # Note: IF NOT EXISTS won't update existing schema if table exists. 
    # But since we are rebuilding Docker with internal DB, it starts fresh.
    c.execute('''CREATE TABLE IF NOT EXISTS assets
                 (symbol TEXT PRIMARY KEY,
                  current_wallet_id INTEGER,
                  teleonomy_score REAL, 
                  quantity REAL,
                  value_usd REAL,
                  avg_buy_price REAL DEFAULT 0,
                  peak_price REAL DEFAULT 0.0, -- Wealth 3.0 Trailing Stop
                  harvest_level INTEGER DEFAULT 0, -- Wealth 3.0 Ladder Sells
                  strategy_type TEXT DEFAULT 'DYNASTY', -- 'DYNASTY' or 'SCALP'
                  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(current_wallet_id) REFERENCES virtual_wallets(id))''')

    # Initialize Default Wallets (The Rooms)
    wallets = [
        ('Dynasty_Core', 'HODL', 0.60),  # 60% of funds
        ('Hunter_Tactical', 'Alpha', 0.20),  # 20%
        ('Builder_Ecosystem', 'Growth', 0.10),  # 10%
        ('Yield_Vault', 'Stable', 0.05),  # 5%
        ('Experimental', 'High_Risk', 0.05)  # 5%
    ]

    c.executemany(
        "INSERT OR IGNORE INTO virtual_wallets (name, role, allocation_cap) VALUES (?, ?, ?)", 
        wallets
    )
    
    # Initialize Stablecoin Buckets (Phase 1)
    buckets = [
        ('IRS_USDT', 'USDT', 'Tax Payments - IRS Compliance', 0.0, 0.0),
        ('SNW_LLC_USDC', 'USDC', 'SNW/LLC Operations - Interest Bearing', 0.0, 0.04),  # 4% APY default
        ('INJECTION_DAI', 'DAI', 'Capital Injections - DeFi Native', 0.0, 0.03)  # 3% APY default
    ]
    
    c.executemany(
        "INSERT OR IGNORE INTO stablecoin_buckets (bucket_type, stablecoin, purpose, balance, interest_rate) VALUES (?, ?, ?, ?, ?)",
        buckets
    )
    
    # 13. Macro History (The World Context) - Agent SNW
    # -- Phase 16: Table removed (never used in production). Preserved as comment for reference.
    # c.execute('''CREATE TABLE IF NOT EXISTS macro_history
    #              (id INTEGER PRIMARY KEY AUTOINCREMENT,
    #               timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    #               fed_rate REAL,
    #               cpi_inflation REAL,
    #               fear_greed_index INTEGER,
    #               liquidity_status TEXT,
    #               notes TEXT)''')
                  
    # 14. Agent Logs (The Action History) - For Governance UI
    c.execute('''CREATE TABLE IF NOT EXISTS agent_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  source TEXT, -- The Agent Name (e.g. AgentCoinbase)
                  level TEXT, -- INFO, WARNING, ERROR
                  message TEXT)''')
                  
    # 15. The Genesis Log (System Memory of Changes)
    c.execute('''CREATE TABLE IF NOT EXISTS genesis_log
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  event_type TEXT, -- RESTART, PATCH, CONFIG_CHANGE
                  description TEXT,
                  changed_files TEXT)''')

    # 16. Agent Health Ledger (The Medical Record)
    c.execute('''CREATE TABLE IF NOT EXISTS agent_health_ledger
                 (name TEXT PRIMARY KEY,
                  crash_count INTEGER DEFAULT 0,
                  health_score REAL DEFAULT 100.0,
                  last_healed_at TIMESTAMP,
                  chronic_issue_detected BOOLEAN DEFAULT 0)''')

    # 17. Profit Ledger (The Scoreboard)
    c.execute('''CREATE TABLE IF NOT EXISTS profit_ledger
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  strategy_name TEXT, -- e.g. GLADIATOR_SCOUT
                  profit_pnl REAL DEFAULT 0.0,
                  win_rate REAL DEFAULT 0.0,
                  total_trades INTEGER DEFAULT 0,
                  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 17b. Realized PnL (The Bank Statement) - Added Phase 9 fix
    c.execute('''CREATE TABLE IF NOT EXISTS realized_pnl
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  trade_id INTEGER,
                  asset TEXT,
                  profit_amount REAL,
                  roi_pct REAL,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(trade_id) REFERENCES trade_queue(id))''')
    
    # 18. Execution Logs (Proprioception Trigger)
    c.execute('''CREATE TABLE IF NOT EXISTS execution_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  trade_id INTEGER,
                  asset TEXT,
                  side TEXT,
                  ordered_price REAL,
                  executed_price REAL,
                  slippage_pct REAL,
                  fee_usd REAL,
                  latency_ms INTEGER,
                  raw_response TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(trade_id) REFERENCES trade_queue(id))''')

    # 19. Memory Experiences (Episodic Learning) - Wealth 3.0
    c.execute("""
        CREATE TABLE IF NOT EXISTS memory_experiences (
            id INTEGER PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            scenario_name TEXT,
            market_condition TEXT,
            action_taken TEXT,
            outcome_pnl_pct REAL,
            outcome_desc TEXT
        )
    """)

    # 20. Library Catalog (The Bookshelf) - Phase 8
    # -- Phase 16: Table removed (never used in production). Preserved as comment for reference.
    # c.execute("""
    #     CREATE TABLE IF NOT EXISTS library_catalog (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         title TEXT,
    #         source_url TEXT,
    #         author TEXT,
    #         category TEXT, -- Economics, History, Strategy, Civics
    #         summary TEXT,
    #         status TEXT DEFAULT 'UNREAD',
    #         ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    #     )
    # """)

    # 21. Mental Models (The Distilled Intellect) - Phase 8
    c.execute("""
        CREATE TABLE IF NOT EXISTS mental_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE, -- e.g. "Soros Reflexivity"
            description TEXT,
            implication_bullish TEXT,
            implication_bearish TEXT,
            source_id INTEGER,
            confidence_score REAL DEFAULT 0.5,
            last_applied TIMESTAMP,
            FOREIGN KEY(source_id) REFERENCES library_catalog(id)
        )
    """)

    # 22. Apoptosis Log (The Death Certificate) - Phase 9
    c.execute("""
        CREATE TABLE IF NOT EXISTS apoptosis_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            trigger_reason TEXT, -- e.g. "NAV Drop > 20%"
            nav_start REAL,
            nav_end REAL,
            drawdown_pct REAL,
            actions_taken TEXT
        )
    """)

    # 23. System State (The Nervous System) - Phase 6 Sabbath Protocol
    c.execute("""
        CREATE TABLE IF NOT EXISTS system_state (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 24. Intent Queue (Motor Cortex - Phase 17) - LEF's pending actions
    c.execute("""
        CREATE TABLE IF NOT EXISTS intent_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intent_type TEXT NOT NULL,
            content TEXT,
            target_agent TEXT,
            status TEXT DEFAULT 'PENDING',  -- PENDING, DISPATCHED, COMPLETED, FAILED
            priority INTEGER DEFAULT 5,
            result TEXT,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            dispatched_at TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)

    # 25. Feedback Log (Motor Cortex - Phase 17) - Agent responses to LEF
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedback_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            intent_id INTEGER,
            feedback_type TEXT,  -- COMPLETE, DISCOVERY, STATUS, ERROR, INSIGHT
            message TEXT,
            data TEXT,  -- JSON data
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(intent_id) REFERENCES intent_queue(id)
        )
    """)

    # 26. Agent Experiences (Pain Protocol - Phase 20) - System stress tracking
    c.execute("""
        CREATE TABLE IF NOT EXISTS agent_experiences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,  -- e.g. 'system_stress'
            value TEXT,
            source TEXT,  -- Agent that recorded the experience
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 27. Inbox (Bridge Communication) - User-Agent messaging
    c.execute("""
        CREATE TABLE IF NOT EXISTS inbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,  -- USER, AGENT_NAME, SYSTEM
            recipient TEXT,
            subject TEXT,
            message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read INTEGER DEFAULT 0
        )
    """)

    # 28. Constitutional Amendments (Phase 21) - Amendment voting system
    c.execute("""
        CREATE TABLE IF NOT EXISTS constitutional_amendments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id TEXT,
            amendment_text TEXT,
            rationale TEXT,
            proposed_by TEXT,
            status TEXT DEFAULT 'PROPOSED',
            votes_for INTEGER DEFAULT 0,
            votes_against INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        )
    """)

    # 29. Agent Handoffs (Phase 22) - Context preservation between agents
    c.execute("""
        CREATE TABLE IF NOT EXISTS agent_handoffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_agent TEXT NOT NULL,
            target_agent TEXT,  -- NULL = broadcast to all
            context TEXT NOT NULL,  -- JSON blob
            intent_type TEXT,
            priority INTEGER DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            consumed_at TIMESTAMP,  -- NULL until read
            ttl_days INTEGER DEFAULT 7
        )
    """)
    # Index for efficient handoff queries
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_handoffs_target 
        ON agent_handoffs(target_agent, consumed_at)
    """)

    # 30. Compressed Wisdom (Phase 22) - Semantic compression of episodic memories
    c.execute("""
        CREATE TABLE IF NOT EXISTS compressed_wisdom (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wisdom_type TEXT NOT NULL,  -- 'FAILURE_LESSON', 'MARKET_PATTERN', 'BEHAVIOR_INSIGHT'
            summary TEXT NOT NULL,      -- The compressed insight
            source_type TEXT,           -- 'book_of_scars', 'memory_experiences', etc.
            source_ids TEXT,            -- Comma-separated source record IDs
            confidence REAL DEFAULT 0.5,
            times_validated INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_validated TIMESTAMP
        )
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_wisdom_type 
        ON compressed_wisdom(wisdom_type)
    """)

    # 31. Action Training Log (Phase 22) - LAM-style training data
    c.execute("""
        CREATE TABLE IF NOT EXISTS action_training_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            agent_name TEXT NOT NULL,
            intent TEXT NOT NULL,
            context TEXT,
            action_type TEXT,
            action_details TEXT,
            outcome TEXT DEFAULT 'PENDING',
            outcome_details TEXT,
            reward_signal REAL DEFAULT 0,
            duration_ms INTEGER,
            metadata TEXT
        )
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_action_agent 
        ON action_training_log(agent_name)
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_action_outcome 
        ON action_training_log(outcome)
    """)

    # 32. Projects (Phase 22) - Multi-day goal tracking
    c.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            status TEXT DEFAULT 'ACTIVE',
            priority INTEGER DEFAULT 50,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            target_date TIMESTAMP,
            completed_at TIMESTAMP,
            progress_pct REAL DEFAULT 0,
            owner_agent TEXT,
            metadata TEXT
        )
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_project_status 
        ON projects(status)
    """)

    # 33. Project Tasks (Phase 22) - Task slicing for projects
    c.execute("""
        CREATE TABLE IF NOT EXISTS project_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            assigned_agent TEXT,
            notes TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_task_project 
        ON project_tasks(project_id)
    """)

    # 34. Consciousness Feed (The Nervous System) - Phase 1 Active Tasks
    #     Phase 46+: Added signal_weight and signal_vector to match PostgreSQL schema
    c.execute("""
        CREATE TABLE IF NOT EXISTS consciousness_feed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'reflection',
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            consumed INTEGER DEFAULT 0,
            signal_weight REAL DEFAULT 0.5,
            signal_vector TEXT DEFAULT '{}'
        )
    """)

    # Phase 5.5: Indexes for consciousness_feed — reduces lock contention on queries
    c.execute("CREATE INDEX IF NOT EXISTS idx_cf_consumed ON consciousness_feed(consumed)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cf_timestamp ON consciousness_feed(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cf_agent ON consciousness_feed(agent_name)")

    # 35. Republic Awareness (Body One output — Phase 9 Three-Body Reflection)
    c.execute("""
        CREATE TABLE IF NOT EXISTS republic_awareness (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            active_patterns TEXT NOT NULL DEFAULT '[]',
            scar_domain_activity TEXT NOT NULL DEFAULT '{}',
            agent_health TEXT NOT NULL DEFAULT '{}',
            republic_health_signals TEXT NOT NULL DEFAULT '{}',
            pattern_count INTEGER DEFAULT 0,
            cycle_number INTEGER DEFAULT 0
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_ra_timestamp ON republic_awareness(timestamp)")

    # 36. Sovereign Reflection (Body Two output — Phase 9 Three-Body Reflection)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sovereign_reflection (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            pattern_id TEXT NOT NULL,
            pattern_description TEXT NOT NULL,
            gravity_profile TEXT NOT NULL DEFAULT '{}',
            gravity_level TEXT DEFAULT 'baseline',
            scar_resonance_count INTEGER DEFAULT 0,
            impression TEXT,
            status TEXT DEFAULT 'active',
            first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
            surfaced_to_sabbath INTEGER DEFAULT 0,
            resolution TEXT
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_sr_status ON sovereign_reflection(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sr_gravity ON sovereign_reflection(gravity_level)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sr_timestamp ON sovereign_reflection(timestamp)")

    # 37. Sabbath Log (Body Three audit trail — Phase 9 Three-Body Reflection)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sabbath_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            trigger_pattern_id TEXT NOT NULL,
            gravity_profile TEXT NOT NULL DEFAULT '{}',
            gravity_level TEXT NOT NULL,
            duration_seconds REAL,
            logical_assessment TEXT,
            resonance_assessment TEXT,
            outcome TEXT NOT NULL,
            intention TEXT,
            proposal_id TEXT,
            notes TEXT
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_sabbath_timestamp ON sabbath_log(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sabbath_outcome ON sabbath_log(outcome)")

    # 38. Reverb Log (Phase 10 — tracks effects of enacted evolution changes)
    c.execute("""
        CREATE TABLE IF NOT EXISTS reverb_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            proposal_id TEXT NOT NULL,
            domain TEXT,
            change_description TEXT,
            reverb_assessment TEXT,
            observations TEXT DEFAULT '[]',
            hours_post_enactment REAL DEFAULT 0
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_reverb_proposal ON reverb_log(proposal_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_reverb_timestamp ON reverb_log(timestamp)")

    # Table 81: execution_feedback (Phase 19.2a — execution quality tracking)
    c.execute("""
        CREATE TABLE IF NOT EXISTS execution_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_queue_id INTEGER,
            asset TEXT,
            intended_price REAL,
            actual_price REAL,
            slippage_pct REAL,
            intended_qty REAL,
            actual_qty REAL,
            fill_rate REAL,
            fees_usd REAL,
            execution_time_ms INTEGER,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_exec_feedback_asset ON execution_feedback(asset)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_exec_feedback_created ON execution_feedback(created_at)")

    # Phase 21.1b: Composite index for consciousness_feed cleanup queries
    c.execute("CREATE INDEX IF NOT EXISTS idx_cf_cleanup ON consciousness_feed(consumed, timestamp, category)")

    # Phase 51.1: Consciousness Archive — long-term store for rotated entries
    c.execute("""
        CREATE TABLE IF NOT EXISTS consciousness_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_id INTEGER NOT NULL,
            agent_name TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'reflection',
            original_timestamp TEXT,
            signal_weight REAL DEFAULT 0.5,
            signal_vector TEXT DEFAULT '{}',
            archived_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_ca_agent ON consciousness_archive(agent_name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ca_category ON consciousness_archive(category)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ca_original_ts ON consciousness_archive(original_timestamp)")

    # Phase 21.1c: Indexes for agent_logs (high-volume table, needs fast queries)
    c.execute("CREATE INDEX IF NOT EXISTS idx_agent_logs_source ON agent_logs(source)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_agent_logs_level ON agent_logs(level)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_agent_logs_ts ON agent_logs(timestamp)")

    # Phase 21.1d: Training summary table (archive before purging action_training_log)
    c.execute("""
        CREATE TABLE IF NOT EXISTS training_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT,
            action_type TEXT,
            avg_reward REAL,
            total_count INTEGER,
            positive_count INTEGER,
            negative_count INTEGER,
            period_start TIMESTAMP,
            period_end TIMESTAMP,
            summarized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_training_summary_agent ON training_summary(agent_name)")

    conn.commit()
    conn.close()
    print("Database initialized. The Virtual Fleet is ready.")
    print(f"Database location: {os.path.abspath(db_path)}")

if __name__ == "__main__":
    init_db()
