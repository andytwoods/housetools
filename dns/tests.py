import json
from unittest import mock

import pytest

from dns.alexa_commands import AlexaClient, AlexaError

KITCHEN = {"accountName": "Kitchen", "deviceFamily": "ECHO", "online": True, "serialNumber": "SN1",
           "deviceType": "DT1", "deviceOwnerCustomerId": "CUST1"}
FIRE_TV = {"accountName": "Andy's Fire TV", "deviceFamily": "FIRE_TV", "online": True, "serialNumber": "SN2",
           "deviceType": "DT2", "deviceOwnerCustomerId": "CUST1"}


def _response(status=200, body=None, cookies=None):
    r = mock.Mock(status_code=status, ok=status < 400, text=json.dumps(body or {}), cookies=cookies or {})
    r.json.return_value = body
    return r


def _client(cookie="session-id=1; csrf=abc"):
    return AlexaClient(cookie=cookie, base_url="https://alexa.example", locale="en-GB")


def test_missing_cookie_is_an_error():
    with pytest.raises(AlexaError, match="ALEXA_COOKIE"):
        AlexaClient(cookie="", base_url="https://alexa.example", locale="en-GB")


@mock.patch("dns.alexa_commands.requests.get")
def test_devices_keeps_only_echos(get):
    get.return_value = _response(body={"devices": [FIRE_TV, KITCHEN]})
    assert list(_client().devices()) == ["Kitchen"]


@mock.patch("dns.alexa_commands.requests.get")
def test_expired_cookie_says_so(get):
    get.return_value = _response(status=401)
    with pytest.raises(AlexaError, match="fresh ALEXA_COOKIE"):
        _client().devices()


@mock.patch("dns.alexa_commands.requests.post")
def test_text_command_payload(post):
    post.return_value = _response()
    _client().text_command(KITCHEN, "What's the weather, today?")

    kwargs = post.call_args.kwargs
    assert post.call_args.args[0] == "https://alexa.example/api/behaviors/preview"
    assert kwargs["headers"]["csrf"] == "abc"
    node = json.loads(kwargs["json"]["sequenceJson"])["startNode"]
    assert node["type"] == "Alexa.TextCommand"
    assert node["operationPayload"] == {"deviceType": "DT1", "deviceSerialNumber": "SN1",
                                        "customerId": "CUST1", "locale": "en-GB",
                                        "text": "what's the weather today"}


@mock.patch("dns.alexa_commands.requests.post")
@mock.patch("dns.alexa_commands.requests.get")
def test_csrf_fetched_when_cookie_lacks_it(get, post):
    get.return_value = _response(cookies={"csrf": "fresh"})
    post.return_value = _response()
    _client(cookie="session-id=1").text_command(KITCHEN, "hello")
    assert post.call_args.kwargs["headers"]["csrf"] == "fresh"
    assert "csrf=fresh" in post.call_args.kwargs["headers"]["Cookie"]


def test_empty_command_rejected():
    with pytest.raises(AlexaError, match="Type a command"):
        _client().text_command(KITCHEN, " ?! ")


def _watch(rf, path, data, **headers):
    from dns.views import watch
    return watch(rf.post(path, data, **headers))


@pytest.fixture
def watch_settings(settings):
    settings.WATCH_TOKEN = "secret"
    settings.VOICE_MONKEY_TOKEN = "vm"
    settings.STORAGES = {**settings.STORAGES,
                         "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
    return settings


def test_watch_rejects_bad_token(rf, watch_settings):
    r = _watch(rf, "/watch/", {"room": "RYAN", "action": "alarm"}, HTTP_AUTHORIZATION="Bearer nope")
    assert r.status_code == 403


def test_watch_rejects_unknown_room(rf, watch_settings):
    r = _watch(rf, "/watch/", {"room": "GARAGE", "action": "alarm"}, HTTP_AUTHORIZATION="Bearer secret")
    assert r.status_code == 400


@mock.patch("dns.views.requests.post")
def test_watch_plays_alarm_in_ryans_room(post, rf, watch_settings):
    post.return_value = _response(body={"success": True})
    r = _watch(rf, "/watch/", {"room": "RYAN", "action": "alarm"}, HTTP_AUTHORIZATION="Bearer secret")
    assert json.loads(r.content) == {"ok": True}
    payload = post.call_args.kwargs["json"]
    assert payload["device"] == "ryanroom2-62kme"
    assert payload["audio"].endswith("long_alarm.mp3")
