# Быстрая настройка MultiParsing Bot

## 1. Создайте файл .env

Создайте файл `.env` в корневой директории проекта:

```env
# Telegram Bot Token
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here

# Email настройки для уведомлений
ALERT_EMAIL_USER=your-email@gmail.com
ALERT_EMAIL_PASSWORD=your-app-password-here
```

## 2. Настройте Gmail App Password

1. Войдите в Gmail → Настройки безопасности
2. Включите двухфакторную аутентификацию
3. Создайте "Пароль приложения" для MultiParsing Bot
4. Используйте этот пароль в `ALERT_EMAIL_PASSWORD`

## 3. Установите зависимости

```bash
pip install -r requirements.txt
```

## 4. Запустите бота

```bash
python bot.py
```

## Готово! 

- Все действия логируются в `logs/`
- Ошибки отправляются на `nikita.tishkin.13+alertMultiBot@gmail.com`
- Система автоматически обрабатывает все исключения

## Дополнительные настройки

Для кастомных SMTP серверов добавьте в `.env`:
```env
SMTP_SERVER=your-smtp-server.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

