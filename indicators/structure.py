"""Structure indicators: ADX, break of structure, S/R, pullback validation."""
from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
import pandas as pd
from ta.trend import ADXIndicator

from data.candle_builder import Candle
from config.settings import settings


@dataclass
class StructureResult:
    """Result of structure analysis."""
    adx: float  # ADX value (trend strength)
    plus_di: float  # +DI value
    minus_di: float  # -DI value
    bos_bullish: bool  # Break of structure to upside
    bos_bearish: bool  # Break of structure to downside
    recent_high: float  # Recent swing high
    recent_low: float  # Recent swing low
    pullback_valid: bool  # Price has pulled back after BoS
    sr_distance_pct: float  # Distance from nearest S/R level (%)
    trend_strength: str  # "STRONG", "MODERATE", "WEAK", "NONE"


class StructureIndicator:
    """Calculates market structure indicators from candle data."""
    
    def __init__(
        self,
        adx_period: int = None,
        swing_lookback: int = 20,
        pullback_threshold: float = 0.3,
    ):
        """
        Initialize structure indicator.
        
        Args:
            adx_period: ADX period (default: settings.adx_period)
            swing_lookback: Candles to look back for swing points
            pullback_threshold: Minimum pullback ratio to consider valid
        """
        self.adx_period = adx_period or settings.adx_period
        self.swing_lookback = swing_lookback
        self.pullback_threshold = pullback_threshold
    
    def _find_swing_points(self, candles: List[Candle]) -> Tuple[float, float]:
        """
        Find recent swing high and low.
        
        Returns:
            Tuple of (swing_high, swing_low)
        """
        if len(candles) < self.swing_lookback:
            recent = candles
        else:
            recent = candles[-self.swing_lookback:]
        
        highs = [c.high for c in recent]
        lows = [c.low for c in recent]
        
        return max(highs), min(lows)
    
    def _detect_bos(
        self, 
        candles: List[Candle], 
        swing_high: float, 
        swing_low: float
    ) -> Tuple[bool, bool]:
        """
        Detect break of structure.
        
        Returns:
            Tuple of (bullish_bos, bearish_bos)
        """
        if len(candles) < 3:
            return False, False
        
        current = candles[-1]
        prev = candles[-2]
        
        # Bullish BoS: current close breaks above previous swing high
        bullish_bos = current.close > swing_high and prev.close <= swing_high
        
        # Bearish BoS: current close breaks below previous swing low
        bearish_bos = current.close < swing_low and prev.close >= swing_low
        
        return bullish_bos, bearish_bos
    
    def _validate_pullback(
        self,
        candles: List[Candle],
        swing_high: float,
        swing_low: float,
        direction: str,
    ) -> bool:
        """
        Check if price has pulled back after a directional move.
        
        A valid pullback means price has retraced somewhat before
        potentially continuing in the direction.
        """
        if len(candles) < 5:
            return False
        
        recent = candles[-10:]
        current_price = candles[-1].close
        
        # Find the extreme point in the direction
        if direction == "BUY":
            # For bullish, we want price to have pulled back from high
            recent_extreme = max(c.high for c in recent)
            range_size = recent_extreme - swing_low
            pullback = recent_extreme - current_price
        else:
            # For bearish, we want price to have pulled back from low
            recent_extreme = min(c.low for c in recent)
            range_size = swing_high - recent_extreme
            pullback = current_price - recent_extreme
        
        if range_size == 0:
            return False
        
        pullback_ratio = pullback / range_size
        
        # Valid pullback: between threshold and 0.7 (not too deep)
        return self.pullback_threshold <= pullback_ratio <= 0.7
    
    def _calculate_sr_distance(
        self,
        current_price: float,
        swing_high: float,
        swing_low: float,
    ) -> float:
        """
        Calculate distance from nearest support/resistance level.
        
        Returns percentage distance from nearest S/R level.
        """
        dist_to_high = abs(current_price - swing_high)
        dist_to_low = abs(current_price - swing_low)
        
        nearest_dist = min(dist_to_high, dist_to_low)
        
        # Return as percentage
        if current_price > 0:
            return (nearest_dist / current_price) * 100
        return 0.0
    
    def _get_trend_strength(self, adx: float) -> str:
        """Categorize trend strength based on ADX."""
        if adx >= 40:
            return "STRONG"
        elif adx >= 25:
            return "MODERATE"
        elif adx >= 15:
            return "WEAK"
        return "NONE"
    
    def calculate(self, candles: List[Candle]) -> Optional[StructureResult]:
        """
        Calculate structure indicators from candles.
        
        Args:
            candles: List of Candle objects (oldest first)
        
        Returns:
            StructureResult or None if not enough data
        """
        min_candles = max(self.adx_period + 10, self.swing_lookback)
        if len(candles) < min_candles:
            return None
        
        # Create DataFrame for ta library
        df = pd.DataFrame({
            'high': [c.high for c in candles],
            'low': [c.low for c in candles],
            'close': [c.close for c in candles],
        })
        
        # Calculate ADX
        adx_indicator = ADXIndicator(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=self.adx_period,
        )
        
        adx = adx_indicator.adx().iloc[-1]
        plus_di = adx_indicator.adx_pos().iloc[-1]
        minus_di = adx_indicator.adx_neg().iloc[-1]
        
        # Find swing points
        swing_high, swing_low = self._find_swing_points(candles)
        
        # Detect break of structure
        bos_bullish, bos_bearish = self._detect_bos(candles, swing_high, swing_low)
        
        # Determine implied direction from DI
        implied_dir = "BUY" if plus_di > minus_di else "SELL"
        
        # Validate pullback
        pullback_valid = self._validate_pullback(
            candles, swing_high, swing_low, implied_dir
        )
        
        # Calculate S/R distance
        current_price = candles[-1].close
        sr_distance_pct = self._calculate_sr_distance(
            current_price, swing_high, swing_low
        )
        
        # Get trend strength category
        trend_strength = self._get_trend_strength(adx)
        
        return StructureResult(
            adx=adx,
            plus_di=plus_di,
            minus_di=minus_di,
            bos_bullish=bos_bullish,
            bos_bearish=bos_bearish,
            recent_high=swing_high,
            recent_low=swing_low,
            pullback_valid=pullback_valid,
            sr_distance_pct=sr_distance_pct,
            trend_strength=trend_strength,
        )
    
    def score(self, result: StructureResult, direction: str) -> float:
        """
        Calculate structure score (0-100).
        
        Args:
            result: StructureResult from calculate()
            direction: "BUY" or "SELL"
        
        Returns:
            Score from 0 to 100
        """
        if result is None:
            return 0.0
        
        score = 0.0
        is_bullish = direction == "BUY"
        
        # ADX trend strength (25 points max)
        if result.adx >= 40:
            score += 25.0
        elif result.adx >= 30:
            score += 20.0
        elif result.adx >= 25:
            score += 15.0
        elif result.adx >= 20:
            score += 10.0
        elif result.adx >= 15:
            score += 5.0
        
        # Break of structure in signal direction (40 points max)
        if is_bullish and result.bos_bullish:
            score += 40.0
        elif not is_bullish and result.bos_bearish:
            score += 40.0
        elif is_bullish and result.plus_di > result.minus_di:
            score += 15.0  # Partial: DI suggests bullish
        elif not is_bullish and result.minus_di > result.plus_di:
            score += 15.0  # Partial: DI suggests bearish
        
        # Pullback validation (20 points max)
        if result.pullback_valid:
            score += 20.0
        
        # S/R distance - not too close to resistance (15 points max)
        # Want > 0.1% distance from nearest S/R
        if result.sr_distance_pct > 0.3:
            score += 15.0
        elif result.sr_distance_pct > 0.2:
            score += 10.0
        elif result.sr_distance_pct > 0.1:
            score += 5.0
        
        return min(score, 100.0)
