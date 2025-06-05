from django.utils import timezone
from django.db.models import Sum, F, Q, DecimalField, Count
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from datetime import timedelta, datetime
from decimal import Decimal

from .models import Order, OrderItem, OrderStatus
from .admin_site import perfume_admin_site


def financial_analytics(request):
    """
    Представление для финансовой аналитики с фильтрацией по периодам
    """
    # Получаем выбранный период из запроса
    period = request.GET.get('period', 'all')
    include_all_statuses = request.GET.get('all_statuses', 'true') == 'true'
    
    # Получаем даты из параметров (для кастомного диапазона)
    date_from = request.GET.get('date__gte')
    date_to = request.GET.get('date__lte')
    
    # Определяем дату начала и конца
    end_date = timezone.now().date()
    start_date = None
    
    # Если указан кастомный диапазон дат
    if date_from or date_to:
        period = 'custom'
        if date_from:
            try:
                start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            except ValueError:
                start_date = None
        if date_to:
            try:
                end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            except ValueError:
                end_date = timezone.now().date()
    else:
        # Стандартные периоды
        period_mapping = {
            'day': end_date,  # Сегодня
            'week': end_date - timedelta(days=7),
            'month': end_date - timedelta(days=30),
            '3months': end_date - timedelta(days=90),
            '6months': end_date - timedelta(days=180),
            'year': end_date - timedelta(days=365),
        }
        
        start_date = period_mapping.get(period)
    
    # Базовый queryset для заказов
    orders_qs = Order.objects.all()
    
    # Фильтрация по статусам
    if not include_all_statuses:
        # Получаем статусы для завершенных заказов
        completed_statuses = OrderStatus.objects.filter(
            code__in=['delivered', 'completed', 'shipped']
        )
        if completed_statuses.exists():
            orders_qs = orders_qs.filter(status__in=completed_statuses)
    
    # Фильтрация по датам
    if start_date and end_date:
        orders_qs = orders_qs.filter(date__gte=start_date, date__lte=end_date)
    elif start_date:
        orders_qs = orders_qs.filter(date__gte=start_date)
    elif end_date:
        orders_qs = orders_qs.filter(date__lte=end_date)
    
    # Агрегация данных через OrderItem для корректного подсчета
    items_qs = OrderItem.objects.filter(order__in=orders_qs)
    
    # Подсчет сумм через OrderItem
    analytics = items_qs.aggregate(
        # Сумма продаж в рублях
        total_sales_rub=Sum(
            F('retail_price') * F('quantity'),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        ),
        # Сумма закупок в USD
        total_purchases_usd=Sum(
            F('purchase_price_usd') * F('quantity'),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        ),
        # Сумма закупок в рублях
        total_purchases_rub=Sum(
            F('purchase_price_rub') * F('quantity'),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        ),
        # Количество товаров
        items_count=Count('id')
    )
    
    # Вычисляем прибыль
    total_profit = Decimal('0')
    if analytics['total_sales_rub'] and analytics['total_purchases_rub']:
        total_profit = analytics['total_sales_rub'] - analytics['total_purchases_rub']
    
    # Дополнительная диагностическая информация
    debug_info = {
        'total_orders': orders_qs.count(),
        'total_items': analytics['items_count'],
        'has_retail_prices': items_qs.filter(retail_price__gt=0).count(),
        'has_purchase_usd': items_qs.filter(purchase_price_usd__gt=0).count(),
        'has_purchase_rub': items_qs.filter(purchase_price_rub__gt=0).count(),
    }
    
    # Получаем все статусы для отображения
    all_statuses = OrderStatus.objects.all().order_by('order')
    
    # Получаем контекст админки
    context = {
        **perfume_admin_site.each_context(request),
        'title': 'Финансовая аналитика',
        'period': period,
        'include_all_statuses': include_all_statuses,
        'all_statuses': all_statuses,
        'total_sales_rub': analytics['total_sales_rub'] or Decimal('0'),
        'total_purchases_usd': analytics['total_purchases_usd'] or Decimal('0'),
        'total_purchases_rub': analytics['total_purchases_rub'] or Decimal('0'),
        'total_profit': total_profit,
        'start_date': start_date,
        'end_date': end_date,
        'orders_count': orders_qs.count(),
        'debug_info': debug_info,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'admin/perfume/financial_analytics.html', context)
