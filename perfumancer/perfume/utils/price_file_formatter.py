from openpyxl import load_workbook


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
