import urllib.request
import json
import random
import time
import StorageServer

cache = StorageServer.StorageServer("Netclient", 24)


def get_user_agents():

    url = "https://microlink.io/user-agents.json"
    # Defining the header to look exactly like a curl request

    headers = {
        "User-Agent": "curl"
    }

    # Create the request object
    req = urllib.request.Request(url, headers=headers)

    # Using a context manager to handle the connection
    with urllib.request.urlopen(req) as response:
        data = response.read().decode('utf-8')
        return json.loads(data)


def get_ua():

    result = cache.cacheFunction(get_user_agents)

    last_gen = cache.get('last_ua_create')
    user_agent = cache.get('user_agent')

    if not last_gen:
        last_gen = 0

    if not user_agent or float(last_gen) < (time.time() - (7 * 24 * 60 * 60)):

        get_user_agents_list = result['user']
        choices = [ua for ua in get_user_agents_list if 'Edg' in ua or 'Chrome' in ua or 'Firefox' in ua and 'Mobile' not in ua and 'Android' not in ua and 'iPhone' not in ua and 'iPad' not in ua]
        user_agent = random.choice(choices)
        cache.set('user_agent', user_agent)
        cache.set('last_ua_create', str(int(time.time())))

        return user_agent

    else:

        return user_agent
