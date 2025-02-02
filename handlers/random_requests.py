import asyncio
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from utils.settings import load_settings
from utils.generator import generate_name_from_db, generate_phone_from_db, generate_quantity
import random
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

stop_random_requests_flag = False


def generate_schedule(request_count):
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
    global stop_random_requests_flag
    try:
        for _ in range(seconds):
            if stop_random_requests_flag:
                raise asyncio.CancelledError
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        return


async def process_url(url, url_number, update, context, min_requests, max_requests):
    global stop_random_requests_flag

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context_browser = await browser.new_context()
        page = await context_browser.new_page()

        try:
            while not stop_random_requests_flag:
                requests_count = random.randint(min_requests, max_requests)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"New cycle for URL #{url_number} ({url}). {requests_count} requests will be made."
                )

                for i in range(requests_count):
                    if stop_random_requests_flag:
                        return

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

                    delay = random.randint(60, 3600)
                    next_request_time = datetime.now() + timedelta(seconds=delay)
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Next request for URL #{url_number} ({url}) at {next_request_time.strftime('%H:%M:%S')}"
                    )

                    await async_delay(delay)
        except asyncio.CancelledError:
            return
        finally:
            await browser.close()


async def run_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global stop_random_requests_flag
    stop_random_requests_flag = False

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

    loop = asyncio.get_running_loop()
    for i, url in enumerate(urls):
        loop.create_task(process_url(url, i + 1, update, context, min_requests, max_requests))


async def stop_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global stop_random_requests_flag
    stop_random_requests_flag = True

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Random requests have been stopped."
    )


def get_random_request_handlers():
    return [
        CommandHandler("random_requests", run_random_requests),
        CommandHandler("stop_random_requests", stop_random_requests),
    ]
