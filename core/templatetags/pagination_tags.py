from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def page_url(context, page_number):
    request = context.get('request')
    if request is None:
        return f'?page={page_number}'
    params = request.GET.copy()
    params.pop('page', None)
    params['page'] = page_number
    return '?' + params.urlencode()
