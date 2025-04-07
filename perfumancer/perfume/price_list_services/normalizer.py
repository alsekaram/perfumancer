import os
# from pathlib import Path

import pandas as pd
import re

# from dotenv import load_dotenv

from .brand import get_standard_brand_fuzzy, get_brand_from_name
from ..utils.price_file_formatter import format_price_list

# ====== Справочники ======
CONCENTRATION_MAP = {
    'edp': 'EDP',
    'eau de parfum': 'EDP',
    'парфюмерная вода': 'EDP',
    'парфюмированная вода': 'EDP',
    'extrait de parfum': 'EDP',
    'extrait': 'EDP',
    'edt': 'EDT',
    'eau de toilette': 'EDT',
    'туалетная вода': 'EDT',
    'edc': 'EDC',
    'eau de cologne': 'EDC',
    'pp': 'Parfum',
    'parfum': 'Parfum',
    'духи': 'Parfum'
}

TYPE_KEYWORDS = {
    'tester': 'тестер',
    'test': 'тестер',
    'тестер': 'тестер',
    '<tst> ': 'тестер',
    'пробник': 'пробник',
    'sample': 'пробник',
    'mini': 'mini',
    'мини': 'mini',
    'minispray': 'mini',
    'отливант': 'отливант',
    'подарочный набор': 'giftset',
    'gift set': 'giftset',
    'повреждена упаковка': 'повреждена упаковка'
}

GENDER_PATTERNS = [
    ('women', 'female'),  # Check women before w or man
    ('woman', 'female'),  # Check woman before w or man
    ('female', 'female'),
    ('lady', 'female'),
    ('ledy', 'female'),
    ('her', 'female'),
    ('жен', 'female'),
    (r'\bw\b', 'female'),
    (r'\bwo\b', 'female'),
    ('pour homme', 'male'),
    ('men', 'male'),
    ('man', 'male'),
    (r'\bm\b', 'male'),
    ('муж', 'male'),
    ('unisex', 'unisex'),
    ('уни', 'unisex'),
]


EXTRA_INFO_WORDS = ["пакет", "test золотые", "new"]

COMMON_VOLUMES = [1, 1.5, 2, 5, 7, 8, 10, 15, 20, 30, 50, 75, 90, 100, 120, 125, 150, 200]

FLANKER_SYNONYMS = [
    (r'\bencre noir\b', 'encre noire'),
    (r'a\s*l[’\' ]?extreme\b', "a l'extreme"),
    (r'\bl[’\' ]?extreme\b', "a l'extreme"),
    (r'\bextreme\b', "a l'extreme"),
]


def preprocess_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return re.sub(r'\s+', ' ', text.strip().lower())

def fix_fractional_spaces(t: str) -> str:
    # "1 5 ml" -> "1.5 ml"
    t = re.sub(r'(\d)\s+(\d)(ml|мл)', r'\1.\2\3', t)
    t = re.sub(r'(\d)\s+(\d)\s+ml', r'\1.\2 ml', t)
    return t

def extract_volume(text: str) -> str:
    t = fix_fractional_spaces(text.lower()).replace(',', '.')

    # 1) oz
    match_oz = re.search(r'(\d+(?:\.\d+)?)\s*(floz|oz)', t)
    if match_oz:
        val = float(match_oz.group(1)) * 29.57
        return f"{int(round(val))} мл"

    # 2) ml|мл|l|л
    match_vol = re.search(r'(\d+(?:\.\d+)?)\s*(ml|мл|l|л)', t)
    if match_vol:
        val = float(match_vol.group(1))
        if match_vol.group(2) in ['l', 'л']:
            val *= 1000
        return f"{int(val) if val.is_integer() else val} мл"

    # 3) COMMON_VOLUMES
    for vol in COMMON_VOLUMES:
        if re.search(rf'\b{vol}\b', t):
            return f"{int(vol) if float(vol).is_integer() else vol} мл"
    return ""

def extract_concentration(text: str) -> str:
    for key, canonical in CONCENTRATION_MAP.items():
        if re.search(rf'\b{key}\b', text.lower()):
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
            if pattern in text:
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
    # Замена l' / d'
    text = re.sub(r'l\s*[\'`](\w)', r"l'\1", text)
    text = re.sub(r'd\s*[\'`](\w)', r"d'\1", text)
    # Убираем дубликаты предлогов
    text = re.sub(r'\b(a|de|le|la|les|l\')\s+\1\b', r'\1', text, flags=re.IGNORECASE)
    text = re.sub(r'\ba\s+l[\'`]', r"a l'", text, flags=re.IGNORECASE)
    text = re.sub(r'\ba\s+l[\'`]\s*a\s+l[\'`]', r"a l'", text, flags=re.IGNORECASE)
    # Специальная обработка "encre noire a l’extreme"
    if "encre noire" in text.lower():
        text = re.sub(r'encre\s+noire\s+a\s+(?:a\s+)?l[\'`](?:a\s+)?l[\'`]extreme',
                      'encre noire a l\'extreme', text, flags=re.IGNORECASE)
        text = re.sub(r'encre\s+noire\s+a\s+l[\'`]extreme',
                      'encre noire a l\'extreme', text, flags=re.IGNORECASE)
    return text

def extract_aroma_name(original_text: str, brand: str, volume: str,
                       concentration: str, type_: str, gender: str) -> str:
    text = preprocess_text(original_text)
    text = clean_extra_info(text)

    # Удаляем упоминание бренда, если он есть
    if brand and brand.lower() in text:
        text = text.replace(brand.lower(), '')

    # Удаляем все формы записи объема
    if volume:
        volume_num = re.match(r'^(\d+(?:\.\d+)?)', volume)
        if volume_num:
            v = volume_num.group(1)
            patterns = [
                rf'{re.escape(v)}\s*(ml|мл)',
                r'\.\d+\s*(ml|мл)',
                rf'\b{v.split(".")[0]}\s*(ml|мл)\b' if '.' in v else '',
                rf'\b{v}\b'
            ]
            for p in [pp for pp in patterns if pp]:
                text = re.sub(p, '', text)

    # Удаляем все формы записи концентрации
    if concentration:
        if concentration == "EDP":
            synonyms = ["edp", "eau de parfum", "парфюмерная вода", "extrait de parfum", "extrait"]
        elif concentration == "EDT":
            synonyms = ["edt", "eau de toilette", "туалетная вода"]
        elif concentration == "EDC":
            synonyms = ["edc", "eau de cologne"]
        elif concentration == "Parfum":
            synonyms = ["pp", "parfum", "духи"]
        else:
            synonyms = [concentration.lower()]
        for syn in synonyms:
            text = re.sub(rf'\b{syn}\b', '', text)

    # Удаляем ключевые слова типа (тестер, пробник и т.д.)
    if type_:
        synonyms = [k for (k, v) in TYPE_KEYWORDS.items() if v == type_]
        for syn in synonyms:
            text = re.sub(rf'\b{syn}\b', '', text)

    # Удаляем паттерны пола (муж, жен и т.д.)
    if gender:
        for pattern, gen_val in GENDER_PATTERNS:
            if gen_val == gender:
                if pattern.startswith(r'\b'):
                    text = re.sub(pattern, '', text)
                else:
                    text = text.replace(pattern, '')

    text = re.sub(r'[(),|\-]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    text = unify_flanker_words(text)
    text = normalize_french_names(text)
    text = re.sub(r'\s+', ' ', text).strip()
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
        subset = df.loc[idx, fill_col].dropna()
        non_empty = [x for x in subset if x.strip()]
        if len(set(non_empty)) == 1:  # ровно одно уникальное значение
            unique_val = non_empty[0]
            mask = df.loc[idx, fill_col].isin(["", None, "nan"])
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

        # 2) Заполняем пропущенные Concentration и Gender
        result_df = fill_column_if_unique(
            result_df, fill_col="Concentration",
            group_cols=["Canonical Brand", "Aroma Name", "Gender", "Volume", "Type"]
        )
        result_df = fill_column_if_unique(
            result_df, fill_col="Gender",
            group_cols=["Canonical Brand", "Aroma Name", "Volume", "Concentration", "Type"]
        )

        print(
            f"После fill_column_if_unique: строк = {len(result_df)}, пустых Product Name = {(result_df['Product Name'].fillna('') == '').sum()}")

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

    # Создаем новый DataFrame только с нужными колонками и переименовываем их
    sorted_df = result_df[['Brand', 'Product Name', 'Price', 'Supplier']].copy()
    sorted_df.columns = ['Бренд', 'Наименование', 'Цена', 'Поставщик']

    # Сортируем по бренду, а затем по наименованию
    sorted_df = sorted_df.sort_values(by=['Бренд', 'Наименование'])

    # Сохраняем в новый файл
    sorted_out_file = "../" + os.getenv("OUTPUT_DIR") + "/sorted_brands_output.xlsx"
    sorted_df.to_excel(sorted_out_file, index=False)
    print(f"Готово! Файл, отсортированный по бренду и наименованию: {sorted_out_file}")
    format_price_list(sorted_out_file)


if __name__ == "__main__":
    main()
