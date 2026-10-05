import urllib.request
from urllib.parse import urlencode
import json
import random
import time
import StorageServer

cache = StorageServer.StorageServer("Netclient", 24)


# Static fallback list of modern desktop User Agents in case of offline/network issues
FALLBACK_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64; rv:135.0) Gecko/20100101 Firefox/135.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
]


def get_user_agents():

    url = "https://microlink.io/user-agents.json"
    headers = {
        "User-Agent": "curl"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = response.read().decode('utf-8')
            return json.loads(data)
    except Exception:
        # Fallback to local defaults if network request fails or service is unreachable
        return {'user': FALLBACK_USER_AGENTS}


def get_ua():

    try:
        result = cache.cacheFunction(get_user_agents)
    except Exception:
        result = {'user': FALLBACK_USER_AGENTS}

    last_gen = cache.get('last_ua_create')
    user_agent = cache.get('user_agent')

    if not last_gen:
        last_gen = 0

    if not user_agent or float(last_gen) < (time.time() - (7 * 24 * 60 * 60)):

        get_user_agents_list = result.get('user') or FALLBACK_USER_AGENTS
        # Filter desktop browsers, explicitly excluding mobile devices with proper boolean precedence
        choices = [
            ua for ua in get_user_agents_list
            if any(b in ua for b in ('Edg', 'Chrome', 'Firefox'))
            and not any(m in ua for m in ('Mobile', 'Android', 'iPhone', 'iPad'))
        ]
        if not choices:
            choices = FALLBACK_USER_AGENTS

        user_agent = random.choice(choices)
        cache.set('user_agent', user_agent)
        cache.set('last_ua_create', str(int(time.time())))

        return user_agent

    else:

        return user_agent


def spoofer(url=None, headers=None, get_result=False):

    pipe = '|'

    if not headers:
        headers = {}

    if not headers:
        headers.update({'User-Agent': get_ua()})

    if not get_result:
        return pipe.join([url, urlencode(headers)])
    else:
        return ''.join([pipe, urlencode(headers)])
