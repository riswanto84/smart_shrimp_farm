from django.core.paginator import Paginator
from .search import apply_database_search


def paginate_queryset(request, queryset, per_page=10):
    """Return a Django Page object for list/table pages.

    Parameter ``q`` diterapkan pada QuerySet sebelum pagination sehingga
    pencarian membaca seluruh database, bukan hanya baris pada halaman aktif.
    """
    keyword = (request.GET.get('q') or '').strip()
    if keyword and hasattr(queryset, 'model'):
        queryset = apply_database_search(queryset, keyword)

    try:
        per_page = int(request.GET.get('per_page') or per_page)
    except (TypeError, ValueError):
        per_page = per_page
    per_page = max(5, min(per_page, 100))
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
