from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes
from utils.settings import load_settings

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет стартовое сообщение и отображает меню."""
    keyboard = [
        ["♻️ Выполнение случайных запросов 24/7"],
        ["❌ Остановить выполнение случайных запросов"],
        ["📬Минимальное количество запросов", "📬Максимальное количество запросов"],
        ["🛍️Минимальное количество вещей", "🛍️Максимальное количество вещей"],
        ["⚙️ Настройки"],
        ["🔗 Добавить ссылку", "🔗 Список ссылок"],
        ["🔗 Убрать ссылку", "⬅️ Отмена"],  # Добавлены команды для работы с ссылками
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome! Use the menu below to select a command.",
        reply_markup=reply_markup
    )

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает текущие настройки."""
    settings = load_settings()
    urls = settings.get("urls", ["No URLs available"])
    urls_text = "\n".join([f"{i+1}. {url}" for i, url in enumerate(urls)])
    await update.message.reply_text(
        f"Current settings:\n"
        f"- URLs:\n{urls_text}\n"
        f"- Request Count: {settings['request_count']}\n"
        f"- Min Requests: {settings['min_requests']}\n"
        f"- Max Requests: {settings['max_requests']}\n"
        f"- Min Quantity: {settings['min_quantity']}\n"
        f"- Max Quantity: {settings['max_quantity']}"
    )

def get_basic_handlers():
    """Возвращает обработчики для базовых команд."""
    return [
        CommandHandler("start", start),
        CommandHandler("show_settings", show_settings),
    ]