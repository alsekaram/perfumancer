def pluralize_russian(number, singular, singular_genitive, plural_genitive):
    """
    Подбирает правильное склонение слова для русского языка.

    :param number: Число, для которого нужно подобрать слово.
    :param singular: Форма единственного числа (например, "покупатель").
    :param singular_genitive: Родительный падеж единственного числа (например, "покупателя").
    :param plural_genitive: Родительный падеж множественного числа (например, "покупателей").
    :return: Строка с числом и правильной формой слова.
    """
    number = abs(number)

    if number % 10 == 1 and number % 100 != 11:
        return f"{number} {singular}"
    elif 2 <= number % 10 <= 4 and not (12 <= number % 100 <= 14):
        return f"{number} {singular_genitive}"
    else:
        return f"{number} {plural_genitive}"


