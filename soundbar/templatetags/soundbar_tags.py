"""So the home page can show the soundbar profiles without its view knowing."""

from django import template

from soundbar.models import SmartThingsAuth
from soundbar.models import SoundProfile

register = template.Library()


@register.inclusion_tag("soundbar/_profiles.html", takes_context=True)
def soundbar_profiles(context):
    return {
        "request": context.get("request"),
        "profiles": SoundProfile.objects.all(),
        "auth": SmartThingsAuth.load(),
    }
