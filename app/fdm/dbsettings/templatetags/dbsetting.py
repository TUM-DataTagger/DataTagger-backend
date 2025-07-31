from django import template

from fdm.dbsettings.functions import get_dbsettings_value

register = template.Library()


@register.simple_tag
def setting(key, default=""):
    return get_dbsettings_value(key, default)
