from django.contrib.admin import AdminSite
from django.urls import reverse
from django.urls import path
from . import views


class PerfumeAdminSite(AdminSite):
    site_header = "Perfumancer"
    site_title = "Perfumancer"
    index_title = "Perfume"
    login_template = "admin/login.html"  # Используем стандартный шаблон входа

    def each_context(self, request):
        """
        Добавляем контекст для кастомного сайта.
        """
        context = super().each_context(request)
        context["site_url"] = reverse("perfume:login")
        return context

    def has_permission(self, request):
        """
        Проверяем, есть ли у пользователя доступ к кастомному сайту.
        """
        return request.user.is_active and request.user.is_staff

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "renew-prices/",
                self.admin_view(views.renew_prices),
                name="renew_prices",
            ),
            path(
                "download-prices/",
                self.admin_view(views.download_prices),
                name="download_prices",
            ),
        ]
        return custom_urls + urls

    def get_app_list(self, request, app_label=None, skip_duplicates=False):
        """
        Переопределяем порядок отображения моделей 'слева' в админке.
        """
        app_list = super().get_app_list(request)  # Получаем стандартный список
        for app in app_list:
            if app["app_label"] == "perfume":  # Проверяем, что это наше приложение
                # Устанавливаем вручную строго заданный порядок
                manual_order = [
                    "CurrencyRate",
                    "Supplier",
                    "PriceList",
                    "Brand",
                    "ProductBase",
                ]
                app["models"].sort(
                    key=lambda model: (
                        manual_order.index(model["object_name"])
                        if model["object_name"] in manual_order
                        else len(manual_order)
                    )
                )
                break  # Выходим из цикла, если нашли нужное приложение
        return app_list


perfume_admin_site = PerfumeAdminSite(name="perfume")
