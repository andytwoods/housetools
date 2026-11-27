"""Turning a profile into SmartThings commands.

The payloads here are not guesses. They come from
`c-kick/ha-smartthings-soundbar-extras`, whose author tests on an HW-Q930D,
the same model as ours.

Nothing can be read back: SmartThings has returned null for every
`/sec/networkaudio/*` resource since March 2024. So a profile is a set of
values to send, never a snapshot of how the bar is set, and it goes stale the
moment someone uses the remote.
"""

import logging

from soundbar import oauth

logger = logging.getLogger(__name__)

PREFIX = "x.com.samsung.networkaudio."

# Samsung's wire value for Adaptive is "adaptive sound", not "adaptive".
SOUND_MODES = {
    "standard": "standard",
    "surround": "surround",
    "game": "game",
    "adaptive": "adaptive sound",
}

CHANNELS = {
    "centre": "Spk_Center",
    "side": "Spk_Side",
    "wide": "Spk_Wide",
    "front_top": "Spk_Front_Top",
    "rear": "Spk_Rear",
    "rear_top": "Spk_Rear_Top",
}

LEVEL_MIN, LEVEL_MAX = -6, 6
# Not -12: below -6 the HW-Q930D snaps to a single -12 step, so the app would
# show a value the soundbar does not have.
WOOFER_MIN, WOOFER_MAX = -6, 6


class CommandRefusedError(Exception):
    pass


def soundbar_device_id():
    """The bar's SmartThings id, found once and remembered.

    The install only grants the devices picked in the SmartThings app, so
    "the one with volume and execute" is reliable enough and survives the
    device being renamed.
    """
    from soundbar.models import SmartThingsAuth

    auth = SmartThingsAuth.load()
    if auth.soundbar_device_id:
        return auth.soundbar_device_id

    for device in oauth.devices():
        capabilities = {
            capability.get("id")
            for component in device.get("components", [])
            for capability in component.get("capabilities", [])
        }
        if {"audioVolume", "execute"}.issubset(capabilities):
            auth.soundbar_device_id = device["deviceId"]
            auth.save(update_fields=["soundbar_device_id", "updated"])
            return auth.soundbar_device_id

    msg = "no soundbar among the devices this install can see"
    raise CommandRefusedError(msg)


def send(device_id, capability, command, arguments=None):
    """One command. Raises unless SmartThings reports COMPLETED."""
    body = {
        "commands": [
            {
                "component": "main",
                "capability": capability,
                "command": command,
                "arguments": arguments or [],
            },
        ],
    }
    result = oauth.api("POST", f"/devices/{device_id}/commands", json=body)
    results = result.get("results") or []
    if len(results) != 1 or results[0].get("status") != "COMPLETED":
        logger.warning("SmartThings refused %s.%s: %s", capability, command, result)
        msg = f"the soundbar refused {capability}.{command}"
        raise CommandRefusedError(msg)
    return result


def execute(device_id, resource, payload):
    """A write to one of the /sec/networkaudio resources."""
    return send(
        device_id,
        "execute",
        "execute",
        [f"/sec/networkaudio/{resource}", payload],
    )


def set_switch(device_id, *, on):
    return send(device_id, "switch", "on" if on else "off")


def is_on(device_id):
    """Whether the bar is on. Power is a standard capability, so it does read back."""
    status = oauth.api("GET", f"/devices/{device_id}/status")
    value = (
        status.get("components", {})
        .get("main", {})
        .get("switch", {})
        .get("switch", {})
        .get("value")
    )
    return value == "on"


def set_volume(device_id, level):
    return send(device_id, "audioVolume", "setVolume", [int(level)])


def set_mute(device_id, *, muted):
    return send(device_id, "audioMute", "mute" if muted else "unmute")


def set_input(device_id, source):
    return send(device_id, "samsungvd.audioInputSource", "setInputSource", [source])


def set_sound_mode(device_id, mode):
    if mode not in SOUND_MODES:
        msg = f"unknown sound mode {mode!r}"
        raise CommandRefusedError(msg)
    return execute(device_id, "soundmode", {f"{PREFIX}soundmode": SOUND_MODES[mode]})


def set_advanced(device_id, setting, *, on):
    """nightmode, voiceamplifier or bassboost."""
    return execute(device_id, "advancedaudio", {f"{PREFIX}{setting}": int(on)})


def set_woofer(device_id, level):
    return execute(device_id, "woofer", {f"{PREFIX}woofer": int(level)})


def set_channel(device_id, channel, level):
    """One channel only. Never send guessed values for its neighbours."""
    payload = {
        f"{PREFIX}channelVolume": [
            {"name": CHANNELS[channel], "value": int(level)},
        ],
    }
    return execute(device_id, "channelVolume", payload)
