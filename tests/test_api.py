import os
import sys

os.environ['BRAVE_API_KEY'] = ''
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import app as appmod


@pytest.fixture()
def client():
    appmod._cache.clear()
    appmod._rate.clear()
    appmod.app.config['TESTING'] = True
    with appmod.app.test_client() as c:
        yield c
    appmod._cache.clear()
    appmod._rate.clear()


def test_health(client):
    assert client.get('/health').get_json() == {'ok': True}


def test_projects_default(client):
    d = client.get('/api/projects').get_json()
    assert len(d['projects']) == 5
    assert d['mode'] == 'demo'
    assert d['source'] == 'local catalogue'


def test_projects_query_filter(client):
    d = client.get('/api/projects?q=kahn').get_json()
    assert len(d['projects']) == 2


def test_projects_type_and_country_filter(client):
    assert len(client.get('/api/projects?type=Residential').get_json()['projects']) == 2
    assert len(client.get('/api/projects?country=Switzerland').get_json()['projects']) == 1


def test_project_detail_full_assets(client):
    d = client.get('/api/project/kimbell-art-museum').get_json()
    counts = d['project']['counts']
    assert len(d['assets']) == sum(counts.values())
    assert all('confidence' not in a for a in d['assets'])
    photos = [a for a in d['assets'] if a['type'] == 'photo']
    assert sum(1 for p in photos if p['thumbnail']) == 1


def test_project_404(client):
    assert client.get('/api/project/does-not-exist').status_code == 404


def test_search_invalid_mode(client):
    r = client.get('/api/search?q=x&mode=bogus')
    assert r.status_code == 400
    assert 'Invalid mode' in r.get_json()['error']


def test_search_empty_query(client):
    d = client.get('/api/search').get_json()
    assert d['results'] == []
    assert 'Enter a project' in d['message']


def test_local_match_phrase(client):
    d = client.get('/api/search?q=louis+kahn&mode=web').get_json()
    assert len(d['local']) == 2


def test_local_match_precision(client):
    d = client.get('/api/search?q=kahn+zzzqqq&mode=web').get_json()
    assert d['local'] == []


def test_local_match_single_token(client):
    d = client.get('/api/search?q=kahn&mode=web').get_json()
    assert len(d['local']) == 2


def test_classify_word_boundary():
    assert appmod.classify('a complaint letter') == 'reference'
    assert appmod.classify('ground floor plans and elevations') == 'plan'
    assert appmod.classify('cross section detail') == 'section'
    assert appmod.classify('kitchen photograph interior') == 'photo'


def test_brave_failure_is_graceful(client, monkeypatch):
    monkeypatch.setenv('BRAVE_API_KEY', 'test-key')
    monkeypatch.setattr(appmod, 'brave', lambda *a, **k: None)
    r = client.get('/api/search?q=anything&mode=all')
    assert r.status_code == 200
    d = r.get_json()
    assert d['mode'] == 'demo'
    assert 'unavailable' in d['notice']


def test_search_results_cached(client, monkeypatch):
    monkeypatch.setenv('BRAVE_API_KEY', 'test-key')
    calls = {'n': 0}

    def fake_brave(endpoint, params):
        calls['n'] += 1
        return {'web': {'results': [{'title': 'Cache probe', 'url': 'https://example.com', 'description': ''}]}}

    monkeypatch.setattr(appmod, 'brave', fake_brave)
    d1 = client.get('/api/search?q=cacheprobe&mode=web').get_json()
    d2 = client.get('/api/search?q=cacheprobe&mode=web').get_json()
    assert calls['n'] == 1
    assert len(d1['results']) == 1
    assert d1['results'] == d2['results']


def test_images_mode_only_images(client, monkeypatch):
    monkeypatch.setenv('BRAVE_API_KEY', 'test-key')
    monkeypatch.setattr(appmod, 'brave', lambda ep, p: {'results': [{'title': 'Plan image', 'link': 'https://img.example/1', 'description': ''}]})
    d = client.get('/api/search?q=plans&mode=images').get_json()
    assert d['results']
    assert all(r['kind'] == 'image' for r in d['results'])


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(appmod, 'RATE_LIMIT', 2)
    assert client.get('/api/search?q=rl1&mode=web').status_code == 200
    assert client.get('/api/search?q=rl2&mode=web').status_code == 200
    r = client.get('/api/search?q=rl3&mode=web')
    assert r.status_code == 429
    assert 'rate limit' in r.get_json()['error']
