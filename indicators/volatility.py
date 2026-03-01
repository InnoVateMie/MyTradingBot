"""Volatility indicators: ATR, range expansion."""
from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import pandas as pd
from ta.volatility import AverageTrueRange

from data.candle_builder import Candle
from config.settings import settings


@dataclass
class VolatilityResult:
    """Result of volatility analysis."""
    atr: float  # Current ATR value
    atr_ratio: float  # Current ATR / Average ATR (expansion indicator)
    range_current: float  # Current candle range (high - low)
    range_average: float  # Average candle range
    range_expansion: float  # Current range / Average range
    is_expanding: bool  # True if volatility is increasing


class VolatilityIndicator:
    """Calculates volatility indicators from candle data."""
    
    def __init__(
        self,
        atr_period: int = None,
        atr_average_lookback: int = 20,
        range_lookback: int = 20,
    ):
        """
        Initialize volatility indicator.
        
        Args:
            atr_period: ATR period (default: settings.atr_period)
            atr_average_lookback: Periods to average ATR for comparison
            range_lookback: Periods to average range for comparison
        """
        self.atr_period = atr_period or settings.atr_period
        self.atr_average_lookback = atr_average_lookback
        self.range_lookback = range_lookback
    
    def calculate(self, candles: List[Candle]) -> Optional[VolatilityResult]:
        """
        Calculate volatility indicators from candles.
        
        Args:
            candles: List of Candle objects (oldest first)
        
        Returns:
            VolatilityResult or None if not enough data
        """
        min_candles = max(self.atr_period + self.atr_average_lookback, self.range_lookback)
        if len(candles) < min_candles:
            return None
        
        # Create DataFrame for ta library
        df = pd.DataFrame({
            'high': [c.high for c in candles],
            'low': [c.low for c in candles],
            'close': [c.close for c in candles],
        })
        
        # Calculate ATR
        atr_indicator = AverageTrueRange(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=self.atr_period,
        )
        atr_series = atr_indicator.average_true_range()
        
        # Get current and average ATR
        atr_current = atr_series.iloc[-1]
        atr_recent = atr_series.iloc[-self.atr_average_lookback:]
        atr_average = atr_recent.mean()
        
        # ATR ratio (expansion indicator)
        atr_ratio = atr_current / atr_average if atr_average > 0 else 1.0
        
        # Calculate candle ranges
        ranges = [c.high - c.low for c in candles]
        range_current = ranges[-1]
        range_recent = ranges[-self.range_lookback:]
        range_average = np.mean(range_recent)
        
        # Range expansion
        range_expansion = range_current / range_average if range_average > 0 else 1.0
        
        # Determine if volatility is expanding
        is_expanding = atr_ratio > 1.1 or range_expansion > 1.1
        
        return VolatilityResult(
            atr=atr_current,
            atr_ratio=atr_ratio,
            range_current=range_current,
            range_average=range_average,
            range_expansion=range_expansion,
            is_expanding=is_expanding,
        )
    
    def score(self, result: VolatilityResult, direction: str) -> float:
        """
        Calculate volatility score (0-100).
        
        Higher volatility is generally better for short-term trades
        as it provides clearer price movements.
        
        Args:
            result: VolatilityResult from calculate()
            direction: "BUY" or "SELL" (not used for volatility)
        
        Returns:
            Score from 0 to 100
        """
        if result is None:
            return 0.0
        
        score = 0.0
        
        # ATR expansion ratio (50 points max)
        # > 1.3 = very high volatility (ideal)
        # > 1.1 = moderate expansion (good)
        # > 1.0 = normal (acceptable)
        # < 0.9 = contracting (not ideal)
        if result.atr_ratio > 1.3:
            score += 50.0
        elif result.atr_ratio > 1.2:
            score += 40.0
        elif result.atr_ratio > 1.1:
            score += 30.0
        elif result.atr_ratio > 1.0:
            score += 20.0
        elif result.atr_ratio > 0.9:
            score += 10.0
        
        # Range expansion (50 points max)
        if result.range_expansion > 1.5:
            score += 50.0
        elif result.range_expansion > 1.3:
            score += 40.0
        elif result.range_expansion > 1.1:
            score += 30.0
        elif result.range_expansion > 1.0:
            score += 20.0
        elif result.range_expansion > 0.8:
            score += 10.0
        
        return min(score, 100.0)
