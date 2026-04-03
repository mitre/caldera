import json
from types import SimpleNamespace
from unittest import mock

import pytest

from app.contacts.contact_html import Contact
from app.utility.base_world import BaseWorld


class _MockRequest:
    def __init__(self, body):
        self._body = body

    async def text(self):
        return self._body


def _decode_payload(encoded_payload):
    return json.loads(BaseWorld.decode_bytes(encoded_payload))


@pytest.mark.asyncio
async def test_accept_beacon_returns_base64_payload_on_success():
    BaseWorld.apply_config('main', {'app.contact.html': '/weather'})
    contact_svc = mock.AsyncMock()
    app_svc = mock.Mock()
    contact = Contact({'app_svc': app_svc, 'contact_svc': contact_svc})

    agent = SimpleNamespace(
        paw='abc123',
        watchdog=0,
        calculate_sleep=mock.AsyncMock(return_value=30)
    )
    instruction = SimpleNamespace(display={'command': 'whoami'})
    contact_svc.handle_heartbeat.return_value = (agent, [instruction])

    profile = {
        'host': 'test-host',
        'platform': 'linux',
        'executors': ['sh']
    }
    request = _MockRequest(BaseWorld.encode_string(json.dumps(profile)))
    context = await contact._accept_beacon.__wrapped__(contact, request)

    decoded_response = _decode_payload(context['instructions'])
    assert context['contact_path'] == '/weather'
    assert decoded_response['paw'] == 'abc123'
    assert decoded_response['sleep'] == 30
    assert decoded_response['watchdog'] == 0
    assert json.loads(decoded_response['instructions']) == [json.dumps({'command': 'whoami'})]


@pytest.mark.asyncio
async def test_accept_beacon_returns_base64_payload_on_error():
    BaseWorld.apply_config('main', {'app.contact.html': '/weather'})
    contact = Contact({'app_svc': mock.Mock(), 'contact_svc': mock.AsyncMock()})

    context = await contact._accept_beacon.__wrapped__(contact, _MockRequest('not-base64'))
    decoded_response = _decode_payload(context['instructions'])

    assert context['contact_path'] == '/weather'
    assert decoded_response['paw'] == ''
    assert decoded_response['sleep'] == 60
    assert decoded_response['watchdog'] == 0
    assert json.loads(decoded_response['instructions']) == []
