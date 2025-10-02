from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from utils.settings import load_settings, save_settings
from utils.logger import logger, bot_logger
from utils.email_notifier import email_notifier

# Определяем состояния
NEW_VALUE = 0
URL_MANAGEMENT = 1
ADDING_URLS = 2

# ==== Настройка числовых значений ====
async def start_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс установки настройки."""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        command = update.message.text
        
        logger.info(f"User {username} (ID: {user_id}) started setting: {command}")
        bot_logger.log_user_action(user_id, username, "start_setting", f"Command: {command}")
        
        key_map = {
            "/set_min_requests": "min_requests",
            "/set_max_requests": "max_requests",
            "/set_min_quantity": "min_quantity",
            "/set_max_quantity": "max_quantity",
        }
        key = key_map.get(command)

        if not key:
            await update.message.reply_text("Команда не распознана.")
            logger.warning(f"Unknown setting command from user {username} (ID: {user_id}): {command}")
            return ConversationHandler.END

        context.user_data["setting_key"] = key
        await update.message.reply_text("Введите новое значение (только число):")
        logger.info(f"Setting prompt sent to user {username} (ID: {user_id}) for key: {key}")
        return NEW_VALUE
        
    except Exception as e:
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        username = update.effective_user.username if update.effective_user else "Unknown"
        
        logger.log_error(e, f"Error in start_setting for user {username} (ID: {user_id})")
        email_notifier.send_error_notification(
            e, 
            f"Error in start_setting for user {username} (ID: {user_id})",
            {"user_id": user_id, "username": username, "command": "start_setting"}
        )
        
        try:
            await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        except Exception:
            pass
        return ConversationHandler.END


async def set_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняет новое значение настройки."""
    key = context.user_data.get("setting_key")
    value = update.message.text

    if not value.isdigit():
        await update.message.reply_text("Ошибка: Введите число.")
        return NEW_VALUE

    value = int(value)
    settings = load_settings()

    # Проверка зависимостей для min и max
    if "min" in key and settings.get(key.replace("min", "max"), float("inf")) < value:
        await update.message.reply_text("Ошибка: Значение должно быть меньше максимального.")
        return NEW_VALUE
    if "max" in key and settings.get(key.replace("max", "min"), float("-inf")) > value:
        await update.message.reply_text("Ошибка: Значение должно быть больше минимального.")
        return NEW_VALUE

    # Сохраняем значение
    settings[key] = value
    save_settings(settings)

    await update.message.reply_text(f"Настройка '{key}' обновлена до: {value}")
    return ConversationHandler.END


# ==== Управление ссылками ====
async def list_urls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выводит список текущих ссылок."""
    settings = load_settings()
    urls = settings.get("urls", [])
    if not urls:
        await update.message.reply_text("Список ссылок пуст.")
    else:
        url_list = "\n".join([f"{i+1}. {url}" for i, url in enumerate(urls)])
        await update.message.reply_text(f"Текущие ссылки:\n{url_list}")


async def add_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс добавления ссылок."""
    await update.message.reply_text(
        "Введите одну или несколько ссылок (каждую на новой строке):"
    )
    return ADDING_URLS


async def save_urls(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняет добавленные ссылки."""
    new_urls = update.message.text.split("\n")
    settings = load_settings()

    # Проверка на существующий список
    if "urls" not in settings:
        settings["urls"] = []

    # Ограничение на количество ссылок
    if len(settings["urls"]) + len(new_urls) > 10:
        await update.message.reply_text(
            f"Ошибка: Максимум можно сохранить 10 ссылок. Сейчас добавлено {len(settings['urls'])}."
        )
        return ADDING_URLS

    # Добавляем новые ссылки
    settings["urls"].extend(new_urls)
    save_settings(settings)

    await update.message.reply_text(
        "Ссылки добавлены:\n" + "\n".join([f"- {url}" for url in new_urls])
    )
    return ConversationHandler.END


async def remove_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс удаления ссылки."""
    settings = load_settings()
    urls = settings.get("urls", [])
    if not urls:
        await update.message.reply_text("Список ссылок пуст. Нечего удалять.")
        return ConversationHandler.END

    url_list = "\n".join([f"{i+1}. {url}" for i, url in enumerate(urls)])
    await update.message.reply_text(
        f"Текущие ссылки:\n{url_list}\nВведите номер ссылки для удаления:"
    )
    return URL_MANAGEMENT


async def delete_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Удаляет выбранную ссылку из списка."""
    settings = load_settings()
    urls = settings.get("urls", [])

    try:
        # Преобразуем ввод пользователя в индекс
        index = int(update.message.text) - 1

        # Проверяем, что индекс в пределах списка
        if index < 0 or index >= len(urls):
            raise ValueError("Неверный индекс")

        # Удаляем ссылку
        removed_url = urls.pop(index)
        settings["urls"] = urls
        save_settings(settings)

        await update.message.reply_text(f"Ссылка удалена:\n{removed_url}")
    except ValueError:
        await update.message.reply_text("Ошибка: Введите корректный номер ссылки.")
        return URL_MANAGEMENT

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет настройку."""
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END


# ==== Создание обработчиков ====
def get_settings_conversation_handler():
    """Обработчик для настройки числовых значений."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("set_min_requests", start_setting),
            CommandHandler("set_max_requests", start_setting),
            CommandHandler("set_min_quantity", start_setting),
            CommandHandler("set_max_quantity", start_setting),
        ],
        states={
            NEW_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^\d+$'), set_value),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )


def get_url_management_handler():
    """Обработчик для управления ссылками."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("list_urls", list_urls),
            CommandHandler("add_url", add_url),
            CommandHandler("remove_url", remove_url),
        ],
        states={
            ADDING_URLS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_urls),
            ],
            URL_MANAGEMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^\d+$'), delete_url),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )