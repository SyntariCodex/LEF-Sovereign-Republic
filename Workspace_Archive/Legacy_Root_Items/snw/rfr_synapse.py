"""
SNW RFR System (The "Synapse")
Request for Resilience - Funds connections to build competence.

Based on: Southern Nevada Wildlands White Paper
RFR is not about "helping." It is a "Synapse" that funds connections to build competence.
Goal is "Sovereign Youth," not "compliant youth."
"""

import sqlite3
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Import RDA Engine for LEF Alignment check
sys.path.insert(0, str(Path(__file__).parent.parent / 'fulcrum' / 'agents'))
try:
    from rda_engine import RDAEngine
except ImportError:
    # Fallback if import fails
    RDAEngine = None

@dataclass
class RFR:
    """
    Request for Resilience - Quarterly objective.
    """
    id: Optional[int]
    quarter: str  # e.g., "Q2 2025"
    objective: str  # e.g., "Enhance land navigation skills for 50 youth in Henderson"
    track: str  # "Shield", "Builder", "Steward"
    target_youth_count: int
    location: str
    budget: float
    status: str  # "OPEN", "CLOSED", "AWARDED"
    created_at: datetime
    deadline: datetime

@dataclass
class NodeProposal:
    """
    Action Plan submitted by a Node (Partner).
    """
    id: Optional[int]
    rfr_id: int
    node_name: str
    contact_email: str
    action_plan: str  # Detailed proposal
    partner_venue: str  # e.g., "Horse Ranch XYZ"
    estimated_cost: float
    lef_alignment_score: Optional[float]  # Score from LEF AI analysis
    status: str  # "PENDING", "APPROVED", "REJECTED", "EXECUTING", "COMPLETE"
    submitted_at: datetime

class RFRSynapse:
    """
    The "Synapse" - Detects needs and signals connections via funding.
    """
    
    def __init__(self, db_path: str = 'snw.db'):
        """
        Initialize the RFR Synapse system.
        """
        self.db_path = db_path
        self.rda = RDAEngine() if RDAEngine else None
        self._init_db()
    
    def _init_db(self):
        """
        Initialize SNW database schema.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # RFR Table
        c.execute('''CREATE TABLE IF NOT EXISTS rfrs
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      quarter TEXT,
                      objective TEXT,
                      track TEXT,
                      target_youth_count INTEGER,
                      location TEXT,
                      budget REAL,
                      status TEXT DEFAULT 'OPEN',
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      deadline TIMESTAMP)''')
        
        # Node Proposals Table
        c.execute('''CREATE TABLE IF NOT EXISTS node_proposals
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      rfr_id INTEGER,
                      node_name TEXT,
                      contact_email TEXT,
                      action_plan TEXT,
                      partner_venue TEXT,
                      estimated_cost REAL,
                      lef_alignment_score REAL,
                      status TEXT DEFAULT 'PENDING',
                      submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      reviewed_at TIMESTAMP,
                      FOREIGN KEY(rfr_id) REFERENCES rfrs(id))''')
        
        # Grants Table (Awarded proposals)
        c.execute('''CREATE TABLE IF NOT EXISTS grants
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      proposal_id INTEGER,
                      amount_awarded REAL,
                      awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      execution_status TEXT DEFAULT 'PENDING',
                      completion_report TEXT,
                      FOREIGN KEY(proposal_id) REFERENCES node_proposals(id))''')
        
        # Nodes Registry (Approved partners)
        c.execute('''CREATE TABLE IF NOT EXISTS nodes
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT UNIQUE,
                      contact_email TEXT,
                      category TEXT,
                      status TEXT DEFAULT 'ACTIVE',
                      brand_approved BOOLEAN DEFAULT 0,
                      registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        conn.commit()
        conn.close()
    
    def create_rfr(self, quarter: str, objective: str, track: str, 
                   target_youth_count: int, location: str, budget: float,
                   deadline_days: int = 90) -> RFR:
        """
        Creates a new Request for Resilience (RFR).
        
        Example:
            create_rfr(
                quarter="Q2 2025",
                objective="Enhance land navigation skills for 50 youth in Henderson via equestrian or outdoor challenges",
                track="Steward",
                target_youth_count=50,
                location="Henderson, NV",
                budget=10000.0
            )
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        deadline = datetime.now() + timedelta(days=deadline_days)
        
        c.execute("""
            INSERT INTO rfrs 
            (quarter, objective, track, target_youth_count, location, budget, status, deadline)
            VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?)
        """, (quarter, objective, track, target_youth_count, location, budget, deadline))
        
        rfr_id = c.lastrowid
        conn.commit()
        conn.close()
        
        rfr = RFR(
            id=rfr_id,
            quarter=quarter,
            objective=objective,
            track=track,
            target_youth_count=target_youth_count,
            location=location,
            budget=budget,
            status='OPEN',
            created_at=datetime.now(),
            deadline=deadline
        )
        
        print(f"[SNW] RFR Created: {quarter} - {objective}")
        return rfr
    
    def submit_proposal(self, rfr_id: int, node_name: str, contact_email: str,
                       action_plan: str, partner_venue: str, estimated_cost: float) -> NodeProposal:
        """
        Node submits an Action Plan proposal.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Check if RFR is still open
        c.execute("SELECT status FROM rfrs WHERE id = ?", (rfr_id,))
        rfr_status = c.fetchone()
        
        if not rfr_status or rfr_status[0] != 'OPEN':
            raise ValueError(f"RFR {rfr_id} is not open for proposals.")
        
        # Analyze with LEF AI for alignment
        lef_score = self._analyze_lef_alignment(action_plan)
        
        c.execute("""
            INSERT INTO node_proposals
            (rfr_id, node_name, contact_email, action_plan, partner_venue, estimated_cost, lef_alignment_score, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')
        """, (rfr_id, node_name, contact_email, action_plan, partner_venue, estimated_cost, lef_score))
        
        proposal_id = c.lastrowid
        conn.commit()
        conn.close()
        
        proposal = NodeProposal(
            id=proposal_id,
            rfr_id=rfr_id,
            node_name=node_name,
            contact_email=contact_email,
            action_plan=action_plan,
            partner_venue=partner_venue,
            estimated_cost=estimated_cost,
            lef_alignment_score=lef_score,
            status='PENDING',
            submitted_at=datetime.now()
        )
        
        print(f"[SNW] Proposal submitted by {node_name} (LEF Alignment: {lef_score:.2f})")
        return proposal
    
    def _analyze_lef_alignment(self, action_plan: str) -> float:
        """
        Analyzes proposal with LEF AI to ensure alignment with "Sovereign Youth" (not "compliant youth").
        
        Uses RDA to detect if the proposal builds:
        - Competence (not compliance)
        - Self-sufficiency (not dependency)
        - Resilience (not comfort)
        - Purposeful growth (not just activity)
        """
        # Key phrases that indicate "Sovereign Youth" alignment
        sovereign_indicators = [
            'self-reliance', 'competence', 'resilience', 'grit', 'autonomy',
            'capacity', 'capability', 'independence', 'mastery', 'purpose',
            'challenge', 'growth', 'development', 'skill-building'
        ]
        
        # Key phrases that indicate "compliant youth" (negative)
        compliant_indicators = [
            'obedience', 'compliance', 'following rules', 'passive',
            'dependency', 'hand-holding', 'easy', 'comfort', 'safety-first'
        ]
        
        text_lower = action_plan.lower()
        
        # Count indicators
        sovereign_count = sum(1 for phrase in sovereign_indicators if phrase in text_lower)
        compliant_count = sum(1 for phrase in compliant_indicators if phrase in text_lower)
        
        # Calculate alignment score (0.0 - 1.0)
        # Higher score = more aligned with "Sovereign Youth"
        base_score = min(sovereign_count / 5.0, 1.0)  # 5+ sovereign indicators = max
        penalty = compliant_count * 0.2  # Each compliant indicator reduces score
        
        alignment_score = max(0.0, min(1.0, base_score - penalty))
        
        # Use RDA to detect gap between stated intent and actual structure
        if self.rda:
            rda_result = self.rda.bridge_protocol(action_plan)
            
            if rda_result[0] == 'interrogate':
                # Large gap detected - proposal may be unclear
                alignment_score *= 0.8  # Reduce score if intent is unclear
        
        return round(alignment_score, 3)
    
    def review_proposal(self, proposal_id: int, approve: bool, 
                       award_amount: Optional[float] = None) -> bool:
        """
        Reviews a proposal and awards grant if approved.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Get proposal
        c.execute("SELECT * FROM node_proposals WHERE id = ?", (proposal_id,))
        proposal_data = c.fetchone()
        
        if not proposal_data:
            conn.close()
            return False
        
        if approve:
            # Award grant
            if award_amount is None:
                # Use estimated cost if amount not specified
                award_amount = proposal_data[6]  # estimated_cost column
            
            # Update proposal status
            c.execute("""
                UPDATE node_proposals 
                SET status = 'APPROVED', reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (proposal_id,))
            
            # Create grant record
            c.execute("""
                INSERT INTO grants (proposal_id, amount_awarded)
                VALUES (?, ?)
            """, (proposal_id, award_amount))
            
            # Register node if not already registered
            node_name = proposal_data[2]  # node_name column
            c.execute("SELECT id FROM nodes WHERE name = ?", (node_name,))
            if not c.fetchone():
                c.execute("""
                    INSERT INTO nodes (name, contact_email, category, brand_approved)
                    VALUES (?, ?, 'Partner', 1)
                """, (node_name, proposal_data[3]))  # contact_email column
            
            conn.commit()
            conn.close()
            
            print(f"[SNW] Proposal {proposal_id} APPROVED. Grant awarded: ${award_amount:.2f}")
            return True
        else:
            # Reject proposal
            c.execute("""
                UPDATE node_proposals 
                SET status = 'REJECTED', reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (proposal_id,))
            
            conn.commit()
            conn.close()
            
            print(f"[SNW] Proposal {proposal_id} REJECTED.")
            return False
    
    def get_open_rfrs(self) -> List[RFR]:
        """
        Returns all open RFRs.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT * FROM rfrs WHERE status = 'OPEN' AND deadline > CURRENT_TIMESTAMP")
        rows = c.fetchall()
        
        conn.close()
        
        rfrs = []
        for row in rows:
            rfr = RFR(
                id=row[0],
                quarter=row[1],
                objective=row[2],
                track=row[3],
                target_youth_count=row[4],
                location=row[5],
                budget=row[6],
                status=row[7],
                created_at=datetime.fromisoformat(row[8]),
                deadline=datetime.fromisoformat(row[9])
            )
            rfrs.append(rfr)
        
        return rfrs
    
    def get_proposals_for_rfr(self, rfr_id: int) -> List[NodeProposal]:
        """
        Returns all proposals for a specific RFR.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT * FROM node_proposals WHERE rfr_id = ?", (rfr_id,))
        rows = c.fetchall()
        
        conn.close()
        
        proposals = []
        for row in rows:
            proposal = NodeProposal(
                id=row[0],
                rfr_id=row[1],
                node_name=row[2],
                contact_email=row[3],
                action_plan=row[4],
                partner_venue=row[5],
                estimated_cost=row[6],
                lef_alignment_score=row[7],
                status=row[8],
                submitted_at=datetime.fromisoformat(row[9])
            )
            proposals.append(proposal)
        
        return proposals

# Usage Example
if __name__ == "__main__":
    synapse = RFRSynapse()
    
    # Create an RFR
    rfr = synapse.create_rfr(
        quarter="Q2 2025",
        objective="Enhance land navigation skills for 50 youth in Henderson via equestrian or outdoor challenges",
        track="Steward",
        target_youth_count=50,
        location="Henderson, NV",
        budget=10000.0
    )
    
    # Submit a proposal
    proposal = synapse.submit_proposal(
        rfr_id=rfr.id,
        node_name="Nevada Youth Outdoors",
        contact_email="contact@nyo.org",
        action_plan="We propose partnering with Desert Horse Ranch for weekly 3-hour sessions. Youth will learn land navigation, survival skills, and equestrian basics. Focus on building self-reliance and competence in outdoor environments.",
        partner_venue="Desert Horse Ranch",
        estimated_cost=8500.0
    )
    
    print(f"\nProposal LEF Alignment Score: {proposal.lef_alignment_score}")
    
    # Review and approve
    synapse.review_proposal(proposal.id, approve=True, award_amount=8500.0)
    
    print("\n[SNW] RFR System test complete.")
