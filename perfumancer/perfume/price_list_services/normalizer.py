import math
import os

# from pathlib import Path

import pandas as pd
import re

from dotenv import load_dotenv

from .french_normalizer import FrenchNameNormalizer

# ====== Справочники ======
# порядок и позиция важны
from .constants import (
    CONCENTRATION_MAP,
    TYPE_KEYWORDS,
    EXTRA_INFO_WORDS,
    GENDER_PATTERNS,
    COMMON_VOLUMES,
    FLANKER_SYNONYMS,
)


# from dotenv import load_dotenv

from .brand import get_standard_brand_fuzzy, get_brand_from_name
from ..utils.price_file_formatter import format_price_list


_french_normalizer = FrenchNameNormalizer()


def clean_trailing_prepositions(text: str) -> str:
    """Remove dangling French prepositions at the end of phrases."""
    return _french_normalizer.remove_dangling_prepositions(text)


def _build_pattern(key: str) -> re.Pattern:
    """
    Для «многословных» ключей разрешаем любое количество пробелов
    (edp, напротив, ищем строго как цельное слово).
    """
    if " " in key:
        words = map(re.escape, key.split())
        return re.compile(r"\b" + r"\s+".join(words) + r"\b")
    else:
        return re.compile(rf"\b{re.escape(key)}\b")


# пред-компилируем все паттерны
CONC_PATTERNS = [
    (canonical, _build_pattern(key)) for key, canonical in CONCENTRATION_MAP.items()
]


# -----------------------------------------------------------------
# помощник: проверка «пустой» ячейки гендера ----------------------
def _is_blank_gender(series: pd.Series) -> pd.Series:
    """True, если NaN, None, '', 'nan', 'none' (регистронезависимо)."""
    return series.isna() | series.astype(str).str.strip().str.lower().isin(
        ["", "nan", "none"]
    )


# -----------------------------------------------------------------
def assign_female_to_eclat(
    df: pd.DataFrame,
    aroma_col: str = "Aroma Name",
    gender_col: str = "Gender",
) -> pd.DataFrame:
    """
    Всем строкам с ароматом *eclat d'arpege* и пустым гендером
    проставляем 'female'.  Работает in-place и возвращает df
    (удобно для чейнинга).
    """
    mask_aroma = df[aroma_col].str.lower().str.strip() == "eclat d'arpege"
    mask_no_gndr = _is_blank_gender(df[gender_col])

    df.loc[mask_aroma & mask_no_gndr, gender_col] = "female"
    return df


def extract_concentration(text: str) -> str:
    """
    Возвращает каноническую концентрацию (EDP / EDT / PARFUM …)
    или '' (пустую строку), если в исходном тексте ничего похожего нет.
    """
    t = " ".join(text.lower().split())  # нормализуем пробелы
    for canonical, pattern in CONC_PATTERNS:
        if pattern.search(t):
            return canonical
    return ""  # ←  Ничего не нашли


# -------------------------------------------------
# 2.  Унифицируем концентрацию внутри групп
# -------------------------------------------------
def unify_concentration_by_volume_groups(df: pd.DataFrame) -> pd.DataFrame:
    """
    * Если в группе (бренд, аромат, пол, объём) присутствует ровно одна
      непустая концентрация — проставляем её во всей группе.
    * Если в группе несколько разных непустых концентраций — удаляем строки,
      где концентрация пустая (NaN или '').
    """

    def _is_blank(val) -> bool:
        """True, если NaN или пустая/пробельная строка."""
        return pd.isna(val) or not str(val).strip()

    for _, grp in df.groupby(["Canonical Brand", "Aroma Name", "Gender", "Volume"]):
        # уникальные НЕПУСТЫЕ концентрации (регистр игнорируем)
        non_blank = (
            grp.loc[~grp["Concentration"].apply(_is_blank), "Concentration"]
            .str.strip()
            .str.upper()
            .unique()
        )

        if len(non_blank) == 1:  # одна → размазываем
            df.loc[grp.index, "Concentration"] = non_blank[0]

        elif len(non_blank) > 1:  # несколько → чистим
            blank_idx = grp.loc[grp["Concentration"].apply(_is_blank)].index
            df.drop(blank_idx, inplace=True)

    return df


def normalize_aroma_variants(df):
    df["Aroma Name"] = df["Aroma Name"].apply(
        lambda x:
        # First do a direct match and replace for encre noire extreme variants
        (
            "encre noire a l'extreme"
            if (
                (
                    "encre" in x.lower()
                    and "noir" in x.lower()
                    and "extreme" in x.lower()
                )
                or re.search(
                    r'encre\s+noir[e]?(?:\s+|["`\'])?(?:a\s+)?(?:l[`\'\"])?(?:a\s+)?(?:l[`\'\"])?extreme',
                    x.lower(),
                )
            )
            # Handle l'amour variations
            else (
                "l'amour"
                if re.search(r"l[\'\s]*amour\s*(?:de\s+)?(?:lady)?", x.lower())
                # Handle perles de variations - preserve the full name with what follows "perles de"
                else (
                    re.sub(
                        r"\bperles?\s+de\s+(\w+)",
                        r"perles de \1",
                        x.lower(),
                        flags=re.IGNORECASE,
                    )
                    if ("perle" in x.lower() and "de" in x.lower())
                    else x
                )
            )
        )
    )
    # Создаем временную колонку с набором слов
    df["Word_Set"] = df["Aroma Name"].apply(
        lambda x: frozenset(x.lower().strip().split())
    )

    # Шаг 1: Группируем по бренду и набору слов для нормализации имён ароматов
    for (brand, words), group in df.groupby(["Canonical Brand", "Word_Set"]):
        if len(group) > 1:  # Есть варианты с одинаковыми словами
            # Берем вариант, который встречается чаще
            counts = group["Aroma Name"].value_counts()
            standard_name = counts.index[0]

            # Устанавливаем стандартное имя для всех вариантов
            df.loc[group.index, "Aroma Name"] = standard_name

            # Проверяем гендеры в группе
            genders = set(group["Gender"].dropna())
            if "unisex" in genders:
                # Если в группе есть unisex, устанавливаем его всем в группе
                df.loc[group.index, "Gender"] = "unisex"

    # Шаг 2: Дополнительная группировка только по бренду и имени аромата
    # для обработки случаев с одинаковыми названиями, но разными наборами слов
    for (brand, aroma_name), group in df.groupby(["Canonical Brand", "Aroma Name"]):
        if len(group) > 1:
            # Проверяем гендеры в этой группе
            genders = set(group["Gender"].dropna())

            # Если есть разные гендеры (м, ж, у)
            if len(genders) > 1 and "unisex" in genders:
                # Если есть и мужской, и женский, и унисекс - приоритет у унисекс
                df.loc[group.index, "Gender"] = "unisex"
            # elif 'male' in genders and 'female' in genders:
            #     # Если есть и мужской, и женский (но нет унисекс) - считаем унисекс
            #     df.loc[group.index, 'Gender'] = 'unisex'

    # Удаляем временную колонку
    df.drop("Word_Set", axis=1, inplace=True)

    # Пересобираем канонические имена
    df["Canonical Name"] = df.apply(
        lambda row: assemble_canonical_name(
            row["Canonical Brand"],
            row["Aroma Name"],
            row["Gender"],
            row["Volume"],
            row["Concentration"],
            row["Type"],
        ),
        axis=1,
    )

    return df


def preprocess_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", text.strip().lower())


def fix_fractional_spaces(t: str) -> str:
    # "1 5 ml" -> "1.5 ml"
    t = re.sub(r"(\d)\s+(\d)(ml|мл)", r"\1.\2\3", t)
    t = re.sub(r"(\d)\s+(\d)\s+ml", r"\1.\2 ml", t)
    return t


def extract_volume(text: str) -> str:

    t = fix_fractional_spaces(text.lower()).replace(",", ".")

    # Ищем ВСЕ совпадения «число + единица измерения»
    matches = list(
        re.finditer(
            r"(\d+(?:[.,]\d+)?)\s*(ml|мл|l|л)\b", t.lower()  # <-- [.,] вместо \.
        )
    )
    if matches:
        # Берём ПОСЛЕДНЕЕ совпадение
        m = matches[-1]
        value = float(m.group(1))
        unit = m.group(2)

        # Переводим литры → миллилитры
        if unit in {"l", "л"}:
            value *= 1000

        # Красивый вывод: без .0, если число целое
        value = int(value) if value.is_integer() else value
        return f"{value} мл"

    # Фоллбэк: ищем популярные объёмы без указания единиц
    for vol in COMMON_VOLUMES:  # например ['30', '50', '100', ...]
        if re.search(rf"\b{vol}\b", t):
            value = float(vol)
            value = int(value) if value.is_integer() else value
            return f"{value} мл"

    return ""


def extract_type(text: str) -> str:
    t = text.lower()
    for kw, val in TYPE_KEYWORDS.items():
        if kw in t:
            return val
    return ""


def extract_gender(text: str) -> str:
    text = text.lower()

    for pattern, gender_value in GENDER_PATTERNS:
        if pattern.startswith(r"\b"):
            # Pattern is a regex
            if re.search(pattern, text):
                return gender_value
        else:
            # Simple string matching for non-regex patterns
            if f" {pattern} " in f" {text} ":
                return gender_value
    return ""


# ─── стало ────────────────────────────────────────────────────────
_extra_re = re.compile(
    r"\b(?:" + "|".join(map(re.escape, EXTRA_INFO_WORDS)) + r")\b",
    flags=re.IGNORECASE,
)


def clean_extra_info(text: str) -> str:
    """
    Убирает кавычки, [скобки] и «мусорные» слова из EXTRA_INFO_WORDS
    за ОДИН проход по строке.
    """
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r'[\"""\']+', "", text)
    text = re.sub(r"^\s*:", "", text)
    text = re.sub(r"№\s+(\d+)", r"№\1", text)

    # новый быстрый вызов
    text = _extra_re.sub("", text)

    return re.sub(r"\s+", " ", text).strip()


def unify_flanker_words(text: str) -> str:
    for pattern, replacement in FLANKER_SYNONYMS:
        text = re.sub(pattern, replacement, text)
    return text


def normalize_french_names(text: str) -> str:
    """Обертка для совместимости со старым кодом."""
    return _french_normalizer.normalize(text)


def collapse_split_letters(text: str) -> str:
    """
    Превращает разбитые буквы в слова, сохраняя пробелы между словами.
    Примеры:
    'c.l,u,b,' → 'club'
    'l a d y' → 'lady'
    'c_h_a_n_e_l' → 'chanel'
    'c.l.u.b de paris' → 'club de paris'
    """
    # Разбиваем текст на слова по пробелам
    words = text.split()
    processed_words = []

    for word in words:
        # Применяем регулярное выражение только если слово содержит буквы и разделители
        if re.search(r"[a-zа-я][\s\.,\/_-]+[a-zа-я]", word, re.I):
            # Извлекаем только буквы из слова
            processed_word = "".join(re.findall(r"[a-zа-я]", word, re.I))
            processed_words.append(processed_word)
        else:
            processed_words.append(word)

    # Объединяем обработанные слова обратно в текст
    result = " ".join(processed_words)
    return result


def extract_aroma_name(
    original_text: str,
    brand: str,
    volume: str,
    concentration: str,
    type_: str,
    gender: str,
) -> str:
    text = preprocess_text(original_text)

    text = clean_trailing_prepositions(text)

    # Special direct replacement for problem cases
    text_lower = text.lower()
    # text = clean_extra_info(text_lower)

    # text_lower = preprocess_text(text_lower)

    # Special case for "encre noire a l'extreme"
    if "encre" in text_lower and "noir" in text_lower and "extreme" in text_lower:
        # Apply direct extraction for these cases
        text = re.sub(
            r'encre\s+noir[e]?(?:\s+|["`\'])?(?:a\s+)?(?:l[`\'\"])?(?:a\s+)?(?:l[`\'\"])?extreme',
            "encre noire a l'extreme",
            text,
            flags=re.IGNORECASE,
        )

    # Special case for "perles de" perfumes
    if "perle" in text_lower and "de" in text_lower:
        match = re.search(r"\bperles?\s+de\s+(\w+)", text_lower)
        if match:
            full_name = f"perles de {match.group(1)}"
            # Temporarily replace with a placeholder to prevent further processing
            text = re.sub(
                r"\bperles?\s+de\s+\w+",
                "__PERLES_DE_PLACEHOLDER__",
                text,
                flags=re.IGNORECASE,
            )

    # Удаляем упоминание бренда, если он есть
    if brand and brand.lower() in text.lower():
        text = re.sub(rf"\b{re.escape(brand.lower())}\b", "", text, flags=re.IGNORECASE)

    text = clean_extra_info(text_lower)

    # Удаляем все формы записи объема
    if volume:
        # Нормализуем входящий объем, заменяя пробелы между цифрами на точку
        volume = re.sub(r"(\d+)\s+(\d+)", r"\1.\2", volume)

        # Обрабатываем случай когда в volume только "ml"/"мл" без числа
        if volume.lower() in ["ml", "мл"]:
            text = re.sub(r"\b(?:ml|мл)\b", "", text, flags=re.IGNORECASE)

        # Извлекаем числовое значение
        volume_num = re.match(r"^(\d+(?:\.\d+)?)", volume)
        if volume_num:
            v = volume_num.group(1)

            # Проверяем, есть ли в тексте числа с ml/мл и соответствующие им одиночные числа
            # Если в тексте есть "7.5 мл" и где-то "7", это может быть одно и то же значение
            whole_part = v.split(".")[0]

            patterns = [
                rf"{re.escape(v)}\s*(?:ml|мл)\.?",  # 50 ml, 50 мл
                r"\.\d+\s*(?:ml|мл)\.?",  # .5 ml
                rf"\b{whole_part}\s*(?:ml|мл)\.?\b",  # целая часть с единицами измерения
                rf"\b{v}\b",  # просто число
                # Форматы с пробелом вместо точки
                rf"\b{whole_part}\s+\d+\s*(?:ml|мл)\.?\b" if "." in v else "",
                # Отдельное число, совпадающее с объемом или его частью
                rf"\b{whole_part}\b" if whole_part != v else "",
            ]

            # Удаляем все найденные шаблоны
            for p in [pp for pp in patterns if pp]:
                text = re.sub(p, "", text)

            # Дополнительно проверяем числа, которые могут быть частью объема
            # Например, если объем 7.5 мл, ищем отдельно стоящие "7" и "7.5"
            decimal_pattern = r"\b(\d+)(?:\.(\d+))?\b"
            numbers_in_text = re.finditer(decimal_pattern, text)

            for match in numbers_in_text:
                num = match.group(0)
                # Если число совпадает с объемом или его целой частью и после него не идут единицы измерения
                if (num == v or num == whole_part) and not re.match(
                    r"\s*(?:ml|мл)", text[match.end() : match.end() + 3]
                ):
                    # Удаляем это число, если оно скорее всего является повторением объема
                    if re.search(rf"{re.escape(v)}\s*(?:ml|мл)", text) or re.search(
                        rf"{whole_part}\.?\d*\s*(?:ml|мл)", text
                    ):
                        text = text[: match.start()] + text[match.end() :]

        # Финальная очистка лишних "ml"/"мл" без цифр
        text = re.sub(r"\b(?:ml|мл)\b", "", text, flags=re.IGNORECASE)

        # Удаляем оставшиеся метки объема в стандартных форматах
        text = re.sub(r"\b\d+(?:\.\d+)?\s*(?:ml|мл)\b", "", text)

    text = collapse_split_letters(text)

    # Удаляем все формы записи концентрации
    if concentration:
        # Находим все ключи из CONCENTRATION_MAP, которые соответствуют данной концентрации
        matching_keys = [
            key for key, value in CONCENTRATION_MAP.items() if value == concentration
        ]

        # Удаляем все вхождения ключевых слов, ТОЛЬКО как отдельные слова
        for keyword in matching_keys:
            text = re.sub(rf"\b{re.escape(keyword)}\b", "", text, flags=re.IGNORECASE)
            # УДАЛЯЕМ эту строку - она вызывает проблему с "parfumees"
            # text = re.sub(rf'{re.escape(keyword)}', '', text, flags=re.IGNORECASE)

    # Дополнительный проход: удаляем все ключи из CONCENTRATION_MAP
    # вне зависимости от того, была ли определена концентрация
    for conc_key in CONCENTRATION_MAP.keys():
        text = re.sub(rf"\b{re.escape(conc_key)}\b", "", text, flags=re.IGNORECASE)

    # Удаляем ключевые слова типа (тестер, пробник и т.д.)
    if type_:
        synonyms = [k for (k, v) in TYPE_KEYWORDS.items() if v == type_]
        # Приводим текст к нижнему регистру для сравнения
        # lower_text = text.lower()
        for syn in synonyms:
            # Более надежное регулярное выражение с учетом возможных пробелов
            pattern = rf"(?<!\w){re.escape(syn)}(?!\w)"
            # Или используйте замену с учетом регистра для кириллицы
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # ИСПРАВЛЕННЫЙ БЛОК: Удаляем паттерны пола (муж, жен и т.д.)
    if gender:
        # Сначала явно удаляем гендерные символы
        if gender == "male":
            text = text.replace("♂", "")
        elif gender == "female":
            text = text.replace("♀", "")
        elif gender == "unisex":
            text = text.replace("♂", "").replace("♀", "")

        # Затем удаляем все текстовые паттерны
        for pattern, gen_val in GENDER_PATTERNS:
            if gen_val == gender:
                if pattern.startswith(r"\b"):
                    # Это регулярное выражение
                    text = re.sub(pattern, "", text, flags=re.IGNORECASE)
                else:
                    # Это обычная строка - удаляем как точное совпадение
                    # Ищем как самостоятельное слово
                    text = re.sub(
                        rf"\b{re.escape(pattern)}\b", "", text, flags=re.IGNORECASE
                    )
                    # И как часть текста
                    text = text.replace(pattern, "")

    text = normalize_french_names(text)

    text = re.sub(r"[(),|\-\.]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    text = unify_flanker_words(text)
    text = re.sub(r"\s+", " ", text).strip()

    # Restore the "perles de" placeholder if it exists
    if "__PERLES_DE_PLACEHOLDER__" in text:
        text = text.replace("__PERLES_DE_PLACEHOLDER__", full_name)

    # Спец-обработка perles de для Lalique
    if brand.lower() == "lalique":
        # если видим 'perles de' + что-то, заменяем на 'Perles de Lalique'
        text_lower = text.lower()
        if "perles de" in text_lower:
            # принудительно ставим единый вариант
            return "Perles de Lalique"

    return text if text else "NoName"


def assemble_canonical_name(
    brand: str, aroma: str, gender: str, volume: str, conc: str, type_: str
) -> str:
    parts = [
        p
        for p in [brand, aroma, gender, volume, conc, type_]
        if p and p.lower() not in ["nan", "noname"]
    ]
    return " | ".join(parts)


def fill_column_if_unique(
    df: pd.DataFrame, fill_col: str, group_cols: list
) -> pd.DataFrame:
    """
    Если в группе group_cols есть ровно одно непустое значение fill_col,
    то оно проставляется всем пустым записям в этой группе.
    """
    df = df.copy()
    for _, idx in df.groupby(group_cols).groups.items():
        subset = df.loc[idx, fill_col]
        # Improved: better handling of NaN values
        subset = subset.dropna().astype(str)
        non_empty = [
            x for x in subset if x.strip() and x.lower() not in ["nan", "none"]
        ]
        if len(set(non_empty)) == 1:  # ровно одно уникальное значение
            unique_val = non_empty[0]
            # Improved: more accurate mask for empty values
            mask = (
                df.loc[idx, fill_col].isna()
                | (df.loc[idx, fill_col].astype(str).str.strip() == "")
                | (df.loc[idx, fill_col].astype(str).str.lower() == "nan")
                | (df.loc[idx, fill_col].astype(str).str.lower() == "none")
            )
            df.loc[idx, fill_col] = df.loc[idx, fill_col].where(~mask, unique_val)
    return df


class PerfumeNormalizer:
    def __init__(self, file_path, sheet_name=None):
        self.file_path = file_path
        self.sheet_name = sheet_name
        self.df = None

    def load_file(self):
        df = pd.read_excel(self.file_path, sheet_name=self.sheet_name)
        self.df = df if not isinstance(df, dict) else list(df.values())[0]
        return self.df

    def normalize_brand(self, raw_brand: str, product_name: str) -> str:
        """Определяем бренд по полю 'raw_brand' или извлекаем его из названия."""
        if raw_brand and raw_brand.strip().lower() != "nan":
            return get_standard_brand_fuzzy(raw_brand)
        else:
            return get_brand_from_name(product_name)

    def process(self):
        if self.df is None:
            raise ValueError("Сначала вызовите load_file().")

        # Сохраняем исходное количество строк для отчета
        original_count = len(self.df)

        def normalize_row(row):
            supplier, raw_brand, product_name, price = row.iloc[:4]
            name_clean = preprocess_text(product_name)

            brand = raw_brand
            vol = extract_volume(name_clean)
            conc = extract_concentration(name_clean)
            ttype = extract_type(name_clean)
            gender = extract_gender(name_clean)
            aroma = extract_aroma_name(product_name, brand, vol, conc, ttype, gender)

            can_brand = brand if brand else ""
            can_name = assemble_canonical_name(
                can_brand, aroma, gender, vol, conc, ttype
            )

            return pd.Series(
                {
                    "Supplier": supplier,
                    "Brand": raw_brand,
                    "Product Name": product_name,
                    "Price": price,
                    "Canonical Brand": can_brand,
                    "Volume": vol,
                    "Concentration": conc,
                    "Gender": gender,
                    "Type": ttype,
                    "Aroma Name": aroma,
                    "Canonical Name": can_name,
                }
            )

        # 1) Прогоняем все строки через normalize_row
        result_df = self.df.apply(normalize_row, axis=1)
        print(
            f"После normalize_row: строк = {len(result_df)}, пустых Product Name = {(result_df['Product Name'].fillna('') == '').sum()}"
        )

        # 3) ЗДЕСЬ добавляем нормализацию ароматов
        result_df = normalize_aroma_variants(result_df)

        # 3.5) Унифицируем концентрации в группах с одинаковым брендом, ароматом, гендером и объемом
        result_df = unify_concentration_by_volume_groups(result_df)

        # 2) Заполняем пропущенные Concentration и Gender
        result_df = fill_column_if_unique(
            result_df,
            fill_col="Concentration",
            group_cols=["Canonical Brand", "Aroma Name", "Gender", "Volume", "Type"],
        )
        result_df = fill_column_if_unique(
            result_df, fill_col="Gender", group_cols=["Canonical Brand", "Aroma Name"]
        )

        result_df = assign_female_to_eclat(result_df)

        print(
            f"После fill_column_if_unique: строк = {len(result_df)}, пустых Product Name = {(result_df['Product Name'].fillna('') == '').sum()}"
        )

        # After normalize_aroma_variants and unify_concentration_by_volume_groups
        result_df = fill_column_if_unique(
            result_df,
            fill_col="Concentration",
            group_cols=["Canonical Brand", "Aroma Name", "Gender", "Volume", "Type"],
        )

        # 3) Пересобираем Canonical Name (т.к. мог измениться Gender/Concentration)
        def reassemble(row):
            return assemble_canonical_name(
                row["Canonical Brand"],
                row["Aroma Name"],
                row["Gender"],
                row["Volume"],
                row["Concentration"],
                row["Type"],
            )

        result_df["Canonical Name"] = result_df.apply(reassemble, axis=1)

        print(
            f"После reassemble: строк = {len(result_df)}, пустых Product Name = {(result_df['Product Name'].fillna('') == '').sum()}"
        )

        # 4) Смотрим, сколько товаров встречается у нескольких поставщиков
        suppliers_per_item = result_df.groupby("Canonical Name")["Supplier"].nunique()
        print(
            "Товаров, встречающихся у нескольких поставщиков:",
            (suppliers_per_item > 1).sum(),
        )

        # 5) Убираем дубли (берём первую запись по минимальной цене)
        result_df = (
            result_df.sort_values("Price", ascending=True)
            .groupby("Canonical Name", as_index=False)
            .first()
        )
        return result_df


def main():
    # file_path = "../" + os.getenv("OUTPUT_DIR") + "/combined_price_list_melted.xlsx"
    file_path = "../" + os.getenv("OUTPUT_DIR") + "/nan_clear_pl.xlsx"

    normalizer = PerfumeNormalizer(file_path, sheet_name=0)
    df_in = normalizer.load_file()

    result_df = normalizer.process()

    out_file = "../" + os.getenv("OUTPUT_DIR") + "/normalized_output.xlsx"
    result_df.to_excel(out_file, index=False)
    print(f"Готово! Итоговый файл: {out_file}")

    # Сортируем по бренду, а затем по наименованию
    sorted_df = result_df.sort_values(by=["Canonical Name", "Product Name"])

    # Создаем новый DataFrame только с нужными колонками и переименовываем их
    sorted_df = result_df[
        [
            "Brand",
            # "Canonical Name",
            "Product Name",
            "Price",
            "Supplier",
        ]
    ].copy()

    # Округляем значения цен до 2 знаков в большую сторону
    sorted_df["Price"] = sorted_df["Price"].apply(lambda x: math.ceil(x * 100) / 100)

    # Переименовываем колонки на русский язык
    sorted_df.columns = [
        "Бренд",
        # "Нормализация",
        "Наименование",
        "Цена",
        "Поставщик",
    ]

    # Сохраняем в новый файл
    sorted_out_file = "../" + os.getenv("OUTPUT_DIR") + "/sorted_brands_output.xlsx"
    sorted_df.to_excel(sorted_out_file, index=False)
    print(f"Готово! Файл, отсортированный по бренду и наименованию: {sorted_out_file}")
    format_price_list(sorted_out_file)


if __name__ == "__main__":
    load_dotenv()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(script_dir)

    main()
