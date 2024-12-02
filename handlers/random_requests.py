import asyncio
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from utils.settings import load_settings
from utils.generator import generate_name_from_db, generate_phone_from_db, generate_quantity
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
import random
from datetime import datetime, timedelta

# Глобальный флаг и список задач для управления выполнением запросов
stop_random_requests_flag = False
tasks = []  # Список активных задач


async def process_url(url, url_number, requests_count, update, context, daily_requests):
    """Асинхронно выполняет запросы для одной ссылки с динамическим обновлением запросов и нумерацией."""
    global stop_random_requests_flag

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    try:
        for i in range(requests_count):
            if not stop_random_requests_flag:  # Проверяем флаг остановки
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Stopping requests for URL #{url_number} ({url}). Remaining requests: {requests_count - i} will not be executed."
                )
                return

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Executing request for URL #{url_number} ({url}). Remaining requests: {requests_count - i - 1}"
            )

            try:
                driver.get(url)

                # Генерация и заполнение данных
                input_name = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, 'full-name'))
                )
                input_phone = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, 'phone'))
                )
                input_quantity = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, 'qty'))
                )
                order_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Оформити замовлення")]'))
                )

                name = generate_name_from_db()
                phone = generate_phone_from_db()
                quantity = generate_quantity()

                input_name.send_keys(name)
                input_phone.send_keys(phone)
                Select(input_quantity).select_by_value(quantity)
                order_button.click()

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Request sent for URL #{url_number} ({url}):\nName: {name}\nPhone: {phone}\nQuantity: {quantity}"
                )

            except Exception as e:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Error during request execution for URL #{url_number} ({url}): {e}"
                )

            # Задержка перед следующим запросом
            delay = random.randint(60, 3600)  # от 1 до 60 минут
            next_request_time = datetime.now() + timedelta(seconds=delay)

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Next request for URL #{url_number} ({url}) will be executed at {next_request_time.strftime('%H:%M:%S')} "
                     f"(in {delay // 60} minutes and {delay % 60} seconds)."
            )

            # Проверяем флаг остановки во время ожидания
            for _ in range(delay):
                if not stop_random_requests_flag:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Stopping requests for URL #{url_number} ({url}). Remaining requests: {requests_count - i - 1} will not be executed."
                    )
                    return
                await asyncio.sleep(1)

        # Если запросы для ссылки закончились, генерируем новый лимит
        new_count = random.randint(1, 5)  # Подставьте актуальные лимиты
        daily_requests[url] = new_count
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"All requests for URL #{url_number} ({url}) completed.\nGenerating new requests: {new_count} requests."
        )
        # Рекурсивно вызываем обработку с новым количеством запросов
        await process_url(url, url_number, new_count, update, context, daily_requests)

    except asyncio.CancelledError:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Task for URL #{url_number} ({url}) has been forcibly stopped."
        )
        return

    finally:
        driver.quit()


async def run_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запускает выполнение запросов для каждой ссылки в отдельной задаче."""
    global stop_random_requests_flag, tasks
    stop_random_requests_flag = True  # Устанавливаем флаг перед запуском
    tasks = []  # Сброс задач

    settings = load_settings()
    urls = settings["urls"]  # Загружаем список ссылок
    min_requests = settings["min_requests"]
    max_requests = settings["max_requests"]

    if not urls:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Список ссылок пуст. Добавьте ссылки через /add_url."
        )
        return

    # Генерация количества запросов для каждой ссылки
    daily_requests = {url: random.randint(min_requests, max_requests) for url in urls}
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Starting requests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n"
             f"Requests for each URL:\n" +
             "\n".join([f"#{i + 1}: {url}: {count} requests" for i, (url, count) in enumerate(daily_requests.items())])
    )

    # Создаем отдельную задачу для каждой ссылки
    tasks = [
        asyncio.create_task(process_url(url, i + 1, count, update, context, daily_requests))
        for i, (url, count) in enumerate(daily_requests.items())
    ]

    # Дожидаемся завершения всех задач
    await asyncio.gather(*tasks, return_exceptions=True)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="All requests for today completed."
    )


async def stop_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Останавливает выполнение случайных запросов."""
    global stop_random_requests_flag, tasks
    stop_random_requests_flag = False  # Устанавливаем флаг остановки

    # Отменяем все активные задачи
    for task in tasks:
        if not task.done():
            task.cancel()

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Random requests have been stopped."
    )


async def handle_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик запуска случайных запросов."""
    asyncio.create_task(run_random_requests(update, context))


def get_random_request_handlers():
    """Возвращает список обработчиков для управления случайными запросами."""
    return [
        CommandHandler("random_requests", handle_random_requests),
        CommandHandler("stop_random_requests", stop_random_requests),
    ]