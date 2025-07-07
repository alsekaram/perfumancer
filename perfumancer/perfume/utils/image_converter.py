"""
Утилиты для конвертации изображений
Автоматическая конвертация HEIC в JPEG для совместимости
"""

import os
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image

# Проверяем наличие pillow-heif
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_SUPPORT = True
except ImportError:
    HEIF_SUPPORT = False


class ImageConverter:
    """Класс для конвертации изображений"""
    
    HEIC_EXTENSIONS = ['.heic', '.heif']
    TARGET_FORMAT = 'JPEG'
    TARGET_EXTENSION = '.jpg'
    QUALITY = 85  # Качество JPEG (0-100)
    
    @classmethod
    def needs_conversion(cls, filename):
        """Проверяет, нужна ли конвертация файла"""
        if not filename:
            return False
        
        file_ext = os.path.splitext(filename.lower())[1]
        return file_ext in cls.HEIC_EXTENSIONS
    
    @classmethod
    def convert_heic_to_jpeg(cls, file_content, original_filename):
        """
        Конвертирует HEIC файл в JPEG
        
        Args:
            file_content: Содержимое файла (bytes или file-like object)
            original_filename: Оригинальное имя файла
            
        Returns:
            ContentFile: Сконвертированный файл в формате JPEG
        """
        if not HEIF_SUPPORT:
            return None
        
        try:
            # Читаем содержимое файла
            if hasattr(file_content, 'read'):
                image_data = file_content.read()
                file_content.seek(0)  # Возвращаем указатель на начало
            else:
                image_data = file_content
            
            # Открываем изображение
            image = Image.open(BytesIO(image_data))
            
            # Конвертируем в RGB (JPEG не поддерживает прозрачность)
            if image.mode in ('RGBA', 'LA', 'P'):
                # Создаем белый фон для изображений с прозрачностью
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Сохраняем в JPEG
            output_buffer = BytesIO()
            image.save(
                output_buffer, 
                format=cls.TARGET_FORMAT,
                quality=cls.QUALITY,
                optimize=True
            )
            output_buffer.seek(0)
            
            # Создаем новое имя файла
            base_name = os.path.splitext(original_filename)[0]
            new_filename = f"{base_name}{cls.TARGET_EXTENSION}"
            
            # Создаем ContentFile
            converted_file = ContentFile(
                output_buffer.getvalue(),
                name=new_filename
            )
            
            return converted_file
            
        except Exception as e:
            return None
    
    @classmethod
    def process_uploaded_file(cls, uploaded_file):
        """
        Обрабатывает загруженный файл, конвертирует HEIC при необходимости
        
        Args:
            uploaded_file: Django UploadedFile объект
            
        Returns:
            UploadedFile: Оригинальный файл или сконвертированный
        """
        if not cls.needs_conversion(uploaded_file.name):
            return uploaded_file
        
        converted_file = cls.convert_heic_to_jpeg(uploaded_file, uploaded_file.name)
        
        if converted_file:
            # Копируем метаданные
            converted_file.content_type = 'image/jpeg'
            return converted_file
        else:
            return uploaded_file


def convert_image_if_needed(uploaded_file):
    """
    Функция-хелпер для конвертации изображений
    Используется в моделях и формах
    """
    return ImageConverter.process_uploaded_file(uploaded_file)


# Функция для проверки поддержки HEIC
def check_heic_support():
    """Проверяет поддержку формата HEIC"""
    return HEIF_SUPPORT
