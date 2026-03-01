"""Finnhub WebSocket client for real-time market data."""
import asyncio
import json
import time
from typing import Callable, Optional, List
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from config.settings import settings
from utils.logger import logger


class FinnhubWebSocket:
    """Async WebSocket client for Finnhub market data with auto-reconnect."""
    
    def __init__(self, on_tick: Callable):
        """
        Initialize the WebSocket client.
        
        Args:
            on_tick: Callback function called with tick data dict
                    {symbol, price, volume, timestamp}
        """
        self._on_tick = on_tick
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._reconnect_delay = settings.ws_reconnect_delay_initial
        self._last_successful_time = 0
        self._subscribed_symbols: List[str] = []
    
    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._ws is not None and self._ws.open
    
    def _get_ws_url(self) -> str:
        """Build the WebSocket URL with API key."""
        return f"{settings.finnhub_ws_url}?token={settings.finnhub_api_key}"
    
    async def _subscribe(self, symbols: List[str]) -> None:
        """Subscribe to symbols."""
        if not self._ws:
            return
        
        for symbol in symbols:
            subscribe_msg = json.dumps({"type": "subscribe", "symbol": symbol})
            await self._ws.send(subscribe_msg)
            logger.debug(f"Subscribed to {symbol}")
        
        self._subscribed_symbols = symbols.copy()
    
    async def _unsubscribe(self, symbols: List[str]) -> None:
        """Unsubscribe from symbols."""
        if not self._ws:
            return
        
        for symbol in symbols:
            unsubscribe_msg = json.dumps({"type": "unsubscribe", "symbol": symbol})
            await self._ws.send(unsubscribe_msg)
            logger.debug(f"Unsubscribed from {symbol}")
    
    async def _handle_message(self, message: str) -> None:
        """Process incoming WebSocket message."""
        try:
            data = json.loads(message)
            
            if data.get("type") == "trade":
                trades = data.get("data", [])
                for trade in trades:
                    tick = {
                        "symbol": trade.get("s"),
                        "price": trade.get("p"),
                        "volume": trade.get("v", 0),
                        "timestamp": trade.get("t", int(time.time() * 1000)),
                    }
                    await self._on_tick(tick)
            
            elif data.get("type") == "ping":
                # Respond to ping with pong
                if self._ws:
                    await self._ws.send(json.dumps({"type": "pong"}))
            
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {message[:100]}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def _reset_reconnect_delay(self) -> None:
        """Reset reconnection delay after successful connection."""
        self._reconnect_delay = settings.ws_reconnect_delay_initial
    
    def _increase_reconnect_delay(self) -> None:
        """Increase reconnection delay using exponential backoff."""
        self._reconnect_delay = min(
            self._reconnect_delay * settings.ws_reconnect_delay_multiplier,
            settings.ws_reconnect_delay_max
        )
    
    async def connect(self, symbols: Optional[List[str]] = None) -> None:
        """
        Connect to Finnhub WebSocket and start receiving data.
        
        Args:
            symbols: List of symbols to subscribe to. Defaults to settings.symbols.
        """
        if symbols is None:
            symbols = settings.symbols
        
        self._running = True
        
        while self._running:
            try:
                logger.info("Connecting to Finnhub WebSocket...")
                
                async with websockets.connect(
                    self._get_ws_url(),
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    self._ws = ws
                    logger.info("Connected to Finnhub WebSocket")
                    
                    # Subscribe to symbols
                    await self._subscribe(symbols)
                    
                    # Reset reconnect delay on successful connection
                    self._reset_reconnect_delay()
                    self._last_successful_time = time.time()
                    
                    # Listen for messages
                    async for message in ws:
                        if not self._running:
                            break
                        await self._handle_message(message)
                        
                        # Reset delay if connected successfully for 5 minutes
                        if time.time() - self._last_successful_time > 300:
                            self._reset_reconnect_delay()
                            self._last_successful_time = time.time()
            
            except ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}")
            except WebSocketException as e:
                logger.error(f"WebSocket error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in WebSocket: {e}")
            finally:
                self._ws = None
            
            if self._running:
                logger.info(f"Reconnecting in {self._reconnect_delay:.1f}s...")
                await asyncio.sleep(self._reconnect_delay)
                self._increase_reconnect_delay()
    
    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        self._running = False
        
        if self._ws:
            try:
                await self._unsubscribe(self._subscribed_symbols)
                await self._ws.close()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._ws = None
        
        logger.info("Disconnected from Finnhub WebSocket")
