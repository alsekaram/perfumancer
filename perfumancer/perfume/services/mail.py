import os
import time
import asyncio
import imaplib
import email
import re
from email.header import decode_header
from email.utils import parseaddr
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


async def start_server_email_standalone():
    """Отдельная функция работы с почтой"""
    logger.info("Сервер запущен!")
    try:
        imap = imaplib.IMAP4_SSL(os.getenv("IMAP_EMAIL"))
        IsLogin = imap.login(os.getenv("USERNAME_EMAIL"), os.getenv("PASSWORD_EMAIL"))
        if IsLogin[1][0].decode('UTF-8') == 'Authentication successful':
            logger.info("Аутентификация прошла успешно!")

            # Проверка новых писем в папке INBOX
            imap.select("INBOX")
            emails = fetch_emails_with_excel_attachments(imap, days=8)
            logger.info(f"Найдено {len(emails)} писем с прайсами")

            if emails:
                logger.info("Начинаем сохранение вложений...")

                save_attachments(imap, emails)

                for email_data in emails:
                    logger.debug("Письмо от %s (%s) с темой %s, вложение: %s",
                                 email_data["name"], email_data["address"], email_data["subject"], email_data["files"])

            else:
                logger.info("Нет писем с вложениями Excel за последние 1 день.")
        else:
            logger.error("Аутентификация не удалась! Повторное подключение через 60 секунд")
            time.sleep(60)
    except imaplib.IMAP4.error as e:
        logger.error(f"Ошибка IMAP: {e}")
        await asyncio.sleep(60)


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
    pattern = r'\("application" "vnd\.(ms-excel|openxmlformats-officedocument\.spreadsheetml\.sheet)".*?\("attachment" \("filename" "(.*?)"\)\)'
    matches = re.findall(pattern, bodystructure, re.IGNORECASE)
    for _, encoded_filename in matches:
        attachments.append(clean_header(encoded_filename))
    return attachments


def fetch_emails_with_excel_attachments(imap, days=8):
    """Получение информации о письмах с Excel-вложениями за последние N дней."""
    logger.info(f"Поиск писем с Excel-вложениями за последние %s дней...", days)
    try:
        last_day_date = (datetime.now() - timedelta(days=days)).strftime('%d-%b-%Y')
        status, messages = imap.search(None, f'SINCE {last_day_date}')
        if status != "OK":
            logger.error("Ошибка поиска писем")
            return []

        email_ids = messages[0].split()
        if not email_ids:
            logger.debug("Писем за последние дни не обнаружено")
            return []
        logger.info("Писем за последние дни найдено: %d", len(email_ids))

        fetch_command = ",".join(email_id.decode('utf-8') for email_id in email_ids)
        logger.debug("Получение STRUCTURE и HEADER писем с ID: %s", fetch_command)

        # Загружаем только структуру и заголовки
        res, fetched_data = imap.fetch(fetch_command, '(BODYSTRUCTURE BODY.PEEK[HEADER])')
        if res != "OK":
            logger.error("Ошибка массового получения писем")
            return []
        logger.info("Письма успешно получены")

        messages_data = []
        for response_part in fetched_data:
            if isinstance(response_part, tuple):
                try:
                    # Получаем структуру и заголовки
                    bodystructure = response_part[0].decode() if response_part[0] else ""
                    logger.debug(f"Структура BODYSTRUCTURE для письма: {bodystructure}")

                    # Определяем наличие вложений Excel
                    attachments = extract_excel_attachments_from_bodystructure(bodystructure)
                    logger.info("Найдены вложения: %s", attachments)
                    if not attachments:
                        continue

                    # Парсим заголовки
                    msg = email.message_from_bytes(response_part[1])
                    msg_data = {
                        "name": parseaddr(clean_header(msg["From"]))[0],  # Извлечение имени отправителя
                        "address": parseaddr(clean_header(msg["From"]))[1],  # Извлечение адреса отправителя
                        "subject": clean_header(msg["Subject"]),
                        "date": msg["Date"] or "Дата не указана",
                        "email_id": response_part[0].split()[0].decode("utf-8"),
                        "files": attachments  # Оставляем информацию о файлах
                    }
                    messages_data.append(msg_data)
                except Exception as e:
                    logger.error(f"Ошибка обработки письма: {e}")

        logger.info(f"Найдено {len(messages_data)} писем с Excel-вложениями за последние {days} дней")
        messages_data = filter_message(messages_data)
        return messages_data

    except Exception as e:
        logger.error(f"Ошибка в процессе извлечения писем: {e}")
        return []


def filter_message(messages_data):
    filtered_messages = []
    for message in messages_data:
        # Если есть тема
        if not message.get("subject"):
            continue
        # Проверяем наличие подстроки в теме
        if 'накла' in message.get("subject", "").lower():
            continue  # Пропускаем это письмо

        # Проверяем наличие подстроки в названиях вложений
        if any('накла' in file.lower() for file in message.get("files", [])):
            continue  # Пропускаем это письмо

        # Если проверка пройдена, добавляем сообщение в результат
        filtered_messages.append(message)
    unique_senders = {msg["address"]: msg for msg in filtered_messages}
    logger.info(f"Найдено {len(unique_senders)} уникальных адресов")
    # У каждого сообщения в unique_senders есть дата, сортируем по дате сообщения для каждого адреса и оставляем только последнее
    filtered_messages = [msg for msg in sorted(unique_senders.values(), key=lambda x: x["date"])]

    return filtered_messages


def save_attachments(imap, emails):
    dir_path = "./" + os.getenv("SAVE_DIR")

    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    # если директория не пустая - удаляем все файлы
    for file in os.listdir(dir_path):
        file_path = os.path.join(dir_path, file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            logger.error("Ошибка удаления файла %s:",  file_path, e)

    logger.info("Директория %s очищена", dir_path)

    # time.sleep(60)
    for email_data in emails:
        email_id = email_data["email_id"]
        res, fetched_data = imap.fetch(email_id, '(BODY.PEEK[])')
        if res != "OK":
            logger.error("Ошибка получения тела письма для ID %s", email_id)
            continue

        for response_part in fetched_data:
            if isinstance(response_part, tuple):
                try:
                    msg = email.message_from_bytes(response_part[1])
                    for part in msg.walk():
                        content_disposition = part.get("Content-Disposition", "")
                        file_name = part.get_filename()
                        if file_name and "attachment" in content_disposition:
                            decoded_name = clean_header(file_name)
                            file_extension = "." + decoded_name.split(".")[-1] if "." in decoded_name else ""
                            if decoded_name in email_data["files"]:
                                file_path = os.path.join(dir_path, email_data["address"] + file_extension)
                                with open(file_path, "wb") as f:
                                    f.write(part.get_payload(decode=True))
                                logger.debug(f"Сохранён файл: {file_path}")
                except Exception as e:
                    logger.error(f"Ошибка при сохранении вложения для письма {email_id}: {e}")


def main_mail() -> bool:
    logger.info("Запуск почтовой службы")
    try:
        asyncio.run(start_server_email_standalone())
        return True
    except Exception as e:
        logger.error(f"Ошибка в процессе работы с почтой: {e}")
        return False


if __name__ == "__main__":
    from dotenv import load_dotenv
    from perfumancer.perfume.utils.custom_logging import configure_color_logging

    load_dotenv()

    configure_color_logging(level="DEBUG")

    main_mail()
