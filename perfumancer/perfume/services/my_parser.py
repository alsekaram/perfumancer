import re

import pandas as pd
from pathlib import Path

from django.db import IntegrityError, transaction



from .brand import get_standard_brand_fuzzy, get_brand_aliases, get_brand_from_name




def extract_volume(name):
    name = re.sub(" +", " ", name.lower())

    """Извлекает объем из названия товара и нормализует в формат float."""
    if not isinstance(name, str):
        return None
    volume_match = re.search(r"(\d+([.,]\d+)?)\s*?-*?\s*?ml\.?", name.lower())
    if volume_match:
        volume = volume_match.group(1).replace(",", ".")
        return float(volume)
    return None


def extract_tester(name):
    """Проверяет, является ли товар тестером, включая <TST>, и возвращает 'тестер' или None."""
    if not isinstance(name, str):
        return None
    if re.search(r"(\btester\b|\bтестер\b|\btest\b|\bsample\b|<tst>)", name.lower()):
        return "тестер"
    return None


def extract_extra(name):
    """Извлекает дополнительные обозначения, такие как <пляжный эффект>, исключая тестеры."""
    extra = re.findall(r"<.*?>", name)
    extra = [e for e in extra if not re.search(r"<tst>", e.lower())]
    return ", ".join(extra) if extra else None


def replace_once(name):
    replacements = [
        ("(m)", "man"),
        (" m ", " man "),
        (" men ", " man "),
        ("for men", "man"),
        ("for man", "man"),
        ("(l)", "woman"),
        (" l ", " woman "),
        (" w ", " woman "),
        (" wom ", " woman "),
        ("for women", "woman"),
        ("lady", "woman"),
        (" women", " woman"),
    ]
    name = name.lower()
    name = name + " "
    for old, new in replacements:
        if "pour femme" in name or "pour homme" in name:
            name = name.replace(old, "")
        else:
            if old in name:

                name = name.replace(old, new)
                name = name.strip()
                return name

    name = name.strip()
    return name


def remove_second_occurrence(s, target):
    first_occurrence_index = s.find(target)
    if first_occurrence_index != -1:
        second_occurrence_index = s.find(target, first_occurrence_index + len(target))
        if second_occurrence_index != -1:
            s = s[:second_occurrence_index] + s[second_occurrence_index + len(target) :]
    return s


def clean_name(name, brand):
    # по ключу из get_standard_brand получаем стандартное название бренда и меняем то что есть в названии на стандартное
    # name = name.lower()
    name = re.sub(" +", " ", name.lower())

    name = re.sub(r"(\d+([.,]\d+)?)\s*?-*?\s*?ml\.?", "", name.lower())
    name = re.sub(r"<.*?>", "", name)
    name = re.sub(r"(tester|тестер|test|sample)", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name)

    name = name.replace("`", "'")
    name = name.replace("''", "'")

    name = name.replace("'nina'", "nina")

    name = replace_once(name)

    name = name.strip().rstrip(".").strip()

    if "l'homme" in name and "man" in name:
        name = name.replace("man", "")

    if "femme" in name and "woman" in name:
        name = name.replace("woman", "")

    name = name.replace("extrait de parfum", "exdp")
    # name = re.sub(r'extrait de parfum', 'exdp', name, flags=re.IGNORECASE)
    name = name.replace("extra de parfum", "exdp")

    name = remove_second_occurrence(name, "man")
    name = remove_second_occurrence(name, "woman")
    if brand != "CALVIN KLEIN":
        name = name.replace("woman", "pour femme")
        name = name.replace("man", "pour homme")
        name = remove_second_occurrence(name, "pour homme")
        name = remove_second_occurrence(name, "pour femme")

    name = re.sub(" +", " ", name.lower())

    name = name.replace("jtc", "join the club")
    name = name.replace("new", "")
    # убираем год (первая цифра 1 или 2)
    name = re.sub(r"\b[12]\d{3}\b", "", name)

    name = name.lower()
    if brand:
        brand = brand.lower()
        brand_aliases = get_brand_aliases(brand)
        # print(name, brand)
        if brand_aliases:
            for alias in brand_aliases:
                if alias.lower() in name.lower():
                    # и чистим строку от других алиасов этого бренда
                    for alias in brand_aliases:
                        if alias.lower() in name.lower():
                            name = name.replace(alias, "")
                    # и добавляем бренд в начало строки
                    name = brand + " " + name

                    break

    # если name начинается с названия бренда - убираем его
    if brand:
        if name.startswith(brand.lower()):
            name = name[len(brand) + 1 :]

        name = f"{brand.lower()} {name}"

    return name.strip()


def auto_detect_columns(df):
    """
    Автоматически определяет, какие колонки соответствуют 'Название' и 'Цена'.
    """
    name_col = None
    price_col = None

    # Убираем строки без данных в начале
    df = df.dropna(how="all").reset_index(drop=True)

    # Убираем колонку если она пустая везде, кроме первых 3 строк строки
    for col in df.columns:
        if df[col].dropna().shape[0] < 3:
            df.drop(col, axis=1, inplace=True)

    # Определяем колонку с названием
    for col in df.columns:
        non_empty_values = df[col].dropna()
        if all(isinstance(v, str) for v in non_empty_values):  # Колонка с текстом
            name_col = col

            break

    if not name_col:
        raise ValueError("Не удалось определить колонку с названием.")

    # Определяем колонку с ценой (правее названия)
    for col in df.columns[df.columns.get_loc(name_col) + 1 :]:
        non_empty_values = df[col].dropna()
        # и не все равный нулю

        # Проверяем, что хотя бы 50% значений заполнены, числовые и не равный нулю и меньше 10000
        numeric_values = pd.to_numeric(non_empty_values, errors="coerce")
        if (
            numeric_values.notna().mean() > 0.5
            and numeric_values.min() > 0
            and numeric_values.max() < 10000
        ):
            price_col = col
            break

    if not price_col:
        print("⚠️ Колонка с ценой не найдена, обработка продолжается без неё.")
    print(
        f"Первые строки файла c Названием и Ценой:\n {df[[name_col, price_col]].head(10)}"
    )

    return name_col, price_col


def process_price_list(file_path):
    """Обрабатывает один прайс-лист, выделяет торговые марки и сопоставляет их с товарами."""
    print(f"Чтение файла: {file_path}")
    df = pd.read_excel(file_path, engine="openpyxl", header=None)
    # print(f"Первые строки файла {file_path}:\n{df.head(10)}")

    df.columns = [f"Колонка {i}" for i in range(len(df.columns))]

    # Определяем основные колонки
    try:
        name_col, price_col = auto_detect_columns(df)
    except ValueError as e:
        print(f"⚠️ Ошибка при автоматическом определении колонок: {e}")
        raise

    print(f"Найдены колонки: Название - '{name_col}', Цена - '{price_col}'")

    df[name_col] = df[name_col].astype(str)

    # Обработка брендов
    df["brand"] = None
    current_brand = None
    brands = []

    for i, row in df.iterrows():
        name = row[name_col]
        price = row[price_col] if price_col else None

        # Определяем, является ли строка брендом
        if pd.isna(price) and name.strip():
            current_brand = name.strip()
            current_brand = get_standard_brand_fuzzy(current_brand)

        brands.append(current_brand)

    df["brand"] = brands

    # Убираем строки без названия
    df = df.dropna(subset=[name_col]).reset_index(drop=True)
    df["brand"] = df.apply(
        lambda x: (
            get_brand_from_name(x[name_col]) if x["brand"] == "NAN" else x["brand"]
        ),
        axis=1,
    )

    # Извлекаем объем, тестер и дополнительные обозначения
    df["volume"] = df[name_col].apply(
        lambda x: extract_volume(x) if isinstance(x, str) else None
    )
    df["tester"] = df[name_col].apply(
        lambda x: extract_tester(x) if isinstance(x, str) else None
    )
    df["extra"] = df[name_col].apply(
        lambda x: extract_extra(x) if isinstance(x, str) else None
    )
    df[name_col] = df.apply(lambda x: clean_name(x[name_col], x["brand"]), axis=1)
    # Приведение volume к числовому типу
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

    # если бренд называется 'NAN' ищем бренд в имени

    # колонку с ценой делаем числовой, если не получается - значение должно быть пустым
    if price_col:
        df[price_col] = pd.to_numeric(df[price_col], errors="coerce")
        # Убираем строки без цены
        df = df.dropna(subset=[price_col]).reset_index(drop=True)

    result_columns = ["brand", name_col, "volume", "tester", "extra"]
    if price_col:
        result_columns.append(price_col)

    return df[result_columns].rename(columns={name_col: "name", price_col: "price"})


def save_unique_brands(brands):
    """
    Сохраняет уникальные бренды в базу данных.

    :param brands: список уникальных брендов
    """
    for brand_name in brands:
        if brand_name:
            # Если бренд уже существует, он не будет создан
            brand_obj, created = Brand.objects.get_or_create(name=brand_name)
            if created:
                print(f"Новый бренд сохранен в базу данных: {brand_name}")

def get_supplier_dict():
    """
    Возвращает словарь, который сопоставляет префиксы email'ов с объектами поставщиков.
    """
    supplier_dict = {}
    suppliers = Supplier.objects.all()
    for supplier in suppliers:
        email_prefix = supplier.email.split('@')[0]  # Получаем префикс email до "@".
        supplier_dict[email_prefix] = supplier
    return supplier_dict


def get_brand_id_dict():
    return {brand.name: brand.id for brand in Brand.objects.all()}


def save_price_lists(df, brand_dict):
    products_to_create = []
    pricelists_to_create = []

    # Извлекаем поставщиков из базы данных и создаем словарь с префиксами
    suppliers = PerfumeSupplier.objects.all()
    supplier_dict = {supplier.email.split('@')[0]: supplier.id for supplier in suppliers}

    # Заменяем NaN на 0.0 в колонке volume
    df['volume'] = df['volume'].fillna(0.0)

    # Перебираем столбцы с ценами
    for price_column in ['price_9', 'price_23', 'price_ast', 'price_OPT', 'price_OfferTemplate', 'price_igor']:
        prefix = price_column.replace('price_', '')

        # Получаем ID поставщика по префиксу электронной почты
        supplier_id = supplier_dict.get(prefix)
        if not supplier_id:
            print(f"⚠️ Поставщик для префикса '{prefix}' не найден.")
            continue

        for _, row in df.iterrows():
            name = row['name']
            brand_name = row['brand']
            volume = float(row['volume'])
            is_tester = row['tester'] == "тестер"
            price = row[price_column]

            brand_id = brand_dict.get(brand_name)
            if not brand_id:
                print(f"⚠️ Бренд '{brand_name}' не найден.")
                continue

            # Create or find the brand
            brand, created = PerfumeBrand.objects.get_or_create(id=brand_id)

            # Add product for creation
            product = PerfumeProduct(name=name, brand_id=brand.id, volume=volume, is_tester=is_tester)
            products_to_create.append(product)

            # Add price list entry
            pricelist_entry = PerfumePriceList(price=price, supplier_id=supplier_id)
            pricelists_to_create.append(pricelist_entry)

    # Массовая вставка всех новых объектов PerfumeProduct и PerfumePriceList
    try:
        with transaction.atomic():
            PerfumeProduct.objects.bulk_create(products_to_create)
            PerfumePriceList.objects.bulk_create(pricelists_to_create)

        print(f"Создано {len(products_to_create)} новых продуктов и {len(pricelists_to_create)} записей в прайс-листе.")
    except IntegrityError as e:
        print(f"Ошибка уникальности: {e}")

def merge_price_lists(directory_path):
    """Ищет все файлы .xlsx в указанной папке, обрабатывает их и объединяет в одну таблицу."""
    all_data = []
    file_paths = list(Path(directory_path).glob("*.xlsx"))
    if not file_paths:
        print("В указанной папке нет файлов .xlsx.")
        return None

    print(f"Найдено {len(file_paths)} файлов .xlsx для обработки.")

    for file_path in file_paths:
        print(f"Обработка файла: {file_path.name}")
        try:
            df = process_price_list(file_path)
            file_name = file_path.stem
            df.rename(columns={"price": f"price_{file_name}"}, inplace=True)
            all_data.append(df)
        except ValueError as e:
            print(f"⚠️ Пропущен файл {file_path.name}: {e}")
            continue

    combined_df = all_data[0]
    for df in all_data[1:]:
        combined_df = pd.merge(
            combined_df,
            df,
            on=["brand", "name", "volume", "tester", "extra"],
            how="outer",
        )

    combined_df.fillna({"price": 0}, inplace=True)
    # список колонок
    print(f"Колонки в объединённом прайс-листе: {combined_df.columns}")

    # печатем уникальные бренды через запятую исключая None
    brands = combined_df["brand"].unique()
    brands = [brand for brand in brands if brand]
    print(f"Уникальные бренды: {brands}")
    # всего брендов
    print(f"Всего брендов: {len(brands)}")
    save_unique_brands(brands)
    supplier_dict = get_supplier_dict()
    brand_dict = get_brand_id_dict()
    save_price_lists(combined_df, brand_dict, supplier_dict)

    # выводим название всех колонок
    print(f"Колонки в объединённом прайс-листе: {combined_df.columns}")

    return combined_df


def main() -> None:
    directory = os.path.abspath("./perfume/services/prices")
    print(directory)
    result = merge_price_lists(directory)
    if result is not None:
        result.to_excel("combined_price_list.xlsx", index=False)
        # всего записей
        print(f"Всего записей: {len(result)}")
        # число строк где правее колонки 'extra' есть хотя бы два значения
        print(
            f"Записей с несколькими ценами: {result[result.columns[result.columns.get_loc('extra') + 1:]].count(axis=1).gt(1).sum()}"
        )

        print("✅ Объединённый прайс-лист сохранён в файл 'combined_price_list.xlsx'.")


if __name__ == "__main__":
    import os
    import django

    print(django.VERSION)
    # Установите DJANGO_SETTINGS_MODULE и выполните настройку Django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "perfumancer.settings")
    django.setup()
    from ..models import Brand, Product, PriceList, Supplier

    main()
