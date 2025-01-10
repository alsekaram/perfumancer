from django.core.validators import RegexValidator, EmailValidator
from django.utils.translation import gettext_lazy as _

phone_validator = RegexValidator(
    regex=r"^\+?7\d{10}$",
    message=_('Номер телефона должен быть в формате: "+79991234567"'),
    code="invalid_phone",
)

email_validator = EmailValidator(
    message=_("Введите корректный email адрес"), code="invalid_email"
)
