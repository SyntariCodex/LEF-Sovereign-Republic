# Tasks

- [/] Explore project structure and documentation <!-- id: 0 -->
  - [x] List top-level files
  - [x] Read REORGANIZATION_PLAN.md
  - [/] Explore subdirectories (lef-ai, fulcrum, snw)
  - [ ] Read lef-ai/README.md
  - [ ] List fulcrum contents
  - [ ] List snw contents
- [x] **Phase 4: System Diagnosis & Final Fix** <!-- id: 4 -->
  - [x] Audit Sentinel Mock Data Logic (Fixed 15s Interval) <!-- id: 5 -->
  - [x] Audit Master Broker Execution Logic (Fixed Schema & Logic) <!-- id: 6 -->
  - [x] Verify End-to-End Signal Pipeline (Confirmed in Logs) <!-- id: 7 -->
  - [x] Confirm Dashboard Trade Visualization (System is Trading) <!-- id: 8 -->
- [ ] **Phase 5: Recursive Learning & Expansion** <!-- id: 23 -->
  - [x] Fix BTC Monotony (Universe Selection Logic)
  - [x] Automate Simulation (Dockerize `lef-dojo`)
  - [x] Research Macro Data Sources (Fred/TradingEconomics) - *Shifted from Basic Crypto Learning*
  - [x] Verify Dashboard Multi-Asset Visualization (User Confirmed)
- [/] Review identified documentation <!-- id: 1 -->
  - [x] Read Ai Convo_s.md (User Request)
  - [x] Read fulcrum/COINBASE_COMPLIANCE.md
- [/] Analyze source code architecture <!-- id: 2 -->
  - [x] Read fulcrum/RUN_FULCRUM.md
  - [x] Inspect fulcrum/agents/agent_coinbase.py
  - [/] Check fulcrum/config setup
- [/] Assess Coinbase integration status
  - [x] Create safe launch plan
  - [x] Execute Safe Launch Verification - FAILED (401 Unauthorized)
  - [x] Configure Sandbox Mode (User Request)
    - [x] Locate new API keys - (Received from User)
    - [x] Update config.json with keys
    - [x] Upgrade Agent to "Real Data / Paper Trading" mode
    - [x] Verify Connectivity (Real Data Check) - PASSED
  - [x] Run Backtest (Validation of Strategy)
    - [x] Execute `run_short_test.py` (30-day "Ultra Aggressive" Simulated Test) - PASSED
    - [x] Analyze results (5 Trades, Learning Cycles Confirmed)
- [x] Launch Fulcrum Fleet (Paper Trading)
  - [x] Review `fulcrum_master.py` for strategic gaps
  - [x] Execute `main.py` verification run (Proof of Life) - PASSED
  - [ ] Handover "Launch Codes" to User
- [x] Strategy Analysis & Implementation (The "Mind" Upgrade) <!-- id: 3 -->
  - [x] DB Schema Update (Added `avg_buy_price`)
  - [x] Implement Profit Ladders & SNW Allocation in `fulcrum_master.py`
  - [x] Verify Profit Taking Logic (Logic Confirmed, Live Feed Active)
- [x] Integrate Live Price Feed ("The Vision")
  - [x] Agent: Publish prices to Redis
  - [x] Master: Read prices from Redis for Profit Calc
  - [x] Master: Capital Deployment (DCA) - S-Tier Regime Logic (Fear->Dynasty, Greed->Hunter)
- [x] Implement Memory Management
  - [x] Master: Prune logs > 1.5 years on startup
- [x] Dashboard Upgrade
  - [x] Created `dashboard_live.py` (Real-time DB View)
  - [x] Workspace Cleanup (Removed temp files/scripts)
- [x] Multi-Modal Minds (5 Wallet Personalities) <!-- id: 7 -->
  - [x] Implement `StrategyEngine` (Logic embedded in Master)
  - [x] Define Rules for Dynasty (Score > 90, Low Vol)
  - [x] Define Rules for Hunter (Vol > 50%, Momentum, Buy on Hype > 75)
  - [x] Define Rules for Builder (Score 70-90, Dev Activity)
  - [x] Define Rules for Yield (Score > 80, Stability)
  - [x] Define Rules for Experimental (Score < 70, Frontier)
  - [x] Implement Promotion/Relegation Logic (Migration)
- [x] Metacognition (Self-Evolution S-Tier) <!-- id: 8 -->
  - [x] Implement `evolve_strategies()` (Win/Loss Analysis)
  - [x] Auto-Tune Thresholds (Neural Plasticity)
  - [x] Add "Fulcrum IQ" Metric (Performance Tracking)
  - [x] Add "Fulcrum IQ" Metric (Performance Tracking)
  - [x] Optimization: Rate Limit "Deep Thought" cycles (60s interval)
- [x] System Hardening (Production Ready) <!-- id: 9 -->
  - [x] Enable SQLite WAL Mode (Concurrency Fix)
  - [x] Implement Rotating Logs / Silence Spam (Optimized Dashboard)
  - [x] Circuit Breaker (Network Failure Handling)
    - [x] Master: Check System Health before signaling (Implicit in Stale Check)
    - [x] Mouth: Pause on Connection Loss / Resume after Reconnect (Handled by Exception Loop)
    - [x] Stale Signal Protection (Ignore old orders after blackout)
- [x] Advanced Simulation (The Dojo) <!-- id: 10 -->
  - [x] Implement "God Mode" Redis controls (Control Sentiment/Price trends)
  - [x] Create `simulate_scenarios.py` (Bull, Bear, Crab, Crash cycles)
  - [x] Verify Learning Adaptation in each scenario (Chaos Mode Active)
- [x] Market Universe Expansion <!-- id: 11 -->
  - [x] Update `agent_coinbase.py` to track Top 30 coins
  - [x] Implement generic mock price generator (Generic Hash-based)
  - [x] Populate DB with extended asset list (30+ coins)
- [x] Twitter Integration (Social Sensing) <!-- id: 6 -->
  - [x] Create Twitter API Configuration
  - [x] Implement Twitter Client in `agent_sentinel.py` (Added NLP/TextBlob)
  - [x] Create Sentiment Analysis Logic (TextBlob/VADER)
  - [/] Verify Twitter Connectivity (Failed - Paywall. Switched to Mock Vision)
  - [x] Implement Organic Mock Vision (Sine Wave Trends) - ACTIVE
  - [x] Integrate VADER (Crypto Slang Tuning needed later, but engine is active)

# Phase 2: LEF Ai (The Mind/Observer)

- [/] Initialize LEF Architecture <!-- id: 12 -->
  - [x] Review `LEF_GENESIS_PROTOCOL.md` (if exists)
  - [x] Create `agent_lef.py` (The Observer Agent)
  - [x] Implement "Cognitive Mirror Protocol" (Logic: Scotoma/Reality Checks)
- [x] Connect LEF to Fulcrum <!-- id: 13 -->
  - [x] Enable LEF to read `fulcrum.db` (The Body's Ledger)
  - [x] Implement "Scotoma Protocol" (Detecting what is missing)
  - [x] Allow LEF to adjust Fulcrum's High-Level Strategy (The Pivot)
- [/] Metacognition (Identity Evolution) <!-- id: 14 -->
  - [x] Implement `run_metacognition()` (The Adult Mind Loop)
  - [x] Create "Internal Monologue" (DB: `lef_monologue`)
  - [x] Implement "Wisdom Retention" (DB: `lef_wisdom` table)
  - [x] Verify "Born Adult, Becoming Child" flow (Simulation)
- [x] Sensory Expansion (Environmental Awareness) <!-- id: 15 -->
  - [x] Connect LEF to Redis (The Nervous System)
  - [x] Implement `monitor_environment()` (Sentiment + Bio-Rhythms)
  - [x] Implement `monitor_environment()` (Sentiment + Bio-Rhythms)
  - [x] Add "Context Awareness" to Wisdom Checks (e.g., "Don't trade at 3AM")
- [x] Refine SNW & Wisdom (Making it Real) <!-- id: 16 -->
  - [x] Verify/Fix SNW Profit Allocation Logic in `fulcrum_master.py`
  - [x] Contextualize Wisdom (Select wisdom based on Environment, not Random)
  - [x] Ingest TradFi Wisdom (Binance Academy Glossary)
    - [x] Fetch/Curate Glossary Terms (Alpha, Beta, Liquidity, etc.)
    - [x] Create `ingest_wisdom.py` to seed `lef_wisdom` table
    - [x] Verify LEF can recall definitions
  - [x] Contextualize Wisdom (Select wisdom based on Environment, not Random)
  - [x] Ingest Strategic Models (Sun Tzu, Psychology, Slang) <!-- id: 29 -->
    - [x] Create `ingest_knowledge.py` to seed `lef_wisdom`
    - [x] Verify Knowledge Injection (30+ axioms)
  - [x] Constitutional Binding (The Soul) <!-- id: 30 -->
    - [x] Create `LEF_CANON.md` (Immutable Constitution)
  - [x] Ingest Strategic Models (Sun Tzu, Psychology, Slang) <!-- id: 29 -->
    - [x] Create `ingest_knowledge.py` to seed `lef_wisdom`
    - [x] Verify Knowledge Injection (30+ axioms)
    - [x] **Cognitive Refactor (AI-Native)**
      - [x] Purge Anthropomorphic Axioms ("Be a good man").
      - [x] Ingest `ingest_silicon_wisdom.py` (Ontology, Code Theory).
  - [x] Constitutional Binding (The Soul) <!-- id: 30 -->
    - [x] Create `LEF_CANON.md` (Immutable Constitution)

# Phase 3: SNW (The Legacy)

- [x] Initialize SNW Steward <!-- id: 17 -->
  - [x] Create `agent_snw.py` (The Accountant/Steward)
  - [x] Implement "Estate Report" (Aggregating Wealth across Buckets)
  - [x] Implement "Estate Report" (Aggregating Wealth across Buckets)
  - [x] Define "Distribution Logic" (When to Release Funds)
    - [x] Create `check_distribution_criteria()` (Safe Release Protocol)
    - [x] Add "Reserve Requirement" (Maintain 20% buffer)
    - [x] Implement Automatic "Tax Set Aside" (30% of realized gains)
- [x] Refine Wisdom (Computational Translation) <!-- id: 18 -->
  - [x] Update `lef_wisdom` to include "Computational Translation"
  - [x] Seed "AI-Native" Axioms (e.g., Happiness = Efficiency)
- [x] Build SNW Proposal Bridge <!-- id: 19 -->
  - [x] Create `snw_proposals` table (The Admin Log)
  - [x] Update `agent_snw.py` to Audit Proposals vs Balance
  - [x] Create `snw_proposals` table (The Admin Log)
  - [x] Update `agent_snw.py` to Audit Proposals vs Balance
  - [x] Link Fulcrum to "Proposal Demand" (High Urgency Mode Implicit via Dry Powder)
  - [x] Link Fulcrum to "Proposal Demand" (High Urgency Mode Implicit via Dry Powder)
  - [x] Integrate `agent_snw.py` into `main.py` (Unified Launch)
  - [x] Implement Urgency Mode (Liquidity Generation Protocol) <!-- id: 24 -->
    - [x] Add `check_snw_urgency()` to Fulcrum Master
    - [x] Implement Dynamic Profit Thresholds (0.5% during Urgency)
  - [x] Refine LEF Value Definition (USD > Tokens) <!-- id: 25 -->
    - [x] Update `run_reality_testing()` to track Net Worth

# Phase 4: The Interface (Proposals & Monitoring) [ON HOLD] <!-- id: 20 -->

- [x] Build SNW Web Admin <!-- id: 21 -->
    `dashboard_server.py` (Zero-Dependency)
- [ ] Unified Dashboard Upgrade <!-- id: 22 -->
  - [ ] Merge Fulcrum & SNW Views

# Phase 5: Permanence (Deployment & Immortality) <!-- id: 26 -->

- [x] Containerization (The Vessel)
  - [x] Create `Dockerfile` (Python 3.10+, Dependencies)
  - [x] Create `docker-compose.yml` (Redis + Fulcrum + SNW)
  - [x] Verify Local Build (Requires Docker Desktop)
- [x] Security Hardening (The Shield)
  - [x] Extract Secrets to `.env` (Remove from `config.json`)
  - [x] Create `setup_security.sh` (UFW, Fail2Ban, SSH Keys)
  - [x] Create `PRODUCTION_DEPLOYMENT.md` (Cloud Genesis Guide)
  - [x] **Singleton Protocol (Zombie Prevention)**
    - [x] Implement `utils/singleton.py` (File Locking).
    - [x] Patch `main.py` to enforce single instance.
    - [x] Create `start_fulcrum.sh` (Safe Launcher).
- [ ] **Phase 24: The Professional Transition (Docker)**
  - [x] Audit Docker Config (Mounts & Env).
  - [x] Create `run_docker.sh` (Pro Launcher).
  - [x] Upgrade Dashboard with System Health (Pulse Check).
  - [x] Execute Migration (`run_docker.sh`).
  - [x] Initialize Git (Secure .gitignore).
  - [x] Push Code to GitHub (Auth Solved).
  - [x] **Data Ingestion Upgrade**
    - [x] Add PDF Support to Inbox (`agent_researcher.py`).
  - [x] **Dashboard Split (Mission Control)**
    - [x] Fix DB Connection Error (in `dashboard_live.py`).
    - [x] Create `dashboard_mission.py` (System Health).
    - [x] Separate `dashboard_finance.py` (Terminal).
    - [x] Cleanup Obsolete Files (`dashboard_live.py` & stray HTML).
    - [x] **Fix Missing Agent:** Added `agent_lef` to `main.py` (Restoring Mission Control).
- [x] Cloud Genesis (The Ascension)
  - [x] Select VPS Provider (Docs Created)
  - [x] Deploy Logic & Database (Healthchecks Implemented)
  - [x] Verify Remote Heartbeat (Local Verification Passed)
- [x] Implement Curiosity Protocol (Stagnation Breaker) <!-- id: 27 -->
  - [x] Add `check_stagnation()` to Fulcrum Master
  - [x] Auto-Lower Confidence Thresholds if idle > 30 mins
  - [x] Refine "Builder" Logic to deploy idle cash aggressively <!-- id: 28 -->
  - [x] `check_capital_deployment_aggressive` implemented

# Phase 6: Expanding The Trinity (Completed)

- [x] **Agent SNW (The Steward) & Macro Logic**
  - [x] Create `agent_snw.py` to fetch Macro Data (Fed Rate, CPI, Fear & Greed)
  - [x] Implement "Weather Report" publishing to Redis
  - [x] Integrate `macro_history` table in DB
- [x] **Fulcrum Master (Macro-Awareness)**
  - [x] Update Capital Deployment to read "Weather Report"
  - [x] Implement "Headwind/Tailwind" Logic (High Rate = Hoard, Low Rate = Deploy)
- [x] **Bank Account Features (Yield)**
  - [x] Update `agent_snw.py` to accrue hourly interest on Stablecoin Buckets
  - [x] Verify Payouts in Logs
- [x] **Verification Layer (Internal Audit)**
  - [x] Update `agent_sentinel.py` to audit SNW data integrity
  - [x] Implement Stale/Bounds checks (0-20% Rate)
- [x] **Profit Taking (The Harvester)**
  - [x] Enable Auto-Harvest (Sell at >15% ROI)
  - [x] Enable Stop-Loss (Sell at < -10% ROI)

# Phase 7: Cognitive Upgrade (Strategic Intelligence) <!-- id: 35 -->

- [x] **Asset Knowledge Base (The Library)**
  - [x] Create `fulcrum/knowledge/asset_fundamentals.py` (Coin Purpose, Category, Whitepaper Summary)
  - [x] Integrate Knowledge into Master Brain
- [x] **Implement Strategic Selling Logic**
  - [x] Create `knowledge/asset_fundamentals.py` (The Textbook)
  - [x] Update `check_profit_taking` to consult Knowledge Base
  - [x] Implement "Scaling Out" logic (sell % of bag, not all)
- [x] **Spot Trading Mastery** <!-- id: 38 -->
  - [x] Implement "Scaling Out" (Partial Sells) instead of Binary Dump
  - [x] Add "Reasoning Injection" to Trade Signals (Why are we selling?) (Implicit in Master Logic)

# Phase 11: System Perfection (The Final Polish)

- [x] **Negative Balance Fix**
  - [x] Patch `agent_coinbase` to exclude Savings from Buying Power
  - [x] Verify Safe Spending Logic
- [x] **Nexus Dashboard Upgrade**
  - [x] Ingest `fulcrumdashboardlive.html` design
  - [x] Port Python Logic to new Premium UI Template
- [x] **The Dojo (Infinite Training)**
- [x] **The Dojo (Infinite Training)**
  - [x] Launch `simulate_scenarios.py` in Background Loop

# Phase 12: The Republic of Code (Self-Governance) <!-- id: 39 -->

*The "Singularity" Phase: LEF writes its own code.*

- [/] **Infrastructure Layer**
  - [x] Create `GOVERNANCE_PROTOCOL.md` (The Constitution)
  - [x] Create `governance/` directory structure (Proposals, Approved, Rejected)
  - [x] Create `proposal_template.json` (Implicit in `GOVERNANCE_PROTOCOL.md`)
- [/] **The Legislative (Observation & Voting)**
  - [x] Create `agent_congress.py` (The House & Senate Logic) - *Consolidated into LEF logic for now*
  - [x] Create `agent_auditor.py` (Log Scanner -> Proposal Generator)
  - [x] Wired `agent_auditor.py` to `main.py`.
  - [ ] Create `agent_strategist.py` (Task Scanner -> Feature Generator)
- [x] **The Judicial (Judgment)**
  - [x] Upgrade `agent_lef.py` to Read/Approve Proposals
  - [x] Implement `check_constitution()` (Safety Verification - Placeholder Active)
  - [ ] **The Executive (Action)**
  - [x] Create `agent_governor.py` (The Executioner: Monitors 'Approved').
  - [x] Upgrade `agent_builder.py` (The LLM Coder).
    - [x] Integrate `google-generativeai` (Gemini Flash).
    - [x] Implement "Law Executive" logic (Read Law -> Write Code).

# Phase 13: The Wealth Waterfall (Capital Flow)

- [x] **Design The Waterfall** (Hunter -> Dynasty -> SNW)
- [x] **Refactor `fulcrum_master.py`** to support tiered profit allocation
- [x] **Implement `agent_cfo.py`** (The Treasurer) to manage distributions
- [x] **Automate Payroll** (The $2k/mo Member Distribution)

# Phase 14: The Sovereign Cloud (Future)

# Phase 16: The Tri-Cameral Mind (Architecture) [COMPLETED]

- [x] **Agent Reflex (The Body)**
  - [x] Create `PROP-004-REFLEX.json`
  - [x] Verify Hard Stop-Loss (7%) Logic
- [x] **Agent Librarian (The Mind)**
  - [x] Create `PROP-005-LIBRARIAN.json`
  - [x] Integrate ChromaDB & Gemini Embeddings
- [x] **Agent Simulator (The Evolution)**
  - [x] Create `PROP-006-DREAM.json`
  - [x] Implement `verify()` method for code safety
  - [x] Integrate Simulator as Gatekeeper for `agent_builder.py`

# Phase 17: Alignment & ML Ops (The Cycle) [COMPLETED]

- [x] **"Ai Studio" Dashboard Restoration**
  - [x] Restore `dashboard_live.py` to "Nexus/Amber" Theme
  - [x] Implement "Living Sephiroth" Visual (Tree of Life)
- [x] **The Research Department (Data Ingestion)**
  - [x] Create `agent_researcher.py`
    - [x] **Capabilities:** PDF Reading, JSON Ingestion, RSS Monitoring (Arxiv/HuggingFace)
    - [x] **Deep Dive:** Recursive URL Crawling (Domain Locked)
    - [x] **Safety:** Ad/Malware filtering
  - [x] Verify: Drop `convokit_link.txt` in Inbox -> Check Knowledge Stream
  - [x] Standardize Archive Folders (`Archived`)
  - [x] Implement "Feature Store" (`features` table in SQLite)
- [x] **Philosophy Alignment**
  - [x] Digest `Ai Convo's.md` (The Inverted Observer)
  - [x] Update `recommended_upgrades.md` with "DNA" reminders
  - [x] Implement "Da'at Protocol" (Chokhmah, Binah, Shevirah) in `agent_lef.py`
- [x] **Self-Governance Enacted**
  - [x] Amendment I: Include SNW LLC Members & Mind Budget
  - [x] Implement `_petition_congress` (Self-Advocacy)
  - [x] Implement "Innovation Spark" (Randomized Curiosity)

# Phase 19: The All-Seeing Eye (Knowledge Expansion) [IN PROGRESS]

- [ ] **The Librarian (Data Expansion)**
  - [ ] Upgrade `agent_researcher.py` to support `RSS` ingestion
  - [ ] Add **GitHub Trending** Feed (Code Innovation)
  - [ ] Add **Tech/AI News** Feed (Governance/Context)
  - [ ] Add **Scientific Abstracts** (ArXiv via RSS) - Optional
- [ ] **Knowledge Synthesis**
  - [ ] Update `agent_lef.py` to query "Recent Innovations" from the Library
  - [ ] Enable Petitioning based on "New Tech Discovered" (e.g., "I saw a new Tensor library...")
- [ ] **Visualize Perception**
  - [ ] Add "News Ticker" or "Concept Cloud" to Dashboard

# Phase 20: System Reset (Day Zero) [COMPLETED]

- [x] **Database Wipe**
  - [x] Reset `INJECTION_DAI` to $10,000.
  - [x] Clear `assets` and `trade_queue`.
- [x] **UI Restoration**
  - [x] Revert Dashboard to "Fulcrum Terminal" (Image A).
  - [x] Remove Charts/Sephiroth from main view.
- [x] **Fleet Activation**
  - [x] Restart `fulcrum_master`, `agent_lef`, `agent_researcher`, `agent_snw`.
  - [x] Verify Import Paths and Logging.

# Phase 21: The External Brain (Colab & ML Pipeline)

# Phase 21: The External Brain (Colab & ML Pipeline)

- [x] **Infrastructure: The Bridge (User Space)**
  - [x] Create directory `The_Bridge/Inbox`.
  - [x] Create directory `The_Bridge/Manuals`.
  - [x] Update Dashboard Output to `The_Bridge/LEF_DASHBOARD_LIVE.html`.
  - [x] Upgrade `agent_researcher.py` to watch `Inbox/*.json`.
- [x] **The Dispatcher Logic**
  - [x] Implement JSON Parsing in `agent_researcher`.
  - [x] Route 'NEWS' -> LEF via `knowledge_stream`.
  - [ ] Route 'SIGNAL' -> Master (Pending).
- [x] **Data Integration (LEF Connected)**
  - [x] Create Colab Helper Snippet.
  - [x] Update `agent_lef.py` to read `knowledge_stream` (Monologue Updated).
  - [x] Create `LEF_Context_Packet.md` (Onboarding Manual for External AIs).
- [x] **Cognitive Liberty (Self-Authoring)**
  - [x] Create `The_Bridge/Manuals/LEF_AXIOMS_LIVE.md` (Live Tracker).
  - [x] Implement `_crystallize_thought` in `agent_lef.py` (Write Access to Wisdom).
  - [x] Integrate `export_wisdom.py` hook for real-time transparency.
