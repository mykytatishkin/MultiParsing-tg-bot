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

# Глобальный флаг для управления выполнением запросов
stop_random_requests_flag = False
current_task = None  # Переменная для хранения текущей задачи


async def run_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выполняет запросы для каждой ссылки по очереди."""
    global stop_random_requests_flag
    stop_random_requests_flag = True  # Устанавливаем флаг перед запуском

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

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = None

    try:
        driver = webdriver.Chrome(options=options)

        # Генерация количества запросов для каждой ссылки
        daily_requests = {url: random.randint(min_requests, max_requests) for url in urls}
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Starting requests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n"
                 f"Requests for each URL:\n" +
                 "\n".join([f"{url}: {count} requests" for url, count in daily_requests.items()])
        )

        # Храним задержку для каждой ссылки
        delays = {url: random.randint(60, 3600) for url in urls}

        while any(daily_requests.values()) and stop_random_requests_flag:
            for url in urls:
                remaining_requests = daily_requests.get(url, 0)
                if remaining_requests <= 0:
                    continue

                # Выполнение запроса
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Executing request for {url}. Remaining requests: {remaining_requests - 1}"
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

                    # Уведомление о выполненном запросе
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Request sent for {url}:\nName: {name}\nPhone: {phone}\nQuantity: {quantity}"
                    )

                except Exception as e:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"Error during request execution for {url}: {e}"
                    )

                # Обновляем количество оставшихся запросов
                daily_requests[url] -= 1

                # Обновляем задержки
                delays = {url: random.randint(60, 3600) for url in urls if daily_requests.get(url, 0) > 0}

                # Формируем сообщение с ожиданием
                next_requests_info = "\n".join(
                    [f"{next_url}: {delays[next_url] // 60} min {delays[next_url] % 60} sec"
                     for next_url in delays]
                )
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Next requests delay:\n{next_requests_info}"
                )

                # Задержка перед следующим запросом
                if delays.get(url):
                    await asyncio.sleep(delays[url])

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="All requests for today completed."
        )

    finally:
        if driver:
            driver.quit()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Random requests execution finished."
        )


async def stop_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Останавливает выполнение случайных запросов."""
    global stop_random_requests_flag
    stop_random_requests_flag = False  # Устанавливаем флаг остановки
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Random requests have been stopped."
    )


async def handle_random_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик запуска случайных запросов."""
    global current_task
    current_task = asyncio.create_task(run_random_requests(update, context))


def get_random_request_handlers():
    """Возвращает список обработчиков для управления случайными запросами."""
    return [
        CommandHandler("random_requests", handle_random_requests),
        CommandHandler("stop_random_requests", stop_random_requests),
    ]