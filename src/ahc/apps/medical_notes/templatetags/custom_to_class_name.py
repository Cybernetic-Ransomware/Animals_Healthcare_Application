from django import template

from ahc.apps.medical_notes.models.type_feeding_notes import FeedingNotification

register = template.Library()


@register.filter
def to_class_name(value):
    if value is None:
        return ""

    if not isinstance(value, FeedingNotification):
        return ""

    return value.__class__.__name__
