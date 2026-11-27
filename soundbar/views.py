import json
import logging
import secrets

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.crypto import constant_time_compare
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from soundbar import lifecycle
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


@csrf_exempt
@require_POST
def smartapp(request):
    """Where SmartThings posts its lifecycle events.

    Open by necessity: SmartThings has to reach it before any credential
    exists. Signature verification comes once registration works, and until
    then the only thing an unsigned caller can do is make the app GET a URL
    on api.smartthings.com or overwrite tokens it cannot read back.
    """
    try:
        body = json.loads(request.body)
    except ValueError:
        return HttpResponseBadRequest("expected JSON")

    if not isinstance(body, dict):
        return HttpResponseBadRequest("expected an object")

    logger.info("SmartThings lifecycle: %s", body.get("lifecycle"))
    response = lifecycle.handle(body)
    return JsonResponse(response, status=response.get("statusCode", 200))
