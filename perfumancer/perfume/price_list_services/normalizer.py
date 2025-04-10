import os
# from pathlib import Path

import pandas as pd
import re

from dotenv import load_dotenv

from .french_normalizer import FrenchNameNormalizer
# from dotenv import load_dotenv

from .brand import get_standard_brand_fuzzy, get_brand_from_name
from ..utils.price_file_formatter import format_price_list


_french_normalizer = FrenchNameNormalizer()

# ====== Справочники ======
# порядок и позиция важны
CONCENTRATION_MAP = {
    # EDP – Eau de Parfum
    'edp': 'EDP',
    'eau de parfum': 'EDP',
    'парфюмерная вода': 'EDP',
    'парфюмированная вода': 'EDP',
    'парфюмюрованная вода': 'EDP',

    # EDT – Eau de Toilette
    'edt': 'EDT',
    'eau de toilette': 'EDT',
    'туалетная вода': 'EDT',
    'toilet water': 'EDT',

    # EDC – Eau de Cologne
    'edc': 'EDC',
    'eau de cologne': 'EDC',
    'cologne': 'EDC',
    'одеколон': 'EDC',

    # Parfum / Extrait de Parfum
    'extrait de parfum': 'Parfum',
    'exrait de parfum': 'Parfum',
    'pp': 'Parfum',
    'parfum': 'Parfum',
    'perfume': 'Parfum',
    'духи': 'Parfum',
    'per': 'Parfum',
    'extrait': 'Parfum',

    # Дополнительная категория (если используется)
    'eau fraiche': 'Eau Fraiche',
    'свежая вода': 'Eau Fraiche',
}

TYPE_KEYWORDS = {
    'tester': 'тестер',
    'test': 'тестер',
    'тестер': 'тестер',
    '<tst>': 'тестер',
    'чуть подмятый': 'тестер',
    'подмятый': 'тестер',
    'подмятая': 'тестер',
    'подмятость': 'тестер',
    'подмят': 'тестер',
    'подм': 'тестер',
    'мятый': 'тестер',
    'без коробки': 'тестер',
    'повреждена упаковка': 'тестер',
}

GARBAGE_WORDS = ["пакет", "test золотые", "new", "пробник",
                    "mini", "мини", "minispray", "отливант",
                    "подарочный набор", "gift set", "сколы", "остаток",
                 "косметичка", "свеча", "balm", "с русификацией", "..&", "сломан",
                 "не хватает", "сумка", "клатч", "крем", "dutyfree",
                 ]

EXTRA_INFO_WORDS = ["sample", "(travel)", "travel", "пробирка", "probirka",
                    "fragrance world"]

GENDER_PATTERNS = [
    # Унисекс варианты (unisex)
    ('unisex', 'unisex'),
    ('unisexe', 'unisex'),
    ('уни', 'unisex'),
    (r'\bu\b', 'unisex'),  # Добавляем 'u' как унисекс

    # Женские варианты (female)
    ('women', 'female'),
    ('woman', 'female'),
    ('female', 'female'),
    ('femme', 'female'),
    ('fem', 'female'),
    ('lady', 'female'),
    ('ledy', 'female'),
    ('dame', 'female'),
    ('mrs', 'female'),
    ('miss', 'female'),
    ('her', 'female'),
    ('женская', 'female'),
    ('жен', 'female'),
    (r'\bw\b', 'female'),
    (r'\bwo\b', 'female'),
    ('♀', 'female'),

    # Мужские варианты (male)
    ('pour homme', 'male'),
    ('homme', 'male'),
    ('men', 'male'),
    ('man', 'male'),
    ('male', 'male'),
    ('gentleman', 'male'),
    ('mr', 'male'),
    ('мужской', 'male'),
    ('муж', 'male'),
    (r'\bm\b', 'male'),
    ('♂', 'male'),
]




COMMON_VOLUMES = [1, 1.5, 2, 5, 7, 8, 10, 15, 20, 30, 50, 75, 90, 100, 120, 125, 150, 200]

# Update the FLANKER_SYNONYMS list
FLANKER_SYNONYMS = [
    # Improve encre noire handling
    (r'\bencre\s+noir[e]?\b', 'encre noire'),
    (r'\bencre\s+noir[e]?(?:\s+|["`\'])?(?:a\s+)?(?:l[`\'\"])?(?:a\s+)?(?:l[`\'\"])?extreme\b',
     'encre noire a l\'extreme'),
    (r'\bencre\s+noir[e]?(?:\s+extreme|\s+a\s+extreme|\s+a\s+l\s*[\'`]extreme)\b', 'encre noire a l\'extreme'),

    # Original entries
    (r"a\s*l['\' ]?extreme\b", "a l'extreme"),
    (r"\bl['\' ]?extreme\b", "a l'extreme"),
    (r'\bextreme\b', "a l'extreme"),
    # New synonyms
    (r'\bexclusif\b', 'exclusive'),
    (r'\bexclusive\b', 'exclusive'),
    (r'\bexclusiv\b', 'exclusive'),

    # L'Amour variations
    (r'\bl[\'\s]*amour\s*de?\b', "l'amour"),
    (r'\bl[\'\s]*amour\s+de\s+lady\b', "l'amour"),
    (r'\blamour\b', "l'amour"),

    # Other common perfume name variations
    (r'\bnoir[e]?\b', 'noir'),
    (r'\bintens[ei]?\b', 'intense'),
    (r'\boriental[e]?\b', 'oriental'),
    (r'\bsport\b', 'sport'),
    (r'\blimit[ée]?d?\s*edition\b', 'limited edition'),
    (r'\blanc[he]?\b', 'blanc'),
    (r'\brouge\b', 'rouge'),
    (r'\bbleu[e]?\b', 'bleu'),
    (r'\bvert[e]?\b', 'vert'),
    (r'\bnuit\b', 'nuit'),
    (r'\blive\b', 'live'),
    (r'\blegere\b', 'legere'),
    (r'\baqua\b', 'aqua'),
    (r'\bpour\s+homme\b', 'pour homme'),
    (r'\bpour\s+femme\b', 'pour femme'),

    (r'\b(?:perles\s+de|perle\s+de)\b', 'perles de'),
    (r'\ble\s+baiser\s+de\b', 'le baiser'),
    (r'\bsatin[e]?\b', 'satine'),  # Normalize both satin and satine to satine

    # обработка апострофов
    (r"(\w)d\s+([aeiouy]\w*)", r"\1d'\2"),  # darpege -> d'arpege
    (r"(\w)d([aeiouy]\w*)", r"\1d'\2"),  # darpege -> d'arpege





]

def clean_trailing_prepositions(text: str) -> str:
    """Remove dangling French prepositions at the end of phrases."""
    return _french_normalizer.remove_dangling_prepositions(text)


def unify_concentration_by_volume_groups(df):
    """
    If multiple products share the same brand, aroma name, gender, and volume,
    but some have concentration specified and others don't, apply the specified
    concentration to all products in the group.
    """
    # Create groups by brand, aroma name, gender, and volume
    for (brand, aroma, gender, volume), group in df.groupby(['Canonical Brand', 'Aroma Name', 'Gender', 'Volume']):
        if len(group) > 1:  # There are multiple products in the group
            # Get all non-empty concentrations in the group
            concentrations = group['Concentration'].dropna().unique()
            concentrations = [c for c in concentrations if c and str(c).strip()]

            # If there's exactly one unique concentration, apply it to all items in the group
            if len(concentrations) == 1:
                concentration = concentrations[0]
                # Update all items in the group to have this concentration
                df.loc[group.index, 'Concentration'] = concentration

    return df


def normalize_aroma_variants(df):
    df['Aroma Name'] = df['Aroma Name'].apply(lambda x:
          # First do a direct match and replace for encre noire extreme variants
          'encre noire a l\'extreme' if (
                  (
                              'encre' in x.lower() and 'noir' in x.lower() and 'extreme' in x.lower()) or
                  re.search(
                      r'encre\s+noir[e]?(?:\s+|["`\'])?(?:a\s+)?(?:l[`\'\"])?(?:a\s+)?(?:l[`\'\"])?extreme',
                      x.lower())
          )
          # Handle l'amour variations
          else "l'amour" if re.search(r'l[\'\s]*amour\s*(?:de\s+)?(?:lady)?',
                                      x.lower())
          # Handle perles de variations - preserve the full name with what follows "perles de"
          else re.sub(r'\bperles?\s+de\s+(\w+)', r'perles de \1', x.lower(),
                      flags=re.IGNORECASE)
          if ('perle' in x.lower() and 'de' in x.lower())
          else x
          )
    # Создаем временную колонку с набором слов
    df['Word_Set'] = df['Aroma Name'].apply(lambda x: frozenset(x.lower().strip().split()))

    # Шаг 1: Группируем по бренду и набору слов для нормализации имён ароматов
    for (brand, words), group in df.groupby(['Canonical Brand', 'Word_Set']):
        if len(group) > 1:  # Есть варианты с одинаковыми словами
            # Берем вариант, который встречается чаще
            counts = group['Aroma Name'].value_counts()
            standard_name = counts.index[0]

            # Устанавливаем стандартное имя для всех вариантов
            df.loc[group.index, 'Aroma Name'] = standard_name

            # Проверяем гендеры в группе
            genders = set(group['Gender'].dropna())
            if 'unisex' in genders:
                # Если в группе есть unisex, устанавливаем его всем в группе
                df.loc[group.index, 'Gender'] = 'unisex'

    # Шаг 2: Дополнительная группировка только по бренду и имени аромата
    # для обработки случаев с одинаковыми названиями, но разными наборами слов
    for (brand, aroma_name), group in df.groupby(['Canonical Brand', 'Aroma Name']):
        if len(group) > 1:
            # Проверяем гендеры в этой группе
            genders = set(group['Gender'].dropna())

            # Если есть разные гендеры (м, ж, у)
            if len(genders) > 1 and 'unisex' in genders:
                # Если есть и мужской, и женский, и унисекс - приоритет у унисекс
                df.loc[group.index, 'Gender'] = 'unisex'
            # elif 'male' in genders and 'female' in genders:
            #     # Если есть и мужской, и женский (но нет унисекс) - считаем унисекс
            #     df.loc[group.index, 'Gender'] = 'unisex'

    # Удаляем временную колонку
    df.drop('Word_Set', axis=1, inplace=True)

    # Пересобираем канонические имена
    df['Canonical Name'] = df.apply(lambda row: assemble_canonical_name(
        row['Canonical Brand'], row['Aroma Name'], row['Gender'],
        row['Volume'], row['Concentration'], row['Type']), axis=1)

    return df


def preprocess_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return re.sub(r'\s+', ' ', text.strip().lower())

def fix_fractional_spaces(t: str) -> str:
    # "1 5 ml" -> "1.5 ml"
    t = re.sub(r'(\d)\s+(\d)(ml|мл)', r'\1.\2\3', t)
    t = re.sub(r'(\d)\s+(\d)\s+ml', r'\1.\2 ml', t)
    return t

# Изменение в функции extract_volume
def extract_volume(text: str) -> str:
    t = fix_fractional_spaces(text.lower()).replace(',', '.')

    # 1) oz (остается как есть)
    match_oz = re.search(r'(\d+(?:\.\d+)?)\s*(floz|oz)', t)
    if match_oz:
        val = float(match_oz.group(1)) * 29.57
        return f"{int(round(val))} мл"

    # 2) ml|мл|l|л - захватываем также точку после единиц измерения, если она есть
    match_vol = re.search(r'(\d+(?:\.\d+)?)\s*(ml|мл|l|л)\.?', t)
    if match_vol:
        val = float(match_vol.group(1))
        if match_vol.group(2) in ['l', 'л']:
            val *= 1000
        return f"{int(val) if val.is_integer() else val} мл"

    # 3) COMMON_VOLUMES (остается как есть)
    for vol in COMMON_VOLUMES:
        if re.search(rf'\b{vol}\b', t):
            return f"{int(vol) if float(vol).is_integer() else vol} мл"
    return ""

def extract_concentration(text: str) -> str:
    text_lower = text.lower()

    # Предварительно очищаем текст от лишних пробелов
    text_lower = ' '.join(text_lower.split())

    # Проверяем точное вхождение ключа в текст
    for key, canonical in CONCENTRATION_MAP.items():
        if key in text_lower:
            return canonical

    # Проверяем формат с границами слов
    for key, canonical in CONCENTRATION_MAP.items():
        # Для многословных ключей используем более гибкий подход
        if ' ' in key:
            words = key.split()
            pattern = r'\b' + r'\s+'.join([re.escape(word) for word in words]) + r'\b'
            if re.search(pattern, text_lower):
                return canonical
        else:
            if re.search(rf'\b{re.escape(key)}\b', text_lower):
                return canonical

    # Проверяем формат, где концентрация сразу следует за числами
    for key, canonical in CONCENTRATION_MAP.items():
        if re.search(rf'\b{re.escape(key)}\d+', text_lower):
            return canonical

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
        if pattern.startswith(r'\b'):
            # Pattern is a regex
            if re.search(pattern, text):
                return gender_value
        else:
            # Simple string matching for non-regex patterns
            if f" {pattern} " in f" {text} ":
                return gender_value
    return ""


def clean_extra_info(text: str) -> str:
    text = re.sub(r'\[.*?\]', '', text)  # убираем [ ... ]
    text = re.sub(r'[\"“”\']+', '', text)  # кавычки
    for w in EXTRA_INFO_WORDS:
        text = re.sub(rf'\b{w}\b', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def unify_flanker_words(text: str) -> str:
    for pattern, replacement in FLANKER_SYNONYMS:
        text = re.sub(pattern, replacement, text)
    return text


def normalize_french_names(text: str) -> str:
    """Обертка для совместимости со старым кодом."""
    return _french_normalizer.normalize(text)

def extract_aroma_name(original_text: str, brand: str, volume: str,
                       concentration: str, type_: str, gender: str) -> str:
    text = preprocess_text(original_text)

    text = clean_trailing_prepositions(text)

    # Special direct replacement for problem cases
    text_lower = text.lower()
    text = clean_extra_info(text_lower)
    # text_lower = preprocess_text(text_lower)

    # Special case for "encre noire a l'extreme"
    if ("encre" in text_lower and "noir" in text_lower and "extreme" in text_lower):
        # Apply direct extraction for these cases
        text = re.sub(r'encre\s+noir[e]?(?:\s+|["`\'])?(?:a\s+)?(?:l[`\'\"])?(?:a\s+)?(?:l[`\'\"])?extreme',
                      'encre noire a l\'extreme', text, flags=re.IGNORECASE)

    # Special case for "perles de" perfumes
    if "perle" in text_lower and "de" in text_lower:
        match = re.search(r'\bperles?\s+de\s+(\w+)', text_lower)
        if match:
            full_name = f"perles de {match.group(1)}"
            # Temporarily replace with a placeholder to prevent further processing
            text = re.sub(r'\bperles?\s+de\s+\w+', '__PERLES_DE_PLACEHOLDER__', text, flags=re.IGNORECASE)

    # Удаляем упоминание бренда, если он есть
    if brand and brand.lower() in text.lower():
        text = re.sub(rf'\b{re.escape(brand.lower())}\b', '', text, flags=re.IGNORECASE)

    # Удаляем все формы записи объема
    if volume:
        volume_num = re.match(r'^(\d+(?:\.\d+)?)', volume)
        if volume_num:
            v = volume_num.group(1)
            patterns = [
                rf'{re.escape(v)}\s*(ml|мл)\.?',  # Add \.? to handle trailing dot
                r'\.\d+\s*(ml|мл)\.?',  # Add \.? here too
                rf'\b{v.split(".")[0]}\s*(ml|мл)\.?\b' if '.' in v else '',
                rf'\b{v}\b'
            ]
            for p in [pp for pp in patterns if pp]:
                text = re.sub(p, '', text)

    # Удаляем все формы записи концентрации
    if concentration:
        # Находим все ключи из CONCENTRATION_MAP, которые соответствуют данной концентрации
        matching_keys = [key for key, value in CONCENTRATION_MAP.items() if value == concentration]

        # Удаляем все вхождения ключевых слов, ТОЛЬКО как отдельные слова
        for keyword in matching_keys:
            text = re.sub(rf'\b{re.escape(keyword)}\b', '', text, flags=re.IGNORECASE)
            # УДАЛЯЕМ эту строку - она вызывает проблему с "parfumees"
            # text = re.sub(rf'{re.escape(keyword)}', '', text, flags=re.IGNORECASE)

    # Дополнительный проход: удаляем все ключи из CONCENTRATION_MAP
    # вне зависимости от того, была ли определена концентрация
    for conc_key in CONCENTRATION_MAP.keys():
        text = re.sub(rf'\b{re.escape(conc_key)}\b', '', text, flags=re.IGNORECASE)

    # Удаляем ключевые слова типа (тестер, пробник и т.д.)
    if type_:
        synonyms = [k for (k, v) in TYPE_KEYWORDS.items() if v == type_]
        # Приводим текст к нижнему регистру для сравнения
        # lower_text = text.lower()
        for syn in synonyms:
            # Более надежное регулярное выражение с учетом возможных пробелов
            pattern = rf'(?<!\w){re.escape(syn)}(?!\w)'
            # Или используйте замену с учетом регистра для кириллицы
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # ИСПРАВЛЕННЫЙ БЛОК: Удаляем паттерны пола (муж, жен и т.д.)
    if gender:
        # Сначала явно удаляем гендерные символы
        if gender == 'male':
            text = text.replace('♂', '')
        elif gender == 'female':
            text = text.replace('♀', '')
        elif gender == 'unisex':
            text = text.replace('♂', '').replace('♀', '')

        # Затем удаляем все текстовые паттерны
        for pattern, gen_val in GENDER_PATTERNS:
            if gen_val == gender:
                if pattern.startswith(r'\b'):
                    # Это регулярное выражение
                    text = re.sub(pattern, '', text, flags=re.IGNORECASE)
                else:
                    # Это обычная строка - удаляем как точное совпадение
                    # Ищем как самостоятельное слово
                    text = re.sub(rf'\b{re.escape(pattern)}\b', '', text, flags=re.IGNORECASE)
                    # И как часть текста
                    text = text.replace(pattern, '')

    text = normalize_french_names(text)

    text = re.sub(r'[(),|\-\.]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    text = unify_flanker_words(text)
    text = re.sub(r'\s+', ' ', text).strip()

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


def assemble_canonical_name(brand: str, aroma: str, gender: str, volume: str,
                           conc: str, type_: str) -> str:
    parts = [p for p in [brand, aroma, gender, volume, conc, type_] if p and p.lower() not in ["nan", "noname"]]
    return " | ".join(parts)

def fill_column_if_unique(df: pd.DataFrame, fill_col: str, group_cols: list) -> pd.DataFrame:
    """
    Если в группе group_cols есть ровно одно непустое значение fill_col,
    то оно проставляется всем пустым записям в этой группе.
    """
    df = df.copy()
    for _, idx in df.groupby(group_cols).groups.items():
        subset = df.loc[idx, fill_col]
        # Improved: better handling of NaN values
        subset = subset.dropna().astype(str)
        non_empty = [x for x in subset if x.strip() and x.lower() not in ['nan', 'none']]
        if len(set(non_empty)) == 1:  # ровно одно уникальное значение
            unique_val = non_empty[0]
            # Improved: more accurate mask for empty values
            mask = df.loc[idx, fill_col].isna() | (df.loc[idx, fill_col].astype(str).str.strip() == '') | (df.loc[idx, fill_col].astype(str).str.lower() == 'nan') | (df.loc[idx, fill_col].astype(str).str.lower() == 'none')
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

        # Фильтруем строки, содержащие слова из GARBAGE_WORDS
        for word in GARBAGE_WORDS:
            self.df = self.df[~self.df["Наименование"].astype(str).str.lower().str.contains(word.lower(), na=False)]

        filtered_count = len(self.df)
        print(f"Удалено {original_count - filtered_count} строк, содержащих ключевые слова из GARBAGE_WORDS")

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
            can_name = assemble_canonical_name(can_brand, aroma, gender, vol, conc, ttype)

            return pd.Series({
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
                "Canonical Name": can_name
            })

        # 1) Прогоняем все строки через normalize_row
        result_df = self.df.apply(normalize_row, axis=1)
        print(
            f"После normalize_row: строк = {len(result_df)}, пустых Product Name = {(result_df['Product Name'].fillna('') == '').sum()}")

        # 3) ЗДЕСЬ добавляем нормализацию ароматов
        result_df = normalize_aroma_variants(result_df)

        # 3.5) Унифицируем концентрации в группах с одинаковым брендом, ароматом, гендером и объемом
        result_df = unify_concentration_by_volume_groups(result_df)

        # 2) Заполняем пропущенные Concentration и Gender
        result_df = fill_column_if_unique(
            result_df, fill_col="Concentration",
            group_cols=["Canonical Brand", "Aroma Name", "Gender", "Volume", "Type"]
        )
        result_df = fill_column_if_unique(
            result_df, fill_col="Gender",
            group_cols=["Canonical Brand", "Aroma Name"]
        )

        print(
            f"После fill_column_if_unique: строк = {len(result_df)}, пустых Product Name = {(result_df['Product Name'].fillna('') == '').sum()}")


        # After normalize_aroma_variants and unify_concentration_by_volume_groups
        result_df = fill_column_if_unique(
            result_df, fill_col="Concentration",
            group_cols=["Canonical Brand", "Aroma Name", "Gender", "Volume", "Type"]
        )

        # 3) Пересобираем Canonical Name (т.к. мог измениться Gender/Concentration)
        def reassemble(row):
            return assemble_canonical_name(
                row["Canonical Brand"], row["Aroma Name"], row["Gender"],
                row["Volume"], row["Concentration"], row["Type"]
            )

        result_df["Canonical Name"] = result_df.apply(reassemble, axis=1)

        print(
            f"После reassemble: строк = {len(result_df)}, пустых Product Name = {(result_df['Product Name'].fillna('') == '').sum()}")

        # 4) Смотрим, сколько товаров встречается у нескольких поставщиков
        suppliers_per_item = result_df.groupby("Canonical Name")["Supplier"].nunique()
        print("Товаров, встречающихся у нескольких поставщиков:",
              (suppliers_per_item > 1).sum())

        # 5) Убираем дубли (берём первую запись по минимальной цене)
        result_df = (
            result_df.sort_values("Price", ascending=True)
            .groupby("Canonical Name", as_index=False)
            .first()
        )
        return result_df


def main():
    file_path = "../" + os.getenv("OUTPUT_DIR") + "/combined_price_list_melted.xlsx"

    normalizer = PerfumeNormalizer(file_path, sheet_name=0)
    df_in = normalizer.load_file()


    result_df = normalizer.process()

    out_file = "../" + os.getenv("OUTPUT_DIR") + "/normalized_output.xlsx"
    result_df.to_excel(out_file, index=False)
    print(f"Готово! Итоговый файл: {out_file}")

    # Сортируем по бренду, а затем по наименованию
    sorted_df = result_df.sort_values(by=['Canonical Name'])

    # Создаем новый DataFrame только с нужными колонками и переименовываем их
    sorted_df = result_df[['Brand', 'Product Name', 'Price', 'Supplier']].copy()
    sorted_df.columns = ['Бренд', 'Наименование', 'Цена', 'Поставщик']


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
