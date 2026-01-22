from django import template

register = template.Library()


@register.simple_tag
def qs(request, **kwargs):
    """
    Собирает querystring, сохраняя текущие GET-параметры.
    Пример: {% qs request sort='date' dir='asc' page=1 %}
    """
    q = request.GET.copy()
    for k, v in kwargs.items():
        if v is None or v == "":
            q.pop(k, None)
        else:
            q[k] = str(v)
    return q.urlencode()
