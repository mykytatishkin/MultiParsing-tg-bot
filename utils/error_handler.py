"""
Глобальный обработчик ошибок для Telegram бота.
"""
import sys
import traceback
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from .logger import logger, bot_logger
from .email_notifier import email_notifier

class GlobalErrorHandler:
    """Глобальный обработчик ошибок для всех обработчиков бота."""
    
    def __init__(self):
        self.error_count = 0
        self.max_errors_per_hour = 10  # Максимум ошибок в час для отправки email
    
    async def handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает все необработанные ошибки в боте.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст бота
        """
        try:
            # Получаем информацию об ошибке
            error = context.error
            user_info = self._get_user_info(update)
            
            # Логируем ошибку
            logger.log_error(
                error, 
                f"Unhandled error in bot for user {user_info['username']} (ID: {user_info['user_id']})"
            )
            
            # Увеличиваем счетчик ошибок
            self.error_count += 1
            
            # Отправляем email уведомление только если не превышен лимит
            if self.error_count <= self.max_errors_per_hour:
                email_notifier.send_error_notification(
                    error,
                    f"Unhandled error in bot for user {user_info['username']} (ID: {user_info['user_id']})",
                    {
                        "user_id": user_info['user_id'],
                        "username": user_info['username'],
                        "chat_id": user_info['chat_id'],
                        "message_text": user_info['message_text'],
                        "error_count": self.error_count
                    }
                )
            else:
                logger.warning(f"Error notification limit reached ({self.max_errors_per_hour} per hour)")
            
            # Уведомляем пользователя об ошибке
            await self._notify_user(update, context)
            
        except Exception as e:
            # Если произошла ошибка в самом обработчике ошибок
            logger.critical(f"Critical error in error handler: {e}")
            logger.critical(traceback.format_exc())
            
            # Отправляем критическое уведомление
            email_notifier.send_critical_notification(
                e,
                "Critical error in global error handler",
                {"original_error": str(context.error) if context.error else "Unknown"}
            )
    
    def _get_user_info(self, update: Update) -> dict:
        """Извлекает информацию о пользователе из обновления."""
        try:
            user = update.effective_user
            chat = update.effective_chat
            message = update.effective_message
            
            return {
                "user_id": user.id if user else "Unknown",
                "username": user.username if user and user.username else "Unknown",
                "first_name": user.first_name if user else "Unknown",
                "chat_id": chat.id if chat else "Unknown",
                "message_text": message.text if message and message.text else "No text",
                "message_id": message.message_id if message else "Unknown"
            }
        except Exception as e:
            logger.error(f"Error extracting user info: {e}")
            return {
                "user_id": "Unknown",
                "username": "Unknown", 
                "first_name": "Unknown",
                "chat_id": "Unknown",
                "message_text": "Unknown",
                "message_id": "Unknown"
            }
    
    async def _notify_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Отправляет уведомление пользователю об ошибке."""
        try:
            if update and update.effective_chat:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="😔 Произошла неожиданная ошибка. Мы уже работаем над её исправлением. Попробуйте позже."
                )
        except Exception as e:
            logger.error(f"Failed to notify user about error: {e}")
    
    def reset_error_count(self):
        """Сбрасывает счетчик ошибок (вызывать каждый час)."""
        self.error_count = 0
        logger.info("Error count reset")

# Глобальный экземпляр обработчика ошибок
global_error_handler = GlobalErrorHandler()
