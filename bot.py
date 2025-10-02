from telegram.ext import Application
import sys
import signal
import atexit

from handlers.basic import get_basic_handlers
from handlers.settings import get_settings_conversation_handler, get_url_management_handler
from handlers.random_requests import get_random_request_handlers
from utils.settings import load_telegram_token
from utils.logger import logger, bot_logger
from utils.email_notifier import email_notifier
from utils.error_handler import global_error_handler

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения работы бота."""
    logger.info(f"Received signal {signum}. Shutting down gracefully...")
    sys.exit(0)

def cleanup():
    """Функция очистки при завершении работы."""
    logger.info("Bot shutdown completed.")

def main():
    """Основная функция запуска бота."""
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(cleanup)
    
    logger.info("Starting MultiParsing Bot...")
    bot_logger.log_bot_action("Bot startup initiated")
    
    try:
        # Загружаем токен Telegram
        token = load_telegram_token()
        logger.info("Telegram token loaded successfully")
    except FileNotFoundError:
        error_msg = "Error: 'settings.json' file not found. Make sure the file exists in the expected location."
        logger.error(error_msg)
        print(error_msg)
        return
    except KeyError:
        error_msg = "Error: Telegram bot token not found in 'settings.json'. Please check your configuration."
        logger.error(error_msg)
        print(error_msg)
        return
    except Exception as e:
        logger.log_error(e, "Failed to load Telegram token")
        email_notifier.send_error_notification(e, "Failed to load Telegram token")
        print(f"Error loading token: {e}")
        return

    try:
        # Создаем экземпляр приложения
        application = Application.builder().token(token).build()
        logger.info("Telegram application created successfully")

        # Добавляем обработчики
        application.add_handlers(get_basic_handlers())  # Базовые команды (/start, /menu)
        application.add_handler(get_settings_conversation_handler())  # Настройки
        application.add_handler(get_url_management_handler())  # Управление ссылками
        application.add_handlers(get_random_request_handlers())  # Случайные запросы
        
        # Добавляем глобальный обработчик ошибок
        application.add_error_handler(global_error_handler.handle_error)
        
        logger.info("All handlers added successfully")
        bot_logger.log_bot_action("Bot handlers configured")
        
    except Exception as e:
        logger.log_critical_error(e, "Failed to setup bot application")
        email_notifier.send_critical_notification(e, "Failed to setup bot application")
        print(f"Error while setting up the bot: {e}")
        return

    logger.info("Bot is running... Press Ctrl+C to stop.")
    bot_logger.log_bot_action("Bot started successfully")
    print("Bot is running... Press Ctrl+C to stop.")

    # Запускаем бота
    try:
        application.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
        bot_logger.log_bot_action("Bot stopped by user")
    except Exception as e:
        logger.log_critical_error(e, "Critical error while running the bot")
        email_notifier.send_critical_notification(e, "Critical error while running the bot")
        print(f"Critical error while running the bot: {e}")
        # Отправляем уведомление о падении сервера
        email_notifier.send_server_down_notification(
            f"Bot crashed with error: {type(e).__name__}: {str(e)}",
            {"error_type": type(e).__name__, "error_message": str(e)}
        )

if __name__ == "__main__":
    main()