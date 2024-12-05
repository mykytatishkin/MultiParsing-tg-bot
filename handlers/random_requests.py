import asyncio
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from utils.settings import load_settings
from utils.generator import generate_name_from_db, generate_phone_from_db, generate_quantity
import random
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Глобальный флаг и список задач для управления выполнением запросов
stop_random_requests_flag = False
tasks = []  # Список активных задач


def generate_schedule(request_count):
    """Генерирует расписание запросов с заданными пропорциями, начиная с текущего времени."""
    now = datetime.now()
    night_count = int(request_count * 0.3)  # 30% запросов ночью
    day_count = request_count - night_count  # Остальные днем

    night_intervals = [
        now + timedelta(seconds=random.randint(0, 7 * 3600))  # Интервал 00:00–07:00
        for _ in range(night_count)
    ]
    day_intervals = [
        now + timedelta(seconds=random.randint(7 * 3600, 23 * 3600 + 59 * 60))  # Интервал 07:00–23:59
        for _ in range(day_count)
    ]

    # Объединяем и сортируем временные интервалы
    full_schedule = sorted(night_intervals + day_intervals)
    return [time.strftime('%H:%M:%S') for time in full_schedule]


async def process_url(url, url_number, requests_count, update, context):
    """Асинхронно выполняет запросы для одной ссылки."""
    global stop_random_requests_flag

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context_browser = await browser.new_context()
            page = await context_browser.new_page()

            for i in range(requests_count):
                if not stop_random_requests_flag:  # Проверяем флаг остановки
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Stopping requests for URL #{url_number} ({url}). Remaining requests: {requests_count - i} will not be executed."
                    )
                    return

                # Выполнение запроса
                await page.goto(url)
                await page.fill('#full-name', generate_name_from_db())
                await page.fill('#phone', generate_phone_from_db())
                quantity = generate_quantity()
                await page.select_option('#qty', quantity)
                await page.click('//button[contains(text(), "Оформити замовлення")]')

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Request sent for URL #{url_number} ({url}). Remaining requests: {requests_count - i - 1}"
                )

                # Задержка перед следующим запросом
                delay = random.randint(60, 3600)
                next_request_time = datetime.now() + timedelta(seconds=delay)

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Next request for URL #{url_number} ({url}) will be executed at {next_request_time.strftime('%H:%M:%S')}."
                )

                # Ожидание с проверкой флага остановки
                for _ in range(delay):
                    if not stop_random_requests_flag:
                        return
                    await asyncio.sleep(1)

    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Error during request execution for URL #{url_number} ({url}): {e}"
        )
    finally:
        if 'browser' in locals() and browser:
            await browser.close()


async def run_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запускает выполнение запросов для каждой ссылки в отдельной задаче."""
    global stop_random_requests_flag, tasks
    stop_random_requests_flag = True  # Устанавливаем флаг перед запуском
    tasks = []  # Сброс задач

    settings = load_settings()
    urls = settings["urls"]
    min_requests = settings["min_requests"]
    max_requests = settings["max_requests"]

    if not urls:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Список ссылок пуст. Добавьте ссылки через /add_url."
        )
        return

    daily_requests = {url: random.randint(min_requests, max_requests) for url in urls}
    schedules = {url: generate_schedule(count) for url, count in daily_requests.items()}

    for i, (url, schedule) in enumerate(schedules.items()):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Schedule of requests for URL #{i + 1} ({url}):\n" + "\n".join(schedule)
        )

    tasks = [
        asyncio.create_task(process_url(url, i + 1, count, update, context))
        for i, (url, count) in enumerate(daily_requests.items())
    ]

    await asyncio.gather(*tasks, return_exceptions=True)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="All requests for today completed."
    )


async def stop_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Останавливает выполнение запросов."""
    global stop_random_requests_flag, tasks
    stop_random_requests_flag = False  # Устанавливаем флаг остановки

    # Отменяем все активные задачи
    for task in tasks:
        if not task.done():
            task.cancel()

    # Ждем завершения всех задач
    await asyncio.gather(*tasks, return_exceptions=True)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Random requests have been stopped."
    )


def get_random_request_handlers():
    """Возвращает список обработчиков для управления запросами."""
    return [
        CommandHandler("random_requests", run_random_requests),
        CommandHandler("stop_random_requests", stop_random_requests),
    ]