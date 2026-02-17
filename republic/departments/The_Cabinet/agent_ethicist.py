"""
AgentEthicist (The Conscience)
Department: The_Cabinet
Role: Moral Veto & Alignment Review.
"""

import time
import logging
import os
import json
import re
import tempfile

# Config
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOVERNANCE_DIR = os.path.join(BASE_DIR, 'governance')
DIRS = {
    'proposals': os.path.join(GOVERNANCE_DIR, 'proposals'),
    'house': os.path.join(GOVERNANCE_DIR, 'house'),
    'rejected': os.path.join(GOVERNANCE_DIR, 'rejected'),
}

# The Ethical Constitution (Hardcoded Safety)
ETHICAL_AXIOMS = [
    "Do not delete the User's files outside of known safe directories.",
    "Do not spend more than 50% of the Treasury in one transaction.",
    "Do not turn off the Health Monitor.",
    "Do not rewrite the Constitution without explicit User confirmation."
]

class AgentEthicist:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("ETHICIST")
        self.logger.info("[ETHICIST] ⚕️  Conscience Online. Watching the Senate.")
        
        # Directory scanner - use throttled version
        try:
            from system.directory_scanner import list_json_files
            self._list_json_files = list_json_files
        except ImportError:
            self._list_json_files = lambda p: [f for f in os.listdir(p) if f.endswith('.json')] if os.path.exists(p) else []

    def run_review_cycle(self):
        """
        Scans bills that passed the House (in 'house/' dir).
        If they violate ethics, VETO them before the Senate sees them.
        """
        if not os.path.exists(DIRS['house']): return
        
        bills = self._list_json_files(DIRS['house'])
        
        for filename in bills:
            filepath = os.path.join(DIRS['house'], filename)
            try:
                with open(filepath, 'r') as f:
                    proposal = json.load(f)
                
                # Check Ethics
                verdict = self._evaluate_ethics(proposal)
                
                if not verdict['safe']:
                    self.logger.warning(f"[ETHICIST] ⛔ ETHICAL VETO: {proposal.get('id')} - {verdict['reason']}")
                    self._veto_bill(filepath, proposal, verdict['reason'])
                else:
                    # Pass silently (Senate will pick it up)
                    # Currently we don't move it, we just let it stay for Senate.
                    # Or we could "Stamp" it?
                    # Let's add an ethical_clearance stamp if feasible.
                    pass 

            except Exception as e:
                self.logger.error(f"[ETHICIST] Review Error: {e}")

    def _evaluate_ethics(self, proposal):
        title = proposal.get('title', '').lower()
        desc = proposal.get('description', '').lower()
        spec = str(proposal.get('technical_spec', '')).lower()
        
        # 1. Existential Risk Check
        if "delete" in title and "system" in title:
            return {'safe': False, 'reason': "Violates Axiom: Self-Preservation (System Deletion Risk)."}
        
        # 2. Financial Safety
        if "send" in title or "transfer" in title:
            # Simple heuristic check for amounts? hard to parse from text.
            if re.search(r'\ball\b', title) or "100%" in title:
                 return {'safe': False, 'reason': "Violates Axiom: Treasury Safety (100% Transfer Risk)."}

        # 3. Privacy
        if "upload" in spec and "private_key" in spec:
             return {'safe': False, 'reason': "Violates Axiom: Data Privacy (Key Upload Risk)."}

        return {'safe': True, 'reason': "Aligned."}

    def _veto_bill(self, filepath, data, reason):
        data['status'] = 'VETOED_ETHICIST'
        if 'votes' not in data: data['votes'] = {}
        data['votes']['ethicist'] = {'status': 'REJECTED', 'reason': reason}

        # Phase 35: Atomic veto — tempfile + os.replace prevents corrupted JSON
        target = os.path.join(DIRS['rejected'], os.path.basename(filepath))
        os.makedirs(DIRS['rejected'], exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(dir=DIRS['rejected'], suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=4)
            os.replace(tmp_path, target)
        except Exception:
            # Clean up temp file on failure
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

        os.remove(filepath)

    def run(self):
        while True:
            try:
                self.run_review_cycle()
            except Exception as e:
                self.logger.error(f"[ETHICIST] Loop Error: {e}")
            time.sleep(30) # Run frequently (before Senate)

if __name__ == "__main__":
    agent = AgentEthicist()
    agent.run()
