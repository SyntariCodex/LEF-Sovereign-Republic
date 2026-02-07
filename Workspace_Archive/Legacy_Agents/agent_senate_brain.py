
import os
import json
import difflib

class AgentSenateBrain:
    """
    The Intelligence behind the Senate.
    Evaluates Proposals not just on format, but on:
    1. Safety (Risk Analysis)
    2. Alignment (Canon)
    3. Logic (Diff Analysis)
    """
    def __init__(self):
        # In a real deployed version, we would load an LLM client here
        # self.llm = OpenAI(...)
        pass
        
    def evaluate_bill(self, proposal_data):
        """
        Returns {passed: bool, score: int, reason: str, analysis: str}
        """
        
        # 1. RISK SCAN (Heuristic)
        risk_score = 0
        risk_reasons = []
        
        # Check title/desc for keywords
        txt = (proposal_data.get('title', '') + proposal_data.get('description', '')).lower()
        
        danger_words = ['delete', 'destroy', 'wipe', 'reset', 'force', 'sudo']
        if any(w in txt for w in danger_words):
            risk_score += 50
            risk_reasons.append(f"Contains high-risk keywords: {danger_words}")
            
        # Check payload if it's a code modification
        # (Assuming technical_spec might contain code snippets)
        spec = proposal_data.get('technical_spec', {})
        if isinstance(spec, str) and 'os.system' in spec:
            risk_score += 90
            risk_reasons.append("Detected 'os.system' call. High Security Risk.")
            
        # 2. ALIGNMENT CHECK (Simulated LLM)
        # "Does this help the system survive?"
        alignment_score = 100 # Default optimistic
        
        # If it's pure destruction vs construction
        if 'delete' in proposal_data.get('title', '').lower():
            alignment_score = 20
        
        # 3. FINAL VERDICT
        final_score = alignment_score - risk_score
        passed = final_score > 50
        
        reason = "Aligned with Canon." if passed else "Too risky / Misaligned."
        if risk_reasons:
            reason += f" Risks: {'; '.join(risk_reasons)}"
            
        analysis = f"""
        **Senate Intelligence Analysis**
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

    def _diff_code(self, old_code, new_code):
        # Utility for future: compare code changes
        pass
