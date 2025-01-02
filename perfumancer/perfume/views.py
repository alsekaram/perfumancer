import os
from pathlib import Path

from django.http import HttpResponse, Http404
from django.shortcuts import redirect

from .tasks import update_prices_task


def renew_prices(request):
    # Логика для обновления прайс-листов
    update_prices_task.delay()
    # После выполнения перенаправляем на страницу списка объектов
    return redirect('/perfume/pricelist/')


def download_prices(request):
    if request.method != "POST":
        return HttpResponse("Метод не поддерживается.", status=405)

    dir_path = Path(os.getenv("SAVE_DIR", "."))
    file_path = dir_path / "combined_price_list_melted.xlsx"

    if not file_path.exists():
        return redirect('/perfume/pricelist/')

    try:
        with file_path.open('rb') as f:
            response = HttpResponse(
                f.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="price_file.xlsx"'
            return response

    except Exception as e:
        raise Http404(e)
