import logging
import os
import re
from typing import List

import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from openpyxl import load_workbook

from ..utils.custom_logging import configure_color_logging

from ..models import Brand, Product, PriceList, Supplier, ProductBase, CurrencyRate

from .brand import get_standard_brand_fuzzy, get_brand_aliases, get_brand_from_name
from .xls_formatter import format_xls_to_xlsx
from .mail import main_mail as renew_prices_from_mail

logger = logging.getLogger(__name__)
configure_color_logging(level="INFO")
load_dotenv()


def get_currency_rate(currency_code):
    try:
        rate = CurrencyRate.objects.get(currency=currency_code).rate
        print(f"USDRUB: {rate}")
        return rate
    except CurrencyRate.DoesNotExist:
        logger.warning(
            "Курс валюты для %s не найден в базе данных, возвращаем курс по умолчанию",
            currency_code,
        )
        return float(120)


def clean_name(name, brand):
    name = re.sub(
        r"\s+",
        " ",
        name.lower()
        .replace("`", "'")
        .replace("''", "'")
        .replace("'nina'", "nina")
        .strip()
        .rstrip("."),
    )

    if brand:
        brand = brand.lower()
        brand_aliases = get_brand_aliases(brand)
        for alias in brand_aliases:
            if alias.lower() in name:
                for alias in brand_aliases:
                    name = name.replace(alias, "")
                name = f"{brand} {name}"
                break

    if brand and name.startswith(brand):
        name = name[len(brand) + 1 :]

    return name.lstrip(":").strip()


def auto_detect_columns(df):
    """
    Автоматически определяет, какие колонки соответствуют 'Название' и 'Цена'.
    """
    name_col = None
    price_col = None

    # Убираем строки без данных в начале
    df = df.dropna(how="all").reset_index(drop=True)

    # Убираем колонку, если она пустая везде, кроме первых 5 строк.
    for col in df.columns:
        if df[col].dropna().shape[0] < 5:
            df.drop(col, axis=1, inplace=True)

    # Регулярные выражения для формул Excel и UUID
    excel_formula_pattern = r"^=[A-Z]+\d+C\d+(?:[+\-*\/][A-Z]+\d+C\d+)*$"
    uuid_pattern = (
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )

    # Определяем колонку с названием
    for col in df.columns:
        non_empty_values = df[col].dropna()

        # Пропускаем строки, похожие на формулы Excel или UUID
        if (
            non_empty_values.str.contains(excel_formula_pattern, regex=True).any()
            or non_empty_values.str.contains(uuid_pattern, regex=True).any()
        ):
            continue

        # Проверяем длину строк - самая длинная строка более 30 символов
        if non_empty_values.iloc[10:].astype(str).str.len().max() > 30:
            name_col = col
            break

    if not name_col:
        logger.warning("Не удалось определить колонку с названием.")
        raise ValueError("Не удалось определить колонку с названием.")
    else:
        logger.debug(f"Колонка с названием: '{name_col}'")
        logger.debug("Первые 5 названий: %s", df[name_col].head(5).to_list())

    # Определяем колонку с ценой (правее названия)
    for col in df.columns[df.columns.get_loc(name_col) + 1 :]:
        non_empty_values = df[col].dropna()

        # Проверяем, что хотя бы 50% значений заполнены, числовые и не равны нулю и меньше 5000
        numeric_values = pd.to_numeric(non_empty_values, errors="coerce")
        if (
            numeric_values.notna().mean() > 0.5
            and numeric_values.mean() > 1
            and numeric_values.max() < 5000 * get_currency_rate("USD")
        ):
            price_col = col
            break
        else:
            logger.debug(f"⚠️ Колонка '{col}' не является колонкой с ценой.")
            # Дополнительная информация
            logger.debug(
                "Отношение заполненных значений: %s", numeric_values.notna().mean()
            )
            logger.debug("Минимальное значение: %s", numeric_values.min())
            logger.debug("Максимальное значение: %s", numeric_values.max())
            logger.debug("Среднее значение: %s", numeric_values.mean())

    if price_col is None:
        logger.debug("⚠️ Колонка с ценой не найдена.")
        return name_col, None

    logger.debug(
        f"Первые строки файла c Названием и Ценой:\n %s",
        df[[name_col, price_col]].head(10).to_string(),
    )
    return name_col, price_col


def process_price_list(file_path):
    """Обрабатывает один прайс-лист, выделяет торговые марки и сопоставляет их с товарами."""
    logger.info(
        "Чтение файла: %s", file_path
    )
    df = pd.read_excel(file_path, engine="openpyxl", header=None)
    if len(df) < 30:
        logger.warning(
            f"⚠️ Пропущен файл {file_path.name} из-за малого количества строк."
        )
        return None

    df.columns = [f"Колонка {i}" for i in range(len(df.columns))]

    # Определяем основные колонки
    try:
        name_col, price_col = auto_detect_columns(df)
    except ValueError as e:
        logger.warning(f"⚠️ Ошибка при автоматическом определении колонок: {e}")
        return None  # Прекращаем обработку текущего файла

    # Проверка: если колонка цены отсутствует, пропустить файл
    if price_col is None:
        logger.warning(
            f"⚠️ Колонка цены не найдена в файле {file_path.name}, обработка файла прекращена."
        )
        return None

    logger.info(
        f"Найдены колонки: Название - '{name_col}', Цена - '{price_col}'"
    )  # Было: print(...)
    df[name_col] = df[name_col].astype(str)

    # Обработка брендов
    df["brand"] = None
    # current_brand = None

    df["brand"] = df["brand"].replace(
        to_replace=r"^\s*(NAN|nan|NaN)\s*$", value=pd.NA, regex=True
    )

    brands = []
    for i, row in df.iterrows():
        name = row[name_col]
        price = row[price_col]

        # Определяем, является ли строка брендом
        if pd.isna(price) and name.strip():
            current_brand = name.strip().replace("\xa0", " ")
            current_brand = get_standard_brand_fuzzy(current_brand)
        else:
            current_brand = None

        brands.append(current_brand)

    if len(brands) != len(df):
        logger.warning(
            f"Длина brands ({len(brands)}) не совпадает с длиной df ({len(df)}), корректируем."
        )
        brands = (
            brands[: len(df)]
            if len(brands) > len(df)
            else brands + [None] * (len(df) - len(brands))
        )

    df["brand"] = brands
    # Убираем строки без названия

    df = df.dropna(subset=[name_col]).reset_index(drop=True)

    # Получаем бренд из имени
    df["brand"] = df.apply(
        lambda x: (
            get_brand_from_name(x[name_col])
            if pd.isna(x["brand"]) or x["brand"] == "NAN"
            else x["brand"]
        ),
        axis=1,
    )

    # Колонку с ценой делаем числовой
    df[price_col] = pd.to_numeric(df[price_col], errors="coerce")
    # Убираем строки без цены
    df = df.dropna(subset=[price_col]).reset_index(drop=True)
    if df[price_col].max() > 5000:
        logger.debug(
            "⚠️ Вероятно цена в рублях: максимальное значение цены больше 5000: %s",
            df[price_col].max(),
        )

        # получаем курс валюты из БД c приведением к Decimal
        usd_rub = pd.to_numeric(get_currency_rate("USD"), errors="coerce")

        # приводим цены к доллару
        df[price_col] = df[price_col] / usd_rub

    result_columns = ["brand", name_col, price_col]
    df[name_col] = df.apply(lambda x: clean_name(x[name_col], x["brand"]), axis=1)

    final_df = df[result_columns].rename(columns={name_col: "name", price_col: "price"})

    logger.debug(
        f"Обработка завершена для файла: {file_path}, колонки: {final_df.columns}"
    )  # Было: print(...)
    return final_df


def save_price_lists(df, filename):
    """
    Сохраняет прайс-лист в базу данных.

    :param df: DataFrame с данными
    :param filename: название файла
    """
    brand_dict = get_brand_id_dict()
    logger.info("Сохранение прайс-листа %s в базу данных...", filename)

    supplier, created = Supplier.objects.get_or_create(
        email=filename, defaults={"name": filename}
    )
    if not supplier:
        logger.warning("⚠️ Поставщик не найден в базе данных.")
        return

    # Создаем список новых продуктов и прайс-листов
    product_bases_to_create = []
    price_lists_to_create = []

    for _, row in df.iterrows():
        brand_name = row["brand"]
        name = row["name"]
        price = row[f"price_{filename}"]

        if brand_name is not None:  # проверка, что brand_name не None
            brand_id = brand_dict.get(brand_name)
            if not brand_id:
                logger.warning(f"⚠️ Бренд '{brand_name}' не найден в базе данных.")
                continue

            # Создaем экземпляр ProductBase и добавляем его в список
            product_base = ProductBase(raw_name=name, brand_id=brand_id)
            product_bases_to_create.append(product_base)

            # Создаем экземпляр PriceList и добавляем его в список
            price_list = PriceList(supplier_id=supplier.id, price=price)
            price_lists_to_create.append(price_list)

    # Массовое создание продуктов
    created_product_bases = ProductBase.objects.bulk_create(product_bases_to_create)

    # Устанавливаем продукты для соответствующих прайс-листов
    for price_list, product_base in zip(price_lists_to_create, created_product_bases):
        price_list.product = product_base

    # Массовое создание прайс-листов
    PriceList.objects.bulk_create(price_lists_to_create)
    logger.debug(f"Создано {len(price_lists_to_create)} прайс-листов.")


def save_unique_brands(unique_brands: List[str]) -> None:
    """
    Сохраняет уникальные бренды в базу данных, если они ещё не существуют.

    :param unique_brands: Список уникальных названий брендов (str).
    """
    existing_brands = set(Brand.objects.values_list("name", flat=True))

    # Фильтруем новые бренды
    new_brands = [
        Brand(name=brand_name)
        for brand_name in unique_brands
        if brand_name and brand_name not in existing_brands
    ]

    # Прерываем выполнение, если сохранять нечего.
    if not new_brands:
        logger.debug("Новые бренды отсутствуют, добавлять нечего.")
        return

    # Массовое сохранение новых брендов в базу.
    Brand.objects.bulk_create(new_brands)

    created_brand_names = [brand.name for brand in new_brands]
    logger.debug(f"Новые бренды добавлены: {', '.join(created_brand_names)}")


def get_supplier_dict():
    """
    Возвращает словарь, который сопоставляет префиксы email'ов с объектами поставщиков.
    """
    supplier_dict = {}
    suppliers = Supplier.objects.all()
    for supplier in suppliers:
        email_prefix = supplier.email.split("@")[0]  # Получаем префикс email до "@".
        supplier_dict[email_prefix] = supplier
    return supplier_dict


def get_brand_id_dict():
    return {brand.name: brand.id for brand in Brand.objects.all()}


def find_xlsx_files(directory_path):
    """Возвращает список всех .xlsx файлов в указанной папке."""
    target_dir = Path(directory_path)
    file_paths = [
        file for file in target_dir.glob("*.xlsx") if not file.name.startswith("~")
    ]

    if not file_paths:
        logger.info("В указанной папке %s нет файлов .xlsx.", target_dir)
        return []

    logger.info(f"Найдено {len(file_paths)} файлов .xlsx для обработки.")
    return file_paths


def process_file(file_path):
    """Обрабатывает один файл прайс-листа."""
    logger.debug("Обработка файла: %s", file_path.name)
    try:
        df = process_price_list(file_path)
        if df is None:
            logger.warning(
                f"⚠️ Пропущен файл {file_path.name} из-за отсутствия подходящих колонок."
            )
            return None

        df.rename(columns={"price": f"price_{file_path.stem}"}, inplace=True)
        return df
    except ValueError as e:
        logger.warning(f"⚠️ Пропущен файл {file_path.name}: {e}")
        return None


def merge_dataframes(dataframes):
    """Объединяет список DataFrame в один."""
    combined_df = dataframes[0]
    for df in dataframes[1:]:
        combined_df = pd.merge(combined_df, df, on=["brand", "name"], how="outer")

    combined_df.fillna({"price": 0}, inplace=True)
    return combined_df


def log_brand_info(combined_df):
    """Логирует информацию о брендах в объединённом DataFrame."""
    brands = [brand for brand in combined_df["brand"].unique() if brand]
    logger.debug(f"Уникальные бренды: {brands}")
    logger.info(f"Всего брендов: {len(brands)}")
    save_unique_brands(brands)


def save_combined_data(combined_df, all_prices):
    """Сохраняет объединённые данные и удаляет старые прайс-листы."""
    deleted = PriceList.objects.all().delete()
    deleted_ProductBase = ProductBase.objects.all().delete()
    logger.debug(f"Удалено {deleted[0]} прайс-листов")

    for file_name, df in all_prices.items():
        save_price_lists(df, file_name)

    logger.debug(f"Колонки в объединённом прайс-листе: {combined_df.columns}")


def merge_price_lists(directory_path):
    """Ищет все файлы .xlsx, обрабатывает их и объединяет в одну таблицу."""
    if not format_xls_to_xlsx(directory_path):
        return None

    file_paths = find_xlsx_files(directory_path)
    if not file_paths:
        return None

    all_data = []
    all_prices = {}

    for file_path in file_paths:
        # if 'nicheperfume' in str(file_path):
        df = process_file(file_path)
        if df is not None:
            all_data.append(df)
            all_prices[file_path.stem] = df

    if not all_data:
        logger.warning("Не найдено подходящих данных для объединения.")
        return None

    combined_df = merge_dataframes(all_data)
    log_brand_info(combined_df)

    save_combined_data(combined_df, all_prices)

    return combined_df


def format_price_list(file_path):
    # Открытие Excel-файла для изменения ширины колонок
    workbook = load_workbook(file_path)
    sheet = workbook.active

    overall_max_length = 50

    # Настройка ширины колонок по содержимому
    for column in sheet.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            if cell.value:  # Вычисляем длину содержимого ячейки
                max_length = max(max_length, len(str(cell.value)))
        adjusted_width = min(max_length, overall_max_length)
        sheet.column_dimensions[column_letter].width = adjusted_width

    # Сохранение изменений в файле
    workbook.save(file_path)


def save_combined_price(result, dir_path):
    # мелтинг
    result = result.melt(
        id_vars=["brand", "name"], var_name="price_list", value_name="price"
    ).dropna(subset=["price"])

    result["supplier"] = result["price_list"].str.replace("price_", "")

    supplier_dict = {}
    suppliers = Supplier.objects.all()
    for supplier in suppliers:
        supplier_dict[supplier.email] = supplier.name

    result["supplier"] = result["supplier"].map(supplier_dict)

    # Переименовываем колонки на русский и переставляем их
    result = result[["supplier", "brand", "name", "price"]]
    result.columns = ["Поставщик", "Бренд", "Наименование", "Цена"]

    # result.to_excel(Path(dir_path) / "combined_price_list_melted.xlsx", index=False)

    # форматируем excel файл
    # format_price_list(Path(dir_path) / "combined_price_list_melted.xlsx")


def main() -> bool:
    # Идем на почту
    if not renew_prices_from_mail():
        return False

    dir_path = "../" + os.getenv("SAVE_DIR")
    logger.info("Директория: %s", dir_path)
    # process_file(Path(dir_path) / "f.sanakov@1st-original.ru.xlsx")
    result = merge_price_lists(dir_path)
    if result is not None:
        # result.to_excel("combined_price_list.xlsx", index=False)
        save_combined_price(result, dir_path)

        logger.info("Добавлено записей: %s", len(result))
    else:
        return False

    return True


if __name__ == "__main__":
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "perfumancer.settings.local")
    django.setup()

    from ..models import Brand, Product, PriceList, Supplier, ProductBase, CurrencyRate

    main(  )