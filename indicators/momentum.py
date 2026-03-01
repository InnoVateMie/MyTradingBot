"""Momentum indicators: RSI, candle body strength, consecutive direction."""
from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator

from data.candle_builder import Candle
from config.settings import settings


@dataclass
class MomentumResult:
    """Result of momentum analysis."""
    rsi: float
    body_strength: float  # 0-1, higher = stronger body
    consecutive_count: int  # Number of consecutive same-direction candles
    direction: str  # "UP", "DOWN", or "NEUTRAL"
    avg_body_strength: float  # Average body strength of recent candles


class MomentumIndicator:
    """Calculates momentum indicators from candle data."""
    
    def __init__(
        self,
        rsi_period: int = None,
        consecutive_lookback: int = 5,
        body_strength_lookback: int = 10,
    ):
        """
        Initialize momentum indicator.
        
        Args:
            rsi_period: RSI period (default: settings.rsi_period)
            consecutive_lookback: Max candles to check for consecutive direction
            body_strength_lookback: Candles to average for body strength
        """
        self.rsi_period = rsi_period or settings.rsi_period
        self.consecutive_lookback = consecutive_lookback
        self.body_strength_lookback = body_strength_lookback
    
    def _calculate_body_strength(self, candle: Candle) -> float:
        """
        Calculate candle body strength (0-1).
        
        Body strength = |close - open| / (high - low)
        Higher value means stronger directional move.
        """
        body = abs(candle.close - candle.open)
        range_val = candle.high - candle.low
        
        if range_val == 0:
            return 0.0
        
        return min(body / range_val, 1.0)
    
    def _count_consecutive_direction(self, candles: List[Candle]) -> tuple:
        """
        Count consecutive candles in same direction.
        
        Returns:
            Tuple of (count, direction)
        """
        if not candles:
            return 0, "NEUTRAL"
        
        recent = candles[-self.consecutive_lookback:]
        
        if not recent:
            return 0, "NEUTRAL"
        
        # Determine direction of last candle
        last = recent[-1]
        if last.close > last.open:
            target_dir = "UP"
        elif last.close < last.open:
            target_dir = "DOWN"
        else:
            return 0, "NEUTRAL"
        
        # Count consecutive candles in same direction
        count = 0
        for candle in reversed(recent):
            if target_dir == "UP" and candle.close > candle.open:
                count += 1
            elif target_dir == "DOWN" and candle.close < candle.open:
                count += 1
            else:
                break
        
        return count, target_dir
    
    def calculate(self, candles: List[Candle]) -> Optional[MomentumResult]:
        """
        Calculate momentum indicators from candles.
        
        Args:
            candles: List of Candle objects (oldest first)
        
        Returns:
            MomentumResult or None if not enough data
        """
        if len(candles) < self.rsi_period + 1:
            return None
        
        # Extract close prices for RSI
        closes = pd.Series([c.close for c in candles])
        
        # Calculate RSI
        rsi_indicator = RSIIndicator(closes, window=self.rsi_period)
        rsi = rsi_indicator.rsi().iloc[-1]
        
        # Calculate current candle body strength
        current_candle = candles[-1]
        body_strength = self._calculate_body_strength(current_candle)
        
        # Calculate average body strength
        recent_candles = candles[-self.body_strength_lookback:]
        strengths = [self._calculate_body_strength(c) for c in recent_candles]
        avg_body_strength = np.mean(strengths) if strengths else 0.0
        
        # Count consecutive direction
        consecutive_count, direction = self._count_consecutive_direction(candles)
        
        return MomentumResult(
            rsi=rsi,
            body_strength=body_strength,
            consecutive_count=consecutive_count,
            direction=direction,
            avg_body_strength=avg_body_strength,
        )
    
    def score(self, result: MomentumResult, direction: str) -> float:
        """
        Calculate momentum score (0-100).
        
        Args:
            result: MomentumResult from calculate()
            direction: "BUY" or "SELL"
        
        Returns:
            Score from 0 to 100
        """
        if result is None:
            return 0.0
        
        score = 0.0
        is_bullish = direction == "BUY"
        
        # RSI in momentum zone (40 points max)
        # Bullish: 55-70 is ideal, 50-80 acceptable
        # Bearish: 30-45 is ideal, 20-50 acceptable
        if is_bullish:
            if 55 <= result.rsi <= 70:
                score += 40.0
            elif 50 <= result.rsi <= 80:
                score += 20.0
            elif result.rsi > 30:  # Not oversold
                score += 10.0
        else:  # Bearish
            if 30 <= result.rsi <= 45:
                score += 40.0
            elif 20 <= result.rsi <= 50:
                score += 20.0
            elif result.rsi < 70:  # Not overbought
                score += 10.0
        
        # Body strength (30 points max)
        if result.body_strength > 0.7:
            score += 30.0
        elif result.body_strength > 0.5:
            score += 20.0
        elif result.body_strength > 0.3:
            score += 10.0
        
        # Consecutive candles in signal direction (30 points max)
        expected_dir = "UP" if is_bullish else "DOWN"
        if result.direction == expected_dir:
            if result.consecutive_count >= 3:
                score += 30.0
            elif result.consecutive_count >= 2:
                score += 20.0
            elif result.consecutive_count >= 1:
                score += 10.0
        
        return min(score, 100.0)
