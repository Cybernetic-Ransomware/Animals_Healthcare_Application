from django import template
from medical_notes.models.type_feeding_notes import FeedingNotification

register = template.Library()


@register.filter
def to_class_name(value):
    if value is None:
        raise template.TemplateSyntaxError("Value cannot be None")

    if FeedingNotification not in value.__class__.__bases__:
        raise template.TemplateSyntaxError(f"Not allowed to use on the model")

    return value.__class__.__name__
