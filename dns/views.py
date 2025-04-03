import requests
from django.conf import settings
from django.http import HttpResponse
from django.template import loader

from dns.models import YouTube

BLOCKLIST_URL = f'https://api.nextdns.io/profiles/{settings.NEXTDNS_PROFILE_ID}/denylist'

# Headers for authorization
HEADERS = {
    'X-Api-Key': settings.NEXTDNS_API_TOKEN,
    'Content-Type': 'application/json'
}

REMOVE = 'remove'
ADD = 'add'
CAN_TAKE_5_MINS = ' (it can take 5 minutes...)'

def modify_blocklist(domain: str, action: str):

    if action == REMOVE:
        requests.delete(BLOCKLIST_URL + '/' + domain, headers=HEADERS)
        return 'allowed access to ' + domain + CAN_TAKE_5_MINS
    if action == ADD:
        try:
            payload = {'id': domain}
            response = requests.post(BLOCKLIST_URL, headers=HEADERS, json=payload)
            return 'blocked ' + domain + CAN_TAKE_5_MINS

        except Exception as e:
            return {'status': 'error', 'message': str(e)}


def get_configuration():
    response = requests.get(f"https://api.nextdns.io/profiles/{settings.NEXTDNS_PROFILE_ID}", headers=HEADERS)
    return response.json()

def scan_currently_being_active():
    pass
#get_configuration()


def youtube_status(request):

    youtube, created = YouTube.objects.get_or_create(status=True)

    if request.htmx:
        if not created:
            youtube.status = not youtube.status

        if youtube.status:
            modify_blocklist('youtube.com', REMOVE)
        else:
            modify_blocklist('youtube.com', ADD)

        youtube.save()

    template = loader.get_template('dns/_youtube_status.html')
    rendered_template = template.render(context={'status': youtube.status})
    return HttpResponse(rendered_template)

