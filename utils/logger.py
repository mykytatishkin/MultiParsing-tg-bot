import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional

class BotLogger:
    """Класс для настройки логирования бота с ротацией файлов."""
    
    def __init__(self, log_dir: str = "logs", max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5):
        """
        Инициализация логгера.
        
        Args:
            log_dir: Директория для хранения логов
            max_bytes: Максимальный размер файла лога в байтах (по умолчанию 10MB)
            backup_count: Количество резервных файлов логов
        """
        self.log_dir = log_dir
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        
        # Создаем директорию для логов если её нет
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        self._setup_logger()
    
    def _setup_logger(self):
        """Настройка логгера с различными обработчиками."""
        # Создаем основной логгер
        self.logger = logging.getLogger('MultiParsingBot')
        self.logger.setLevel(logging.DEBUG)
        
        # Очищаем существующие обработчики
        self.logger.handlers.clear()
        
        # Формат логов
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Обработчик для общих логов с ротацией
        general_handler = logging.handlers.RotatingFileHandler(
            os.path.join(self.log_dir, 'bot.log'),
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        general_handler.setLevel(logging.INFO)
        general_handler.setFormatter(formatter)
        
        # Обработчик для ошибок с ротацией
        error_handler = logging.handlers.RotatingFileHandler(
            os.path.join(self.log_dir, 'errors.log'),
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        
        # Обработчик для консоли (только для разработки)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Добавляем обработчики к логгеру
        self.logger.addHandler(general_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)
        
        # Предотвращаем дублирование логов
        self.logger.propagate = False
    
    def get_logger(self) -> logging.Logger:
        """Возвращает настроенный логгер."""
        return self.logger
    
    def log_user_action(self, user_id: int, username: str, action: str, details: Optional[str] = None):
        """
        Логирует действия пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            username: Имя пользователя
            action: Действие пользователя
            details: Дополнительные детали
        """
        message = f"User {username} (ID: {user_id}) performed action: {action}"
        if details:
            message += f" - Details: {details}"
        self.logger.info(message)
    
    def log_bot_action(self, action: str, details: Optional[str] = None):
        """
        Логирует действия бота.
        
        Args:
            action: Действие бота
            details: Дополнительные детали
        """
        message = f"Bot action: {action}"
        if details:
            message += f" - Details: {details}"
        self.logger.info(message)
    
    def log_error(self, error: Exception, context: Optional[str] = None):
        """
        Логирует ошибки.
        
        Args:
            error: Объект исключения
            context: Контекст возникновения ошибки
        """
        message = f"Error occurred: {type(error).__name__}: {str(error)}"
        if context:
            message += f" - Context: {context}"
        self.logger.error(message, exc_info=True)
    
    def log_critical_error(self, error: Exception, context: Optional[str] = None):
        """
        Логирует критические ошибки.
        
        Args:
            error: Объект исключения
            context: Контекст возникновения ошибки
        """
        message = f"CRITICAL ERROR: {type(error).__name__}: {str(error)}"
        if context:
            message += f" - Context: {context}"
        self.logger.critical(message, exc_info=True)

# Глобальный экземпляр логгера
bot_logger = BotLogger()
logger = bot_logger.get_logger()

