from datetime import date

from django import template

register = template.Library()


@register.filter
def years_and_months_since(value, arg):
    if not value or not arg or not isinstance(value, date) or not isinstance(arg, date):
        return ""

    years = arg.year - value.year
    months = arg.month - value.month
    if months < 0:
        years -= 1
        months += 12

    years_str = "1 year" if years == 1 else f"{years} years"
    months_str = "1 month" if months == 1 else f"{months} months"
    response = f"{years_str}, {months_str}" if years > 0 else f"{months_str}"

    return response
