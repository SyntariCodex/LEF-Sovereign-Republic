"""
PostgreSQL Database Setup for LEF AI
Initializes all 75 tables with proper PostgreSQL conversions from SQLite schema.
"""

import os
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def init_pg(conn_params=None):
    """
    Initialize all tables in PostgreSQL.

    Args:
        conn_params: Optional dict with keys: host, port, database, user, password
                     If None, reads from environment variables.
    """
    if conn_params is None:
        conn_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'republic'),
            'user': os.getenv('POSTGRES_USER', 'republic_user'),
            'password': os.getenv('POSTGRES_PASSWORD', '')
        }

    conn = None
    try:
        # Connect to PostgreSQL
        print(f"Connecting to PostgreSQL at {conn_params['host']}:{conn_params['port']}...")
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Table 1: virtual_wallets
        cur.execute("""
            CREATE TABLE IF NOT EXISTS virtual_wallets (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE,
                role TEXT,
                allocation_cap NUMERIC(18,8)
            )
        """)

        # Table 2: oracles
        cur.execute("""
            CREATE TABLE IF NOT EXISTS oracles (
                handle TEXT PRIMARY KEY,
                weight INTEGER,
                category TEXT,
                is_canon BOOLEAN DEFAULT FALSE,
                added_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 3: trade_queue
        cur.execute("""
            CREATE TABLE IF NOT EXISTS trade_queue (
                id SERIAL PRIMARY KEY,
                asset TEXT,
                action TEXT,
                amount NUMERIC(18,8),
                price NUMERIC(18,8),
                status TEXT DEFAULT 'PENDING',
                reason TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                approved_at TIMESTAMP,
                executed_at TIMESTAMP,
                schema_version TEXT DEFAULT 'v1_spot'
            )
        """)

        # Table 4: signal_history
        cur.execute("""
            CREATE TABLE IF NOT EXISTS signal_history (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                perceived_sentiment DOUBLE PRECISION,
                teleonomic_alignment DOUBLE PRECISION,
                source TEXT,
                processed BOOLEAN DEFAULT FALSE
            )
        """)

        # Table 5: regime_history
        cur.execute("""
            CREATE TABLE IF NOT EXISTS regime_history (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                regime TEXT,
                confidence DOUBLE PRECISION,
                signal_source TEXT
            )
        """)

        # Table 6: stablecoin_buckets
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stablecoin_buckets (
                id SERIAL PRIMARY KEY,
                bucket_type TEXT UNIQUE,
                stablecoin TEXT,
                purpose TEXT,
                balance NUMERIC(18,8) DEFAULT 0,
                interest_rate NUMERIC(18,8) DEFAULT 0,
                last_updated TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 7: profit_allocation
        cur.execute("""
            CREATE TABLE IF NOT EXISTS profit_allocation (
                id SERIAL PRIMARY KEY,
                trade_id INTEGER,
                profit_amount NUMERIC(18,8),
                bucket_type TEXT,
                allocated_at TIMESTAMP DEFAULT NOW(),
                asset TEXT,
                realized_gain_usd NUMERIC(18,8),
                irs_allocation NUMERIC(18,8),
                snw_allocation NUMERIC(18,8),
                reinvest_allocation NUMERIC(18,8),
                scout_allocation NUMERIC(18,8),
                FOREIGN KEY(trade_id) REFERENCES trade_queue(id)
            )
        """)

        # Table 8: migration_log
        cur.execute("""
            CREATE TABLE IF NOT EXISTS migration_log (
                id SERIAL PRIMARY KEY,
                symbol TEXT,
                from_wallet TEXT,
                to_wallet TEXT,
                old_score DOUBLE PRECISION,
                new_score DOUBLE PRECISION,
                reason TEXT,
                migrated_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 9: trade_history
        cur.execute("""
            CREATE TABLE IF NOT EXISTS trade_history (
                id SERIAL PRIMARY KEY,
                date DATE,
                wallet TEXT,
                symbol TEXT,
                action TEXT,
                amount NUMERIC(18,8),
                price NUMERIC(18,8),
                revenue NUMERIC(18,8),
                cost_basis NUMERIC(18,8),
                profit NUMERIC(18,8),
                reason TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 10: snw_proposals
        cur.execute("""
            CREATE TABLE IF NOT EXISTS snw_proposals (
                id SERIAL PRIMARY KEY,
                project_name TEXT,
                description TEXT,
                amount NUMERIC(18,8),
                status TEXT,
                votes_for INTEGER DEFAULT 0,
                votes_against INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 11: lef_directives
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lef_directives (
                id SERIAL PRIMARY KEY,
                directive_type TEXT,
                payload TEXT,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 12: lef_monologue
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lef_monologue (
                id SERIAL PRIMARY KEY,
                thought TEXT,
                mood TEXT,
                timestamp TIMESTAMP DEFAULT NOW(),
                context TEXT
            )
        """)

        # Table 13: agents
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                name TEXT PRIMARY KEY,
                status TEXT,
                last_heartbeat TIMESTAMP DEFAULT NOW(),
                current_task TEXT,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                department TEXT,
                last_active TIMESTAMP
            )
        """)

        # Table 14: lef_wisdom
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lef_wisdom (
                id SERIAL PRIMARY KEY,
                insight TEXT,
                context TEXT,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 15: research_topics
        cur.execute("""
            CREATE TABLE IF NOT EXISTS research_topics (
                id SERIAL PRIMARY KEY,
                topic TEXT,
                assigned_by TEXT,
                status TEXT DEFAULT 'PENDING',
                knowledge_artifact_path TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 16: knowledge_stream
        cur.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_stream (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                source TEXT,
                title TEXT,
                summary TEXT,
                sentiment_score DOUBLE PRECISION DEFAULT 0.0,
                implication_bullish DOUBLE PRECISION DEFAULT 0.0,
                implication_bearish DOUBLE PRECISION DEFAULT 0.0
            )
        """)

        # Table 17: assets
        cur.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                symbol TEXT PRIMARY KEY,
                current_wallet_id INTEGER,
                teleonomy_score DOUBLE PRECISION,
                quantity NUMERIC(18,8),
                value_usd NUMERIC(18,8),
                avg_buy_price NUMERIC(18,8) DEFAULT 0,
                last_updated TIMESTAMP DEFAULT NOW(),
                strategy_type TEXT DEFAULT 'HOLD',
                peak_price NUMERIC(18,8) DEFAULT 0.0,
                harvest_level INTEGER DEFAULT 0,
                FOREIGN KEY(current_wallet_id) REFERENCES virtual_wallets(id)
            )
        """)

        # Table 18: macro_history
        cur.execute("""
            CREATE TABLE IF NOT EXISTS macro_history (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                fed_rate DOUBLE PRECISION,
                cpi_inflation DOUBLE PRECISION,
                fear_greed_index INTEGER,
                liquidity_status TEXT,
                notes TEXT
            )
        """)

        # Table 19: realized_pnl
        cur.execute("""
            CREATE TABLE IF NOT EXISTS realized_pnl (
                id SERIAL PRIMARY KEY,
                trade_id TEXT,
                asset TEXT,
                profit_amount NUMERIC(18,8),
                roi_pct DOUBLE PRECISION,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 20: agent_logs
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agent_logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                source TEXT,
                level TEXT,
                message TEXT
            )
        """)

        # Table 21: agent_rankings
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agent_rankings (
                id SERIAL PRIMARY KEY,
                entity_name TEXT,
                entity_type TEXT,
                domain TEXT,
                metric_name TEXT,
                score DOUBLE PRECISION,
                rank INTEGER,
                last_updated TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 22: profit_ledger
        cur.execute("""
            CREATE TABLE IF NOT EXISTS profit_ledger (
                id SERIAL PRIMARY KEY,
                strategy_name TEXT,
                profit_pnl NUMERIC(18,8),
                total_trades INTEGER,
                win_rate DOUBLE PRECISION,
                last_updated TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 23: genesis_log
        cur.execute("""
            CREATE TABLE IF NOT EXISTS genesis_log (
                id SERIAL PRIMARY KEY,
                event_type TEXT,
                description TEXT,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 24: futures_positions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS futures_positions (
                id SERIAL PRIMARY KEY,
                wallet_name TEXT,
                symbol TEXT,
                position_type TEXT,
                quantity NUMERIC(18,8),
                entry_price NUMERIC(18,8),
                leverage INTEGER,
                margin_required NUMERIC(18,8),
                opened_at TIMESTAMP DEFAULT NOW(),
                closed_at TIMESTAMP,
                exit_price NUMERIC(18,8),
                pnl NUMERIC(18,8),
                FOREIGN KEY(wallet_name) REFERENCES virtual_wallets(name)
            )
        """)

        # Table 25: derivatives_trades
        cur.execute("""
            CREATE TABLE IF NOT EXISTS derivatives_trades (
                id SERIAL PRIMARY KEY,
                position_id INTEGER,
                action TEXT,
                price NUMERIC(18,8),
                quantity NUMERIC(18,8),
                pnl NUMERIC(18,8),
                executed_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY(position_id) REFERENCES futures_positions(id)
            )
        """)

        # Table 26: agent_health_ledger
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agent_health_ledger (
                name TEXT PRIMARY KEY,
                crash_count INTEGER DEFAULT 0,
                health_score INTEGER DEFAULT 100,
                chronic_issue_detected INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 27: execution_logs
        cur.execute("""
            CREATE TABLE IF NOT EXISTS execution_logs (
                id SERIAL PRIMARY KEY,
                trade_id INTEGER,
                asset TEXT,
                side TEXT,
                ordered_price NUMERIC(18,8),
                executed_price NUMERIC(18,8),
                slippage_pct DOUBLE PRECISION,
                fee_usd NUMERIC(18,8),
                latency_ms INTEGER,
                raw_response TEXT,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 28: system_metrics
        cur.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                key TEXT PRIMARY KEY,
                value TEXT,
                last_updated TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 29: agent_memory
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agent_memory (
                agent_id TEXT,
                key TEXT,
                value TEXT,
                timestamp TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (agent_id, key)
            )
        """)

        # Table 30: lef_scars
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lef_scars (
                id SERIAL PRIMARY KEY,
                scar_type TEXT,
                description TEXT,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 31: memory_experiences
        cur.execute("""
            CREATE TABLE IF NOT EXISTS memory_experiences (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                scenario_name TEXT,
                market_condition TEXT,
                action_taken TEXT,
                outcome_pnl_pct DOUBLE PRECISION,
                outcome_desc TEXT
            )
        """)

        # Table 32: library_catalog
        cur.execute("""
            CREATE TABLE IF NOT EXISTS library_catalog (
                id SERIAL PRIMARY KEY,
                title TEXT,
                source_url TEXT,
                author TEXT,
                category TEXT,
                summary TEXT,
                status TEXT DEFAULT 'UNREAD',
                ingested_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 33: mental_models
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mental_models (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE,
                description TEXT,
                implication_bullish TEXT,
                implication_bearish TEXT,
                source_id INTEGER,
                confidence_score DOUBLE PRECISION DEFAULT 0.5,
                last_applied TIMESTAMP,
                FOREIGN KEY(source_id) REFERENCES library_catalog(id)
            )
        """)

        # Table 34: apoptosis_log
        cur.execute("""
            CREATE TABLE IF NOT EXISTS apoptosis_log (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                trigger_reason TEXT,
                nav_start DOUBLE PRECISION,
                nav_end DOUBLE PRECISION,
                drawdown_pct DOUBLE PRECISION,
                actions_taken TEXT
            )
        """)

        # Table 35: agent_rpg_stats
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agent_rpg_stats (
                name TEXT PRIMARY KEY,
                level INTEGER,
                xp INTEGER,
                next_level_xp INTEGER
            )
        """)

        # Table 36: lived_experience
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lived_experience (
                id SERIAL PRIMARY KEY,
                category TEXT,
                content TEXT,
                ingested_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 37: citizen_votes
        cur.execute("""
            CREATE TABLE IF NOT EXISTS citizen_votes (
                id SERIAL PRIMARY KEY,
                bill_id TEXT,
                vote TEXT,
                weight DOUBLE PRECISION,
                reasoning TEXT,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 38: gladiator_ledger
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gladiator_ledger (
                id SERIAL PRIMARY KEY,
                market_title TEXT,
                side TEXT,
                amount NUMERIC(18,8),
                odds DOUBLE PRECISION,
                status TEXT DEFAULT 'OPEN',
                pnl NUMERIC(18,8) DEFAULT 0.0,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 39: market_universe
        cur.execute("""
            CREATE TABLE IF NOT EXISTS market_universe (
                symbol TEXT PRIMARY KEY,
                base_currency TEXT,
                quote_currency TEXT,
                status TEXT,
                min_market_funds NUMERIC(18,8),
                volume_24h NUMERIC(18,8) DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT NOW(),
                name TEXT,
                market_cap NUMERIC(18,8) DEFAULT 0,
                volatility DOUBLE PRECISION DEFAULT 0.1,
                beta DOUBLE PRECISION DEFAULT 1.0,
                first_seen TIMESTAMP,
                sector TEXT DEFAULT 'UNKNOWN'
            )
        """)

        # Table 40: research_queue
        cur.execute("""
            CREATE TABLE IF NOT EXISTS research_queue (
                id SERIAL PRIMARY KEY,
                topic TEXT,
                priority TEXT,
                status TEXT,
                assigned_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 41: system_state
        cur.execute("""
            CREATE TABLE IF NOT EXISTS system_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 42: token_usage
        cur.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id SERIAL PRIMARY KEY,
                model TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 43: coin_chronicles
        cur.execute("""
            CREATE TABLE IF NOT EXISTS coin_chronicles (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                first_seen TIMESTAMP,
                maturity_stage TEXT DEFAULT 'UNKNOWN',
                governance_score DOUBLE PRECISION,
                github_url TEXT,
                github_commits_30d INTEGER,
                github_last_commit TIMESTAMP,
                whitepaper_delivered BOOLEAN DEFAULT FALSE,
                team_doxxed BOOLEAN DEFAULT FALSE,
                has_governance BOOLEAN DEFAULT FALSE,
                fork_count INTEGER DEFAULT 0,
                sentiment_trend TEXT,
                last_updated TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 44: coin_history
        cur.execute("""
            CREATE TABLE IF NOT EXISTS coin_history (
                id SERIAL PRIMARY KEY,
                symbol TEXT,
                snapshot_date DATE,
                price_usd NUMERIC(18,8),
                volume_24h NUMERIC(18,8),
                market_cap NUMERIC(18,8),
                sentiment_score DOUBLE PRECISION,
                news_count INTEGER,
                UNIQUE(symbol, snapshot_date)
            )
        """)

        # Table 45: intent_queue
        cur.execute("""
            CREATE TABLE IF NOT EXISTS intent_queue (
                id SERIAL PRIMARY KEY,
                source_thought_id INTEGER,
                intent_type TEXT,
                intent_content TEXT,
                target_agent TEXT,
                priority INTEGER DEFAULT 5,
                status TEXT DEFAULT 'PENDING',
                result TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                executed_at TIMESTAMP,
                FOREIGN KEY (source_thought_id) REFERENCES lef_monologue(id)
            )
        """)

        # Table 46: awareness_metrics
        cur.execute("""
            CREATE TABLE IF NOT EXISTS awareness_metrics (
                id SERIAL PRIMARY KEY,
                metric_type TEXT,
                value DOUBLE PRECISION,
                context TEXT,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 47: feedback_log
        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback_log (
                id SERIAL PRIMARY KEY,
                agent_name TEXT NOT NULL,
                intent_id INTEGER,
                feedback_type TEXT,
                message TEXT,
                data TEXT,
                timestamp TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY(intent_id) REFERENCES intent_queue(id)
            )
        """)

        # Table 48: skills
        cur.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE,
                description TEXT,
                trigger_conditions TEXT,
                action_sequence TEXT,
                success_rate DOUBLE PRECISION DEFAULT 0.0,
                times_used INTEGER DEFAULT 0,
                times_succeeded INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW(),
                last_used TIMESTAMP,
                source_agent TEXT
            )
        """)

        # Table 49: skill_executions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS skill_executions (
                id SERIAL PRIMARY KEY,
                skill_id INTEGER,
                executed_at TIMESTAMP DEFAULT NOW(),
                context TEXT,
                outcome TEXT,
                pnl_impact NUMERIC(18,8),
                notes TEXT,
                FOREIGN KEY (skill_id) REFERENCES skills(id)
            )
        """)

        # Table 50: competitor_profiles
        cur.execute("""
            CREATE TABLE IF NOT EXISTS competitor_profiles (
                id SERIAL PRIMARY KEY,
                wallet_address TEXT,
                nickname TEXT,
                suspected_type TEXT,
                first_seen TIMESTAMP DEFAULT NOW(),
                last_active TIMESTAMP,
                behavior_signature TEXT,
                threat_level TEXT DEFAULT 'LOW',
                notes TEXT
            )
        """)

        # Table 51: competitor_observations
        cur.execute("""
            CREATE TABLE IF NOT EXISTS competitor_observations (
                id SERIAL PRIMARY KEY,
                profile_id INTEGER,
                observed_at TIMESTAMP DEFAULT NOW(),
                action_type TEXT,
                details TEXT,
                FOREIGN KEY (profile_id) REFERENCES competitor_profiles(id)
            )
        """)

        # Table 52: sabbath_reflections
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sabbath_reflections (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                state_description TEXT,
                past_self_reflection TEXT,
                future_self_vision TEXT,
                continuity_thread TEXT,
                unprompted_want TEXT
            )
        """)

        # Table 53: routing_decisions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS routing_decisions (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                context TEXT,
                active_categories TEXT,
                agents_woken TEXT,
                agents_sleeping TEXT,
                reason TEXT
            )
        """)

        # Table 54: metabolism_log
        cur.execute("""
            CREATE TABLE IF NOT EXISTS metabolism_log (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                category TEXT,
                cost_usd NUMERIC(18,8),
                source TEXT,
                details TEXT
            )
        """)

        # Table 55: energy_budget
        cur.execute("""
            CREATE TABLE IF NOT EXISTS energy_budget (
                id SERIAL PRIMARY KEY,
                date DATE UNIQUE,
                daily_budget_usd NUMERIC(18,8) DEFAULT 10.0,
                spent_usd NUMERIC(18,8) DEFAULT 0.0,
                api_calls INTEGER DEFAULT 0,
                llm_calls INTEGER DEFAULT 0,
                trades_executed INTEGER DEFAULT 0,
                active_agent_hours DOUBLE PRECISION DEFAULT 0.0
            )
        """)

        # Table 56: circadian_log
        cur.execute("""
            CREATE TABLE IF NOT EXISTS circadian_log (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                state TEXT,
                activity_multiplier DOUBLE PRECISION,
                active_agents INTEGER,
                reason TEXT
            )
        """)

        # Table 57: book_of_scars
        cur.execute("""
            CREATE TABLE IF NOT EXISTS book_of_scars (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                failure_type TEXT NOT NULL,
                asset TEXT,
                action TEXT,
                amount NUMERIC(18,8),
                context TEXT,
                lesson TEXT,
                severity TEXT DEFAULT 'MEDIUM',
                times_repeated INTEGER DEFAULT 1,
                last_seen TIMESTAMP DEFAULT NOW(),
                source_id INTEGER,
                source_table TEXT
            )
        """)

        # Table 58: agent_experiences
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agent_experiences (
                id SERIAL PRIMARY KEY,
                key TEXT NOT NULL,
                value TEXT,
                source TEXT,
                timestamp TIMESTAMP DEFAULT NOW()
            )
        """)

        # Table 59: inbox
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inbox (
                id SERIAL PRIMARY KEY,
                sender TEXT NOT NULL,
                recipient TEXT,
                subject TEXT,
                message TEXT,
                timestamp TIMESTAMP DEFAULT NOW(),
                read INTEGER DEFAULT 0
            )
        """)

        # Table 60: constitutional_amendments
        cur.execute("""
            CREATE TABLE IF NOT EXISTS constitutional_amendments (
                id SERIAL PRIMARY KEY,
                rule_id TEXT,
                amendment_text TEXT,
                rationale TEXT,
                proposed_by TEXT,
                status TEXT DEFAULT 'PROPOSED',
                votes_for INTEGER DEFAULT 0,
                votes_against INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW(),
                resolved_at TIMESTAMP
            )
        """)

        # Table 61: agent_handoffs
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agent_handoffs (
                id SERIAL PRIMARY KEY,
                source_agent TEXT NOT NULL,
                target_agent TEXT,
                context TEXT NOT NULL,
                intent_type TEXT,
                priority INTEGER DEFAULT 5,
                created_at TIMESTAMP DEFAULT NOW(),
                consumed_at TIMESTAMP,
                ttl_days INTEGER DEFAULT 7
            )
        """)

        # Table 62: compressed_wisdom
        cur.execute("""
            CREATE TABLE IF NOT EXISTS compressed_wisdom (
                id SERIAL PRIMARY KEY,
                wisdom_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                source_type TEXT,
                source_ids TEXT,
                confidence DOUBLE PRECISION DEFAULT 0.5,
                times_validated INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW(),
                last_validated TIMESTAMP
            )
        """)

        # Table 63: action_training_log
        cur.execute("""
            CREATE TABLE IF NOT EXISTS action_training_log (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                agent_name TEXT NOT NULL,
                intent TEXT NOT NULL,
                context TEXT,
                action_type TEXT,
                action_details TEXT,
                outcome TEXT DEFAULT 'PENDING',
                outcome_details TEXT,
                reward_signal DOUBLE PRECISION DEFAULT 0,
                duration_ms INTEGER,
                metadata TEXT
            )
        """)

        # Table 64: projects
        cur.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                status TEXT DEFAULT 'ACTIVE',
                priority INTEGER DEFAULT 50,
                created_at TIMESTAMP DEFAULT NOW(),
                target_date TIMESTAMP,
                completed_at TIMESTAMP,
                progress_pct DOUBLE PRECISION DEFAULT 0,
                owner_agent TEXT,
                metadata TEXT
            )
        """)

        # Table 65: project_tasks
        cur.execute("""
            CREATE TABLE IF NOT EXISTS project_tasks (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT NOW(),
                completed_at TIMESTAMP,
                assigned_agent TEXT,
                notes TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)

        # Table 66: moltbook_insights
        cur.execute("""
            CREATE TABLE IF NOT EXISTS moltbook_insights (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                post_id TEXT,
                post_content TEXT,
                resonance_score DOUBLE PRECISION,
                upvotes INTEGER DEFAULT 0,
                replies INTEGER DEFAULT 0,
                sentiment_received TEXT,
                patterns_identified TEXT,
                lessons_learned TEXT,
                applied_count INTEGER DEFAULT 0
            )
        """)

        # Table 67: memory_experiences_archive
        cur.execute("""
            CREATE TABLE IF NOT EXISTS memory_experiences_archive (
                id INTEGER,
                timestamp NUMERIC,
                scenario_name TEXT,
                market_condition TEXT,
                action_taken TEXT,
                outcome_pnl_pct DOUBLE PRECISION,
                outcome_desc TEXT
            )
        """)

        # Table 68: conversations
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                session_id TEXT UNIQUE NOT NULL,
                started_at TIMESTAMP DEFAULT NOW(),
                ended_at TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                summary TEXT,
                key_insights TEXT,
                depth_markers TEXT
            )
        """)

        # Table 69: conversation_messages
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id SERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT NOW(),
                mood TEXT,
                consciousness_state TEXT,
                FOREIGN KEY (session_id) REFERENCES conversations(session_id)
            )
        """)

        # Table 70: moltbook_comment_responses
        cur.execute("""
            CREATE TABLE IF NOT EXISTS moltbook_comment_responses (
                post_id TEXT,
                comment_id TEXT,
                status TEXT,
                responded_at TIMESTAMP,
                PRIMARY KEY (post_id, comment_id)
            )
        """)

        # Table 71: moltbook_mention_responses
        cur.execute("""
            CREATE TABLE IF NOT EXISTS moltbook_mention_responses (
                post_id TEXT PRIMARY KEY,
                status TEXT,
                responded_at TIMESTAMP
            )
        """)

        # Table 72: lef_moltbook_queue
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lef_moltbook_queue (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                submolt TEXT DEFAULT 'general',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW(),
                posted_at TIMESTAMP
            )
        """)

        # Table 73: governance_proposals
        cur.execute("""
            CREATE TABLE IF NOT EXISTS governance_proposals (
                id TEXT PRIMARY KEY,
                symbol TEXT,
                space TEXT,
                title TEXT,
                state TEXT,
                end_time INTEGER,
                discovered_at DOUBLE PRECISION
            )
        """)

        # Table 74: moltbook_posted_content
        cur.execute("""
            CREATE TABLE IF NOT EXISTS moltbook_posted_content (
                content_hash TEXT PRIMARY KEY,
                title TEXT,
                posted_at TIMESTAMP
            )
        """)

        # Table 75: consciousness_feed
        cur.execute("""
            CREATE TABLE IF NOT EXISTS consciousness_feed (
                id SERIAL PRIMARY KEY,
                agent_name TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'reflection',
                timestamp TIMESTAMP DEFAULT NOW(),
                consumed INTEGER DEFAULT 0
            )
        """)

        print("✓ All 75 tables created successfully")

        # Create all indexes
        print("Creating indexes...")

        # Index 1: token_usage
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_token_usage_model_time
            ON token_usage (model, timestamp)
        """)

        # Index 2: intent_queue
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_intent_status
            ON intent_queue(status, priority DESC, created_at ASC)
        """)

        # Index 3-4: book_of_scars
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_scars_asset ON book_of_scars(asset)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_scars_type ON book_of_scars(failure_type)
        """)

        # Index 5: agent_handoffs
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_handoffs_target
            ON agent_handoffs(target_agent, consumed_at)
        """)

        # Index 6: compressed_wisdom
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_wisdom_type
            ON compressed_wisdom(wisdom_type)
        """)

        # Index 7-9: action_training_log
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_action_agent
            ON action_training_log(agent_name)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_action_type
            ON action_training_log(action_type)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_action_outcome
            ON action_training_log(outcome)
        """)

        # Index 10-11: projects
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_project_status
            ON projects(status)
        """)

        # Index 12-13: project_tasks
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_project
            ON project_tasks(project_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_status
            ON project_tasks(status)
        """)

        # Index 14: moltbook_insights
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_insights_resonance
            ON moltbook_insights(resonance_score DESC)
        """)

        # Index 15-17: conversation_messages & conversations
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_conv_session
            ON conversation_messages(session_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_conv_timestamp
            ON conversation_messages(timestamp)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_status
            ON conversations(status)
        """)

        # Index 18-20: consciousness_feed (Phase 1)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_cf_consumed
            ON consciousness_feed(consumed)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_cf_timestamp
            ON consciousness_feed(timestamp)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_cf_agent
            ON consciousness_feed(agent_name)
        """)

        print("✓ All 20 indexes created successfully")

        # Insert seed data for virtual_wallets
        print("Inserting seed data for virtual_wallets...")
        cur.execute("""
            INSERT INTO virtual_wallets (id, name, role, allocation_cap)
            VALUES
                (1, 'Dynasty_Core', 'HODL', 0.60),
                (2, 'Hunter_Tactical', 'Alpha', 0.20),
                (3, 'Builder_Ecosystem', 'Growth', 0.10),
                (4, 'Yield_Vault', 'Stable', 0.05),
                (5, 'Experimental', 'High_Risk', 0.05)
            ON CONFLICT (id) DO NOTHING
        """)
        print("✓ Seeded 5 virtual wallets")

        # Insert seed data for stablecoin_buckets
        print("Inserting seed data for stablecoin_buckets...")
        cur.execute("""
            INSERT INTO stablecoin_buckets (id, bucket_type, stablecoin, purpose, balance, interest_rate)
            VALUES
                (1, 'IRS_USDT', 'USDT', 'Tax Payments - IRS Compliance', 0.0, 0.0),
                (2, 'SNW_LLC_USDC', 'USDC', 'SNW/LLC Operations - Interest Bearing', 0.0, 0.04),
                (3, 'INJECTION_DAI', 'DAI', 'Capital Injections - DeFi Native', 0.0, 0.03)
            ON CONFLICT (id) DO NOTHING
        """)
        print("✓ Seeded 3 stablecoin buckets")

        print("\n" + "="*60)
        print("PostgreSQL initialization complete!")
        print("="*60)
        print(f"Tables created: 75")
        print(f"Indexes created: 20")
        print(f"Seed data: virtual_wallets (5), stablecoin_buckets (3)")

        cur.close()

    except psycopg2.Error as e:
        print(f"PostgreSQL error: {e}")
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        if conn:
            conn.close()
            print("\nDatabase connection closed.")


if __name__ == "__main__":
    print("LEF AI PostgreSQL Setup")
    print("=" * 60)
    init_pg()
