# -*- coding: utf-8 -*-

import re
import time

import requests
import six
from six.moves import urllib_parse

from resources.lib.modules import cache
from resources.lib.modules import cleandate
from resources.lib.modules import control
from resources.lib.modules import log_utils
from resources.lib.modules import api_keys

if six.PY2:
    str = unicode
elif six.PY3:
    str = unicode = basestring = str

BASE_URL = 'https://api.trakt.tv'
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'

V2_API_KEY = control.setting('trakt.client_id')
CLIENT_SECRET = control.setting('trakt.client_secret')
UA = control.setting('trakt.ua')
if UA and '/' not in UA:
    UA += '/%s' % control.addonInfo('version')

if V2_API_KEY == '' or CLIENT_SECRET == '':
    V2_API_KEY = api_keys.trakt_client_id
    CLIENT_SECRET = api_keys.trakt_secret
    UA = 'Blacklodge/%s' % control.addonInfo('version')

_SESSION = requests.Session()

from resources.lib.modules.ratelimit import limits, sleep_and_retry
@sleep_and_retry
@limits(calls=1000, period=300)
def _get_limiter():
    pass

@sleep_and_retry
@limits(calls=1, period=1)
def _post_limiter():
    pass


def getTrakt(url, post=None, full=False):
    global _SESSION

    url = urllib_parse.urljoin(BASE_URL, url) if not url.startswith(BASE_URL) else url

    _SESSION.headers.update({'Content-Type': 'application/json', 'User-Agent': UA, 'trakt-api-key': V2_API_KEY, 'trakt-api-version': '2'})

    if getTraktCredentialsInfo():
        if _check_token():
            pass
        else:
            _SESSION.headers.pop('Authorization', None)
    else:
        _SESSION.headers.pop('Authorization', None)

    for attempt in range(3):
        try:
            if not post:
                _get_limiter()
                r = _SESSION.get(url, timeout=30)
            else:
                _post_limiter()
                r = _SESSION.post(url, json=post, timeout=30)

            status_code = r.status_code
            if status_code == 429 or status_code > 500:
                wait_time = int(r.headers.get('Retry-After', 5))
                if status_code == 429:
                    msg = 'Trakt rate limit reached, waiting %s seconds...' % wait_time
                else:
                    msg = 'Trakt Service Unavailable, retrying in %s seconds...' % wait_time
                control.infoDialog(msg)
                log_utils.log('Trakt %s: Waiting %s sec' % (status_code, wait_time))
                control.sleep(wait_time * 1000)
                continue

            if status_code == 401:
                if _refresh_trakt_token():
                    continue
                else:
                    return None

            if status_code in [200, 201, 204]:
                if not full:
                    return r.json()
                else:
                    return r

            if status_code == 400:
                pass
            else:
                log_utils.log('Trakt Error %s for %s' % (status_code, url))
                control.infoDialog('Trakt Error:  %s' % status_code, sound=True)
            return None

        except:
            log_utils.log('getTrakt Error', 1)
            break

    return None

def _check_token():
    now = int(time.time())
    try: expires_at = int(control.setting('trakt.expires_at'))
    except: expires_at = 0

    if (expires_at - now) < 300:
        log_utils.log('Trakt: Token expired or expiring soon. Refreshing...')
        return _refresh_trakt_token()
    return True

def _refresh_trakt_token():
    global _SESSION
    oauth_url = 'https://api.trakt.tv/oauth/token'
    opost = {'client_id': V2_API_KEY, 'client_secret': CLIENT_SECRET, 'redirect_uri': REDIRECT_URI, 'grant_type': 'refresh_token', 'refresh_token': control.setting('trakt.refresh')}

    for _ in range(3):
        _post_limiter()
        try:
            r = _SESSION.post(oauth_url, json=opost, timeout=30)
            if r.status_code == 200:
                res = r.json()
                expires_at = int(time.time()) + int(res['expires_in'])

                control.setSetting(id='trakt.token', value=res['access_token'])
                control.setSetting(id='trakt.refresh', value=res['refresh_token'])
                control.setSetting(id='trakt.expires_at', value=str(expires_at))

                _SESSION.headers.update({'Authorization': 'Bearer %s' % res['access_token']})
                return True
            elif r.status_code == 429:
                control.sleep(int(r.headers.get('Retry-After', 5)) * 1000)
                continue
        except:
            pass
    return False


def authTrakt():
    try:
        if getTraktCredentialsInfo() == True:
            if control.yesnoDialog(control.lang(32511) + '[CR]' + control.lang(32512), heading='Trakt'):
                control.setSetting(id='trakt.user', value='')
                control.setSetting(id='trakt.token', value='')
                control.setSetting(id='trakt.refresh', value='')
                control.setSetting(id='trakt.expires_at', value='')
                control.setSetting(id='trakt.authed', value='')
                control.setSetting(id='trakt.authed2', value='')
                control.setSetting(id='trakt.authed3', value='')
            raise Exception()

        result = getTrakt('/oauth/device/code', {'client_id': V2_API_KEY})
        verification_url = control.lang(32513) % result['verification_url']
        user_code = six.ensure_text(control.lang(32514) % result['user_code'])
        expires_in = int(result['expires_in'])
        device_code = result['device_code']
        interval = result['interval']

        progressDialog = control.progressDialog
        progressDialog.create('Trakt')

        for i in range(0, expires_in):
            try:
                percent = int(100 * float(i) / expires_in)
                progressDialog.update(max(1, percent), verification_url + '[CR]' + user_code)
                if progressDialog.iscanceled(): break
                time.sleep(1)
                if not float(i) % interval == 0: raise Exception()
                r = getTrakt('/oauth/device/token', {'client_id': V2_API_KEY, 'client_secret': CLIENT_SECRET, 'code': device_code})
                if 'access_token' in r: break
            except:
                pass

        try: progressDialog.close()
        except: pass

        token, refresh = r['access_token'], r['refresh_token']
        expires_at = int(time.time()) + int(r['expires_in'])

        headers = {'Content-Type': 'application/json', 'User-Agent': UA, 'trakt-api-key': V2_API_KEY, 'trakt-api-version': '2', 'Authorization': 'Bearer %s' % token}


        result = requests.get(urllib_parse.urljoin(BASE_URL, '/users/me'), headers=headers).json()

        user = result['username']
        authed = '' if user == '' else 'yes'

        control.setSetting(id='trakt.user', value=user)
        control.setSetting(id='trakt.authed', value=authed)
        control.setSetting(id='trakt.authed2', value=authed)
        control.setSetting(id='trakt.authed3', value=authed)
        control.setSetting(id='trakt.token', value=token)
        control.setSetting(id='trakt.refresh', value=refresh)
        control.setSetting(id='trakt.expires_at', value=str(expires_at))
        raise Exception()
    except:
        control.openSettings('4.6')


def getTraktCredentialsInfo():
    user = control.setting('trakt.user').strip()
    token = control.setting('trakt.token')
    refresh = control.setting('trakt.refresh')
    if (user == '' or token == '' or refresh == ''): return False
    return True


def getTraktIndicatorsInfo():
    indicators = control.setting('indicators') if getTraktCredentialsInfo() == False else control.setting('indicators.alt')
    indicators = True if indicators == '1' else False
    return indicators


def getTraktAddonMovieInfo():
    try: scrobble = control.addon('script.trakt').getSetting('scrobble_movie')
    except: scrobble = ''
    try: ExcludeHTTP = control.addon('script.trakt').getSetting('ExcludeHTTP')
    except: ExcludeHTTP = ''
    try: authorization = control.addon('script.trakt').getSetting('authorization')
    except: authorization = ''
    if scrobble == 'true' and ExcludeHTTP == 'false' and not authorization == '': return True
    else: return False


def getTraktAddonEpisodeInfo():
    try: scrobble = control.addon('script.trakt').getSetting('scrobble_episode')
    except: scrobble = ''
    try: ExcludeHTTP = control.addon('script.trakt').getSetting('ExcludeHTTP')
    except: ExcludeHTTP = ''
    try: authorization = control.addon('script.trakt').getSetting('authorization')
    except: authorization = ''
    if scrobble == 'true' and ExcludeHTTP == 'false' and not authorization == '': return True
    else: return False


def manager(name, imdb, tmdb, content):
    try:
        post = {"movies": [{"ids": {"imdb": imdb}}]} if content == 'movie' else {"shows": [{"ids": {"tmdb": tmdb}}]}

        items = [
            (control.lang(32516), '/sync/collection'),
            (control.lang(32517), '/sync/collection/remove'),
            (control.lang(32518), '/sync/watchlist'),
            (control.lang(32519), '/sync/watchlist/remove'),
            (control.lang(32523), '/sync/favorites'),
            (control.lang(32524), '/sync/favorites/remove'),
            (control.lang(32520), '/users/me/lists/%s/items')
        ]

        result = getTrakt('/users/me/lists')
        lists = [(i['name'], i['ids']['slug']) for i in result]
        lists = [lists[i//2] for i in range(len(lists)*2)]
        for i in range(0, len(lists), 2):
            lists[i] = ((six.ensure_str(control.lang(32521) % lists[i][0])), '/users/me/lists/%s/items' % lists[i][1])
        for i in range(1, len(lists), 2):
            lists[i] = ((six.ensure_str(control.lang(32522) % lists[i][0])), '/users/me/lists/%s/items/remove' % lists[i][1])
        items += lists

        select = control.selectDialog([i[0] for i in items], control.lang(32515))

        if select == -1:
            return
        elif select == 6:
            new = control.inputDialog(control.lang(32520))
            if not new: return
            result = getTrakt('/users/me/lists', post={"name": new, "privacy": "private"})

            try: slug = result['ids']['slug']
            except: return control.infoDialog(control.lang(32515), heading=str(name), sound=True, icon='ERROR')
            result = getTrakt(items[select][1] % slug, post=post)
        else:
            result = getTrakt(items[select][1], post=post)

        icon = control.infoLabel('ListItem.Icon') if result else 'ERROR'

        control.infoDialog(control.lang(32515), heading=str(name), sound=True, icon=icon)
    except:
        return


def slug(name):
    name = name.strip()
    name = name.lower()
    name = re.sub('[^a-z0-9_]', '-', name)
    name = re.sub('--+', '-', name)
    if name.endswith('-'):
        name = name.rstrip('-')
    return name


def getActivity():
    try:
        i = getTrakt('/sync/last_activities')

        activity = []
        activity.append(i['movies']['collected_at'])
        activity.append(i['episodes']['collected_at'])
        activity.append(i['movies']['watchlisted_at'])
        activity.append(i['shows']['watchlisted_at'])
        activity.append(i['seasons']['watchlisted_at'])
        activity.append(i['episodes']['watchlisted_at'])
        activity.append(i['movies']['hidden_at'])
        activity.append(i['shows']['hidden_at'])
        activity.append(i['seasons']['hidden_at'])
        activity.append(i['movies']['favorited_at'])
        activity.append(i['shows']['favorited_at'])
        activity.append(i['shows']['dropped_at'])
        activity.append(i['lists']['updated_at'])
        activity.append(i['lists']['liked_at'])
        activity = [int(cleandate.iso_2_utc(i)) for i in activity]
        activity = sorted(activity, key=int)[-1]

        return activity
    except:
        pass


def getWatchedActivity():
    try:
        i = getTrakt('/sync/last_activities')

        activity = []
        activity.append(i['movies']['watched_at'])
        activity.append(i['episodes']['watched_at'])
        activity = [int(cleandate.iso_2_utc(i)) for i in activity]
        activity = sorted(activity, key=int)[-1]

        return activity
    except:
        pass


def cachesyncMovies(timeout=0):
    indicators = cache.get(syncMovies, timeout, control.setting('trakt.user').strip())
    return indicators


def timeoutsyncMovies():
    timeout = cache.timeout(syncMovies, control.setting('trakt.user').strip())
    return timeout


def syncMovies(user):
    try:
        if getTraktCredentialsInfo() == False: return
        indicators = getTrakt('/users/me/watched/movies')
        indicators = [i['movie']['ids'] for i in indicators]
        indicators = [str(i['imdb']) for i in indicators if 'imdb' in i]
        return indicators
    except:
        pass


def cachesyncTVShows(timeout=0):
    indicators = cache.get(syncTVShows, timeout, control.setting('trakt.user').strip())
    return indicators


def timeoutsyncTVShows():
    timeout = cache.timeout(syncTVShows, control.setting('trakt.user').strip())
    if not timeout: timeout = 0
    return timeout


def syncTVShows(user):
    try:
        if getTraktCredentialsInfo() == False: return
        indicators = getTrakt('/users/me/watched/shows?extended=full')
        indicators = [(i['show']['ids']['imdb'], i['show']['aired_episodes'], sum([[(s['number'], e['number']) for e in s['episodes']] for s in i['seasons']], [])) for i in indicators]
        indicators = [(str(i[0]), int(i[1]), i[2]) for i in indicators]
        return indicators
    except:
        pass


def syncSeason(imdb):
    try:
        if getTraktCredentialsInfo() == False: return
        indicators = getTrakt('/shows/%s/progress/watched?specials=false&hidden=false' % imdb)
        indicators = indicators['seasons']
        indicators = [(i['number'], [x['completed'] for x in i['episodes']]) for i in indicators]
        indicators = ['%01d' % int(i[0]) for i in indicators if not False in i[1]]
        return indicators
    except:
        pass


def syncTraktStatus():
    try:
        cachesyncMovies()
        cachesyncTVShows()
        control.infoDialog(control.lang(32092))
    except:
        control.infoDialog('Trakt sync failed')
        pass


def markMovieAsWatched(imdb):
    if not imdb.startswith('tt'): imdb = 'tt' + imdb
    return getTrakt('/sync/history', {"movies": [{"ids": {"imdb": imdb}}]})


def markMovieAsNotWatched(imdb):
    if not imdb.startswith('tt'): imdb = 'tt' + imdb
    return getTrakt('/sync/history/remove', {"movies": [{"ids": {"imdb": imdb}}]})


def markTVShowAsWatched(imdb):
    return getTrakt('/sync/history', {"shows": [{"ids": {"imdb": imdb}}]})


def markTVShowAsNotWatched(imdb):
    return getTrakt('/sync/history/remove', {"shows": [{"ids": {"imdb": imdb}}]})


def markEpisodeAsWatched(imdb, season, episode):
    season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
    return getTrakt('/sync/history', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {"imdb": imdb}}]})


def markEpisodeAsNotWatched(imdb, season, episode):
    season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
    return getTrakt('/sync/history/remove', {"shows": [{"seasons": [{"episodes": [{"number": episode}], "number": season}], "ids": {"imdb": imdb}}]})


def scrobbleMovie(imdb, watched_percent, action):
    if not imdb.startswith('tt'): imdb = 'tt' + imdb
    return getTrakt('/scrobble/%s' % action, {"movie": {"ids": {"imdb": imdb}}, "progress": watched_percent})


def scrobbleEpisode(imdb, season, episode, watched_percent, action):
    if not imdb.startswith('tt'): imdb = 'tt' + imdb
    season, episode = int('%01d' % int(season)), int('%01d' % int(episode))
    return getTrakt('/scrobble/%s' % action, {"show": {"ids": {"imdb": imdb}}, "episode": {"season": season, "number": episode}, "progress": watched_percent})


def getMovieTranslation(id, lang, full=False):
    url = '/movies/%s/translations/%s' % (id, lang)
    try:
        item = getTrakt(url)[0]
        return item if full else item.get('title')
    except:
        pass


def getTVShowTranslation(id, lang, season=None, episode=None, full=False):
    if season and episode:
        url = '/shows/%s/seasons/%s/episodes/%s/translations/%s' % (id, season, episode, lang)
    else:
        url = '/shows/%s/translations/%s' % (id, lang)

    try:
        item = getTrakt(url)[0]
        return item if full else item.get('title')
    except:
        pass


def getMovieAliases(id):
    try: return getTrakt('/movies/%s/aliases' % id)
    except: return []


def getTVShowAliases(id):
    try: return getTrakt('/shows/%s/aliases' % id)
    except: return []


def getMovieSummary(id, full=True):
    try:
        url = '/movies/%s' % id
        if full: url += '?extended=full'
        return getTrakt(url)
    except:
        return


def getTVShowSummary(id, full=True):
    try:
        url = '/shows/%s' % id
        if full: url += '?extended=full'
        return getTrakt(url)
    except:
        return


def getPeople(id, content_type, full=False):
    try:
        url = '/%s/%s/people' % (content_type, id)
        if full: url += '?extended=full'
        return getTrakt(url)
    except:
        return

def SearchAll(title, year, full=True):
    try:
        return SearchMovie(title, year, full) + SearchTVShow(title, year, full)
    except:
        return

def SearchMovie(title, year, full=True):
    try:
        url = '/search/movie?query=%s' % urllib_parse.quote_plus(title)

        if year: url += '&year=%s' % year
        if full: url += '&extended=full'
        return getTrakt(url)
    except:
        return

def SearchTVShow(title, year, full=True):
    try:
        url = '/search/show?query=%s' % urllib_parse.quote_plus(title)

        if year: url += '&year=%s' % year
        if full: url += '&extended=full'
        return getTrakt(url)
    except:
        return

def IdLookup(content, type, type_id):
    try:
        r = getTrakt('/search/%s/%s?type=%s' % (type, type_id, content))
        return r[0].get(content, {}).get('ids', [])
    except:
        return {}

def getGenre(content, type, type_id):
    try:
        r = '/search/%s/%s?type=%s&extended=full' % (type, type_id, content)
        r = getTrakt(r)
        r = r[0].get(content, {}).get('genres', [])
        return r
    except:
        return []

def getEpisodeRating(imdb, season, episode):
    try:
        if not imdb.startswith('tt'): imdb = 'tt' + imdb
        url = '/shows/%s/seasons/%s/episodes/%s/ratings' % (imdb, season, episode)
        r = getTrakt(url)
        r1 = r.get('rating', '0')
        r2 = r.get('votes', '0')
        return str(r1), str(r2)
    except:
        return
