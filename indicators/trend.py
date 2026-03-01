"""Trend indicators: EMA, slope, alignment detection."""
from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import pandas as pd
from ta.trend import EMAIndicator

from data.candle_builder import Candle
from config.settings import settings


@dataclass
class TrendResult:
    """Result of trend analysis."""
    ema_fast: float  # EMA 20
    ema_medium: float  # EMA 50
    ema_slow: float  # EMA 200
    slope_fast: float  # Slope of EMA 20
    slope_medium: float  # Slope of EMA 50
    slope_slow: float  # Slope of EMA 200
    aligned_bullish: bool  # EMA 20 > 50 > 200
    aligned_bearish: bool  # EMA 20 < 50 < 200
    price_above_fast: bool
    price_above_medium: bool
    price_above_slow: bool
    current_price: float


class TrendIndicator:
    """Calculates trend indicators from candle data."""
    
    def __init__(
        self,
        fast_period: int = None,
        medium_period: int = None,
        slow_period: int = None,
        slope_lookback: int = 5,
    ):
        """
        Initialize trend indicator.
        
        Args:
            fast_period: Fast EMA period (default: settings.ema_fast_period)
            medium_period: Medium EMA period (default: settings.ema_medium_period)
            slow_period: Slow EMA period (default: settings.ema_slow_period)
            slope_lookback: Number of periods for slope calculation
        """
        self.fast_period = fast_period or settings.ema_fast_period
        self.medium_period = medium_period or settings.ema_medium_period
        self.slow_period = slow_period or settings.ema_slow_period
        self.slope_lookback = slope_lookback
    
    def _calculate_slope(self, values: np.ndarray, lookback: int) -> float:
        """Calculate slope of a series over lookback period."""
        if len(values) < lookback:
            return 0.0
        
        recent = values[-lookback:]
        x = np.arange(len(recent))
        
        # Linear regression slope
        if len(recent) < 2:
            return 0.0
        
        slope, _ = np.polyfit(x, recent, 1)
        return float(slope)
    
    def calculate(self, candles: List[Candle]) -> Optional[TrendResult]:
        """
        Calculate trend indicators from candles.
        
        Args:
            candles: List of Candle objects (oldest first)
        
        Returns:
            TrendResult or None if not enough data
        """
        if len(candles) < self.slow_period:
            return None
        
        # Extract close prices
        closes = pd.Series([c.close for c in candles])
        current_price = candles[-1].close
        
        # Calculate EMAs using ta library
        ema_fast = EMAIndicator(closes, window=self.fast_period).ema_indicator()
        ema_medium = EMAIndicator(closes, window=self.medium_period).ema_indicator()
        ema_slow = EMAIndicator(closes, window=self.slow_period).ema_indicator()
        
        # Get latest values
        ema_fast_val = ema_fast.iloc[-1]
        ema_medium_val = ema_medium.iloc[-1]
        ema_slow_val = ema_slow.iloc[-1]
        
        # Calculate slopes
        slope_fast = self._calculate_slope(ema_fast.dropna().values, self.slope_lookback)
        slope_medium = self._calculate_slope(ema_medium.dropna().values, self.slope_lookback)
        slope_slow = self._calculate_slope(ema_slow.dropna().values, self.slope_lookback)
        
        # Check alignment
        aligned_bullish = ema_fast_val > ema_medium_val > ema_slow_val
        aligned_bearish = ema_fast_val < ema_medium_val < ema_slow_val
        
        # Price relative to EMAs
        price_above_fast = current_price > ema_fast_val
        price_above_medium = current_price > ema_medium_val
        price_above_slow = current_price > ema_slow_val
        
        return TrendResult(
            ema_fast=ema_fast_val,
            ema_medium=ema_medium_val,
            ema_slow=ema_slow_val,
            slope_fast=slope_fast,
            slope_medium=slope_medium,
            slope_slow=slope_slow,
            aligned_bullish=aligned_bullish,
            aligned_bearish=aligned_bearish,
            price_above_fast=price_above_fast,
            price_above_medium=price_above_medium,
            price_above_slow=price_above_slow,
            current_price=current_price,
        )
    
    def score(self, result: TrendResult, direction: str) -> float:
        """
        Calculate trend score (0-100).
        
        Args:
            result: TrendResult from calculate()
            direction: "BUY" or "SELL"
        
        Returns:
            Score from 0 to 100
        """
        if result is None:
            return 0.0
        
        score = 0.0
        is_bullish = direction == "BUY"
        
        # EMA Alignment (40 points max)
        if is_bullish and result.aligned_bullish:
            score += 40.0
        elif not is_bullish and result.aligned_bearish:
            score += 40.0
        
        # EMA Slope in signal direction (30 points max)
        slopes_positive = (
            result.slope_fast > 0 and 
            result.slope_medium > 0 and 
            result.slope_slow > 0
        )
        slopes_negative = (
            result.slope_fast < 0 and 
            result.slope_medium < 0 and 
            result.slope_slow < 0
        )
        
        if is_bullish and slopes_positive:
            score += 30.0
        elif not is_bullish and slopes_negative:
            score += 30.0
        elif is_bullish and result.slope_fast > 0:
            score += 15.0  # Partial score
        elif not is_bullish and result.slope_fast < 0:
            score += 15.0
        
        # Price relative to EMAs (30 points max)
        if is_bullish:
            if result.price_above_fast:
                score += 10.0
            if result.price_above_medium:
                score += 10.0
            if result.price_above_slow:
                score += 10.0
        else:
            if not result.price_above_fast:
                score += 10.0
            if not result.price_above_medium:
                score += 10.0
            if not result.price_above_slow:
                score += 10.0
        
        return min(score, 100.0)
