"""Signal generator - orchestrates the full indicator to signal pipeline."""
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from data.candle_builder import Candle
from indicators.trend import TrendIndicator, TrendResult
from indicators.momentum import MomentumIndicator, MomentumResult
from indicators.volatility import VolatilityIndicator, VolatilityResult
from indicators.structure import StructureIndicator, StructureResult
from engine.scoring import ScoringEngine, ScoreBreakdown
from engine.expiry import ExpirySelector, ExpiryRecommendation
from config.settings import settings
from utils.logger import logger


@dataclass
class Signal:
    """Trading signal with all relevant information."""
    symbol: str
    direction: str  # "BUY" or "SELL"
    score: float
    confidence: str
    expiry_seconds: int
    expiry_label: str
    expiry_reason: str
    timeframe: int  # Candle timeframe used
    entry_price: float
    timestamp: int  # Signal generation time (ms)
    
    # Detailed breakdown
    trend_score: float = 0.0
    momentum_score: float = 0.0
    volatility_score: float = 0.0
    structure_score: float = 0.0
    
    # Signal numbering
    signal_number: int = 0
    
    # Optional: indicator details for logging
    rsi: Optional[float] = None
    adx: Optional[float] = None
    atr_ratio: Optional[float] = None


@dataclass
class AnalysisResult:
    """Result of analyzing a symbol/timeframe combination."""
    symbol: str
    timeframe: int
    score: ScoreBreakdown
    expiry: ExpiryRecommendation
    trend: Optional[TrendResult]
    momentum: Optional[MomentumResult]
    volatility: Optional[VolatilityResult]
    structure: Optional[StructureResult]
    meets_threshold: bool


class SignalGenerator:
    """
    Orchestrates the full pipeline from candles to signals.
    
    1. Calculate all indicators
    2. Run scoring engine
    3. Check threshold
    4. Select expiry
    5. Generate signal
    """
    
    def __init__(self):
        """Initialize signal generator with all components."""
        self.trend_indicator = TrendIndicator()
        self.momentum_indicator = MomentumIndicator()
        self.volatility_indicator = VolatilityIndicator()
        self.structure_indicator = StructureIndicator()
        self.scoring_engine = ScoringEngine()
        self.expiry_selector = ExpirySelector()
    
    def analyze(
        self,
        symbol: str,
        timeframe: int,
        candles: List[Candle],
    ) -> Optional[AnalysisResult]:
        """
        Analyze candles and return analysis result.
        
        Args:
            symbol: The trading symbol
            timeframe: Candle timeframe in seconds
            candles: List of candles (oldest first)
        
        Returns:
            AnalysisResult or None if not enough data
        """
        if len(candles) < settings.ema_slow_period:
            logger.debug(f"Not enough candles for {symbol} {timeframe}s: {len(candles)}")
            return None
        
        # Calculate all indicators
        trend = self.trend_indicator.calculate(candles)
        momentum = self.momentum_indicator.calculate(candles)
        volatility = self.volatility_indicator.calculate(candles)
        structure = self.structure_indicator.calculate(candles)
        
        # Run scoring engine
        score = self.scoring_engine.calculate(
            trend=trend,
            momentum=momentum,
            volatility=volatility,
            structure=structure,
            trend_indicator=self.trend_indicator,
            momentum_indicator=self.momentum_indicator,
            volatility_indicator=self.volatility_indicator,
            structure_indicator=self.structure_indicator,
        )
        
        # Select expiry
        expiry = self.expiry_selector.select(volatility, structure, score)
        
        # Check threshold
        meets_threshold = self.scoring_engine.meets_threshold(score)
        
        return AnalysisResult(
            symbol=symbol,
            timeframe=timeframe,
            score=score,
            expiry=expiry,
            trend=trend,
            momentum=momentum,
            volatility=volatility,
            structure=structure,
            meets_threshold=meets_threshold,
        )
    
    def analyze_all_timeframes(
        self,
        symbol: str,
        candles_by_timeframe: Dict[int, List[Candle]],
    ) -> Optional[AnalysisResult]:
        """
        Analyze all timeframes and return the best result.
        
        Args:
            symbol: The trading symbol
            candles_by_timeframe: Dict mapping timeframe to candle list
        
        Returns:
            Best AnalysisResult (highest score above threshold) or None
        """
        best_result: Optional[AnalysisResult] = None
        best_score = 0.0
        
        for timeframe, candles in candles_by_timeframe.items():
            result = self.analyze(symbol, timeframe, candles)
            
            if result and result.meets_threshold:
                if result.score.total_score > best_score:
                    best_score = result.score.total_score
                    best_result = result
        
        return best_result
    
    def generate_signal(
        self,
        analysis: AnalysisResult,
        entry_price: float,
    ) -> Signal:
        """
        Generate a Signal from an AnalysisResult.
        
        Args:
            analysis: AnalysisResult from analyze()
            entry_price: Current price for signal
        
        Returns:
            Signal object
        """
        return Signal(
            symbol=analysis.symbol,
            direction=analysis.score.direction,
            score=analysis.score.total_score,
            confidence=analysis.score.confidence,
            expiry_seconds=analysis.expiry.seconds,
            expiry_label=analysis.expiry.label,
            expiry_reason=analysis.expiry.reason,
            timeframe=analysis.timeframe,
            entry_price=entry_price,
            timestamp=int(time.time() * 1000),
            trend_score=analysis.score.trend_score,
            momentum_score=analysis.score.momentum_score,
            volatility_score=analysis.score.volatility_score,
            structure_score=analysis.score.structure_score,
            rsi=analysis.momentum.rsi if analysis.momentum else None,
            adx=analysis.structure.adx if analysis.structure else None,
            atr_ratio=analysis.volatility.atr_ratio if analysis.volatility else None,
        )
