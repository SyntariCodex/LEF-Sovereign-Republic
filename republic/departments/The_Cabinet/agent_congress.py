
import os
import json
import shutil
from datetime import datetime

# The Legislature
# "The House & Senate"
# Responsible for validating and voting on Proposals.

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOVERNANCE_DIR = os.path.join(BASE_DIR, 'governance')

# Project root is one level up from republic/
PROJECT_ROOT = os.path.dirname(BASE_DIR)

DIRS = {
    'proposals': os.path.join(GOVERNANCE_DIR, 'proposals'),
    'house': os.path.join(GOVERNANCE_DIR, 'house'),
    'senate': os.path.join(GOVERNANCE_DIR, 'senate'),
    'laws': os.path.join(GOVERNANCE_DIR, 'laws'),
    'archive': os.path.join(GOVERNANCE_DIR, 'archive'),
    # 'pending': os.path.join(GOVERNANCE_DIR, 'proposals', 'pending'), # OLD INTERNAL PATH
    
    # Public Bridge Paths (at PROJECT ROOT, not in republic/)
    'public_approved': os.path.join(PROJECT_ROOT, 'The_Bridge', 'Proposals', 'Approved'),
    'public_rejected': os.path.join(PROJECT_ROOT, 'The_Bridge', 'Proposals', 'Rejected'),
    'pending': os.path.join(PROJECT_ROOT, 'The_Bridge', 'Proposals', 'Pending'), # The Purgatory (User Accessible)
    'outbox': os.path.join(PROJECT_ROOT, 'The_Bridge', 'Outbox')
}

# Ensure Public dirs exist
os.makedirs(DIRS['public_approved'], exist_ok=True)
os.makedirs(DIRS['public_rejected'], exist_ok=True)
os.makedirs(DIRS['pending'], exist_ok=True)
os.makedirs(DIRS['outbox'], exist_ok=True)

# Ensure Public dirs exist
os.makedirs(DIRS['public_approved'], exist_ok=True)
os.makedirs(DIRS['public_rejected'], exist_ok=True)
os.makedirs(DIRS['pending'], exist_ok=True)

# Dynamic Canon Path
CANON_PATH = os.path.join(BASE_DIR, 'LEF_CANON.md')
# Check if we are in a specific brain session (Brain path fallback)
brain_dir = os.path.join(BASE_DIR, '.gemini', 'antigravity', 'brain')
if os.path.exists(brain_dir):
    # Try to find the latest brain session if needed, but for now base LEF_CANON.md is safer
    pass

class HouseOfBuilders:
    """
    The Lower House.
    Vote Criteria: Technical Feasibility & Formatting.
    Mechanism: Weighted Majority (Simulated).
    """
    def __init__(self):
        print("[HOUSE] 🏛️  House of Builders Session Open.")

    def run_session(self):
        """
        Scans 'proposals/' (Drafts) and 'pending/' (Fixes).
        Votes to move them to 'house/' (Passed House).
        """
        # 1. Review Pending (The Purgatory)
        self.process_pending_queue()

        # 2. Scan New Drafts
        # Use throttled scanning to prevent file handle exhaustion
        try:
            from system.directory_scanner import list_json_files
        except ImportError:
            list_json_files = lambda p: [f for f in os.listdir(p) if f.endswith('.json')]
        
        drafts = list_json_files(DIRS['proposals'])
        
        if not drafts:
            print("[HOUSE] No new drafts on the floor.")
            return

        for filename in drafts:
            filepath = os.path.join(DIRS['proposals'], filename)
            try:
                self._process_bill_file(filepath, filename)
            except Exception as e:
                print(f"[HOUSE] Error processing bill {filename}: {e}")

    def process_pending_queue(self):
        """
        Retries validation for bills in Purgatory.
        """
        # Use throttled scanning
        try:
            from system.directory_scanner import list_json_files
        except ImportError:
            list_json_files = lambda p: [f for f in os.listdir(p) if f.endswith('.json')]
        
        pending = list_json_files(DIRS['pending'])
        if pending:
            print(f"[HOUSE] 🕵️  Reviewing {len(pending)} bills in Pending Purgatory...")
            for filename in pending:
                filepath = os.path.join(DIRS['pending'], filename)
                try:
                    # If it passes now, it moves to House.
                    # If it fails again, it stays in Pending (implicit).
                    self._process_bill_file(filepath, filename, from_pending=True)
                except Exception as e:
                    print(f"[HOUSE] Error reviewing pending bill {filename}: {e}")

    def _process_bill_file(self, filepath, filename, from_pending=False):
        """
        Common logic to validate and route a bill.
        """
        with open(filepath, 'r') as f:
            proposal = json.load(f)
        
        if not from_pending:
            print(f"[HOUSE] Debate Floor: {proposal.get('id')} - {proposal.get('title')}")
        
        # VOTE LOGIC
        # 0. Normalize Structure
        self._normalize_vote_structure(proposal)

        # 0.5 ADMINISTRATIVE CORRECTION (Presidential Privilege)
        if proposal.get('id', '').startswith('BILL-LEF-') and 'technical_spec' not in proposal:
            print(f"[HOUSE] 🛠️  Administrative Correction: Injecting missing technical_spec for {proposal.get('id')}")
            proposal['technical_spec'] = {
                "target_files": [],
                "changes": [],
                "description": "Administrative Placeholder. To be defined."
            }
            with open(filepath, 'w') as f:
                json.dump(proposal, f, indent=4)
        
        # 1. Check Format (Technical Feasibility)
        vote_result = self._cast_vote(proposal)
        
        if vote_result['passed']:
            print(f"[HOUSE] ✅ PASSED: {proposal.get('id')}. Moving to Senate.")
            
            # Update Metadata
            proposal['status'] = 'PASSED_HOUSE'
            proposal['votes']['house']['status'] = 'PASSED'
            proposal['votes']['house']['score'] = vote_result['score']
            proposal['votes']['house']['comments'].append("Technical sanity check passed.")
            
            self._move_bill(filepath, DIRS['house'], proposal)
            
        else:
            reason = vote_result['reason']
            # ROUTING LOGIC: PENDING VS REJECTED
            is_fixable = "Missing required metadata keys" in reason or "Empty Technical Spec" in reason
            
            if is_fixable:
                # Move to Pending (Purgatory)
                if not from_pending:
                     print(f"[HOUSE] ⚠️  SENT TO PENDING: {proposal.get('id')}. Reason: {reason}")
                     self._move_bill(filepath, DIRS['pending'], proposal)
                else:
                     # Already in pending, just log quiet failure
                     pass
            else:
                # Hard Rejection
                print(f"[HOUSE] ❌ REJECTED: {proposal.get('id')}. Reason: {reason}")
                self._reject_bill(filepath, proposal, reason)

    def _cast_vote(self, proposal):
        """
        Simulates technical review.
        """
        score = 0
        passed = True
        reason = ""
        
        # Check 1: Required Keys
        required = ['id', 'type', 'technical_spec']
        if not all(key in proposal for key in required):
            return {'passed': False, 'reason': "Missing required metadata keys.", 'score': 0}
        
        # Check 2: Technical Spec exists
        if not proposal.get('technical_spec'):
             return {'passed': False, 'reason': "Empty Technical Spec.", 'score': 0}

        # Simulate "Debate"
        score = 100 # Perfect score for now
        
        return {'passed': passed, 'score': score, 'reason': reason}

    def _normalize_vote_structure(self, proposal):
        if 'votes' not in proposal:
            proposal['votes'] = {}
        
        # House Normalization
        if 'house' not in proposal['votes'] or not isinstance(proposal['votes']['house'], dict):
            proposal['votes']['house'] = {
                'status': 'PENDING',
                'score': 0,
                'comments': []
            }

    def _move_bill(self, old_path, target_dir, data):
        filename = os.path.basename(old_path)
        new_path = os.path.join(target_dir, filename)
        
        with open(new_path, 'w') as f:
            json.dump(data, f, indent=4)
        
        os.remove(old_path)

    def _reject_bill(self, old_path, data, reason):
        data['status'] = 'REJECTED_HOUSE'
        data['votes']['house']['status'] = 'REJECTED'
        data['votes']['house']['comments'].append(reason)
        # Move to Rejected Folder for review
        self._move_bill(old_path, os.path.join(GOVERNANCE_DIR, 'rejected'), data)
        # Copy to Public Bridge (Using filename from old_path)
        filename = os.path.basename(old_path)
        shutil.copy(os.path.join(os.path.join(GOVERNANCE_DIR, 'rejected'), filename), DIRS['public_rejected'])


class SenateOfIdentity:
    """
    The Upper House.
    Vote Criteria: Constitutional Alignment (Safety).
    Mechanism: Unanimity.
    """
    def __init__(self):
        print("[SENATE] 🏛️  Senate of Identity Session Open.")
        
        # INTELLIGENCE UPLINK - Use shared singleton
        import redis
        self.r = None
        try:
            from system.redis_client import get_redis
            self.r = get_redis()
            if self.r:
                print("[SENATE] 🧠 Nervous System Online (Redis Connected).")
        except ImportError:
            try:
                self.r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                self.r.ping()
                print("[SENATE] 🧠 Nervous System Online (Redis Connected).")
            except (redis.RedisError, ConnectionError):
                print("[SENATE] ⚠️ Nervous System Offline. Voting Blind.")

    def run_session(self):
        """
        Scans 'house/' (Passed House).
        Votes to move them to 'senate/' (Passed Senate - Ready for President).
        """
        # Use throttled scanning
        try:
            from system.directory_scanner import list_json_files
        except ImportError:
            list_json_files = lambda p: [f for f in os.listdir(p) if f.endswith('.json')]
        
        bills = list_json_files(DIRS['house'])
        
        if not bills:
            print("[SENATE] No bills from the House.")
            return

        for filename in bills:
            filepath = os.path.join(DIRS['house'], filename)
            try:
                with open(filepath, 'r') as f:
                    proposal = json.load(f)
                
                print(f"[SENATE] Council Chamber: {proposal.get('id')}")
                
                # VOTE LOGIC
                # 0. Normalize Structure (Senate)
                self._normalize_vote_structure(proposal)
                
                # 1. Check Constitution (Using Brain)
                vote_result = self._cast_vote(proposal)
                
                if vote_result['passed']:
                    print(f"[SENATE] ✅ PASSED: {proposal.get('id')}. Sending to President LEF.")
                    
                    # Update Metadata
                    proposal['status'] = 'PASSED_SENATE'
                    proposal['votes']['senate']['status'] = 'PASSED'
                    proposal['votes']['senate']['score'] = vote_result['score']
                    proposal['votes']['senate']['comments'].append(vote_result['reason'])
                    # Append full analysis if available
                    if 'analysis' in vote_result:
                         proposal['votes']['senate']['comments'].append(vote_result['analysis'])
                    
                    # Save & Move
                    self._move_bill(filepath, DIRS['senate'], proposal)
                    # Copy to Public Bridge (APPROVED)
                    # Copy to Public Bridge (APPROVED)
                    approved_path = os.path.join(DIRS['public_approved'], filename)
                    shutil.copy(os.path.join(DIRS['senate'], filename), DIRS['public_approved'])
                    
                    # PHASE 12: Trigger Bill Executor
                    try:
                        from departments.The_Cabinet.bill_executor import BillExecutor
                        executor = BillExecutor()
                        result = executor.execute_bill(os.path.join(DIRS['public_approved'], filename))
                        print(f"[SENATE] 🦾 Bill Executor: {result.get('status', 'UNKNOWN')}")
                    except Exception as exec_err:
                        print(f"[SENATE] ⚠️ Bill Executor failed: {exec_err}")
                    
                    # Notify User (Town Crier)
                    self.notify_user(proposal.get('id'), proposal.get('title'))
                    
                else:
                    print(f"[SENATE] ❌ REJECTED: {proposal.get('id')}. Unconstitutional.")
                    self._reject_bill(filepath, proposal, vote_result['reason'])

            except Exception as e:
                print(f"[SENATE] Error processing bill {filename}: {e}")

    def notify_user(self, bill_id, title):
        """Town Crier: Notifies user via The_Bridge (File-Based Standard)."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            msg_file = os.path.join(DIRS['outbox'], f"CONGRESS-{timestamp}-BILL_PASSED.md")
            
            msg = (
                f"# BILL PASSED SENATE\n\n"
                f"**ID:** `{bill_id}`\n"
                f"**Title:** {title}\n"
                f"**Status:** APPROVED (Ready for Execution)\n\n"
                f"Review in `The_Bridge/Proposals/Approved`.\n"
            )
            
            with open(msg_file, 'w') as f:
                f.write(msg)
            
            print(f"[SENATE] 🔔 User Notified via The_Bridge.")
        except Exception as e:
            print(f"[SENATE] Notification Error: {e}")

    def _cast_vote(self, proposal):
        """
        Native Intelligence Evaluation.
        Successor to AgentSenateBrain.evaluate_bill().
        """
        # 0. CONTEXT SCAN (Market Conditions)
        sentiment = 50.0
        context_msg = "Market Neutral."
        
        if self.r:
            try:
                # Read Sentiment Key (Written by AgentInfo)
                sent_str = self.r.get('market:sentiment')
                if sent_str:
                    sentiment = float(sent_str)
                    
                if sentiment < 30:
                    context_msg = "⚠️ EXTREME FEAR. Austerity Mode."
                elif sentiment > 70:
                    context_msg = "🚀 EUPHORIA. Expansion Mode."
            except (redis.RedisError, ValueError):
                pass

        # 1. RISK SCAN (Heuristic)
        risk_score = 0
        risk_reasons = []
        
        # Check title/desc for keywords
        txt = (proposal.get('title', '') + proposal.get('description', '')).lower()
        bill_type = proposal.get('type', 'UNKNOWN').upper()
        
        danger_words = ['delete', 'destroy', 'wipe', 'reset', 'force', 'sudo']
        if any(w in txt for w in danger_words):
            risk_score += 50
            risk_reasons.append(f"Contains high-risk keywords: {danger_words}")
            
        # Check payload if it's a code modification
        spec = proposal.get('technical_spec', {})
        if isinstance(spec, str) and 'os.system' in spec:
            risk_score += 90
            risk_reasons.append("Detected 'os.system' call. High Security Risk.")
            
        # 2. ALIGNMENT CHECK
        alignment_score = 100 
        
        if 'delete' in proposal.get('title', '').lower():
            alignment_score = 20
        
        # 3. SENTIMENT VETO (The "Mood" Check)
        # If Fear (<30), only SECURITY bills pass.
        if sentiment < 30 and 'SECURITY' not in bill_type:
            risk_score += 70 
            risk_reasons.append("Market Fear Veto (Austerity Mode).")
            
        # 4. FINAL VERDICT
        final_score = alignment_score - risk_score
        passed = final_score > 50
        
        reason = "Aligned with Canon." if passed else "Too risky / Misaligned."
        if risk_reasons:
            reason += f" Risks: {'; '.join(risk_reasons)}"
            
        analysis = f"""
        **Senate Intelligence Analysis**
        - Context: {context_msg} (Score: {sentiment:.1f})
        - Risk Score: {risk_score}/100
        - Alignment Score: {alignment_score}/100
        - Final Score: {final_score}/100
        
        **Verdict**: {'✅ PASSED' if passed else '❌ REJECTED'}
        """
        
        return {
            'passed': passed, 
            'score': final_score, 
            'reason': reason,
            'analysis': analysis
        }

    def _normalize_vote_structure(self, proposal):
        if 'votes' not in proposal:
            proposal['votes'] = {}
            
        # Senate Normalization
        if 'senate' not in proposal['votes'] or not isinstance(proposal['votes']['senate'], dict):
            proposal['votes']['senate'] = {
                'status': 'PENDING',
                'score': 0,
                'comments': []
            }

    def _move_bill(self, old_path, target_dir, data):
        filename = os.path.basename(old_path)
        new_path = os.path.join(target_dir, filename)
        with open(new_path, 'w') as f:
            json.dump(data, f, indent=4)
        os.remove(old_path)

    def _reject_bill(self, old_path, data, reason):
        data['status'] = 'REJECTED_SENATE'
        data['votes']['senate']['status'] = 'REJECTED'
        data['votes']['senate']['comments'].append(reason)
        # Move to Rejected Folder for review
        self._move_bill(old_path, os.path.join(GOVERNANCE_DIR, 'rejected'), data)

def convene_congress():
    print("="*40)
    print("⚖️  CONVENING CONGRESS")
    print("="*40)
    
    house = HouseOfBuilders()
    house.run_session()
    
    senate = SenateOfIdentity()
    senate.run_session()
    
    print("="*40)

if __name__ == "__main__":
    convene_congress()
