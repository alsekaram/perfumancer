from django.contrib.admin import AdminSite
from django.urls import reverse, NoReverseMatch
from django.urls import path
from django.apps import apps
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
        from .views_analytics import financial_analytics

        urls = super().get_urls()
        custom_urls = [
            path(
                "analytics/",
                self.admin_view(financial_analytics),
                name="financial_analytics",
            ),
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

    def _build_app_dict(self, request, label=None):
        """
        Build the app dictionary. The optional `label` parameter filters models
        of a specific app.
        """
        app_dict = {}

        if label:
            models = {
                m: m_a
                for m, m_a in self._registry.items()
                if m._meta.app_label == label
            }
        else:
            models = self._registry

        for model, model_admin in models.items():
            app_label = model._meta.app_label

            has_module_perms = model_admin.has_module_permission(request)
            if not has_module_perms:
                continue

            perms = model_admin.get_model_perms(request)

            # Check whether user has any perm for this module.
            # If so, add the module to the model_list.
            if True not in perms.values():
                continue

            info = (app_label, model._meta.model_name)
            model_dict = {
                "model": model,
                "name": str(model._meta.verbose_name_plural),
                "object_name": model.__name__,
                "perms": perms,
                "admin_url": None,
                "add_url": None,
            }
            if perms.get("change") or perms.get("view"):
                model_dict["view_only"] = not perms.get("change")
                try:
                    model_dict["admin_url"] = reverse(
                        "perfume:%s_%s_changelist" % info, current_app=self.name
                    )
                except NoReverseMatch:
                    pass
            if perms.get("add"):
                try:
                    model_dict["add_url"] = reverse(
                        "perfume:%s_%s_add" % info, current_app=self.name
                    )
                except NoReverseMatch:
                    pass

            if app_label in app_dict:
                app_dict[app_label]["models"].append(model_dict)
            else:
                app_dict[app_label] = {
                    "name": apps.get_app_config(app_label).verbose_name,
                    "app_label": app_label,
                    "app_url": reverse(
                        "perfume:app_list",
                        kwargs={"app_label": app_label},
                        current_app=self.name,
                    ),
                    "has_module_perms": has_module_perms,
                    "models": [model_dict],
                }

        if label:
            return app_dict.get(label)
        return app_dict

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
        # Добавляем пункт "Финансовая аналитика"
        analytics_item = {
            "name": "Finance",
            "app_label": "analytics",
            "app_url": reverse("perfume:financial_analytics"),
            "models": [
                {
                    "name": "Сводки",
                    "object_name": "FinancialAnalytics",
                    "admin_url": reverse("perfume:financial_analytics"),
                    "view_only": True,
                }
            ],
        }

        app_list.append(analytics_item)
        return app_list


perfume_admin_site = PerfumeAdminSite(name="perfume")
