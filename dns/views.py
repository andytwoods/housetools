import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
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

