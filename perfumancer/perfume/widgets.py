from django.contrib.admin.widgets import AdminFileWidget
from django.utils.safestring import mark_safe
from django.utils.html import format_html


class ProxyFileWidget(AdminFileWidget):
    """
    Виджет для отображения файлов через proxy URL в админке
    """
    
    def format_value(self, value):
        """
        Переопределяем отображение существующего файла
        """
        if value and hasattr(value, 'instance'):
            # Получаем экземпляр модели из файла
            instance = value.instance
            if hasattr(instance, 'get_invoice_proxy_url') and instance.get_invoice_proxy_url():
                # Заменяем S3 URL на proxy URL
                filename = value.name.split('/')[-1]  # Только имя файла
                proxy_url = instance.get_invoice_proxy_url()
                
                return format_html(
                    '<a href="{}" target="_blank">{}</a>',
                    proxy_url,
                    filename
                )
        
        # Fallback на стандартное поведение
        return super().format_value(value)
