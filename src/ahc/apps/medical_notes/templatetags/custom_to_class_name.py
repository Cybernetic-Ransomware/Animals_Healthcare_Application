from django import template

register = template.Library()


@register.filter
def to_file_name(value):
    if value is None:
        raise template.TemplateSyntaxError("Value cannot be None")

    if not isinstance(value, str):
        return value

    return value.split("/")[-1]
