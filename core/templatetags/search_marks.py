from django import template

from core.search_marks import mark_match

register = template.Library()


@register.filter
def marked(text, query):
    """{{ name|marked:query }}: the name with what was searched marked (core/search_marks.py)"""
    return mark_match(text, query)
