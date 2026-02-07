"""
AgentProposal - SNW Node Proposal Evaluator
Department: Dept_Wealth (under Co Creator LLC umbrella)
Purpose: Evaluate Node funding proposals for SNW alignment.

STATUS: DORMANT — Activates when SNW_LLC_USDC bucket > $500

Pipeline:
    1. Nodes submit RFRs (Requests for Resilience)
    2. AgentProposal scores alignment with SNW mission
    3. Human approval/veto before disbursement
    4. Funds released from SNW_LLC_USDC bucket
"""

import os
import sqlite3
import logging
from datetime import datetime

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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.getenv('DB_PATH', os.path.join(BASE_DIR, 'republic.db'))

# Activation threshold — agent remains dormant until funding is available
ACTIVATION_THRESHOLD_USD = 500.0


class AgentProposal:
    """
    SNW Node Proposal Evaluator
    
    Evaluates funding proposals from partner Nodes against SNW mission alignment.
    
    Scoring Criteria (0-100):
    - Mission Alignment (40%): Does this build resilience in Southern Nevada youth?
    - Track Match (20%): Shield / Builder / Steward focus?
    - Partner Quality (20%): Established org? Liability handled?
    - Cost Efficiency (20%): $/participant, overhead ratio
    """
    
    TRACKS = {
        'SHIELD': 'Community safety, law enforcement partnerships, protector training',
        'BUILDER': 'Trades, infrastructure, practical skills',
        'STEWARD': 'Environmental conservation, Mojave ecosystem, biology'
    }
    
    def __init__(self, db_path=None):
        self.name = "AgentProposal"
        self.db_path = db_path or DB_PATH
        self.active = False
        self._ensure_tables()
        self._check_activation()
    
    def _ensure_tables(self):
        """Create proposals table if not exists."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                
                c.execute("""
                    CREATE TABLE IF NOT EXISTS snw_proposals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        node_name TEXT NOT NULL,
                        track TEXT,
                        title TEXT NOT NULL,
                        description TEXT,
                        requested_amount REAL,
                        participant_count INTEGER,
                        alignment_score REAL,
                        total_score REAL,
                        status TEXT DEFAULT 'PENDING',
                        human_decision TEXT,
                        decision_notes TEXT,
                        decided_at TIMESTAMP
                    )
                """)
                
                conn.commit()
            logger.info("[PROPOSAL] 📋 snw_proposals table ready.")
        except sqlite3.Error as e:
            logger.error(f"[PROPOSAL] Table creation error: {e}")
    
    def _check_activation(self):
        """Check if SNW_LLC_USDC has enough funds to activate."""
        try:
            with db_connection(self.db_path) as conn:
                c = conn.cursor()
                c.execute("SELECT balance FROM stablecoin_buckets WHERE bucket_type = 'SNW_LLC_USDC'")
                row = c.fetchone()
            
            if row and row[0] >= ACTIVATION_THRESHOLD_USD:
                self.active = True
                logger.info(f"[PROPOSAL] ✅ ACTIVE — SNW bucket: ${row[0]:.2f}")
            else:
                self.active = False
                balance = row[0] if row else 0
                logger.info(f"[PROPOSAL] 💤 DORMANT — SNW bucket: ${balance:.2f} (need ${ACTIVATION_THRESHOLD_USD})")
        except sqlite3.Error:
            self.active = False
    
    def submit_proposal(self, node_name: str, track: str, title: str, 
                       description: str, requested_amount: float,
                       participant_count: int = 0) -> int:
        """
        Submit a new funding proposal from a Node.
        
        Returns proposal_id
        """
        if track not in self.TRACKS:
            logger.warning(f"[PROPOSAL] Unknown track: {track}. Using 'GENERAL'.")
            track = 'GENERAL'
        
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            # Auto-score alignment
            alignment_score = self._score_alignment(title, description, track)
            
            # Calculate total score
            cost_per_participant = requested_amount / max(participant_count, 1)
            efficiency_score = max(0, 100 - (cost_per_participant / 10))  # $100/person = 90, $500 = 50
            
            total_score = (
                alignment_score * 0.40 +
                (80 if track in self.TRACKS else 50) * 0.20 +  # Track match
                70 * 0.20 +  # Default partner quality (can be refined)
                efficiency_score * 0.20
            )
            
            c.execute("""
                INSERT INTO snw_proposals 
                (node_name, track, title, description, requested_amount, participant_count, alignment_score, total_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (node_name, track, title, description, requested_amount, participant_count, alignment_score, total_score))
            
            proposal_id = c.lastrowid
            conn.commit()
        
        logger.info(f"[PROPOSAL] 📥 New proposal #{proposal_id}: {title} (Score: {total_score:.1f})")
        return proposal_id
    
    def _score_alignment(self, title: str, description: str, track: str) -> float:
        """
        Score mission alignment (0-100).
        
        Keywords that boost score:
        - resilience, grit, competence, self-reliance
        - youth, Southern Nevada, Mojave
        - outdoor, challenge, training
        """
        text = f"{title} {description}".lower()
        
        score = 50  # Base score
        
        # Mission keywords
        mission_keywords = ['resilience', 'grit', 'competence', 'self-reliance', 'youth', 
                           'challenge', 'training', 'outdoor', 'skill', 'capable']
        for kw in mission_keywords:
            if kw in text:
                score += 5
        
        # Location keywords
        location_keywords = ['southern nevada', 'las vegas', 'henderson', 'mojave', 'nevada']
        for kw in location_keywords:
            if kw in text:
                score += 3
        
        # Track-specific keywords
        if track == 'SHIELD':
            shield_kw = ['safety', 'protect', 'law enforcement', 'community', 'response']
            for kw in shield_kw:
                if kw in text:
                    score += 3
        elif track == 'BUILDER':
            builder_kw = ['trade', 'build', 'construct', 'infrastructure', 'hands-on']
            for kw in builder_kw:
                if kw in text:
                    score += 3
        elif track == 'STEWARD':
            steward_kw = ['environment', 'conservation', 'nature', 'ecosystem', 'biology']
            for kw in steward_kw:
                if kw in text:
                    score += 3
        
        return min(100, max(0, score))
    
    def get_pending_proposals(self) -> list:
        """Get all proposals awaiting human decision."""
        with db_connection(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute("""
                SELECT id, node_name, track, title, requested_amount, total_score, submitted_at
                FROM snw_proposals
                WHERE status = 'PENDING'
                ORDER BY total_score DESC
            """)
            
            proposals = [dict(row) for row in c.fetchall()]
        return proposals
    
    def approve_proposal(self, proposal_id: int, notes: str = None) -> bool:
        """Human approves a proposal for funding."""
        return self._decide_proposal(proposal_id, 'APPROVED', notes)
    
    def reject_proposal(self, proposal_id: int, notes: str = None) -> bool:
        """Human rejects a proposal."""
        return self._decide_proposal(proposal_id, 'REJECTED', notes)
    
    def _decide_proposal(self, proposal_id: int, decision: str, notes: str) -> bool:
        """Record human decision on proposal."""
        with db_connection(self.db_path) as conn:
            c = conn.cursor()
            
            c.execute("""
                UPDATE snw_proposals
                SET status = 'DECIDED', human_decision = ?, decision_notes = ?, decided_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (decision, notes, proposal_id))
            
            success = c.rowcount > 0
            conn.commit()
        
        if success:
            logger.info(f"[PROPOSAL] ✅ Proposal #{proposal_id} → {decision}")
        return success
    
    def run(self):
        """
        Main loop — checks for proposals and activation status.
        
        NOTE: This agent is DORMANT until SNW_LLC_USDC bucket has funds.
        """
        import time
        
        logger.info(f"[PROPOSAL] 🏛️ SNW Proposal Evaluator Online.")
        logger.info(f"[PROPOSAL] 💤 DORMANT MODE — Waiting for SNW funding (>${ACTIVATION_THRESHOLD_USD})")
        
        while True:
            self._check_activation()
            
            if self.active:
                pending = self.get_pending_proposals()
                if pending:
                    logger.info(f"[PROPOSAL] 📋 {len(pending)} proposals awaiting review")
            
            time.sleep(3600)  # Check every hour


def run_proposal_loop(db_path=None):
    """Entry point for main.py thread."""
    agent = AgentProposal(db_path)
    agent.run()


if __name__ == "__main__":
    agent = AgentProposal()
    
    # Demo: Submit a test proposal
    if agent.active:
        proposal_id = agent.submit_proposal(
            node_name="Horseman's Park LV",
            track="STEWARD",
            title="Mojave Youth Equestrian Challenge",
            description="Weekly equestrian sessions teaching resilience and land navigation to Henderson youth",
            requested_amount=2500.00,
            participant_count=25
        )
        print(f"Created proposal #{proposal_id}")
    else:
        print("Agent is DORMANT — no SNW funds available")
