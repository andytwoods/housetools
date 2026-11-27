"""Scheduled soundbar jobs.

These run in the Huey consumer (the `worker` service in appliku.yml), not in
the web process. Nothing here is scheduled unless that process is running.
"""

import logging

from huey import crontab
from huey.contrib.djhuey import db_periodic_task

from soundbar import control
from soundbar.models import SmartThingsAuth
from soundbar.models import SoundProfile

logger = logging.getLogger(__name__)

RESET_PROFILE = "Default"


@db_periodic_task(crontab(hour=0, minute=0))
def reset_soundbar():
    """Put the soundbar back to the Default profile at midnight.

    Two things it deliberately will not do: switch the bar on (it only tidies
    what is already playing), and wake it when it is off (there is nothing to
    reset, and a sleeping soundbar should stay asleep).
    """
    auth = SmartThingsAuth.load()
    if not auth.is_connected:
        logger.warning("Nightly soundbar reset skipped: not connected to SmartThings")
        return

    profile = SoundProfile.objects.filter(name=RESET_PROFILE).first()
    if profile is None:
        logger.warning("Nightly soundbar reset skipped: no %r profile", RESET_PROFILE)
        return

    try:
        device_id = control.soundbar_device_id()
        if not control.is_on(device_id):
            logger.info("Nightly soundbar reset skipped: the soundbar is off")
            return
    except Exception:
        logger.exception("Nightly soundbar reset could not reach SmartThings")
        return

    done, failed = profile.apply(device_id, power=False)
    if failed:
        label, reason = failed
        logger.error("Nightly soundbar reset stopped at %s: %s", label, reason)
    else:
        logger.info("Nightly soundbar reset sent %s", ", ".join(done))
