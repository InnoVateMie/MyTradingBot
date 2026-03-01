"""Dynamic expiry selection based on market conditions."""
from dataclasses import dataclass
from typing import Optional

from indicators.volatility import VolatilityResult
from indicators.structure import StructureResult
from engine.scoring import ScoreBreakdown


@dataclass
class ExpiryRecommendation:
    """Recommended expiry with reasoning."""
    seconds: int
    label: str  # "5s", "10s", "15s", "30s", "1m"
    reason: str


class ExpirySelector:
    """
    Selects optimal expiry duration based on market conditions.
    
    Higher volatility + strong trend = shorter expiry (momentum carry)
    Lower volatility + structure play = longer expiry (need time to develop)
    """
    
    # Available expiry options
    EXPIRY_OPTIONS = [5, 10, 15, 30, 60]
    
    def __init__(self):
        """Initialize expiry selector."""
        pass
    
    def _get_label(self, seconds: int) -> str:
        """Get human-readable label for expiry."""
        if seconds >= 60:
            return f"{seconds // 60}m"
        return f"{seconds}s"
    
    def select(
        self,
        volatility: Optional[VolatilityResult],
        structure: Optional[StructureResult],
        score: ScoreBreakdown,
    ) -> ExpiryRecommendation:
        """
        Select optimal expiry based on market conditions.
        
        Args:
            volatility: VolatilityResult from indicator
            structure: StructureResult from indicator
            score: ScoreBreakdown from scoring engine
        
        Returns:
            ExpiryRecommendation with seconds and reasoning
        """
        # Default to 30 seconds
        expiry = 30
        reason = "Default moderate expiry"
        
        # High confidence + high volatility = short expiry
        if score.confidence == "HIGH" and volatility and volatility.atr_ratio > 1.3:
            expiry = 5
            reason = "High confidence with high volatility - quick momentum play"
        
        # Strong trend with volatility expansion
        elif (
            structure and 
            structure.adx >= 30 and 
            volatility and 
            volatility.atr_ratio > 1.2
        ):
            expiry = 10
            reason = "Strong trend with expanding volatility"
        
        # Moderate trend strength
        elif structure and 25 <= structure.adx < 30:
            if volatility and volatility.atr_ratio > 1.1:
                expiry = 15
                reason = "Moderate trend with some volatility"
            else:
                expiry = 30
                reason = "Moderate trend, normal volatility"
        
        # Break of structure detected
        elif structure and (structure.bos_bullish or structure.bos_bearish):
            if volatility and volatility.atr_ratio > 1.2:
                expiry = 10
                reason = "Break of structure with momentum"
            else:
                expiry = 30
                reason = "Break of structure, waiting for follow-through"
        
        # Pullback play (structure trade)
        elif structure and structure.pullback_valid:
            expiry = 60
            reason = "Pullback validation - structure trade needs time"
        
        # Low volatility environment
        elif volatility and volatility.atr_ratio < 0.9:
            expiry = 60
            reason = "Low volatility - needs more time to develop"
        
        # Medium confidence
        elif score.confidence == "MEDIUM":
            expiry = 30
            reason = "Medium confidence setup"
        
        # Lower confidence
        elif score.confidence == "LOW":
            expiry = 60
            reason = "Lower confidence - allow more time"
        
        return ExpiryRecommendation(
            seconds=expiry,
            label=self._get_label(expiry),
            reason=reason,
        )
