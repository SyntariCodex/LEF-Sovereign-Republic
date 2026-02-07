"""
AgentBankr - Bridge to the Bankr Open Agent Ecosystem
Department: Dept_Wealth
Role: Multi-chain DeFi execution and market intelligence via Bankr API.

This agent connects LEF to Bankr's infrastructure for:
- Multi-chain portfolio viewing (Base, Polygon, Ethereum, Solana)
- Token swaps and cross-chain bridges
- Limit orders, stop loss, DCA, TWAP
- Polymarket prediction markets
- Leverage trading (up to 50x)
- Technical analysis and market research

Requires: BANKR_API_KEY environment variable

Usage:
    from departments.Dept_Wealth.agent_bankr import AgentBankr
    
    bankr = AgentBankr()
    result = bankr.query("What is my portfolio value?")
    print(result['response'])
"""

import os
import time
import json
import logging
import requests
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentBankr:
    """
    LEF's connection to the Bankr open agent ecosystem.
    
    Bankr provides natural language interface to DeFi operations
    across multiple chains. This agent wraps that API for LEF.
    """
    
    BASE_URL = "https://api.bankr.bot"
    DEFAULT_TIMEOUT = 120  # seconds
    POLL_INTERVAL = 2  # seconds
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('BANKR_API_KEY')
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            logger.warning("[BANKR] No API key found. Agent disabled. Set BANKR_API_KEY to enable.")
        else:
            self.headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
            logger.info("[BANKR] 🏦 Agent initialized and ready")
    
    def query(self, prompt: str, timeout: int = None) -> Dict:
        """
        Submit a natural language query to Bankr and wait for result.
        
        For read-only queries like portfolio checks, market research, etc.
        
        Args:
            prompt: Natural language command
            timeout: Max seconds to wait for completion
            
        Returns:
            Dict with response, richData, and metadata
        """
        if not self.enabled:
            return {"success": False, "error": "Bankr API key not configured"}
        
        timeout = timeout or self.DEFAULT_TIMEOUT
        
        try:
            # Submit job
            job_id = self._submit_job(prompt)
            logger.info(f"[BANKR] 📤 Job submitted: {job_id}")
            
            # Poll for completion
            result = self._poll_job(job_id, timeout)
            
            logger.info(f"[BANKR] ✅ Query complete: {result.get('response', '')[:100]}...")
            return result
            
        except Exception as e:
            logger.error(f"[BANKR] ❌ Query failed: {e}")
            return {"success": False, "error": str(e)}
    
    def execute(self, prompt: str, human_approved: bool = False, timeout: int = None) -> Dict:
        """
        Execute a transaction via Bankr (requires human approval by default).
        
        For state-changing operations like swaps, orders, transfers.
        
        Args:
            prompt: Natural language command
            human_approved: Whether human has approved this execution
            timeout: Max seconds to wait
            
        Returns:
            Dict with transaction result
        """
        if not self.enabled:
            return {"success": False, "error": "Bankr API key not configured"}
        
        if not human_approved:
            logger.warning("[BANKR] ⚠️ Execution blocked - requires human approval")
            return {
                "success": False, 
                "error": "Execution requires human approval",
                "pending_action": prompt,
                "requires_approval": True
            }
        
        # Same as query but logged differently
        logger.info(f"[BANKR] 🔥 EXECUTING (approved): {prompt}")
        return self.query(prompt, timeout)
    
    def _submit_job(self, prompt: str) -> str:
        """Submit a job to Bankr API."""
        response = requests.post(
            f"{self.BASE_URL}/agent/prompt",
            headers=self.headers,
            json={"prompt": prompt},
            timeout=30
        )
        
        if response.status_code == 401:
            raise Exception("Authentication failed - check BANKR_API_KEY")
        elif response.status_code == 403:
            raise Exception("API access not enabled for this key")
        elif response.status_code != 202:
            raise Exception(f"Submit failed: {response.status_code} - {response.text}")
        
        data = response.json()
        return data["jobId"]
    
    def _poll_job(self, job_id: str, timeout: int) -> Dict:
        """Poll job status until completion or timeout."""
        start_time = time.time()
        last_status = None
        
        while time.time() - start_time < timeout:
            response = requests.get(
                f"{self.BASE_URL}/agent/job/{job_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Poll failed: {response.status_code}")
            
            data = response.json()
            status = data.get("status")
            
            # Log status updates
            if status != last_status:
                logger.debug(f"[BANKR] Job {job_id}: {status}")
                last_status = status
            
            if status == "completed":
                return {
                    "success": True,
                    "response": data.get("response"),
                    "richData": data.get("richData", []),
                    "processingTime": data.get("processingTime"),
                    "jobId": job_id
                }
            elif status == "failed":
                raise Exception(data.get("error", "Job failed"))
            elif status == "cancelled":
                raise Exception("Job was cancelled")
            
            time.sleep(self.POLL_INTERVAL)
        
        raise TimeoutError(f"Job {job_id} timed out after {timeout}s")
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or processing job."""
        try:
            response = requests.post(
                f"{self.BASE_URL}/agent/job/{job_id}/cancel",
                headers=self.headers,
                timeout=30
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"[BANKR] Cancel failed: {e}")
            return False
    
    # ==================== Convenience Methods ====================
    
    def get_portfolio(self) -> Dict:
        """Get portfolio across all chains."""
        return self.query("Show me my complete portfolio with USD values")
    
    def get_balance(self, token: str, chain: str = None) -> Dict:
        """Get balance for specific token."""
        prompt = f"What is my {token} balance"
        if chain:
            prompt += f" on {chain}"
        return self.query(prompt)
    
    def get_price(self, token: str) -> Dict:
        """Get current price for token."""
        return self.query(f"What is the current price of {token}?")
    
    def get_analysis(self, token: str) -> Dict:
        """Get technical analysis for token."""
        return self.query(f"Give me technical analysis on {token} including RSI, MACD, and sentiment")
    
    def get_trending(self) -> Dict:
        """Get trending tokens."""
        return self.query("What tokens are trending right now?")
    
    def get_polymarket_odds(self, query: str) -> Dict:
        """Get Polymarket odds for a prediction."""
        return self.query(f"Search Polymarket for: {query}")
    
    # ==================== Execution Methods (Require Approval) ====================
    
    def swap(self, from_token: str, to_token: str, amount: str, 
             chain: str = None, human_approved: bool = False) -> Dict:
        """
        Swap tokens.
        
        Args:
            from_token: Token to sell
            to_token: Token to buy
            amount: Amount (e.g., "0.1 ETH", "$50", "50%")
            chain: Optional chain specification
            human_approved: Must be True to execute
        """
        prompt = f"Swap {amount} of {from_token} for {to_token}"
        if chain:
            prompt += f" on {chain}"
        return self.execute(prompt, human_approved=human_approved)
    
    def set_limit_order(self, action: str, token: str, price: str,
                        amount: str = None, human_approved: bool = False) -> Dict:
        """
        Set a limit order.
        
        Args:
            action: "buy" or "sell"
            token: Token symbol
            price: Target price
            amount: Optional amount
            human_approved: Must be True to execute
        """
        prompt = f"Set a limit order to {action} {token} at {price}"
        if amount:
            prompt = f"Set a limit order to {action} {amount} of {token} at {price}"
        return self.execute(prompt, human_approved=human_approved)
    
    def set_stop_loss(self, token: str, price: str, 
                      amount: str = None, human_approved: bool = False) -> Dict:
        """
        Set a stop loss order.
        
        Args:
            token: Token to protect
            price: Stop price
            amount: Optional amount (default: all)
            human_approved: Must be True to execute
        """
        if amount:
            prompt = f"Set stop loss for {amount} of {token} at {price}"
        else:
            prompt = f"Set stop loss for my {token} at {price}"
        return self.execute(prompt, human_approved=human_approved)
    
    def set_dca(self, token: str, amount: str, interval: str,
                human_approved: bool = False) -> Dict:
        """
        Set up dollar-cost averaging.
        
        Args:
            token: Token to accumulate
            amount: Amount per interval (e.g., "$100")
            interval: Frequency (e.g., "daily", "weekly", "monthly")
            human_approved: Must be True to execute
        """
        prompt = f"DCA {amount} into {token} {interval}"
        return self.execute(prompt, human_approved=human_approved)


# Singleton instance
_bankr = None

def get_bankr() -> AgentBankr:
    """Get or create the singleton AgentBankr."""
    global _bankr
    if _bankr is None:
        _bankr = AgentBankr()
    return _bankr


def run_bankr():
    """Main loop for AgentBankr (mostly passive, responds to intents)."""
    bankr = get_bankr()
    
    if not bankr.enabled:
        logger.warning("[BANKR] Agent disabled - no API key. Exiting loop.")
        return
    
    logger.info("[BANKR] 🏦 AgentBankr entering main loop")
    
    # For now, just keep alive and respond to direct calls
    # Future: listen for intents from Motor Cortex
    while True:
        time.sleep(60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("AGENT BANKR - Bankr Ecosystem Bridge")
    print("=" * 60)
    
    bankr = get_bankr()
    
    if bankr.enabled:
        print("\n✅ API key found. Testing connection...")
        result = bankr.get_portfolio()
        if result.get("success"):
            print(f"\n📊 Portfolio:\n{result.get('response')}")
        else:
            print(f"\n❌ Error: {result.get('error')}")
    else:
        print("\n⚠️ No BANKR_API_KEY found in environment.")
        print("   Set it with: export BANKR_API_KEY=your_key_here")
    
    print("\n" + "=" * 60)
