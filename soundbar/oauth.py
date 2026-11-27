"""SmartThings OAuth 2.0, the only approved way in since PATs were cut to 24h.

Samsung killed long-lived personal access tokens on 30 December 2024, so an
app meant to keep working has to hold a refresh token and renew.
"""

import logging
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from soundbar.models import SmartThingsAuth

logger = logging.getLogger(__name__)

AUTHORIZE_URL = "https://api.smartthings.com/oauth/authorize"
TOKEN_URL = "https://api.smartthings.com/oauth/token"  # noqa: S105
API_ROOT = "https://api.smartthings.com/v1"

# Read, write and execute devices. The soundbar's sound settings go through the
# execute capability, hence x:devices.
SCOPES = ["r:devices:*", "w:devices:*", "x:devices:*"]

TIMEOUT = 15


class SmartThingsError(Exception):
    pass


def redirect_uri(request):
    return request.build_absolute_uri(reverse("soundbar:callback"))


def authorize_url(request, state):
    params = {
        "client_id": settings.SMARTTHINGS_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": redirect_uri(request),
        "scope": " ".join(SCOPES),
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def _store(payload):
    auth = SmartThingsAuth.load()
    auth.access_token = payload["access_token"]
    auth.refresh_token = payload["refresh_token"]
    auth.expires_at = timezone.now() + timezone.timedelta(
        seconds=int(payload.get("expires_in", 86399)),
    )
    auth.installed_app_id = payload.get("installed_app_id", auth.installed_app_id)
    auth.save()
    return auth


def _post(data):
    if not settings.SMARTTHINGS_CLIENT_ID or not settings.SMARTTHINGS_CLIENT_SECRET:
        msg = "SMARTTHINGS_CLIENT_ID / SMARTTHINGS_CLIENT_SECRET are not set"
        raise SmartThingsError(msg)
    response = requests.post(
        TOKEN_URL,
        data=data,
        auth=(settings.SMARTTHINGS_CLIENT_ID, settings.SMARTTHINGS_CLIENT_SECRET),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=TIMEOUT,
    )
    if response.status_code != requests.codes.ok:
        # Never log the body: it carries tokens on success and the client id on
        # some failures.
        logger.error("SmartThings token endpoint returned %s", response.status_code)
        msg = f"SmartThings refused the token request ({response.status_code})"
        raise SmartThingsError(msg)
    return response.json()


def exchange_code(request, code):
    return _store(
        _post(
            {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.SMARTTHINGS_CLIENT_ID,
                "redirect_uri": redirect_uri(request),
            },
        ),
    )


def refresh(auth=None):
    auth = auth or SmartThingsAuth.load()
    if not auth.refresh_token:
        msg = "not connected to SmartThings yet"
        raise SmartThingsError(msg)
    return _store(
        _post(
            {
                "grant_type": "refresh_token",
                "refresh_token": auth.refresh_token,
                "client_id": settings.SMARTTHINGS_CLIENT_ID,
            },
        ),
    )


def access_token():
    """A token good for at least the next minute, refreshed if it is not."""
    auth = SmartThingsAuth.load()
    if not auth.is_connected:
        msg = "not connected to SmartThings yet"
        raise SmartThingsError(msg)
    if auth.is_expired:
        auth = refresh(auth)
    return auth.access_token


def api(method, path, **kwargs):
    """A SmartThings API call with the token attached."""
    timeout = kwargs.pop("timeout", TIMEOUT)
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {access_token()}"
    response = requests.request(
        method,
        f"{API_ROOT}{path}",
        headers=headers,
        timeout=timeout,
        **kwargs,
    )
    response.raise_for_status()
    return response.json() if response.content else {}


def devices():
    return api("GET", "/devices").get("items", [])
