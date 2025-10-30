import asyncio
import pytz
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from utils.settings import load_settings
from utils.generator import generate_name_from_db, generate_phone_from_db, generate_quantity
from utils.logger import logger, bot_logger
from utils.email_notifier import email_notifier
import random
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

stop_random_requests_flag = False
KYIV_TZ = pytz.timezone("Europe/Kiev")


def generate_schedule(request_count):
    """Генерация расписания запросов начиная с текущего времени (по Киеву)."""
    now_kyiv = datetime.now(KYIV_TZ)  # Текущее время в Киеве

    night_count = int(request_count * 0.3)
    day_count = request_count - night_count

    night_intervals = [
        now_kyiv + timedelta(seconds=random.randint(0, 7 * 3600))
        for _ in range(night_count)
    ]
    # Дневные заказы: рандомная разница между запросами от 1 минуты до 2 часов
    # Сохраняем базовый подход разбиения на ночь/день, но генерируем дневные времена последовательно
    # так, чтобы интервал между соседними запросами был в диапазоне [1 мин, 2 часа].
    # Окно дня ограничим текущими сутками с 07:00 до 23:59:59 по Киеву.
    today_kyiv = now_kyiv.astimezone(KYIV_TZ).date()
    day_window_start = datetime(
        today_kyiv.year,
        today_kyiv.month,
        today_kyiv.day,
        7,
        0,
        0,
        tzinfo=KYIV_TZ,
    )
    day_window_end = datetime(
        today_kyiv.year,
        today_kyiv.month,
        today_kyiv.day,
        23,
        59,
        59,
        tzinfo=KYIV_TZ,
    )

    # Начинать дневные интервалы с текущего момента (если он уже после 07:00), иначе с 07:00
    current_day_time = max(now_kyiv, day_window_start)
    if current_day_time > day_window_end:
        # Если уже позже дневного окна, переносим на следующий день 07:00
        next_day = (current_day_time + timedelta(days=1)).astimezone(KYIV_TZ).date()
        current_day_time = datetime(
            next_day.year,
            next_day.month,
            next_day.day,
            7,
            0,
            0,
            tzinfo=KYIV_TZ,
        )
    day_intervals = []
    for _ in range(day_count):
        # Добавляем случайную паузу 1 минута ... 2 часа
        increment_seconds = random.randint(60, 2 * 3600)
        candidate_time = current_day_time + timedelta(seconds=increment_seconds)
        # Если выходим за дневное окно — переносим на следующий день и продолжаем
        if candidate_time > day_window_end:
            next_day = (current_day_time + timedelta(days=1)).astimezone(KYIV_TZ).date()
            current_day_time = datetime(
                next_day.year,
                next_day.month,
                next_day.day,
                7,
                0,
                0,
                tzinfo=KYIV_TZ,
            )
            candidate_time = current_day_time + timedelta(seconds=random.randint(60, 2 * 3600))
        day_intervals.append(candidate_time)
        current_day_time = candidate_time

    full_schedule = sorted(night_intervals + day_intervals)
    return full_schedule


async def async_wait_until(target_time):
    """Функция ожидания точного времени запроса"""
    while True:
        now_kyiv = datetime.now(KYIV_TZ)
        delay = (target_time - now_kyiv).total_seconds()
        if delay <= 0:
            break  # Если уже наступило время — отправляем запрос
        await asyncio.sleep(min(60, delay))  # Ждать максимум 60 секунд за раз


async def process_url(url, url_number, update, context, min_requests, max_requests):
    """Обработчик запросов к URL"""
    user_id = update.effective_user.id if update.effective_user else "Unknown"
    username = update.effective_user.username if update.effective_user else "Unknown"
    
    logger.info(f"Starting URL processing for user {username} (ID: {user_id}), URL #{url_number}: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context_browser = await browser.new_context()
        page = await context_browser.new_page()

        try:
            while True:
                if stop_random_requests_flag:
                    logger.info(f"Stopping requests for URL #{url_number} due to stop flag")
                    break
                    
                requests_count = random.randint(min_requests, max_requests)
                schedule = generate_schedule(requests_count)  # Генерация расписания

                # Форматируем расписание в строку
                schedule_str = "\n".join(time.strftime("%H:%M:%S") for time in schedule)

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Schedule of requests for URL #{url_number} (Kyiv Time):\n{schedule_str}"
                )

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Starting requests for URL #{url_number} ({url}). {requests_count} requests will be sent at scheduled times."
                )

                logger.info(f"Generated schedule for URL #{url_number}: {requests_count} requests for user {username} (ID: {user_id})")

                for i, request_time in enumerate(schedule):
                    if stop_random_requests_flag:
                        logger.info(f"Stopping requests for URL #{url_number} due to stop flag during execution")
                        break
                        
                    await async_wait_until(request_time)

                    try:
                        # Выполнение запроса
                        await page.goto(url)
                        await page.fill('#full-name', generate_name_from_db())
                        await page.fill('#phone', generate_phone_from_db())
                        quantity = generate_quantity()
                        await page.select_option('#qty', quantity)
                        await page.click('//button[contains(text(), "Оформити замовлення")]')

                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=f"Request {i + 1}/{requests_count} sent for URL #{url_number} ({url})."
                        )
                        
                        logger.info(f"Request {i + 1}/{requests_count} completed for URL #{url_number} by user {username} (ID: {user_id})")
                        
                    except Exception as e:
                        logger.log_error(e, f"Error in request {i + 1}/{requests_count} for URL #{url_number} by user {username} (ID: {user_id})")
                        email_notifier.send_error_notification(
                            e,
                            f"Error in request {i + 1}/{requests_count} for URL #{url_number} by user {username} (ID: {user_id})",
                            {
                                "user_id": user_id,
                                "username": username,
                                "url_number": url_number,
                                "url": url,
                                "request_number": i + 1,
                                "total_requests": requests_count
                            }
                        )
                        
                        # Уведомляем пользователя об ошибке
                        try:
                            await context.bot.send_message(
                                chat_id=update.effective_chat.id,
                                text=f"Ошибка при выполнении запроса {i + 1}/{requests_count} для URL #{url_number}. Продолжаем..."
                            )
                        except Exception:
                            pass

        except Exception as e:
            logger.log_critical_error(e, f"Critical error in process_url for URL #{url_number} by user {username} (ID: {user_id})")
            email_notifier.send_critical_notification(
                e,
                f"Critical error in process_url for URL #{url_number} by user {username} (ID: {user_id})",
                {
                    "user_id": user_id,
                    "username": username,
                    "url_number": url_number,
                    "url": url
                }
            )
        finally:
            await browser.close()
            logger.info(f"Browser closed for URL #{url_number} processing by user {username} (ID: {user_id})")


async def run_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запуск отправки случайных запросов"""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or "Unknown"
        
        logger.info(f"User {username} (ID: {user_id}) started random requests")
        bot_logger.log_user_action(user_id, username, "run_random_requests", "Random requests started")
        
        global stop_random_requests_flag
        stop_random_requests_flag = False  # Очищаем флаг при новом запуске

        settings = load_settings()
        urls = settings["urls"]
        min_requests = settings["min_requests"]
        max_requests = settings["max_requests"]

        if not urls:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="The list of URLs is empty. Add links using /add_url."
            )
            logger.warning(f"User {username} (ID: {user_id}) tried to start requests with empty URL list")
            return

        logger.info(f"Starting random requests for {len(urls)} URLs for user {username} (ID: {user_id})")
        bot_logger.log_bot_action("Random requests started", f"URLs: {len(urls)}, User: {username}")

        loop = asyncio.get_running_loop()
        for i, url in enumerate(urls):
            loop.create_task(process_url(url, i + 1, update, context, min_requests, max_requests))
            
    except Exception as e:
        user_id = update.effective_user.id if update.effective_user else "Unknown"
        username = update.effective_user.username if update.effective_user else "Unknown"
        
        logger.log_critical_error(e, f"Critical error in run_random_requests for user {username} (ID: {user_id})")
        email_notifier.send_critical_notification(
            e, 
            f"Critical error in run_random_requests for user {username} (ID: {user_id})",
            {"user_id": user_id, "username": username, "command": "run_random_requests"}
        )
        
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Произошла критическая ошибка при запуске запросов. Попробуйте позже."
            )
        except Exception:
            pass


async def stop_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для остановки работы"""
    global stop_random_requests_flag
    stop_random_requests_flag = True

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Stopping requests will not cancel ongoing ones, but no new cycles will start."
    )


def get_random_request_handlers():
    return [
        CommandHandler("random_requests", run_random_requests),
        CommandHandler("stop_random_requests", stop_random_requests),
    ]