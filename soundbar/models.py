from django.db import models
from django.utils import timezone


class SmartThingsAuth(models.Model):
    """The one SmartThings OAuth grant for the house. Single row, pk=1.

    SmartThings access tokens last about 24 hours and the refresh token is
    rotated on every refresh, so both are written back each time.
    """

    access_token = models.TextField(blank=True, default="")
    refresh_token = models.TextField(blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    installed_app_id = models.CharField(max_length=100, blank=True, default="")
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SmartThings authorisation"
        verbose_name_plural = "SmartThings authorisation"

    def __str__(self):
        if not self.refresh_token:
            return "not connected"
        return f"connected, token expires {self.expires_at:%Y-%m-%d %H:%M}"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def is_connected(self):
        return bool(self.refresh_token)

    @property
    def is_expired(self):
        if not self.expires_at:
            return True
        # Refresh a minute early rather than race the expiry.
        return timezone.now() >= self.expires_at - timezone.timedelta(minutes=1)
