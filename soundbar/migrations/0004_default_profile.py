"""A profile that puts the bar back to ordinary."""

from django.db import migrations

DEFAULT = {
    "name": "Default",
    "order": 0,
    "sound_mode": "standard",
    "woofer": 0,
    "night_mode": False,
    "voice_amplifier": False,
    "bass_boost": False,
    "centre": 0,
    "side": 0,
    "wide": 0,
    "front_top": 0,
    "rear": 0,
    "rear_top": 0,
}


def add(apps, schema_editor):
    SoundProfile = apps.get_model("soundbar", "SoundProfile")
    SoundProfile.objects.get_or_create(name=DEFAULT["name"], defaults=DEFAULT)


def remove(apps, schema_editor):
    SoundProfile = apps.get_model("soundbar", "SoundProfile")
    SoundProfile.objects.filter(name=DEFAULT["name"]).delete()


class Migration(migrations.Migration):
    dependencies = [("soundbar", "0003_starter_profiles")]

    operations = [migrations.RunPython(add, remove)]
