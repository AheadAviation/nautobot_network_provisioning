import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name="json")
def json_filter(value):
    """
    Dumps a value as JSON string.
    """
    if value is None or value == "":
        return "[]"
    try:
        if isinstance(value, (dict, list)):
            if not value:
                return "[]" if isinstance(value, list) else "{}"
            return json.dumps(value)
        # If it's a string that looks like JSON, return it as is or parse/dump
        if isinstance(value, str):
            try:
                return json.dumps(json.loads(value))
            except:
                return json.dumps(value)
        return json.dumps(value)
    except (TypeError, ValueError):
        return "[]"

