from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes
from utils.settings import load_settings
from utils.logger import logger, bot_logger
from utils.email_notifier import email_notifier

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет стартовое сообщение и отображает меню."""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        logger.info(f"User {username} (ID: {user_id}) started the bot")
        bot_logger.log_user_action(user_id, username, "start", "Bot started")
        
        keyboard = [
            ["/random_requests"],
            ["/stop_random_requests"],
            ["/set_min_requests", "/set_max_requests"],
            ["/set_min_quantity", "/set_max_quantity"],
            ["/set_request_count", "/show_settings"],
            ["/add_url", "/list_urls"],
            ["/remove_url", "/cancel"],  # Добавлены команды для работы с ссылками
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Welcome! Use the menu below to select a command.",
            reply_markup=reply_markup
        )
        
        logger.info(f"Start menu sent to user {username} (ID: {user_id})")
        
    except Exception as e:
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        username = update.effective_user.username if update.effective_user else "Unknown"
        
        logger.log_error(e, f"Error in start command for user {username} (ID: {user_id})")
        email_notifier.send_error_notification(
            e, 
            f"Error in start command for user {username} (ID: {user_id})",
            {"user_id": user_id, "username": username, "command": "start"}
        )
        
        # Отправляем пользователю сообщение об ошибке
        try:
            await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        except Exception:
            pass

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает текущие настройки."""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        logger.info(f"User {username} (ID: {user_id}) requested settings")
        bot_logger.log_user_action(user_id, username, "show_settings", "Settings displayed")
        
        settings = load_settings()
        urls = settings.get("urls", ["No URLs available"])
        urls_text = "\n".join([f"{i+1}. {url}" for i, url in enumerate(urls)])
        
        settings_text = (
            f"Current settings:\n"
            f"- URLs:\n{urls_text}\n"
            f"- Request Count: {settings['request_count']}\n"
            f"- Min Requests: {settings['min_requests']}\n"
            f"- Max Requests: {settings['max_requests']}\n"
            f"- Min Quantity: {settings['min_quantity']}\n"
            f"- Max Quantity: {settings['max_quantity']}"
        )
        
        await update.message.reply_text(settings_text)
        logger.info(f"Settings sent to user {username} (ID: {user_id})")
        
    except Exception as e:
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        username = update.effective_user.username if update.effective_user else "Unknown"
        
        logger.log_error(e, f"Error in show_settings command for user {username} (ID: {user_id})")
        email_notifier.send_error_notification(
            e, 
            f"Error in show_settings command for user {username} (ID: {user_id})",
            {"user_id": user_id, "username": username, "command": "show_settings"}
        )
        
        # Отправляем пользователю сообщение об ошибке
        try:
            await update.message.reply_text("Произошла ошибка при загрузке настроек. Попробуйте позже.")
        except Exception:
            pass

def get_basic_handlers():
    """Возвращает обработчики для базовых команд."""
    return [
        CommandHandler("start", start),
        CommandHandler("show_settings", show_settings),
        ]