import asyncio
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from utils.settings import load_settings
from utils.generator import generate_name_from_db, generate_phone_from_db, generate_quantity
import random
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Глобальный флаг и список задач
stop_random_requests_flag = False
tasks = []  # Список активных задач


def generate_schedule(request_count):
    """Генерирует расписание запросов."""
    now = datetime.now()
    night_count = int(request_count * 0.3)
    day_count = request_count - night_count

    night_intervals = [
        now + timedelta(seconds=random.randint(0, 7 * 3600))
        for _ in range(night_count)
    ]
    day_intervals = [
        now + timedelta(seconds=random.randint(7 * 3600, 23 * 3600 + 59 * 60))
        for _ in range(day_count)
    ]

    full_schedule = sorted(night_intervals + day_intervals)
    return [time.strftime('%H:%M:%S') for time in full_schedule]


async def async_delay(seconds):
    """Асинхронная задержка с проверкой флага остановки."""
    global stop_random_requests_flag
    try:
        for _ in range(seconds):
            if stop_random_requests_flag:  # Если флаг установлен, прерываем
                raise asyncio.CancelledError
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        return  # Завершаем функцию


async def process_url(url, url_number, requests_count, update, context, daily_requests):
    """Асинхронно выполняет запросы для одной ссылки."""
    global stop_random_requests_flag

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context_browser = await browser.new_context()
        page = await context_browser.new_page()

        try:
            for i in range(requests_count):
                if stop_random_requests_flag:  # Проверяем флаг остановки
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Stopping requests for URL #{url_number} ({url}). Remaining requests: {requests_count - i} will not be executed."
                    )
                    return  # Выходим из цикла

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

                # Используем асинхронную задержку
                await async_delay(delay)

        except asyncio.CancelledError:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Task for URL #{url_number} ({url}) has been stopped."
            )
            return

        finally:
            await browser.close()


async def run_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запускает выполнение запросов в фоне."""
    global stop_random_requests_flag, tasks
    stop_random_requests_flag = False  # Разрешаем выполнение
    tasks = []  # Очистка задач

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

    # Запускаем процесс в фоне
    loop = asyncio.get_running_loop()
    tasks = [
        loop.create_task(process_url(url, i + 1, count, update, context, daily_requests))
        for i, (url, count) in enumerate(daily_requests.items())
    ]


async def stop_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Останавливает выполнение запросов."""
    global stop_random_requests_flag, tasks
    stop_random_requests_flag = True  # Останавливаем выполнение

    # Отменяем все активные задачи
    for task in tasks:
        task.cancel()

    # Дожидаемся завершения всех задач
    await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Random requests have been stopped."
    )


def get_random_request_handlers():
    """Возвращает список обработчиков."""
    return [
        CommandHandler("random_requests", run_random_requests),
        CommandHandler("stop_random_requests", stop_random_requests),
    ]