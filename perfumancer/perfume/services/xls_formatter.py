import os
from pathlib import Path
import pandas as pd
import logging


def format_xls_to_xlsx(directory_path: str) -> bool:
    """
    Конвертирует все файлы .xls в указанной директории в .xlsx.
    """
    target_dir = Path("./" + os.getenv("SAVE_DIR"))


    # Проверяем существование директории
    if not target_dir.exists():
        logging.error("Указанной директории не существует: %s", target_dir)
        return False

    # имена файлов переводятся в нижний регистр
    for file_name in os.listdir(target_dir):
        file_path = target_dir / file_name
        new_file_path = target_dir / file_name.lower()

        if file_path != new_file_path:
            file_path.rename(new_file_path)

    logging.debug("начинаем конвертацию файлов в директории: %s", target_dir)

    # Флаг для фиксации успешной конвертации
    conversion_successful = False
    xlsx_files_exist = False

    for file_name in os.listdir(target_dir):
        file_path = target_dir / file_name

        if file_name.endswith(".xlsx"):
            xlsx_files_exist = True
            continue

        if not file_name.endswith(".xls"):
            logging.debug("пропущен неподходящий файл: %s", file_name)
            continue

        xlsx_file_path = file_path.with_suffix(".xlsx")

        # Конвертируем файл
        if convert_file(file_path, xlsx_file_path):
            remove_file(file_path)
            conversion_successful = True

    if not conversion_successful and not xlsx_files_exist:
        logging.debug("подходящих файлов для конвертации не найдено и файлов .xlsx нет.")
        return False

    return True


def convert_file(xls_path: Path, xlsx_path: Path) -> bool:
    """читает .xls и конвертирует в .xlsx."""
    try:
        if xlsx_path.exists():
            logging.debug("файл .xlsx уже существует: %s", xlsx_path)
            return False

        data_frame = pd.read_excel(xls_path)
        data_frame.to_excel(xlsx_path, engine="openpyxl", index=False)
        logging.debug("файл сконвертирован: %s → %s", xls_path, xlsx_path)

        return True
    except Exception as error:
        logging.error("ошибка при обработке файла %s: %s", xls_path, str(error))
        return False


def remove_file(file_path: Path):
    """удаляет указанный файл .xls."""
    try:
        file_path.unlink()
        logging.debug("удалён исходный файл: %s", file_path)
    except Exception as error:
        logging.error("ошибка при удалении файла %s: %s", file_path, str(error))
