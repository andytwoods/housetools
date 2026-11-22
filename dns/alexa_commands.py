"""Send a typed command to a chosen Echo, as if it had been spoken to it.

Uses the unofficial Alexa web API (the one the old alexa.amazon.co.uk site and
alexa-remote2 use), authenticated with an Amazon session cookie held in
ALEXA_COOKIE. Amazon does not support this: when the cookie expires or Amazon
changes the API, calls fail and the view says so. The Echo answers out loud;
nothing comes back here except whether Amazon accepted the command.
"""
import json
import re

import requests
from django.conf import settings

TIMEOUT = 10
SPEAKER_FAMILIES = {"ECHO", "KNIGHT", "ROOK"}  # Echo, Echo Show, Echo (other)


class AlexaError(Exception):
    pass


def _cookie_value(cookie, name):
    match = re.search(rf"(?:^|;\s*){re.escape(name)}=([^;]+)", cookie)
    return match.group(1) if match else None


class AlexaClient:
    def __init__(self, cookie=None, base_url=None, locale=None):
        self.cookie = (cookie if cookie is not None else settings.ALEXA_COOKIE).strip()
        self.base_url = (base_url or settings.ALEXA_BASE_URL).rstrip("/")
        self.locale = locale or settings.ALEXA_LOCALE
        if not self.cookie:
            raise AlexaError("ALEXA_COOKIE is not set.")
        self._csrf = _cookie_value(self.cookie, "csrf")

    def _headers(self):
        headers = {
            "Cookie": self.cookie,
            "Referer": f"{self.base_url}/spa/index.html",
            "Origin": self.base_url,
            "Accept": "application/json; charset=utf-8",
        }
        if self._csrf:
            headers["csrf"] = self._csrf
        return headers

    def _ensure_csrf(self):
        if self._csrf:
            return
        response = requests.get(f"{self.base_url}/api/language", headers=self._headers(), timeout=TIMEOUT)
        self._csrf = response.cookies.get("csrf")
        if not self._csrf:
            raise AlexaError("Amazon gave no csrf token; the cookie has probably expired.")
        self.cookie = f"{self.cookie}; csrf={self._csrf}"

    def _check(self, response):
        if response.status_code in (401, 403):
            raise AlexaError(f"Amazon refused the cookie (HTTP {response.status_code}); paste a fresh ALEXA_COOKIE.")
        if not response.ok:
            raise AlexaError(f"Amazon returned HTTP {response.status_code}: {response.text[:200]}")
        return response

    def devices(self):
        """Echo devices that can speak, as {name: device dict}."""
        response = self._check(requests.get(
            f"{self.base_url}/api/devices-v2/device", params={"cached": "false"},
            headers=self._headers(), timeout=TIMEOUT))
        try:
            devices = response.json()["devices"]
        except (ValueError, KeyError) as e:
            raise AlexaError("Amazon's device list was not JSON; the cookie has probably expired.") from e
        speakers = [d for d in devices if d.get("deviceFamily") in SPEAKER_FAMILIES and d.get("online", True)]
        return {d["accountName"]: d for d in sorted(speakers, key=lambda d: d["accountName"])}

    def text_command(self, device, text):
        """Make `device` (a dict from devices()) act on `text` as if spoken to it."""
        text = re.sub(r"[,;:!?.]", "", text).strip().lower()
        if not text:
            raise AlexaError("Type a command.")
        self._ensure_csrf()
        node = {
            "@type": "com.amazon.alexa.behaviors.model.OpaquePayloadOperationNode",
            "type": "Alexa.TextCommand",
            "skillId": "amzn1.ask.1p.tellalexa",
            "operationPayload": {
                "deviceType": device["deviceType"],
                "deviceSerialNumber": device["serialNumber"],
                "customerId": device["deviceOwnerCustomerId"],
                "locale": self.locale,
                "text": text,
            },
        }
        body = {
            "behaviorId": "PREVIEW",
            "sequenceJson": json.dumps({"@type": "com.amazon.alexa.behaviors.model.Sequence", "startNode": node}),
            "status": "ENABLED",
        }
        self._check(requests.post(f"{self.base_url}/api/behaviors/preview",
                                  json=body, headers=self._headers(), timeout=TIMEOUT))
