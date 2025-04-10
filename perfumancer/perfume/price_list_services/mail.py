import os
import asyncio
from collections import defaultdict
import imaplib
import email
import re
from email.header import decode_header
from email.utils import parseaddr
from datetime import datetime, timedelta
import logging
import aiofiles
from functools import wraps
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

logger = logging.getLogger(__name__)

BATCH_SIZE = 10
MAX_WORKERS = 4
RETRY_ATTEMPTS = 3
PROCESSED_EMAILS = set()


class IMAPConnectionPool:
    def __init__(self, host, username, password, pool_size=2):
        self.host = host
        self.username = username
        self.password = password
        self.pool_size = pool_size
        self.connections = asyncio.Queue()

    async def get_active_connection(self):
        """Get an active IMAP connection from the pool"""
        return await self.get_connection()

    async def __aenter__(self):
        for _ in range(self.pool_size):
            conn = await self._create_connection()
            await self.connections.put(conn)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        while not self.connections.empty():
            conn = await self.connections.get()
            await self._close_connection(conn)

    async def get_connection(self):
        return await self.connections.get()

    async def release_connection(self, conn):
        await self.connections.put(conn)

    async def _create_connection(self):
        conn = await asyncio.to_thread(imaplib.IMAP4_SSL, self.host)
        await asyncio.to_thread(conn.login, self.username, self.password)
        await asyncio.to_thread(conn.select, "INBOX")  # Select INBOX during connection setup
        return conn

    async def _close_connection(self, conn):
        try:
            await asyncio.to_thread(conn.close)
            await asyncio.to_thread(conn.logout)
        except:
            pass


async def start_server_email_standalone():
    """Отдельная функция работы с почтой"""
    logger.info("Сервер запущен!")

    pool = IMAPConnectionPool(
        os.getenv("IMAP_EMAIL"),
        os.getenv("USERNAME_EMAIL"),
        os.getenv("PASSWORD_EMAIL")
    )

    async with pool as imap:
        try:
            conn = await pool.get_active_connection()
            try:
                logger.info("Аутентификация прошла успешно!")
                emails = await fetch_emails_with_excel_attachments_async(conn, days=8)
                logger.info(f"Найдено {len(emails)} писем с прайсами")

                if emails:
                    logger.info("Начинаем сохранение вложений...")
                    await save_attachments_async(conn, emails)

                    for email_data in emails:
                        logger.debug("Письмо от %s (%s) с темой %s, вложение: %s",
                                     email_data["name"], email_data["address"],
                                     email_data["subject"], email_data["files"])
                else:
                    logger.info("Нет писем с вложениями Excel за последние 1 день.")
            finally:
                await pool.release_connection(conn)
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            raise


async def async_file_write(file_path: str, data: bytes):
    async with aiofiles.open(file_path, mode='wb') as f:
        await f.write(data)


def clean_header(header_value):
    """Очистка и декодирование MIME-заголовков и имен файлов."""
    if not header_value:
        return None
    result = ""
    for decoded, charset in decode_header(header_value):
        if isinstance(decoded, bytes):
            charset = charset or "utf-8"
            result += decoded.decode(charset, errors="ignore")
        else:
            result += decoded
    return result


def extract_excel_attachments_from_bodystructure(bodystructure):
    """Извлечение имен Excel-вложений из строки BODYSTRUCTURE."""
    attachments = []

    # Расширенный паттерн для поиска Excel-вложений
    excel_patterns = [
        # Стандартный паттерн для обычных Excel-файлов
        r'\("application" "vnd\.(ms-excel|openxmlformats-officedocument\.spreadsheetml\.sheet)".*?\("attachment" \("filename" "(.*?)"\)\)',

        # Альтернативный паттерн для других возможных форматов
        r'\("application" "octet-stream".*?\("attachment" \("filename" "(.*?\.xlsx?)"\)\)',

        # Паттерн для поиска по расширению файла
        r'\("attachment".*?\("filename" "(.*?\.xlsx?)"\)\)'
    ]

    for pattern in excel_patterns:
        if pattern.endswith('xlsx?)"\)\)'):
            # Для паттернов, где ищем по расширению, извлекаем только имя файла
            matches = re.findall(pattern, bodystructure, re.IGNORECASE)
            for filename in matches:
                if filename.lower().endswith(('.xls', '.xlsx')):
                    attachments.append(clean_header(filename))
        else:
            # Для остальных паттернов
            matches = re.findall(pattern, bodystructure, re.IGNORECASE)
            for items in matches:
                if isinstance(items, tuple):
                    # Если найдено несколько групп захвата
                    filename = items[-1]  # Берем последний элемент (имя файла)
                    attachments.append(clean_header(filename))
                else:
                    # Если найдена только одна группа
                    attachments.append(clean_header(items))

    # Удаляем дубликаты
    return list(dict.fromkeys(attachments))


def filter_message(messages_data):
    """
    Фильтрует сообщения и оставляет только самое последнее с Excel-вложением
    от каждого отправителя.
    """
    # Первый этап - отфильтровываем ненужные сообщения
    filtered_messages = []
    for message in messages_data:
        if not message.get("subject"):
            continue
        if 'накла' in message.get("subject", "").lower():
            continue
        if any('накла' in file.lower() for file in message.get("files", [])):
            continue
        filtered_messages.append(message)

    # Группируем по адресу отправителя и оставляем только самое свежее сообщение
    latest_messages = {}
    for message in filtered_messages:
        address = message["address"].lower()

        # Если адрес уже встречался, сравниваем даты
        if address in latest_messages:
            try:
                # Пытаемся преобразовать строки дат в datetime объекты для корректного сравнения
                current_date = email.utils.parsedate_to_datetime(message["date"])
                saved_date = email.utils.parsedate_to_datetime(latest_messages[address]["date"])

                # Если текущее сообщение новее, заменяем сохраненное
                if current_date > saved_date:
                    latest_messages[address] = message
            except:
                # Если не получается преобразовать даты, просто заменяем
                # (предполагая, что сообщения отсортированы по дате)
                latest_messages[address] = message
        else:
            # Если это первое сообщение от данного отправителя, сохраняем его
            latest_messages[address] = message

    # Преобразуем словарь обратно в список и сортируем по дате
    result = list(latest_messages.values())
    result.sort(key=lambda x: x.get("date", ""), reverse=True)  # Сортировка от новых к старым

    return result

async def fetch_emails_with_excel_attachments_async(imap, days=8):
    """Async version of fetch_emails_with_excel_attachments"""
    logger.info(f"Поиск писем с Excel-вложениями за последние %s дней...", days)
    try:
        last_day_date = (datetime.now() - timedelta(days=days)).strftime('%d-%b-%Y')
        status, messages = await asyncio.to_thread(
            imap.search, None, f'SINCE {last_day_date}'
        )
        if status != "OK":
            logger.error("Ошибка поиска писем")
            return []

        email_ids = messages[0].split()
        if not email_ids:
            logger.debug("Писем за последние дни не обнаружено")
            return []

        fetch_command = ",".join(email_id.decode('utf-8') for email_id in email_ids)
        res, fetched_data = await asyncio.to_thread(
            imap.fetch, fetch_command, '(BODYSTRUCTURE BODY.PEEK[HEADER])'
        )

        messages_data = []
        for response_part in fetched_data:
            if isinstance(response_part, tuple):
                try:
                    bodystructure = response_part[0].decode()
                    attachments = extract_excel_attachments_from_bodystructure(bodystructure)
                    if not attachments:
                        continue

                    msg = email.message_from_bytes(response_part[1])
                    msg_data = {
                        "name": parseaddr(clean_header(msg["From"]))[0],
                        "address": parseaddr(clean_header(msg["From"]))[1],
                        "subject": clean_header(msg["Subject"]),
                        "date": msg["Date"] or "Дата не указана",
                        "email_id": response_part[0].split()[0].decode("utf-8"),
                        "files": attachments
                    }
                    messages_data.append(msg_data)
                except Exception as e:
                    logger.error(f"Ошибка обработки письма: {e}")

        return filter_message(messages_data)
    except Exception as e:
        logger.error(f"Ошибка в процессе извлечения писем: {e}")
        return []


async def process_and_save_email(fetched_data, email_data, dir_path):
    """Process email data and save attachments asynchronously."""
    for response_part in fetched_data:
        if not isinstance(response_part, tuple):
            continue

        try:
            msg = email.message_from_bytes(response_part[1])
            for part in msg.walk():
                content_disposition = part.get("Content-Disposition", "")
                file_name = part.get_filename()

                if not (file_name and "attachment" in content_disposition):
                    continue

                decoded_name = clean_header(file_name)
                if decoded_name not in email_data["files"]:
                    continue

                file_extension = "." + decoded_name.split(".")[-1] if "." in decoded_name else ""
                file_path = os.path.join(dir_path, email_data["address"] + file_extension)

                payload = part.get_payload(decode=True)
                await async_file_write(file_path, payload)
                logger.debug(f"Сохранён файл: {file_path}")

        except Exception as e:
            logger.error(f"Ошибка при сохранении вложения для письма {email_data['email_id']}: {e}")


async def async_file_write(file_path: str, data: bytes):
    """Helper function to write files asynchronously."""

    def _write():
        with open(file_path, "wb") as f:
            f.write(data)

    await asyncio.to_thread(_write)


async def save_attachments_async(imap, emails):
    """Async version of save_attachments"""
    dir_path = "../" + os.getenv("SAVE_DIR")

    if not os.path.exists(dir_path):
        await asyncio.to_thread(os.makedirs, dir_path)

    for file in os.listdir(dir_path):
        file_path = os.path.join(dir_path, file)
        try:
            if os.path.isfile(file_path):
                await asyncio.to_thread(os.unlink, file_path)
        except Exception as e:
            logger.error("Ошибка удаления файла %s:", file_path, e)

    for email_data in emails:
        email_id = email_data["email_id"]
        res, fetched_data = await asyncio.to_thread(
            imap.fetch, email_id, '(BODY.PEEK[])'
        )
        if res != "OK":
            logger.error("Ошибка получения тела письма для ID %s", email_id)
            continue

        await process_and_save_email(fetched_data, email_data, dir_path)





def main_mail() -> bool:
    logger.info("Запуск почтовой службы")
    try:
        asyncio.run(start_server_email_standalone())
        # asyncio.run(print_grouped_sender_addresses())
        return True
    except Exception as e:
        logger.error(f"Ошибка в процессе работы с почтой: {e}")
        return False


if __name__ == "__main__":
    from dotenv import load_dotenv
    from perfumancer.perfume.utils.custom_logging import configure_color_logging
    load_dotenv()
    configure_color_logging(level="DEBUG")
    # Запуск функции
    main_mail()
