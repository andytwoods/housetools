import logging
import secrets

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.crypto import constant_time_compare

from soundbar import oauth
from soundbar.models import SmartThingsAuth

logger = logging.getLogger(__name__)

STATE_KEY = "smartthings_oauth_state"


@login_required
def status(request):
    auth = SmartThingsAuth.load()
    found = []
    if auth.is_connected:
        try:
            found = [
                (d.get("label") or d.get("name"), d.get("deviceId"))
                for d in oauth.devices()
            ]
        except Exception as error:  # noqa: BLE001
            messages.error(request, f"SmartThings: {error}")
    return render(
        request,
        "soundbar/status.html",
        {"auth": auth, "devices": found, "redirect_uri": oauth.redirect_uri(request)},
    )


@login_required
def connect(request):
    state = secrets.token_urlsafe(24)
    request.session[STATE_KEY] = state
    return redirect(oauth.authorize_url(request, state))


@login_required
def callback(request):
    expected = request.session.pop(STATE_KEY, "")
    given = request.GET.get("state", "")
    if not expected or not constant_time_compare(expected, given):
        messages.error(request, "SmartThings sent back an unexpected state. Try again.")
        return redirect("soundbar:status")

    error = request.GET.get("error")
    if error:
        messages.error(request, f"SmartThings refused: {error}")
        return redirect("soundbar:status")

    code = request.GET.get("code", "")
    if not code:
        messages.error(request, "SmartThings sent no authorisation code.")
        return redirect("soundbar:status")

    try:
        oauth.exchange_code(request, code)
    except Exception as exc:
        logger.exception("SmartThings code exchange failed")
        messages.error(request, f"Could not finish connecting: {exc}")
    else:
        messages.success(request, "Connected to SmartThings.")
    return redirect("soundbar:status")
