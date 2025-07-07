import os
import tempfile
from PIL import Image
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import logging

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_SUPPORT = True
except ImportError:
    HEIC_SUPPORT = False

logger = logging.getLogger(__name__)


def convert_heic_to_jpeg(file_field):
    """
    Конвертирует HEIC файл в JPEG формат
    
    Args:
        file_field: Django FileField объект
        
    Returns:
        ContentFile с JPEG данными или исходный файл если конвертация не нужна
    """
    if not HEIC_SUPPORT:
        logger.warning("HEIC support not available - pillow-heif not installed")
        return file_field
    
    # Получаем расширение файла
    file_name = file_field.name.lower()
    if not file_name.endswith(('.heic', '.heif')):
        return file_field
    
    try:
        # Создаем временный файл для обработки
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            # Записываем содержимое загруженного файла
            for chunk in file_field.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        try:
            # Открываем HEIC файл
            with Image.open(temp_file_path) as img:
                # Конвертируем в RGB если нужно
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Создаем новый временный файл для JPEG
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as jpeg_temp:
                    img.save(jpeg_temp.name, 'JPEG', quality=90, optimize=True)
                    
                    # Читаем сконвертированный файл
                    with open(jpeg_temp.name, 'rb') as f:
                        jpeg_data = f.read()
                    
                    # Создаем новое имя файла
                    original_name = os.path.splitext(file_field.name)[0]
                    new_name = f"{original_name}.jpg"
                    
                    # Создаем ContentFile с новыми данными
                    converted_file = ContentFile(jpeg_data, name=new_name)
                    
                    logger.info(f"Successfully converted HEIC to JPEG: {file_field.name} -> {new_name}")
                    return converted_file
                    
        finally:
            # Удаляем временные файлы
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            if 'jpeg_temp' in locals() and os.path.exists(jpeg_temp.name):
                os.unlink(jpeg_temp.name)
                
    except Exception as e:
        logger.error(f"Error converting HEIC file {file_field.name}: {str(e)}")
        return file_field
    
    return file_field


def process_invoice_file(file_field):
    """
    Обрабатывает загруженный файл накладной
    
    Args:
        file_field: Django FileField объект
        
    Returns:
        Обработанный файл
    """
    if not file_field:
        return file_field
    
    # Конвертируем HEIC в JPEG если нужно
    processed_file = convert_heic_to_jpeg(file_field)
    
    return processed_file 