from django import template

register = template.Library()


@register.filter
def to_file_name(value):
    if value is None:
        return ""

    if not isinstance(value, str):
        return value

    return value.split("/")[-1]
