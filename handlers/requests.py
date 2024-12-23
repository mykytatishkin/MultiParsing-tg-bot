import asyncio
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from utils.settings import load_settings
from utils.generator import generate_name_from_db, generate_phone_from_db, generate_quantity
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver

# Глобальный флаг для управления выполнением запросов
stop_requests_flag = False
current_task = None  # Переменная для хранения текущей задачи


async def run_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запускает серию запросов, пока флаг stop_requests_flag установлен в True."""
    global stop_requests_flag, current_task
    stop_requests_flag = True  # Устанавливаем флаг перед запуском

    settings = load_settings()
    urls = settings.get("urls", [])  # Загружаем список ссылок
    if not urls:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Список ссылок пуст. Добавьте ссылки через /add_url."
        )
        return

    url = urls[0]  # Берём первую ссылку из списка
    request_count = settings["request_count"]

    # Настройки Selenium WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Отключите "--headless" для тестирования, чтобы видеть процесс
    options.add_argument("--headless")

    driver = None  # Инициализируем driver

    try:
        driver = webdriver.Chrome(options=options)

        for i in range(request_count):
            if not stop_requests_flag:  # Проверка перед началом каждого запроса
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Requests stopped by user."
                )
                break

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Executing request #{i + 1} for URL: {url}..."
            )

            try:
                driver.get(url)

                # Проверяем флаг после загрузки страницы
                if not stop_requests_flag:
                    break

                # Обработка полей ввода и кнопок с улучшенной проверкой
                try:
                    input_name = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, 'full-name'))
                    )
                    input_name.send_keys(generate_name_from_db())
                except Exception as e:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Error: 'Full Name' input field not found: {e}"
                    )
                    break

                try:
                    input_phone = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, 'phone'))
                    )
                    input_phone.send_keys(generate_phone_from_db())
                except Exception as e:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Error: 'Phone' input field not found: {e}"
                    )
                    break

                try:
                    input_quantity = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, 'qty'))
                    )
                    Select(input_quantity).select_by_value(generate_quantity())
                except Exception as e:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Error: 'Quantity' dropdown not found: {e}"
                    )
                    break

                try:
                    order_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Оформити замовлення")]'))
                    )
                    order_button.click()
                except Exception as e:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Error: 'Order' button not clickable or not found: {e}"
                    )
                    break

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Request #{i + 1} sent for URL: {url}"
                )

                # Короткая пауза между запросами (даём возможность обработать другие задачи)
                for _ in range(5):  # Проверяем флаг каждые 0.1 секунды (в течение 0.5 секунд)
                    if not stop_requests_flag:
                        break
                    await asyncio.sleep(0.5)
            except Exception as e:
                if not stop_requests_flag:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="Requests stopped by user."
                    )
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Error during request execution for {url}: {e}"
                    )
                break

    finally:
        if driver:
            driver.quit()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Request execution finished."
        )


async def stop_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Останавливает выполнение всех запросов."""
    global stop_requests_flag, current_task
    stop_requests_flag = False  # Устанавливаем флаг остановки
    if current_task:
        current_task.cancel()  # Отменяем текущую задачу, если она выполняется
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="All operations have been stopped."
    )


async def handle_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик запуска задач."""
    global current_task
    current_task = asyncio.create_task(run_requests(update, context))  # Создаем конкурентную задачу


def get_request_handlers():
    """Возвращает список обработчиков для управления запросами."""
    return [
        CommandHandler("run", handle_requests),
        CommandHandler("stop_requests", stop_requests),
    ]