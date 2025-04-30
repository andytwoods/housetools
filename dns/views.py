import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import loader
from django.templatetags.static import static
from django.views.decorators.http import require_POST

from dns.models import YouTube

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


def alexa(request):
    rooms = {
        'ROBIN': "robinroom",
        'RYAN': "ryanroom",
        'LIVINGROOM': "livingroom"
    }

    if request.POST.get('first', 'false') == 'true':
        return render(request, 'dns/_alexa.html',
               context = {'rooms': rooms})

    API_URL = "https://api-v2.voicemonkey.io/announcement"

    room = request.POST.get('room')
    message = request.POST.get('message')

    sound_url = static('alexa_tone.mp3')
    sound_url = request.build_absolute_uri(sound_url)

    requests.post(
        API_URL,
        headers={"Authorization": settings.VOICE_MONKEY_TOKEN, "Content-Type": "application/json"},
        json={"device": rooms[room],
              "text": message,
              "audio": sound_url

              },
        timeout=5
    )

    return HttpResponse(status=204)

