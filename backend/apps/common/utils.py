"""Shared utilities used across PAS apps."""

from django.core.paginator import Paginator

PAGE_SIZE = 10


def paginate(request, queryset, page_size=PAGE_SIZE):
    paginator = Paginator(queryset, page_size)
    return paginator.get_page(request.GET.get('page'))


def status_filter(queryset, request):
    status = request.GET.get('status')
    if status == 'active':
        return queryset.filter(is_active=True)
    if status == 'inactive':
        return queryset.filter(is_active=False)
    return queryset


def format_user_error(exc) -> str:
    """Return a clean user-facing message (avoids ValidationError list repr)."""
    messages = getattr(exc, 'messages', None)
    if messages:
        return '; '.join(str(m) for m in messages)
    return str(exc)
