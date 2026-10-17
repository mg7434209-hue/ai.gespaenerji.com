"""Doğal ses uçları: oturum sınırı, gizlilik ve API hataları (canlı API çağrısı yok)."""
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.config import settings
from app.auth.dependencies import get_current_user
from app.routers.jarvis import router


def client(auth=True):
    app = FastAPI()
    app.include_router(router)
    if auth:
        app.dependency_overrides[get_current_user] = lambda: object()
    return TestClient(app)


def upstream(monkeypatch, status=200, payload=None):
    calls = []
    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def aclose(self): pass
        def build_request(self, method, url, **kwargs):
            return (url, kwargs)
        async def send(self, request, **kwargs):
            url, kwargs = request
            calls.append((url, kwargs))
            if status == 200:
                return httpx.Response(200, content=b'ID3-test-audio', headers={'content-type': 'audio/mpeg'})
            return httpx.Response(status, json={'error': {'code': payload}})
    monkeypatch.setattr(httpx, 'AsyncClient', FakeClient)
    monkeypatch.setattr(settings, 'openai_api_key', 'test-key-not-real')
    return calls


def test_requires_login():
    assert client(False).post('/api/jarvis/speech', json={'text': 'Merhaba'}).status_code == 401


def test_audio_private_and_key_server_only(monkeypatch):
    calls = upstream(monkeypatch)
    response = client().post('/api/jarvis/speech', json={'text': 'Merhaba Mustafa.'})
    assert response.status_code == 200
    assert response.headers['content-type'] == 'audio/mpeg'
    assert response.headers['cache-control'] == 'no-store, private'
    assert b'test-key' not in response.content
    assert calls[0][1]['json']['model'] == 'gpt-4o-mini-tts'
    assert calls[0][1]['json']['voice'] == 'marin'


@pytest.mark.parametrize('text', ['', ' ' , 'x' * 4001])
def test_input_bounded(monkeypatch, text):
    calls = upstream(monkeypatch)
    assert client().post('/api/jarvis/speech', json={'text': text}).status_code in (400, 422)
    assert not calls


@pytest.mark.parametrize('code', ['credit_balance_exhausted', 'insufficient_quota'])
def test_balance_not_rate_limit(monkeypatch, code):
    upstream(monkeypatch, 429, code)
    response = client().post('/api/jarvis/speech', json={'text': 'Merhaba'})
    assert response.status_code == 502
    assert 'kredisi yetersiz' in response.json()['detail']


def test_missing_key_actionable(monkeypatch):
    calls = upstream(monkeypatch)
    monkeypatch.setattr(settings, 'openai_api_key', '')
    response = client().post('/api/jarvis/speech', json={'text': 'Merhaba'})
    assert response.status_code == 503
    assert 'Railway' in response.json()['detail']
    assert not calls
