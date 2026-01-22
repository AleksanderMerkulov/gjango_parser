from django import template

register = template.Library()


@register.simple_tag
def qs(request, **kwargs):
    """
    Обновляет request, добавляя сортировку по колонке
    """
    q = request.GET.copy()
    if 'sort' in q:
        if 'current_sort' in kwargs and 'dir' in q:
            if q['sort'] == kwargs['current_sort']:
                kwargs['dir'] = "min" if q.get('dir') == "max" else "max"
    for k, v in kwargs.items():
        if v is None or v == "":
            q.pop(k, None)
        else:
            q[k] = str(v)
    return q.urlencode()
