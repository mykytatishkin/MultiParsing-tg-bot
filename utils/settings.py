import json
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(BASE_DIR, "../settings.json")

def load_settings():
    """Загружает настройки из settings.json. Если файла нет, создаёт пустой."""
    if not os.path.exists(SETTINGS_PATH):
        save_settings({})
    with open(SETTINGS_PATH, "r") as file:
        return json.load(file)

def save_settings(settings):
    """Сохраняет настройки в settings.json."""
    with open(SETTINGS_PATH, "w") as file:
        json.dump(settings, file, indent=4)

def update_setting(key, value):
    """Обновляет конкретное значение настройки."""
    settings = load_settings()
    settings[key] = value
    save_settings(settings)

def load_telegram_token():
    """Загружает Telegram-токен из переменных окружения или settings.json."""
    # Сначала пытаемся получить токен из переменных окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if token:
        return token
    
    # Если токен не найден в переменных окружения, пытаемся загрузить из settings.json
    try:
        settings = load_settings()
        return settings["telegram_bot_token"]
    except (FileNotFoundError, KeyError):
        raise ValueError("Telegram bot token not found in environment variables or settings.json")