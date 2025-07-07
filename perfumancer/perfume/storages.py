from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings
from django.core.exceptions import SuspiciousOperation


class PrivateSelectelS3Storage(S3Boto3Storage):
    """
    Приватный S3 Storage для Selectel с подписанными URL
    Обеспечивает безопасное хранение и доступ к файлам накладных
    """
    # Настройки безопасности
    default_acl = 'private'
    querystring_auth = True
    querystring_expire = 86400  # 24 часа
    file_overwrite = False
    
    # Дополнительные настройки безопасности
    object_parameters = {
        'CacheControl': 'max-age=86400',
        'ACL': 'private',
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Принудительно устанавливаем приватные настройки
        self.default_acl = 'private'
        self.querystring_auth = True
    
    def url(self, name):
        """
        Возвращает подписанный URL для безопасного доступа к файлу
        """
        if not name:
            raise ValueError("Имя файла не может быть пустым")
            
        try:
            # Создаем подписанный URL
            presigned_url = self.connection.meta.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name, 
                    'Key': name
                },
                ExpiresIn=self.querystring_expire
            )
            
            return presigned_url
            
        except Exception as e:
            # Fallback - возвращаем базовый URL (файл будет недоступен, но не будет ошибки)
            return f"https://{self.bucket_name}.s3.ru-1.storage.selcloud.ru/{name}"
    
    def _save(self, name, content):
        """
        Переопределяем сохранение для принудительной установки приватных прав
        """
        # Убеждаемся, что файл сохраняется с приватными правами
        self.object_parameters = {
            **self.object_parameters,
            'ACL': 'private'
        }
        
        saved_name = super()._save(name, content)
        return saved_name
    
    def delete(self, name):
        """
        Безопасное удаление файла
        """
        try:
            super().delete(name)
        except Exception as e:
            raise


class PublicSelectelS3Storage(S3Boto3Storage):
    """
    Публичный S3 Storage (если вдруг понадобится для других файлов)
    НЕ ИСПОЛЬЗУЕТСЯ для накладных!
    """
    default_acl = 'public-read'
    querystring_auth = False
    file_overwrite = False


# Функции для получения storage
def get_private_file_storage():
    """
    Возвращает приватный Selectel storage для безопасных файлов
    """
    if hasattr(settings, 'AWS_STORAGE_BUCKET_NAME') and settings.AWS_STORAGE_BUCKET_NAME:
        return PrivateSelectelS3Storage()
    else:
        from django.core.files.storage import FileSystemStorage
        return FileSystemStorage()


def get_public_file_storage():
    """
    Возвращает публичный storage (НЕ рекомендуется для накладных)
    """
    if hasattr(settings, 'AWS_STORAGE_BUCKET_NAME') and settings.AWS_STORAGE_BUCKET_NAME:
        return PublicSelectelS3Storage()
    else:
        from django.core.files.storage import FileSystemStorage
        return FileSystemStorage()


# Основная функция для накладных (всегда приватная)
def get_selectel_storage():
    """
    Возвращает приватный Selectel storage для накладных
    """
    return get_private_file_storage()


# Алиас для обратной совместимости
SelectelS3Storage = PrivateSelectelS3Storage
