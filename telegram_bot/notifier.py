"""Signal notifier - broadcasts signals to authorized users."""
from typing import Set, Optional
from telegram import Bot
from telegram.error import Forbidden, TelegramError

from config.auth import auth_manager
from engine.signal_generator import Signal
from telegram_bot.dashboard import Dashboard
from utils.logger import logger


class SignalNotifier:
    """Broadcasts signals to all authorized Telegram chats."""
    
    def __init__(self, bot: Bot):
        """
        Initialize signal notifier.
        
        Args:
            bot: Telegram Bot instance
        """
        self.bot = bot
    
    async def broadcast_signal(self, signal: Signal) -> int:
        """
        Broadcast a signal to all authorized chats.
        
        Args:
            signal: Signal to broadcast
        
        Returns:
            Number of chats successfully notified
        """
        message, keyboard = Dashboard.signal_alert(signal)
        chat_ids = auth_manager.get_authorized_chats()
        
        if not chat_ids:
            logger.warning("No authorized chats to broadcast to")
            return 0
        
        success_count = 0
        failed_chats = []
        
        for chat_id in chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    reply_markup=keyboard,
                    parse_mode=None,
                )
                success_count += 1
                logger.debug(f"Signal sent to chat {chat_id}")
                
            except Forbidden:
                # User blocked the bot
                logger.warning(f"Chat {chat_id} has blocked the bot")
                failed_chats.append(chat_id)
                
            except TelegramError as e:
                logger.error(f"Failed to send signal to {chat_id}: {e}")
        
        # Remove chats that blocked the bot
        for chat_id in failed_chats:
            auth_manager.revoke(chat_id)
        
        logger.info(f"Signal broadcast to {success_count}/{len(chat_ids)} chats")
        return success_count
    
    async def send_to_chat(self, chat_id: int, message) -> bool:
        """
        Send a message to a specific chat.
        
        Args:
            chat_id: Telegram chat ID
            message: Message text or tuple (message_text, keyboard)
        
        Returns:
            True if sent successfully
        """
        # Handle both string messages and tuple (message, keyboard)
        if isinstance(message, tuple):
            msg_text, keyboard = message
        else:
            msg_text = message
            keyboard = None
        
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=msg_text,
                reply_markup=keyboard,
                parse_mode=None,
            )
            return True
            
        except Forbidden:
            logger.warning(f"Chat {chat_id} has blocked the bot")
            auth_manager.revoke(chat_id)
            return False
            
        except TelegramError as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            return False
