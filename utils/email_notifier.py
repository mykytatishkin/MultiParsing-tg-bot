import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import traceback
from datetime import datetime
from typing import Optional, List
import json

from .logger import logger

class EmailNotifier:
    """Класс для отправки email уведомлений об ошибках и критических событиях."""
    
    # Константы для текста писем
    ADDITIONAL_INFO_TEXT = "Дополнительная информация:\n"
    
    def __init__(self, settings_path: str = "settings.json"):
        """
        Инициализация email уведомлений.
        
        Args:
            settings_path: Путь к файлу настроек
        """
        self.settings_path = settings_path
        self.email_config = self._load_email_config()
        self.alert_email = "nikita.tishkin.13+alertMultiBot@gmail.com"
    
    def _load_email_config(self) -> dict:
        """Загружает конфигурацию email из переменных окружения."""
        # Email настройки теперь загружаются только из переменных окружения
        return {}
    
    def _get_smtp_config(self) -> dict:
        """Возвращает конфигурацию SMTP сервера из переменных окружения."""
        # Настройки по умолчанию для Gmail SMTP
        default_config = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'use_tls': True
        }
        
        # Проверяем переменные окружения для пользовательских настроек
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = os.getenv('SMTP_PORT')
        use_tls = os.getenv('SMTP_USE_TLS')
        
        if smtp_server:
            config = {
                'smtp_server': smtp_server,
                'smtp_port': int(smtp_port) if smtp_port else 587,
                'use_tls': use_tls.lower() == 'true' if use_tls else True
            }
            return config
        
        return default_config
    
    def _get_credentials(self) -> tuple:
        """Получает учетные данные для отправки email из переменных окружения."""
        # Получаем учетные данные только из переменных окружения
        email = os.getenv('ALERT_EMAIL_USER')
        password = os.getenv('ALERT_EMAIL_PASSWORD')
        
        if email and password:
            return email, password
        
        # Если учетные данные не найдены, возвращаем None
        return None, None
    
    def send_error_notification(self, error: Exception, context: Optional[str] = None, 
                              additional_info: Optional[dict] = None) -> bool:
        """
        Отправляет уведомление об ошибке на email.
        
        Args:
            error: Объект исключения
            context: Контекст возникновения ошибки
            additional_info: Дополнительная информация
            
        Returns:
            True если email отправлен успешно, False в противном случае
        """
        try:
            subject = f"🚨 MultiParsing Bot Error - {type(error).__name__}"
            
            # Формируем тело письма
            body = self._create_error_email_body(error, context, additional_info)
            
            return self._send_email(subject, body)
            
        except Exception as e:
            logger.error(f"Failed to send error notification email: {e}")
            return False
    
    def send_critical_notification(self, error: Exception, context: Optional[str] = None,
                                 additional_info: Optional[dict] = None) -> bool:
        """
        Отправляет уведомление о критической ошибке на email.
        
        Args:
            error: Объект исключения
            context: Контекст возникновения ошибки
            additional_info: Дополнительная информация
            
        Returns:
            True если email отправлен успешно, False в противном случае
        """
        try:
            subject = f"🔥 CRITICAL: MultiParsing Bot Failure - {type(error).__name__}"
            
            # Формируем тело письма
            body = self._create_critical_email_body(error, context, additional_info)
            
            return self._send_email(subject, body)
            
        except Exception as e:
            logger.error(f"Failed to send critical notification email: {e}")
            return False
    
    def send_server_down_notification(self, reason: str, additional_info: Optional[dict] = None) -> bool:
        """
        Отправляет уведомление о падении сервера.
        
        Args:
            reason: Причина падения сервера
            additional_info: Дополнительная информация
            
        Returns:
            True если email отправлен успешно, False в противном случае
        """
        try:
            subject = "💥 MultiParsing Bot Server Down"
            
            body = self._create_server_down_email_body(reason, additional_info)
            
            return self._send_email(subject, body)
            
        except Exception as e:
            logger.error(f"Failed to send server down notification email: {e}")
            return False
    
    def _create_error_email_body(self, error: Exception, context: Optional[str], 
                               additional_info: Optional[dict]) -> str:
        """Создает тело письма для уведомления об ошибке."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        body = f"""
🚨 ОШИБКА В MULTIPARSING BOT

Время: {timestamp}
Тип ошибки: {type(error).__name__}
Сообщение: {str(error)}

"""
        
        if context:
            body += f"Контекст: {context}\n\n"
        
        if additional_info:
            body += self.ADDITIONAL_INFO_TEXT
            for key, value in additional_info.items():
                body += f"- {key}: {value}\n"
            body += "\n"
        
        body += f"""
Трассировка стека:
{traceback.format_exc()}

---
Это автоматическое уведомление от MultiParsing Bot.
"""
        
        return body
    
    def _create_critical_email_body(self, error: Exception, context: Optional[str],
                                  additional_info: Optional[dict]) -> str:
        """Создает тело письма для уведомления о критической ошибке."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        body = f"""
🔥 КРИТИЧЕСКАЯ ОШИБКА В MULTIPARSING BOT

Время: {timestamp}
Тип ошибки: {type(error).__name__}
Сообщение: {str(error)}

⚠️ ТРЕБУЕТСЯ НЕМЕДЛЕННОЕ ВНИМАНИЕ!

"""
        
        if context:
            body += f"Контекст: {context}\n\n"
        
        if additional_info:
            body += self.ADDITIONAL_INFO_TEXT
            for key, value in additional_info.items():
                body += f"- {key}: {value}\n"
            body += "\n"
        
        body += f"""
Трассировка стека:
{traceback.format_exc()}

---
Это автоматическое уведомление о критической ошибке от MultiParsing Bot.
"""
        
        return body
    
    def _create_server_down_email_body(self, reason: str, additional_info: Optional[dict]) -> str:
        """Создает тело письма для уведомления о падении сервера."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        body = f"""
💥 СЕРВЕР MULTIPARSING BOT НЕ РАБОТАЕТ

Время: {timestamp}
Причина: {reason}

⚠️ БОТ НЕ ОТВЕЧАЕТ НА ЗАПРОСЫ!

"""
        
        if additional_info:
            body += self.ADDITIONAL_INFO_TEXT
            for key, value in additional_info.items():
                body += f"- {key}: {value}\n"
            body += "\n"
        
        body += """
---
Это автоматическое уведомление о падении сервера от MultiParsing Bot.
"""
        
        return body
    
    def _send_email(self, subject: str, body: str) -> bool:
        """
        Отправляет email.
        
        Args:
            subject: Тема письма
            body: Тело письма
            
        Returns:
            True если email отправлен успешно, False в противном случае
        """
        try:
            email, password = self._get_credentials()
            
            if not email or not password:
                logger.warning("Email credentials not configured. Cannot send notification.")
                return False
            
            smtp_config = self._get_smtp_config()
            
            # Создаем сообщение
            msg = MIMEMultipart()
            msg['From'] = email
            msg['To'] = self.alert_email
            msg['Subject'] = subject
            
            # Добавляем тело письма
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Подключаемся к SMTP серверу и отправляем
            context = ssl.create_default_context()
            
            with smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port']) as server:
                if smtp_config['use_tls']:
                    server.starttls(context=context)
                server.login(email, password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent successfully to {self.alert_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

# Глобальный экземпляр уведомлений
email_notifier = EmailNotifier()
