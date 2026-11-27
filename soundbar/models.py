from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
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
    soundbar_device_id = models.CharField(max_length=100, blank=True, default="")
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


def level_field(label, low=-6, high=6, help_text=""):
    return models.SmallIntegerField(
        label,
        null=True,
        blank=True,
        validators=[MinValueValidator(low), MaxValueValidator(high)],
        help_text=help_text or "Leave empty to leave this as it is.",
    )


def toggle_field(label):
    return models.BooleanField(
        label,
        null=True,
        blank=True,
        default=None,
        help_text="Leave unset to leave this as it is.",
    )


class SoundProfile(models.Model):
    """A set of soundbar settings applied in one go.

    Every field may be empty, meaning "leave this alone". Nothing here is read
    from the soundbar, because SmartThings will not say how it is set: a
    profile is what to send, not what is true.
    """

    SOUND_MODES = [
        ("standard", "Standard"),
        ("surround", "Surround"),
        ("game", "Game"),
        ("adaptive", "Adaptive"),
    ]

    name = models.CharField(max_length=60, unique=True)
    order = models.PositiveSmallIntegerField(default=0)

    turn_on = models.BooleanField(
        "Turn the soundbar on first",
        default=True,
    )
    volume = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MaxValueValidator(100)],
        help_text="0 to 100. Leave empty to leave the volume alone.",
    )
    input_source = models.CharField(
        max_length=40,
        blank=True,
        default="",
        help_text="As SmartThings names it, e.g. HDMI1. Leave empty to leave it.",
    )
    sound_mode = models.CharField(
        max_length=20,
        blank=True,
        default="",
        choices=SOUND_MODES,
    )

    woofer = level_field("Subwoofer")
    night_mode = toggle_field("Night mode")
    voice_amplifier = toggle_field("Voice amplifier")
    bass_boost = toggle_field("Bass boost")

    centre = level_field("Centre channel")
    side = level_field("Side channels")
    wide = level_field("Wide channels")
    front_top = level_field("Front top channels")
    rear = level_field("Rear channels")
    rear_top = level_field("Rear top channels")

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    @property
    def summary(self):
        """One line, for the button's tooltip."""
        return ", ".join(label for label, _ in self.steps()) or "nothing set"

    def steps(self):
        """What applying this profile would send, in order."""
        from soundbar import control

        planned = []
        if self.turn_on:
            planned.append(("power on", lambda d: control.set_switch(d, on=True)))
        if self.input_source:
            source = self.input_source
            planned.append(
                (f"input {source}", lambda d: control.set_input(d, source)),
            )
        if self.sound_mode:
            mode = self.sound_mode
            planned.append(
                (f"sound mode {mode}", lambda d: control.set_sound_mode(d, mode)),
            )
        if self.volume is not None:
            volume = self.volume
            planned.append(
                (f"volume {volume}", lambda d: control.set_volume(d, volume)),
            )
        if self.woofer is not None:
            woofer = self.woofer
            planned.append(
                (f"subwoofer {woofer:+d}", lambda d: control.set_woofer(d, woofer)),
            )
        for field, setting in (
            ("night_mode", "nightmode"),
            ("voice_amplifier", "voiceamplifier"),
            ("bass_boost", "bassboost"),
        ):
            value = getattr(self, field)
            if value is not None:
                label = self._meta.get_field(field).verbose_name
                planned.append(
                    (
                        f"{label} {'on' if value else 'off'}",
                        lambda d, s=setting, v=value: control.set_advanced(d, s, on=v),
                    ),
                )
        for channel in control.CHANNELS:
            level = getattr(self, channel)
            if level is not None:
                label = self._meta.get_field(channel).verbose_name
                planned.append(
                    (
                        f"{label} {level:+d}",
                        lambda d, c=channel, v=level: control.set_channel(d, c, v),
                    ),
                )
        return planned

    def apply(self, device_id):
        """Send the lot. Returns what was sent and the first failure, if any."""
        done, failed = [], None
        for label, action in self.steps():
            try:
                action(device_id)
            except Exception as error:  # noqa: BLE001
                failed = (label, str(error))
                break
            done.append(label)
        return done, failed
