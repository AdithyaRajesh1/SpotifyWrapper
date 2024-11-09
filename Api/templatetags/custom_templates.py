# templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def format_duration(duration_ms):
    try:
        # Ensure the input is an integer by converting it if it's a string
        duration_ms = int(duration_ms)
    except ValueError:
        # If the conversion fails, handle the error appropriately
        return "Invalid duration"

    duration_seconds = duration_ms // 1000
    minutes = duration_seconds // 60
    seconds = duration_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"