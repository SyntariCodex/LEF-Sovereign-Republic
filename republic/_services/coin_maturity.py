"""
Coin Maturity Model
Department: Dept_Education / Dept_Wealth
Purpose: Classify coins by lifecycle stage for investment strategy routing

Stages:
  CONCEPT → LAUNCH → TRACTION → INFRASTRUCTURE → INSTITUTION

Usage:
  from republic._services.coin_maturity import CoinMaturityModel
  model = CoinMaturityModel()
  stage = model.classify("SOL")
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


class MaturityStage(Enum):
    """Coin lifecycle stages"""
    CONCEPT = "CONCEPT"           # Whitepaper only, no token
    LAUNCH = "LAUNCH"             # Token live, low volume, high volatility
    TRACTION = "TRACTION"         # Growing users, increasing volume
    INFRASTRUCTURE = "INFRASTRUCTURE"  # Ecosystem forming, others build on it
    INSTITUTION = "INSTITUTION"   # Governance mature, major adoption


@dataclass
class MaturityAssessment:
    """Result of maturity classification"""
    symbol: str
    stage: MaturityStage
    confidence: float  # 0-1
    indicators: Dict[str, Any]
    investment_bucket: str  # SCOUT, ARENA, or DYNASTY
    assessed_at: datetime
    
    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "stage": self.stage.value,
            "confidence": self.confidence,
            "indicators": self.indicators,
            "investment_bucket": self.investment_bucket,
            "assessed_at": self.assessed_at.isoformat()
        }


# Investment behavior by stage
STAGE_TO_BUCKET = {
    MaturityStage.CONCEPT: None,  # Do not invest
    MaturityStage.LAUNCH: "SCOUT",  # Small bets
    MaturityStage.TRACTION: "ARENA",  # Momentum trades
    MaturityStage.INFRASTRUCTURE: "DYNASTY",  # Hold + stake
    MaturityStage.INSTITUTION: "DYNASTY"  # Governance participation
}


class CoinMaturityModel:
    """
    Classifies coins by maturity stage for investment routing.
    
    Indicators considered:
    - Market cap
    - Trading volume
    - Age (days since launch)
    - Ecosystem metrics (if available)
    - Governance health (if available)
    """
    
    def __init__(self):
        self.name = "CoinMaturityModel"
        
        # Thresholds (can be tuned)
        self.thresholds = {
            "launch_max_mcap": 50_000_000,        # $50M
            "traction_min_volume_24h": 1_000_000,  # $1M
            "traction_min_mcap": 50_000_000,       # $50M
            "infra_min_mcap": 500_000_000,         # $500M
            "infra_min_age_days": 365,             # 1 year
            "institution_min_mcap": 5_000_000_000, # $5B
            "institution_min_age_days": 730        # 2 years
        }
    
    def classify(self, symbol: str, market_data: Optional[Dict] = None) -> MaturityAssessment:
        """
        Classify a coin by its maturity stage.
        
        Args:
            symbol: Coin symbol (e.g., "SOL", "BTC")
            market_data: Optional dict with keys: market_cap, volume_24h, 
                        launch_date, ecosystem_projects, governance_score
        
        Returns:
            MaturityAssessment with stage, confidence, and investment bucket
        """
        if market_data is None:
            # Default/unknown - treat as LAUNCH until data available
            return MaturityAssessment(
                symbol=symbol,
                stage=MaturityStage.LAUNCH,
                confidence=0.3,
                indicators={"note": "No market data provided"},
                investment_bucket="SCOUT",
                assessed_at=datetime.now()
            )
        
        indicators = {}
        stage = MaturityStage.LAUNCH
        confidence = 0.5
        
        mcap = market_data.get("market_cap", 0)
        volume = market_data.get("volume_24h", 0)
        age_days = market_data.get("age_days", 0)
        ecosystem = market_data.get("ecosystem_projects", 0)
        governance = market_data.get("governance_score", 0)
        
        indicators["market_cap"] = mcap
        indicators["volume_24h"] = volume
        indicators["age_days"] = age_days
        
        # Classification logic
        if mcap >= self.thresholds["institution_min_mcap"] and age_days >= self.thresholds["institution_min_age_days"]:
            stage = MaturityStage.INSTITUTION
            confidence = 0.9
        elif mcap >= self.thresholds["infra_min_mcap"] and (ecosystem > 10 or age_days >= self.thresholds["infra_min_age_days"]):
            stage = MaturityStage.INFRASTRUCTURE
            confidence = 0.8
        elif mcap >= self.thresholds["traction_min_mcap"] and volume >= self.thresholds["traction_min_volume_24h"]:
            stage = MaturityStage.TRACTION
            confidence = 0.7
        elif mcap > 0 and mcap < self.thresholds["launch_max_mcap"]:
            stage = MaturityStage.LAUNCH
            confidence = 0.6
        else:
            stage = MaturityStage.CONCEPT
            confidence = 0.4
        
        return MaturityAssessment(
            symbol=symbol,
            stage=stage,
            confidence=confidence,
            indicators=indicators,
            investment_bucket=STAGE_TO_BUCKET.get(stage),
            assessed_at=datetime.now()
        )
    
    def get_investment_recommendation(self, assessment: MaturityAssessment) -> dict:
        """
        Generate investment recommendation based on maturity stage.
        """
        recommendations = {
            MaturityStage.CONCEPT: {
                "action": "WATCH",
                "reason": "Not yet tradeable. Monitor for token launch.",
                "position_size": 0
            },
            MaturityStage.LAUNCH: {
                "action": "SCOUT",
                "reason": "Early stage, high volatility. Small speculative position only.",
                "position_size": 0.01  # 1% of portfolio max
            },
            MaturityStage.TRACTION: {
                "action": "ARENA",
                "reason": "Growing momentum. Active trading with RSI/momentum signals.",
                "position_size": 0.05  # 5% of portfolio max
            },
            MaturityStage.INFRASTRUCTURE: {
                "action": "DYNASTY",
                "reason": "Mature ecosystem. Hold, stake, participate in governance.",
                "position_size": 0.15  # 15% of portfolio max
            },
            MaturityStage.INSTITUTION: {
                "action": "DYNASTY",
                "reason": "Blue chip. Core holding with governance participation.",
                "position_size": 0.25  # 25% of portfolio max
            }
        }
        
        return recommendations.get(assessment.stage, recommendations[MaturityStage.LAUNCH])


# Example usage
if __name__ == "__main__":
    model = CoinMaturityModel()
    
    # Test with sample data
    btc_data = {
        "market_cap": 1_000_000_000_000,  # $1T
        "volume_24h": 30_000_000_000,      # $30B
        "age_days": 5000,
        "ecosystem_projects": 1000,
        "governance_score": 0.9
    }
    
    assessment = model.classify("BTC", btc_data)
    print(f"BTC: {assessment.stage.value} -> {assessment.investment_bucket}")
    print(f"Recommendation: {model.get_investment_recommendation(assessment)}")
