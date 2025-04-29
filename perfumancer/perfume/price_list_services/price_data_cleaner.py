import os
from pathlib import Path

import pandas as pd

from dotenv import load_dotenv


def get_filename(dir_path):
    return Path(dir_path) / "nan_clear_pl.xlsx"


def main():
    file_path = "../" + os.getenv("OUTPUT_DIR") + "/combined_price_list_melted.xlsx"

    df = pd.read_excel(file_path)

    df_clean = df.dropna(subset=["Наименование"])

    df_clean = df_clean[(df_clean["Бренд"] != "ПРОЧЕЕ") & (df_clean["Цена"] > 10.0)]

    df_clean = df_clean[df_clean["Цена"] <= 500]

    df_clean = df_clean[df_clean["Бренд"] != "NAN"]

    df_clean = df_clean[
        ~df_clean["Наименование"].str.contains(
            r"\d+\s?[xх\*]\s?\d+", na=False, regex=True
        )
    ]

    df_clean = df_clean[df_clean["Бренд"].map(df_clean["Бренд"].value_counts()) >= 10]

    df_clean = df_clean[
        ~df_clean["Наименование"].str.contains(
            r"(?:ml.*ml|мл.*мл)", na=False, regex=True
        )
    ]
    output_path = "../" + os.getenv("OUTPUT_DIR")

    df_clean.to_excel(get_filename(output_path), index=False)


if __name__ == "__main__":
    load_dotenv()
    main()
