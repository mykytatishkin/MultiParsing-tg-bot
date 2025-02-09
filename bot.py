import os
import asyncio
from telegram.ext import Application
from handlers.basic import get_basic_handlers
from handlers.settings import get_settings_conversation_handler, get_url_management_handler
from handlers.random_requests import get_random_request_handlers
from utils.settings import load_telegram_token

# Получаем токен бота
TOKEN = load_telegram_token()

# Получаем URL хостинга (Render автоматически присваивает `RENDER_EXTERNAL_URL`)
WEBHOOK_URL = f"{os.getenv('RENDER_EXTERNAL_URL')}/webhook"

def main():
    try:
        # Создаем экземпляр приложения
        application = Application.builder().token(TOKEN).build()

        # Добавляем обработчики
        application.add_handlers(get_basic_handlers())  # Базовые команды (/start, /menu)
        application.add_handler(get_settings_conversation_handler())  # Настройки
        application.add_handler(get_url_management_handler())  # Управление ссылками
        application.add_handlers(get_random_request_handlers())  # Случайные запросы
    except Exception as e:
        print(f"Error while setting up the bot: {e}")
        return

    print(f"Starting bot with Webhook at {WEBHOOK_URL}...")

    # Устанавливаем Webhook
    async def set_webhook():
        await application.bot.set_webhook(WEBHOOK_URL)

    try:
        asyncio.run(set_webhook())  # Устанавливаем вебхук
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv("PORT", 8000)),  # Render использует переменную PORT
            webhook_url=WEBHOOK_URL
        )
    except Exception as e:
        print(f"Error while running the bot: {e}")

if __name__ == "__main__":
    main()