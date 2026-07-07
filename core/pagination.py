from django.core.paginator import Paginator


def paginate_queryset(request, queryset, per_page=10):
    """Return a Django Page object for list/table pages.
    Default 10 rows/page keeps Smart Shrimp Farm tables clean and fast.
    """
    try:
        per_page = int(request.GET.get('per_page') or per_page)
    except (TypeError, ValueError):
        per_page = per_page
    per_page = max(5, min(per_page, 100))
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
