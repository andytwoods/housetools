import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import loader
from django.templatetags.static import static
from django.contrib.auth.decorators import login_required
from django.utils.crypto import constant_time_compare
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import logging

from django.utils.html import escape

from dns.alexa_commands import AlexaClient, AlexaError
from dns.models import YouTube

logger = logging.getLogger(__name__)

VOICE_MONKEY_ANNOUNCE_URL = "https://api-v3.voicemonkey.io/announce"

# Room -> Voice Monkey v3 speaker id (GET https://api-v3.voicemonkey.io/devices).
# Ryan's Echo is "ryanroom2"; the parents' Echo kept the old "ryanroom" name.
VOICE_MONKEY_DEVICES = {
    'ROBIN': "robinroom-nw8uu",
    'RYAN': "ryanroom2-62kme",
    'PARENTS': "ryanroom-374ee",
    'LIVINGROOM': "livingroom-2352t",
    'KITCHEN': "kitchen-3ebuj",
}

BLOCKLIST_URL = f'https://api.nextdns.io/profiles/{settings.NEXTDNS_PROFILE_ID}/denylist'

# Headers for authorization
HEADERS = {
    'X-Api-Key': settings.NEXTDNS_API_TOKEN,
    'Content-Type': 'application/json'
}

REMOVE = 'remove'
ADD = 'add'


def modify_blocklist(domain: str, action: str):
    if action == REMOVE:
        requests.delete(BLOCKLIST_URL + '/' + domain, headers=HEADERS)
    if action == ADD:
        try:
            payload = {'id': domain}
            requests.post(BLOCKLIST_URL, headers=HEADERS, json=payload)

        except Exception as e:
            return {'status': 'error', 'message': str(e)}


def get_configuration():
    response = requests.get(f"https://api.nextdns.io/profiles/{settings.NEXTDNS_PROFILE_ID}", headers=HEADERS)
    return response.json()


def check_enabled_in_configuration(youtube_urls_to_block):
    config = get_configuration()["data"]["denylist"]
    blocked_domains = [info['id'] for info in config]
    for domain in youtube_urls_to_block:
        if domain in blocked_domains:
            return False

    return True


@login_required
@require_POST
def youtube_status(request):
    youtube_urls_to_block = ['googlevideo.com', 'youtubei.googleapis.com', 'youtube.com']

    status = check_enabled_in_configuration(youtube_urls_to_block)
    first = request.POST.get('first', 'false') == 'true'
    if not first:
        status = not status
        for domain in youtube_urls_to_block:
            modify_blocklist(domain, REMOVE if status else ADD)

    template = loader.get_template('dns/_youtube_status.html')
    rendered_template = template.render(context={'status': status})
    return HttpResponse(rendered_template)


@login_required
@require_POST
def alexa(request):
    rooms = {
        'ROBIN': "robinroom",
        'RYAN': "ryanroom",
        'PARENTS': "parentsroom",
        'LIVINGROOM': "livingroom",
        'KITCHEN': "kitchen",
    }

    if request.POST.get('first', 'false') == 'true':
        return render(request, 'dns/_alexa.html',
               context = {'rooms': rooms})

    room = request.POST.get('room')
    message = request.POST.get('message')

    sound_url = None
    if request.POST.get('chime'):
        sound_url = request.build_absolute_uri(static('alexa_tone.mp3'))
    if request.POST.get('alarm'):
        sound_url = request.build_absolute_uri(static('long_alarm.mp3'))

    device = VOICE_MONKEY_DEVICES.get(room)
    if device is None:
        return HttpResponse('<p class="text-danger">Pick a device.</p>')

    error = voice_monkey_announce(device, speech=message, audio=sound_url)
    if error is None:
        return HttpResponse(f'<p class="text-success">Sent to {escape(device)}.</p>')
    return HttpResponse(f'<p class="text-danger">{escape(error)}</p>')


def voice_monkey_announce(device, speech=None, audio=None):
    """Announce on a Voice Monkey speaker. Returns None on success, else an error message."""
    payload = {"token": settings.VOICE_MONKEY_TOKEN, "device": device}
    if speech:
        payload["speech"] = speech
    if audio:
        payload["audio"] = audio

    try:
        response = requests.post(VOICE_MONKEY_ANNOUNCE_URL, json=payload, timeout=10)
        result = response.json()
    except (requests.RequestException, ValueError) as e:
        logger.error("Voice Monkey request failed: %s", e)
        return f"Voice Monkey unreachable: {e}"

    if response.ok and result.get("success"):
        return None
    logger.error("Voice Monkey error %s: %s", response.status_code, result)
    return f"Voice Monkey said: {result.get('error', result)}"


# Sounds the watch app can play, by action name (files in housetools/static/).
WATCH_SOUNDS = {
    'alarm': 'long_alarm.mp3',
    'chime': 'alexa_tone.mp3',
    'benny': 'benny_hill.mp3',
}


@csrf_exempt
@require_POST
def watch(request):
    """Garmin watch app: play a sound on a room's Echo. Auth is a shared bearer token."""
    expected = settings.WATCH_TOKEN
    supplied = request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
    if not expected or not constant_time_compare(supplied, expected):
        return JsonResponse({'ok': False, 'error': 'bad token'}, status=403)

    device = VOICE_MONKEY_DEVICES.get(request.POST.get('room', ''))
    sound = WATCH_SOUNDS.get(request.POST.get('action', ''))
    if device is None or sound is None:
        return JsonResponse({'ok': False, 'error': 'bad room or action'}, status=400)

    error = voice_monkey_announce(device, audio=request.build_absolute_uri(static(sound)))
    if error:
        return JsonResponse({'ok': False, 'error': error}, status=502)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def alexa_command(request):
    """Type a command; the chosen Echo acts on it and answers out loud."""
    try:
        client = AlexaClient()
        devices = client.devices()
        if request.POST.get('first', 'false') == 'true':
            return render(request, 'dns/_alexa_command.html', context={'devices': devices})

        device = devices.get(request.POST.get('device', ''))
        if device is None:
            return HttpResponse('<p class="text-danger">Pick an Echo.</p>')
        command = request.POST.get('command', '')
        client.text_command(device, command)
    except (AlexaError, requests.RequestException) as e:
        logger.error("Alexa command failed: %s", e)
        message = f'<p class="text-danger">{escape(str(e))}</p>'
        if request.POST.get('first', 'false') == 'true':
            return render(request, 'dns/_alexa_command.html', context={'error': str(e)})
        return HttpResponse(message)
    return HttpResponse(f'<p class="text-success">Sent "{escape(command)}" to {escape(device["accountName"])}. '
                        f'Listen for the answer.</p>')
