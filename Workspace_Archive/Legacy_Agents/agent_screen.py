
class AgentScreen:
    """
    A class to represent the safety screening agent.
    
    This agent provides a safety score (0-100) based on various token metrics.
    """

    def __init__(self):
        """
        Initializes the AgentScreen.
        """
        # Configuration or thresholds could be set here in a real implementation
        pass

    def check_safety(self, symbol: str) -> float:
        """
        Calculates the safety score (0-100) for a given token symbol.

        For this initial implementation, the checks are mocked.

        Args:
            symbol: The ticker symbol of the token to check (e.g., 'ETH').

        Returns:
            A float representing the safety score (0.0 to 100.0).
        """
        
        # --- Mocked Safety Checks ---
        score = 100.0  # Start with a perfect score

        # 1. Liquidity Locked Check (e.g., reduces score if low or unlocked)
        # Mock assumption: If symbol is 'SCAM', liquidity is unlocked (high risk).
        if symbol.upper() == "SCAM":
            print(f"[{symbol}] Check: Liquidity Locked -> FAILED (Mocked)")
            score -= 40.0
        else:
            print(f"[{symbol}] Check: Liquidity Locked -> PASSED (Mocked)")
            
        # 2. Mintable Disabled Check (e.g., reduces score if tokens can be infinitely minted)
        # Mock assumption: If symbol contains 'MINT', minting is enabled.
        if "MINT" in symbol.upper():
            print(f"[{symbol}] Check: Mintable Disabled -> FAILED (Mocked)")
            score -= 30.0
        else:
            print(f"[{symbol}] Check: Mintable Disabled -> PASSED (Mocked)")

        # 3. Top Holder % Check (e.g., reduces score if a single wallet holds too much)
        # Mock assumption: If symbol contains 'WHALE', top holder percentage is too high.
        if "WHALE" in symbol.upper():
            print(f"[{symbol}] Check: Top Holder % -> FAILED (Mocked)")
            score -= 15.0
        else:
            print(f"[{symbol}] Check: Top Holder % -> PASSED (Mocked)")
            
        # Ensure the score is within 0-100 bounds
        final_score = max(0.0, min(100.0, score))

        return final_score

if __name__ == '__main__':
    # Example Usage for testing purposes
    agent = AgentScreen()
    
    # High Score Example
    safe_score = agent.check_safety("SAFE")
    print(f"\nSafety Score for SAFE: {safe_score:.2f}/100\n")

    # Low Score Example (Fails Liquidity, Fails Mintable)
    risky_score = agent.check_safety("SCAM_MINT")
    print(f"\nSafety Score for SCAM_MINT: {risky_score:.2f}/100\n")
    
    # Medium Score Example (Fails Top Holder)
    whale_score = agent.check_safety("TOKEN_WHALE")
    print(f"\nSafety Score for TOKEN_WHALE: {whale_score:.2f}/100\n")
