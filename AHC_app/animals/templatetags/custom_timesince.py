from datetime import date
from django import template


register = template.Library()

@register.filter
def years_and_months_since(value, arg):
    if not value or not arg or not isinstance(value, date) or not isinstance(arg, date):
        return ''

    years = arg.year - value.year
    months = arg.month - value.month
    if months < 0:
        years -= 1
        months += 12

    if years == 1:
        years_str = '1 year'
    else:
        years_str = f'{years} years'

    if months == 1:
        months_str = '1 month'
    else:
        months_str = f'{months} months'

    if years > 0:
        response = f'{years_str}, {months_str}'
    else:
        response = f'{months_str}'

    return response
