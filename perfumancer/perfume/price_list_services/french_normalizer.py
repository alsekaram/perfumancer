import re
import unicodedata
from typing import Dict, List, Pattern, Tuple, Union, Optional


class FrenchNameNormalizer:
    def __init__(self):
        # Конфигурируемые списки предлогов
        self.dangling_prepositions = [
            "de",
            "du",
            "des",
            "le",
            "la",
            "les",
            "l'",
            "à",
            "au",
            "aux",
            "en",
            "sur",
        ]

        # Исключения - названия, которые не должны терять висячие предлоги
        self.exceptions_for_dangling = ["terre de", "homme de", "femme de"]

        # Словарь паттернов для специальных случаев
        self.special_patterns = {
            # ключ: (regex_pattern, replacement)
            "encre_noire": (
                r'encre\s+noir[e]?(?:\s+|["`\'])?(?:a\s+)?(?:l[`\'\"])?(?:a\s+)?(?:l[`\'\"])?extreme',
                "encre noire a l'extreme",
            ),
            "l_amour": (r"l[\'\s]*amour\s*(?:de\s+)?(?:lady\b)?", "l'amour"),
            "perles_de": (r"\bperles?\s+de\s+", "perles de "),
            "eclat_darpege": (r"eclat\s*d[\'\s]*arpege", "eclat d'arpege"),
        }

        # Компилируем регулярные выражения для лучшей производительности
        self._compile_patterns()

        # Словарь для нормализации французских букв с диакритическими знаками
        self.accent_map = {
            "ô": "o",
            "ê": "e",
            "î": "i",
            "â": "a",
            "û": "u",
            "é": "e",
            "è": "e",
            "ë": "e",
            "ï": "i",
            "ü": "u",
            "ù": "u",
            "ç": "c",
            "œ": "oe",
            "æ": "ae",
            "Ô": "O",
            "Ê": "E",
            "Î": "I",
            "Â": "A",
            "Û": "U",
            "É": "E",
            "È": "E",
            "Ë": "E",
            "Ï": "I",
            "Ü": "U",
            "Ù": "U",
            "Ç": "C",
            "Œ": "OE",
            "Æ": "AE",
        }

    def _compile_patterns(self):
        """Компилирует все регулярные выражения для улучшения производительности."""
        # Паттерн для висячих предлогов
        self.dangling_pattern = re.compile(
            r"\b(" + "|".join(self.dangling_prepositions) + r")\s*$", re.IGNORECASE
        )

        # Компилируем паттерны для специальных случаев
        self.compiled_special_patterns = {}
        for key, (pattern, replacement) in self.special_patterns.items():
            self.compiled_special_patterns[key] = (
                re.compile(pattern, re.IGNORECASE),
                replacement,
            )

        # Другие основные паттерны
        self.apostrophe_patterns = [
            (re.compile(r"l\s*[\'`](\w)", re.IGNORECASE), r"l'\1"),
            (re.compile(r"d\s*[\'`](\w)", re.IGNORECASE), r"d'\1"),
            (re.compile(r"\b(d)\s+([aeiouy]\w*)", re.IGNORECASE), r"d'\2"),
            (re.compile(r"\b(l)\s+([aeiouy]\w*)", re.IGNORECASE), r"l'\2"),
        ]

        self.duplicate_patterns = [
            (re.compile(r"\b(a|de|le|la|les|l\')\s+\1\b", re.IGNORECASE), r"\1"),
            (re.compile(r"\ba\s+l[\'`]", re.IGNORECASE), r"a l'"),
            (re.compile(r"\ba\s+l[\'`]\s*a\s+l[\'`]", re.IGNORECASE), r"a l'"),
        ]

    def add_special_pattern(self, key: str, pattern: str, replacement: str):
        """Добавляет новый специальный паттерн для обработки."""
        self.special_patterns[key] = (pattern, replacement)
        self.compiled_special_patterns[key] = (
            re.compile(pattern, re.IGNORECASE),
            replacement,
        )

    def remove_dangling_prepositions(self, text: str) -> str:
        """Удаляет висячие предлоги, учитывая исключения."""
        # Проверяем исключения
        for exception in self.exceptions_for_dangling:
            if exception.lower() in text.lower():
                return text

        return self.dangling_pattern.sub("", text)

    def apply_special_patterns(self, text: str) -> str:
        """Применяет специальные паттерны на основе ключевых слов."""
        text_lower = text.lower()

        for key, (pattern, replacement) in self.compiled_special_patterns.items():
            # Проверка ключевых слов для оптимизации
            keywords = key.split("_")
            if all(keyword in text_lower for keyword in keywords):
                text = pattern.sub(replacement, text)

        return text

    def fix_apostrophes(self, text: str) -> str:
        """Исправляет апострофы и пробелы."""
        for pattern, replacement in self.apostrophe_patterns:
            text = pattern.sub(replacement, text)
        return text

    def remove_duplicate_prepositions(self, text: str) -> str:
        """Удаляет дублирующиеся предлоги."""
        for pattern, replacement in self.duplicate_patterns:
            text = pattern.sub(replacement, text)
        return text

    def normalize_accents(self, text: str) -> str:
        """Нормализует французские буквы с диакритическими знаками."""
        # Два подхода к нормализации:

        # 1. Использование словаря замен
        for accent, replacement in self.accent_map.items():
            text = text.replace(accent, replacement)

        # 2. Альтернативный метод с использованием unicodedata
        # text = unicodedata.normalize('NFKD', text)
        # text = ''.join([c for c in text if not unicodedata.combining(c)])

        return text

    def normalize(self, text: str) -> str:
        """Нормализует французское название, применяя все правила."""
        if not text or not isinstance(text, str):
            return text

        # Предварительная обработка для наиболее распространенных случаев
        text = re.sub(
            r"(\w)d([aeiouy])", r"\1d\'\2", text
        )  # Замена "darpege" на "d'arpege"

        # Нормализация диакритических знаков
        text = self.normalize_accents(text)

        # Шаг 1: Удаление висячих предлогов
        text = self.remove_dangling_prepositions(text)

        # Шаг 2: Применение специальных паттернов
        text = self.apply_special_patterns(text)

        # Шаг 3: Исправление апострофов
        text = self.fix_apostrophes(text)

        # Шаг 4: Удаление дублирующихся предлогов
        text = self.remove_duplicate_prepositions(text)

        return text
