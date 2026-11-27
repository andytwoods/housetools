from django.contrib import admin

from soundbar.models import SmartThingsAuth


@admin.register(SmartThingsAuth)
class SmartThingsAuthAdmin(admin.ModelAdmin):
    list_display = ("__str__", "updated")
    readonly_fields = ("updated",)
