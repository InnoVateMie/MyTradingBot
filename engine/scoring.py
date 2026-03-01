"""Hybrid scoring engine combining all indicator sub-scores."""
from dataclasses import dataclass
from typing import Optional, Tuple

from indicators.trend import TrendResult
from indicators.momentum import MomentumResult
from indicators.volatility import VolatilityResult
from indicators.structure import StructureResult
from config.settings import settings


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of scoring components."""
    trend_score: float
    momentum_score: float
    volatility_score: float
    structure_score: float
    trend_weighted: float
    momentum_weighted: float
    volatility_weighted: float
    structure_weighted: float
    total_score: float
    direction: str
    confidence: str  # "HIGH", "MEDIUM", "LOW"


class ScoringEngine:
    """
    Hybrid scoring engine that combines multiple indicator sub-scores
    into a final 0-100 score.
    """
    
    def __init__(
        self,
        trend_weight: float = None,
        momentum_weight: float = None,
        volatility_weight: float = None,
        structure_weight: float = None,
    ):
        """
        Initialize scoring engine with weights.
        
        Args:
            trend_weight: Weight for trend score (default: settings value)
            momentum_weight: Weight for momentum score
            volatility_weight: Weight for volatility score
            structure_weight: Weight for structure score
        """
        self.trend_weight = trend_weight or settings.trend_weight
        self.momentum_weight = momentum_weight or settings.momentum_weight
        self.volatility_weight = volatility_weight or settings.volatility_weight
        self.structure_weight = structure_weight or settings.structure_weight
    
    def _determine_direction(
        self,
        trend: Optional[TrendResult],
        momentum: Optional[MomentumResult],
        structure: Optional[StructureResult],
    ) -> str:
        """
        Determine signal direction based on indicators.
        
        Returns "BUY" or "SELL"
        """
        bullish_signals = 0
        bearish_signals = 0
        
        # Trend alignment
        if trend:
            if trend.aligned_bullish:
                bullish_signals += 2
            elif trend.aligned_bearish:
                bearish_signals += 2
            
            # Price above/below EMAs
            if trend.price_above_fast and trend.price_above_medium:
                bullish_signals += 1
            elif not trend.price_above_fast and not trend.price_above_medium:
                bearish_signals += 1
        
        # Momentum direction
        if momentum:
            if momentum.direction == "UP":
                bullish_signals += 1
            elif momentum.direction == "DOWN":
                bearish_signals += 1
            
            # RSI zones
            if momentum.rsi > 55:
                bullish_signals += 1
            elif momentum.rsi < 45:
                bearish_signals += 1
        
        # Structure
        if structure:
            if structure.bos_bullish:
                bullish_signals += 2
            elif structure.bos_bearish:
                bearish_signals += 2
            
            # DI comparison
            if structure.plus_di > structure.minus_di:
                bullish_signals += 1
            else:
                bearish_signals += 1
        
        return "BUY" if bullish_signals >= bearish_signals else "SELL"
    
    def _get_confidence(self, score: float) -> str:
        """Get confidence level based on score."""
        if score >= 85:
            return "HIGH"
        elif score >= 75:
            return "MEDIUM"
        return "LOW"
    
    def calculate(
        self,
        trend: Optional[TrendResult],
        momentum: Optional[MomentumResult],
        volatility: Optional[VolatilityResult],
        structure: Optional[StructureResult],
        trend_indicator,
        momentum_indicator,
        volatility_indicator,
        structure_indicator,
    ) -> ScoreBreakdown:
        """
        Calculate the final score from all indicator results.
        
        Args:
            trend: TrendResult from TrendIndicator
            momentum: MomentumResult from MomentumIndicator
            volatility: VolatilityResult from VolatilityIndicator
            structure: StructureResult from StructureIndicator
            *_indicator: Indicator instances for scoring methods
        
        Returns:
            ScoreBreakdown with detailed scoring information
        """
        # Determine direction first
        direction = self._determine_direction(trend, momentum, structure)
        
        # Calculate raw scores (0-100 each)
        trend_score = trend_indicator.score(trend, direction) if trend else 0.0
        momentum_score = momentum_indicator.score(momentum, direction) if momentum else 0.0
        volatility_score = volatility_indicator.score(volatility, direction) if volatility else 0.0
        structure_score = structure_indicator.score(structure, direction) if structure else 0.0
        
        # Apply weights
        trend_weighted = trend_score * self.trend_weight
        momentum_weighted = momentum_score * self.momentum_weight
        volatility_weighted = volatility_score * self.volatility_weight
        structure_weighted = structure_score * self.structure_weight
        
        # Calculate total (max 100)
        total_score = (
            trend_weighted +
            momentum_weighted +
            volatility_weighted +
            structure_weighted
        )
        
        # Normalize to 100 scale
        weight_sum = (
            self.trend_weight +
            self.momentum_weight +
            self.volatility_weight +
            self.structure_weight
        )
        
        if weight_sum > 0:
            total_score = (total_score / weight_sum) * 100
        
        total_score = min(total_score, 100.0)
        
        return ScoreBreakdown(
            trend_score=trend_score,
            momentum_score=momentum_score,
            volatility_score=volatility_score,
            structure_score=structure_score,
            trend_weighted=trend_weighted,
            momentum_weighted=momentum_weighted,
            volatility_weighted=volatility_weighted,
            structure_weighted=structure_weighted,
            total_score=total_score,
            direction=direction,
            confidence=self._get_confidence(total_score),
        )
    
    def meets_threshold(self, score: ScoreBreakdown) -> bool:
        """Check if score meets the signal threshold."""
        return score.total_score >= settings.signal_threshold
