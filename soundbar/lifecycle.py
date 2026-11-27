"""The SmartThings SmartApp lifecycle, which is how the tokens arrive.

Samsung refuses API-only OAuth apps on a personal account (POST /v1/apps
returns 403 since the Developer Workspace closed to new integrations on
31 August 2026). A WebHook SmartApp is the way left in: SmartThings posts
lifecycle events here, and hands over an auth token and a refresh token at
INSTALL, so there is no browser OAuth flow at all.

Lifecycles, in the order they happen:

  CONFIRMATION  once, at registration. We must GET the confirmation URL.
  PING          health check. Echo the challenge back.
  CONFIGURATION INITIALIZE then PAGE, drawing the install screens.
  INSTALL       tokens arrive here.
  UPDATE        tokens arrive again when the install is edited.
  EVENT         subscriptions fire here. Nothing subscribed yet.
  UNINSTALL     forget the tokens.
"""

import logging

import requests
from django.utils import timezone

from soundbar.models import SmartThingsAuth

logger = logging.getLogger(__name__)

TIMEOUT = 15

# What the SmartApp asks the user to grant at install time.
PERMISSIONS = ["r:devices:*", "x:devices:*"]


def handle(body):
    """Take a lifecycle request body, return the response body."""
    lifecycle = body.get("lifecycle", "")
    handler = {
        "CONFIRMATION": _confirmation,
        "PING": _ping,
        "CONFIGURATION": _configuration,
        "INSTALL": _install,
        "UPDATE": _update,
        "EVENT": _event,
        "UNINSTALL": _uninstall,
        "OAUTH_CALLBACK": _event,
    }.get(lifecycle)
    if handler is None:
        logger.warning("Unknown SmartThings lifecycle %r", lifecycle)
        return {"statusCode": 400}
    return handler(body)


def _confirmation(body):
    url = body.get("confirmationData", {}).get("confirmationUrl", "")
    if not url.startswith("https://api.smartthings.com/"):
        # Only ever call Samsung's own host, never a URL someone else posts.
        logger.error("Refusing a confirmation URL that is not SmartThings')")
        return {"statusCode": 400}
    try:
        requests.get(url, timeout=TIMEOUT).raise_for_status()
    except requests.RequestException:
        logger.exception("Could not reach the SmartThings confirmation URL")
        return {"statusCode": 500}
    logger.info("SmartThings registration confirmed")
    return {"statusCode": 200, "targetUrl": url}


def _ping(body):
    return {
        "statusCode": 200,
        "pingData": {"challenge": body.get("pingData", {}).get("challenge", "")},
    }


def _configuration(body):
    data = body.get("configurationData", {})
    phase = data.get("phase")
    if phase == "INITIALIZE":
        return {
            "statusCode": 200,
            "configurationData": {
                "initialize": {
                    "id": "housetools-soundbar",
                    "name": "housetools",
                    "description": "Sound profiles for the soundbar",
                    "permissions": PERMISSIONS,
                    "firstPageId": "1",
                },
            },
        }
    if phase == "PAGE":
        return {
            "statusCode": 200,
            "configurationData": {
                "page": {
                    "pageId": "1",
                    "name": "Pick the soundbar",
                    "nextPageId": None,
                    "previousPageId": None,
                    "complete": True,
                    "sections": [
                        {
                            "name": "Soundbar",
                            "settings": [
                                {
                                    "id": "soundbar",
                                    "name": "Soundbar",
                                    "description": "Tap to choose",
                                    "type": "DEVICE",
                                    "required": True,
                                    "multiple": False,
                                    "capabilities": ["execute"],
                                    "permissions": ["r", "x"],
                                },
                            ],
                        },
                    ],
                },
            },
        }
    logger.warning("Unknown CONFIGURATION phase %r", phase)
    return {"statusCode": 400}


def _store_tokens(data):
    installed = data.get("installedApp", {})
    auth = SmartThingsAuth.load()
    auth.access_token = data.get("authToken", auth.access_token)
    auth.refresh_token = data.get("refreshToken", auth.refresh_token)
    # The lifecycle payload gives no expiry; SmartThings tokens run about a day.
    auth.expires_at = timezone.now() + timezone.timedelta(seconds=86399)
    auth.installed_app_id = installed.get("installedAppId", auth.installed_app_id)
    auth.save()
    return auth


def _install(body):
    _store_tokens(body.get("installData", {}))
    logger.info("SmartThings SmartApp installed")
    return {"statusCode": 200, "installData": {}}


def _update(body):
    _store_tokens(body.get("updateData", {}))
    logger.info("SmartThings SmartApp updated")
    return {"statusCode": 200, "updateData": {}}


def _event(body):
    return {"statusCode": 200, "eventData": {}}


def _uninstall(body):
    auth = SmartThingsAuth.load()
    auth.access_token = ""
    auth.refresh_token = ""
    auth.expires_at = None
    auth.save()
    logger.info("SmartThings SmartApp uninstalled; tokens cleared")
    return {"statusCode": 200, "uninstallData": {}}
