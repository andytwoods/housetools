from django.contrib import admin

from soundbar.models import SmartThingsAuth
from soundbar.models import SoundProfile


@admin.register(SmartThingsAuth)
class SmartThingsAuthAdmin(admin.ModelAdmin):
    list_display = ("__str__", "soundbar_device_id", "updated")
    readonly_fields = ("updated",)


@admin.register(SoundProfile)
class SoundProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "sound_mode", "volume", "woofer", "night_mode")
    list_editable = ("order",)
    fieldsets = (
        (None, {"fields": ("name", "order")}),
        ("Basics", {"fields": ("turn_on", "input_source", "volume", "sound_mode")}),
        ("Sound", {"fields": ("woofer", "night_mode", "voice_amplifier",
                              "bass_boost")}),
        ("Channel levels", {
            "classes": ("collapse",),
            "fields": ("centre", "side", "wide", "front_top", "rear", "rear_top"),
        }),
    )
