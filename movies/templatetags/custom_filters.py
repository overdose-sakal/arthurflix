from django import template

register = template.Library()

@register.filter
def compact_number(value):
    try:
        value = int(value)
    except (ValueError, TypeError):
        return value

    if value < 1000:
        return str(value)
    elif value < 1000000:
        return f'{value/1000:.1f}k'.replace('.0k', 'k')
    else:
        return f'{value/1000000:.1f}M'.replace('.0M', 'M')