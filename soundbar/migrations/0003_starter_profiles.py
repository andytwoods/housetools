"""Three profiles to start from, so the page is not empty.

Guesses at sensible settings, not measurements: nothing can be read off the
soundbar. Edit them in the admin once you have heard them.
"""

from django.db import migrations

STARTERS = [
    {
        "name": "Film",
        "order": 1,
        "sound_mode": "surround",
        "woofer": 2,
        "night_mode": False,
        "voice_amplifier": False,
        "bass_boost": False,
    },
    {
        "name": "Late night",
        "order": 2,
        "sound_mode": "standard",
        "woofer": -3,
        "night_mode": True,
        "voice_amplifier": True,
        "bass_boost": False,
    },
    {
        "name": "Music",
        "order": 3,
        "sound_mode": "standard",
        "woofer": 1,
        "night_mode": False,
        "voice_amplifier": False,
        "bass_boost": False,
    },
]


def add(apps, schema_editor):
    SoundProfile = apps.get_model("soundbar", "SoundProfile")
    for values in STARTERS:
        SoundProfile.objects.get_or_create(name=values["name"], defaults=values)


def remove(apps, schema_editor):
    SoundProfile = apps.get_model("soundbar", "SoundProfile")
    SoundProfile.objects.filter(name__in=[v["name"] for v in STARTERS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("soundbar", "0002_soundprofile_smartthingsauth_soundbar_device_id"),
    ]

    operations = [migrations.RunPython(add, remove)]
