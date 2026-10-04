# -*- coding: utf-8 -*-

import hashlib
import json
import re
import threading
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

# Trakt's rate-limit guide documents 500 authed GET calls per 5 minutes (and
# 1 POST/PUT/DELETE per second). Measured with real requests, ~4 calls/sec
# returned 429 after roughly 500 calls, while ~2 calls/sec stayed clean past
# 1200 calls. This mirrors the POST limiter and keeps GETs under the rate that
# triggered 429.
@sleep_and_retry
@limits(calls=2, period=1)
def _get_rate_limiter():
    pass

@sleep_and_retry
@limits(calls=1, period=1)
def _post_limiter():
    pass


# State shared by every Blacklodge run (plugin calls, widgets, service): each
# plugin call runs in its own interpreter, so module variables are not shared.
# Home window properties are.
_RETRY_PROP = 'plugin.video.blacklodge.trakt.retry_until'
_REFRESH_PROP = 'plugin.video.blacklodge.trakt.refresh_fail'
_NOTIFY_PROP = 'plugin.video.blacklodge.trakt.auth_notified'
# One refresh at a time within a run (lists fetch in many threads).
_REFRESH_LOCK = threading.Lock()


_MARK_MAX = 600


def _mark_left(until):
    # Seconds left until an absolute time stored in a window property. No mark
    # is ever set longer than _MARK_MAX, so more than that means the clock was
    # moved back (e.g. a box that booted with a wrong date before NTP): the
    # mark is treated as expired instead of blocking until Kodi restarts.
    left = float(until) - time.time()
    return left if 0 < left <= _MARK_MAX else 0


def _retry_wait():
    # Seconds left of the last Retry-After that Trakt sent to any Blacklodge run.
    try: return _mark_left(control.window.getProperty(_RETRY_PROP) or 0)
    except: return 0


def _set_retry(wait_time):
    # Never shortens a longer wait already set by another run.
    try:
        wait_time = min(max(wait_time, 1), _MARK_MAX)
        if _retry_wait() < wait_time:
            control.window.setProperty(_RETRY_PROP, str(time.time() + wait_time))
    except: pass


def _retry_after(r, default=5):
    # Retry-After is seconds, but HTTP also allows a date. A value that cannot
    # be read falls back to the default instead of raising (which skipped the
    # wait and the shared mark).
    value = r.headers.get('Retry-After')
    try: return max(int(value), 1)
    except: pass
    try:
        from email.utils import parsedate_tz, mktime_tz
        return max(int(mktime_tz(parsedate_tz(value)) - time.time()), 1)
    except: return default


def getTrakt(url, post=None, full=False):
    result = _getTrakt(url, post, full)
    if not post:
        # Lets cache.get() tell "Trakt answered: the list is empty" from "the
        # read failed" (it keeps the previous list only for the latter).
        try: cache.TRAKT_READS['fail' if result is None else 'ok'] += 1
        except: pass
    return result


def _getTrakt(url, post=None, full=False):
    global _SESSION

    url = urllib_parse.urljoin(BASE_URL, url) if not url.startswith(BASE_URL) else url
    # The token and API key go only to Trakt: plugin URLs (lists, public lists)
    # carry the Trakt URL as a parameter, and 'https://api.trakt.tv.other.host'
    # or any other host must not receive them.
    # Only over https.
    try: parts = urllib_parse.urlsplit(url); host, scheme = parts.netloc.lower(), parts.scheme.lower()
    except: host = scheme = ''
    if host != 'api.trakt.tv' or scheme != 'https':
        log_utils.log('Trakt: refusing request to %s://%s' % (scheme, host))
        return None

    _SESSION.headers.update({'Content-Type': 'application/json', 'User-Agent': UA, 'trakt-api-key': V2_API_KEY, 'trakt-api-version': '2'})

    # Trakt asked us to wait (429/5xx) in this or another Blacklodge run: a
    # read gives up at once, as it does on its own 429; the caller's cache
    # keeps the previous list. Checked before check_token(), so a token near
    # expiry does not start refresh attempts while Trakt is failing.
    if not post and _retry_wait() > 0:
        log_utils.log('Trakt: waiting for Retry-After, skipping GET %s' % url)
        return None

    check_token()

    refreshed = False
    for _ in range(3):
        try:
            if not post:
                _get_limiter()
                _get_rate_limiter()
                r = _SESSION.get(url, timeout=30)
            else:
                _post_limiter()
                # Anything we send changes the user's activity timestamps.
                _clear_activities()
                # Device token polls: 10 s, so a hanging call does not hold
                # the authorisation window (BACK is handled between calls).
                r = _SESSION.post(url, json=post, timeout=10 if url.endswith('/oauth/device/token') else 30)
            #log_utils.log(r.json())

            status_code = r.status_code
            #log_utils.log(status_code)
            if url.endswith('/oauth/device/token'): _DEVICE_STATUS[0] = status_code
            if post and url.endswith('/oauth/device/token') and (status_code == 429 or status_code >= 500):
                # While polling for authorisation: no retry and no wait here,
                # the poll loop asks again at its interval (on 429 "slow down"
                # it also polls less often, contract oauth/index.ts).
                log_utils.log('Trakt %s on device token: next poll at the interval' % status_code)
                return None

            if status_code == 429 or status_code >= 500:
                wait_time = _retry_after(r)
                # Shared with the other runs only for reads (a POST 429 is the
                # separate write limit): Trakt's Retry-After when it sent one;
                # otherwise 30 s for the gateway/outage codes (502/503/504,
                # Cloudflare 520-524; Trakt's status codes guide: "try again in
                # 30s"), so widgets stop hitting a failing Trakt. A bare 500 is
                # usually one bad request (one show or episode), not an outage:
                # it fails only that call.
                if not post:
                    if status_code == 429 or r.headers.get('Retry-After'):
                        _set_retry(wait_time)
                    elif status_code in (502, 503, 504) or 520 <= status_code <= 524:
                        _set_retry(30)
                # A play added to the history is not sent again after a server
                # error: Trakt may already have stored it, and it does not check
                # for duplicate plays (sync contract).
                if post and status_code >= 500 and url.endswith('/sync/history'):
                    log_utils.log('Trakt %s on /sync/history: not sent again' % status_code)
                    control.infoDialog('Trakt Service Unavailable (%s)' % status_code)
                    return None
                if post and status_code == 429:
                    msg = 'Trakt rate limit reached, waiting %s seconds...' % wait_time
                elif post:
                    msg = 'Trakt Service Unavailable, retrying in %s seconds...' % wait_time
                elif status_code == 429:
                    # Reads are not retried: the saved list is shown.
                    msg = 'Trakt rate limit reached, try again in %s seconds' % wait_time
                else:
                    msg = 'Trakt Service Unavailable (%s), try again shortly' % status_code
                control.infoDialog(msg)
                log_utils.log('Trakt %s: Waiting %s sec' % (status_code, wait_time))
                # Sleeping here also blocks the Kodi worker thread that is
                # building the current directory or widget. With several
                # widgets on the home screen those threads stay parked for up
                # to Retry-After x 3 retries, and unrelated widgets queue
                # behind them - the whole home screen appears to freeze.
                # Reads are safe to give up on: the list is rebuilt on the
                # next refresh. Writes are not, so POST still waits.
                if not post:
                    log_utils.log('Trakt %s: skipping GET %s' % (status_code, url))
                    return None
                # Capped: a write waits, but never long enough to stall Kodi.
                control.sleep(min(wait_time, 30) * 1000)
                continue

            if status_code == 401:
                # At most one refresh per call (a 401 with a valid token would
                # otherwise rotate the token up to 3 times).
                used = (_SESSION.headers.get('Authorization') or '').replace('Bearer ', '', 1)
                if not refreshed and _refresh_trakt_token(rejected=used):
                    refreshed = True
                    continue
                return None

            if status_code in [200, 201, 204]:
                # Cleared again after the write: another run may have stored
                # the answer from before it while the write was in flight.
                if post: _clear_activities()
                if not full:
                    return r.json()
                else:
                    return r

            if status_code == 420:
                # Account limit exceeded (list count, list items, watchlist
                # items). Free accounts hit this; a retry cannot help.
                log_utils.log('Trakt 420: account limit exceeded for %s' % url)
                control.infoDialog(control.lang(32646), sound=True)
                return None

            if status_code == 409:
                # Conflict: already done, e.g. the same item was just scrobbled
                # (possibly by another Trakt client on the same account).
                log_utils.log('Trakt 409: already exists for %s' % url)
                # On the device token it means "code already used" and
                # authorisation stops: the user is told to start again.
                if url.endswith('/oauth/device/token'):
                    control.infoDialog(control.lang(32661), sound=True)
                return None

            if status_code == 423:
                # Locked or deactivated account; only Trakt support can fix it.
                # Reads from all runs pause for 5 minutes instead of every
                # widget asking again (and showing the message) each time.
                log_utils.log('Trakt 423: account locked for %s' % url)
                _set_retry(300)
                control.infoDialog(control.lang(32647), sound=True)
                return None

            if status_code == 403:
                # Invalid API key or unapproved app (status codes guide): the
                # same answer for every call, so reads from all runs pause for
                # 5 minutes instead of asking again at full rate.
                log_utils.log('Trakt 403: forbidden for %s, reads paused for 5 minutes' % url)
                _set_retry(300)
                control.infoDialog('Trakt Error:  403', sound=True)
                return None

            if status_code == 426:
                log_utils.log('Trakt 426: VIP only for %s' % url)
                control.infoDialog(control.lang(32648), sound=True)
                return None

            if status_code == 400:
                pass
            elif status_code in _DEVICE_FINAL and url.endswith('/oauth/device/token'):
                # Code invalid, expired or refused: tell the user to start
                # again (contract, oauth/index.ts), instead of a bare number.
                log_utils.log('Trakt %s on device token' % status_code)
                control.infoDialog(control.lang(32661), sound=True)
            else:
                log_utils.log('Trakt Error %s for %s' % (status_code, url))
                control.infoDialog('Trakt Error:  %s' % status_code, sound=True)
            return None

        except requests.exceptions.Timeout:
            # Trakt not answering: every other call would wait for the same
            # timeout (30 s each). Reads from all Blacklodge runs pause for 30 s
            # and show the cached lists; it clears by itself. (No network at all
            # fails at once and costs nothing, so it sets no pause and the first
            # call after the network returns works.)
            log_utils.log('getTrakt: Trakt timed out, reads paused for 30 s (%s)' % url)
            # Not for a device token poll: the poll loop asks again anyway.
            if not url.endswith('/oauth/device/token'): _set_retry(30)
            break
        except:
            log_utils.log('getTrakt Error', 1)
            break

    return None

def check_token():
    if not getTraktCredentialsInfo():
        _SESSION.headers.pop('Authorization', None)
        return False

    now = int(time.time())
    try: expires_at = int(control.setting('trakt.expires_at')) or 0
    except: expires_at = 0

    if (expires_at - now) > 300:
        _SESSION.headers.update({'Authorization': 'Bearer %s' % control.setting('trakt.token')})
        return True

    log_utils.log('Trakt: Token expired or expiring soon. Refreshing...')
    if _refresh_trakt_token(): return True
    # Refresh failed: an access token that has not expired yet still works.
    if expires_at > now:
        _SESSION.headers.update({'Authorization': 'Bearer %s' % control.setting('trakt.token')})
        return True
    _SESSION.headers.pop('Authorization', None)
    return False

def _fresh_setting(name):
    # Read through a new Addon instance: control.setting is one instance made
    # at import and may not see a token written meanwhile by another run or by
    # an add-on that shares the account.
    try: return control.addon().getSetting(name)
    except: return control.setting(name)


def _use_stored_token(refresh=None, rejected=None):
    # True when the stored token is valid for more than 5 minutes and, if
    # `refresh` is given, belongs to another refresh token than that one (i.e.
    # someone else refreshed meanwhile), and is not the access token Trakt has
    # just rejected with a 401. Then it is used instead of refreshing.
    try:
        if refresh is not None and _fresh_setting('trakt.refresh') == refresh: return False
        if rejected and _fresh_setting('trakt.token') == rejected: return False
        if int(_fresh_setting('trakt.expires_at') or 0) - int(time.time()) <= 300: return False
        _SESSION.headers.update({'Authorization': 'Bearer %s' % _fresh_setting('trakt.token')})
        return True
    except:
        return False


def _refresh_trakt_token(rejected=None):
    # One refresh at a time per run: the other threads wait here and then find
    # either the new token or the mark below, so they do not POST again.
    # rejected: the access token a 401 was just received for (never reused).
    with _REFRESH_LOCK:
        return _refresh_locked(rejected)


def _refresh_locked(rejected=None):
    oauth_url = 'https://api.trakt.tv/oauth/token'
    # Already refreshed (by another thread, run, or add-on): nothing to do.
    if _use_stored_token(rejected=rejected): return True
    refresh = _fresh_setting('trakt.refresh')
    if not refresh: return False
    opost = {'client_id': V2_API_KEY, 'client_secret': CLIENT_SECRET, 'redirect_uri': REDIRECT_URI, 'grant_type': 'refresh_token', 'refresh_token': refresh}

    # A refresh token that Trakt rejected stays rejected. Without this every
    # Trakt call of every run (lists, widgets) tried again: 3 POSTs before the
    # request and 3 more on its 401. The mark holds a hash of the token, not
    # the token, so a new token (re-authorisation, or one written by another
    # add-on) is used at once. Value: "tag|until[|first rejected at]".
    tag = hashlib.md5(refresh.encode('utf-8')).hexdigest()[:12]
    try:
        mark_tag, mark_until = control.window.getProperty(_REFRESH_PROP).split('|')[:2]
        if mark_tag == tag and _mark_left(mark_until): return False
    except:
        pass

    def pause(seconds):
        # Keeps the time this token was first rejected, if any (see below).
        try:
            old = control.window.getProperty(_REFRESH_PROP).split('|')
            first = '|%s' % old[2] if old[0] == tag and len(old) > 2 else ''
        except:
            first = ''
        control.window.setProperty(_REFRESH_PROP, '%s|%s%s' % (tag, time.time() + min(max(seconds, 1), _MARK_MAX), first))

    # In progress: other runs (widgets loading together) see the mark and do
    # not POST the same token meanwhile. Replaced by the outcome below.
    pause(35)

    # One attempt per call. Every failure returns at once (no sleeping, no
    # immediate retries): this runs inside directory builds and widgets.
    _post_limiter()
    if _use_stored_token(refresh, rejected): return True
    try:
        r = _SESSION.post(oauth_url, json=opost, timeout=30)
        #log_utils.log(r.json())
        if r.status_code == 200:
            res = r.json()
            expires_at = int(time.time()) + int(res['expires_in'])

            control.setSetting(id='trakt.token', value=res['access_token'])
            control.setSetting(id='trakt.refresh', value=res['refresh_token'])
            control.setSetting(id='trakt.expires_at', value=str(expires_at))

            _SESSION.headers.update({'Authorization': 'Bearer %s' % res['access_token']})
            control.window.clearProperty(_REFRESH_PROP)
            control.window.clearProperty(_NOTIFY_PROP)
            return True
        if r.status_code in (400, 401, 403):
            # Used up because someone else refreshed between the check above
            # and this POST: use the token they stored.
            if _use_stored_token(refresh, rejected): return True
            if r.status_code == 403:
                # Can also be a temporary block: 1 minute, and it does not
                # count as a rejection for the message below.
                log_utils.log('Trakt: token refresh refused (403), next try in 60 s')
                pause(60)
                return False
            # Rejected (revoked, or already used by another refresh): a retry
            # cannot help. Try again in 10 minutes at the earliest.
            log_utils.log('Trakt: refresh token rejected (%s), not retrying for 600 s' % r.status_code)
            # When this token was first rejected is kept with the mark, so the
            # user is told only if it stays rejected: an add-on that shares the
            # account can replace it within minutes, and then nothing is shown.
            now = time.time()
            first = now
            try:
                old = control.window.getProperty(_REFRESH_PROP).split('|')
                if old[0] == tag and len(old) > 2: first = float(old[2])
            except:
                pass
            control.window.setProperty(_REFRESH_PROP, '%s|%s|%s' % (tag, now + 600, first))
            if now - first >= 1800:
                # The lists keep showing their saved copies, so say why they do
                # not update. Once per 10 minutes for all runs together.
                try: notified = _mark_left(control.window.getProperty(_NOTIFY_PROP) or 0)
                except: notified = 0
                if not notified:
                    control.window.setProperty(_NOTIFY_PROP, str(now + 600))
                    control.infoDialog(control.lang(32656), sound=True, icon='WARNING', time=6000)
            return False
        if r.status_code == 429:
            # Write limit: wait as Trakt says, but as a pause, not a sleep.
            pause(_retry_after(r))
            return False
        # 5xx or anything else: Trakt is failing, try again in a minute.
        log_utils.log('Trakt: token refresh failed (%s), next try in 60 s' % r.status_code)
        pause(60)
        return False
    except requests.exceptions.Timeout:
        # Trakt not answering: short pause instead of 30 s waits on every call.
        pause(60)
        return False
    except requests.exceptions.ConnectionError:
        # No network: fails at once, but each attempt also waits for the POST
        # limiter. A short 15 s pause, so a list of many calls does not try
        # every time, while a network that comes back is used quickly.
        pause(15)
        return False
    except:
        log_utils.log('Trakt: token refresh error', 1)
        pause(60)
        return False


def removePlayback(playback_id):
    """DELETE /sync/playback/{id}: removes one paused point. History is untouched."""
    try:
        if not getTraktCredentialsInfo(): return False
        # The id comes from the plugin URL: digits only, so it cannot point the
        # DELETE at another path.
        playback_id = str(playback_id or '')
        if not re.match(r'^[0-9]+\Z', playback_id): return False
        _SESSION.headers.update({'Content-Type': 'application/json', 'User-Agent': UA, 'trakt-api-key': V2_API_KEY, 'trakt-api-version': '2'})
        if not check_token():
            control.infoDialog('Trakt Error', sound=True)
            return False
        _post_limiter()
        _clear_activities()
        r = _SESSION.delete(urllib_parse.urljoin(BASE_URL, '/sync/playback/%s' % playback_id), timeout=30)
        # 404: already gone (e.g. removed on another device), same result.
        if r.status_code in (200, 204, 404):
            _clear_activities()
            # The list indicators use a cached map of paused points.
            cache.remove_keys('getPlaybackProgress')
            return True
        log_utils.log('Trakt %s: removing playback %s' % (r.status_code, playback_id))
        # Same message style as getTrakt() uses for other errors.
        control.infoDialog('Trakt Error:  %s' % r.status_code, sound=True)
        return False
    except:
        log_utils.log('removePlayback', 1)
        control.infoDialog('Trakt Error', sound=True)
        return False


def getPaginatedResponse(url):
    # The page count comes from X-Pagination-Page-Count, as the Trakt docs
    # require, instead of requesting pages until an empty one comes back.
    # A failed page returns None rather than a partial list, so cache.get()
    # keeps the previous complete result instead of storing half of it.
    try:
        result = []
        found = re.findall(r'[?&]page=(\d+)', url)
        if found:
            page = int(found[0])
        else:
            page = 1
            url += ('&' if '?' in url else '?') + 'page=1'
        while True:
            r = getTrakt(url, full=True)
            if r is None: return None
            data = r.json()
            if not isinstance(data, list): return None
            result.extend(data)
            try: pages = int(r.headers.get('X-Pagination-Page-Count'))
            except: pages = 0
            # No header means the endpoint returned everything at once.
            if not data or page >= pages or page >= 100: break
            page += 1
            url = re.sub(r'([?&])page=\d+', r'\g<1>page=%d' % page, url)
        return result
    except:
        log_utils.log('getPaginatedResponse', 1)
        return None


# Last HTTP status of /oauth/device/token (authTrakt stops on the final ones).
_DEVICE_STATUS = [0]
# Device token answers that end the authorisation (contract, oauth/index.ts):
# 404 invalid code, 409 already used, 410 expired, 418 denied by the user.
_DEVICE_FINAL = (404, 409, 410, 418)


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
        # No code (network or Trakt error): say so instead of reopening the
        # settings page without a word.
        if not isinstance(result, dict) or 'user_code' not in result:
            control.infoDialog('Trakt Error', sound=True)
            raise Exception()
        # The code lives expires_in seconds from now. Monotonic clock: not
        # moved by NTP setting the time while the user authorises.
        _now = getattr(time, 'monotonic', time.time)
        started = _now()
        verification_url = control.lang(32513) % result['verification_url']
        user_code = six.ensure_text(control.lang(32514) % result['user_code'])
        expires_in = int(result['expires_in'])
        device_code = result['device_code']
        interval = result['interval']

        # QR window with the same calls as the progress dialog; falls back to
        # the original dialog if it cannot be shown (traktqr.py).
        try:
            from resources.lib.modules import traktqr
            progressDialog = traktqr.open_dialog(result.get('verification_url'), result['user_code'], expires_in, started)
        except Exception:
            progressDialog = control.progressDialog
            progressDialog.create('Trakt')

        _DEVICE_STATUS[0] = 0
        next_poll = 0
        for i in range(0, expires_in):
            try:
                percent = int(100 * float(i) / expires_in)
                progressDialog.update(max(1, percent), verification_url + '[CR]' + user_code)
                if progressDialog.iscanceled(): break
                # Through Kodi, not time.sleep(): the QR window's keys (BACK,
                # ENTER) are only handled while this thread waits in Kodi.
                control.sleep(1000)
                if control.monitor.abortRequested(): break
                # Cancelled during the wait: stop now, before any poll.
                if progressDialog.iscanceled(): break
                # Stop when the code has really expired (slow or failing
                # calls make the loop longer than expires_in seconds). Only
                # with a monotonic clock (Python 3): on Python 2 the wall
                # clock could jump with NTP, so g9's behaviour is kept there.
                if hasattr(time, 'monotonic') and _now() - started >= expires_in: break
                # Every interval seconds (same rounds as i % interval with a
                # fixed interval; also after Trakt asks to slow down).
                if i < next_poll: raise Exception()
                next_poll = i + interval
                _DEVICE_STATUS[0] = 0   # a timed-out poll leaves no old status
                r = getTrakt('/oauth/device/token', {'client_id': V2_API_KEY, 'client_secret': CLIENT_SECRET, 'code': device_code})
                if _DEVICE_STATUS[0] in _DEVICE_FINAL: break
                if _DEVICE_STATUS[0] == 429:
                    interval += 5
                    next_poll = i + interval
                if r and 'access_token' in r: break
            except:
                pass

        try: progressDialog.close()
        except: pass

        token, refresh = r['access_token'], r['refresh_token']
        expires_at = int(time.time()) + int(r['expires_in'])

        headers = {'Content-Type': 'application/json', 'User-Agent': UA, 'trakt-api-key': V2_API_KEY, 'trakt-api-version': '2', 'Authorization': 'Bearer %s' % token}


        # One retry: the code is already used, a failure here would make the
        # user authorise again.
        for attempt in (1, 2):
            try:
                me = requests.get(urllib_parse.urljoin(BASE_URL, '/users/me'), headers=headers, timeout=20)
                if me.status_code != 200: raise Exception('users/me %s' % me.status_code)
                result = me.json()
                break
            except Exception:
                if control.monitor.abortRequested(): raise
                if attempt == 2:
                    control.infoDialog('Trakt Error', sound=True)
                    raise
                control.sleep(2000)

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
        # Not while Kodi is shutting down.
        if not control.monitor.abortRequested(): control.openSettings('4.6')


def getPlaybackProgress():
    # Trakt paused points (/sync/playback: movies and episodes, all of them,
    # pagination is opt-in) as {'movie': {imdb: %}, 'episode': {'imdb|s|e': %}},
    # keeping the same 1-92% window the player uses for resuming. For
    # cache.get(): a dict (also with nothing paused), None when the call failed.
    result = getTrakt('/sync/playback')
    if not isinstance(result, list): return None
    out = {'movie': {}, 'episode': {}}
    for r in result:
        try:
            progress = float(r.get('progress') or 0)
            if not 1 < progress < 92: continue
            if r.get('type') == 'movie':
                imdb = r['movie']['ids'].get('imdb')
                if imdb: out['movie'][imdb] = progress
            elif r.get('type') == 'episode':
                imdb = r['show']['ids'].get('imdb')
                if imdb: out['episode']['%s|%s|%s' % (imdb, int(r['episode']['season']), int(r['episode']['number']))] = progress
        except:
            pass
    return out


def playbackProgress():
    # The paused points for the list indicators when the resume point source is
    # Trakt (the player already resumes from Trakt then). Cached, asked again
    # only when Trakt reports a newer pause (paused_at in /sync/last_activities).
    try:
        if control.setting('rersume.source') != '1' or not getTraktCredentialsInfo(): return None
        paused = _activity((('movies', 'paused_at'), ('episodes', 'paused_at')))
        timeout = 0 if paused > cache.timeout(getPlaybackProgress) else 720
        return cache.get(getPlaybackProgress, timeout) or None
    except:
        return None


def getSmartLists():
    # The user's Trakt smart lists (/users/me/smart-lists): dynamic lists driven
    # by a source and filters. For cache.get(): a list (also empty), None when
    # the call failed.
    result = getTrakt('/users/me/smart-lists')
    return result if isinstance(result, list) else None


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

        if result:
            # The change is on Trakt at once (measured: within 2 s), but the
            # lists already built were shown again: from Blacklodge's cache and
            # from Kodi's own directory cache. Drop the cached Trakt lists and
            # list menus (also the raw lists of traktmixed.py: smart lists can be
            # driven by the watchlist), and refresh the screen.
            cache.remove_keys('movies.trakt_list', 'tvshows.trakt_list', 'movies.trakt_user_list',
                              'tvshows.trakt_user_list', 'episodes.trakt_user_list',
                              'getTrakt', 'getSmartLists')
            control.refresh()
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


# One directory build can ask for the activity timestamps several times (the
# progress list does it twice in a row). Reuse the answer for a few seconds
# within the same run; any POST clears it, so our own scrobbles and watched
# marks are seen immediately.
_LAST_ACTIVITIES = {'time': 0, 'data': None}
# The same answer shared with the other runs for the same 10 seconds (widgets
# loading together each asked for it). Any POST clears it too.
_ACTIVITIES_PROP = 'plugin.video.blacklodge.trakt.last_activities'


def _clear_activities():
    _LAST_ACTIVITIES['data'] = None
    try: control.window.clearProperty(_ACTIVITIES_PROP)
    except: pass


def _last_activities():
    now = time.time()
    if _LAST_ACTIVITIES['data'] and now - _LAST_ACTIVITIES['time'] < 10:
        return _LAST_ACTIVITIES['data']
    try:
        shared = json.loads(control.window.getProperty(_ACTIVITIES_PROP) or '{}')
        if shared.get('data') and 0 <= now - float(shared.get('time', 0)) < 10:
            _LAST_ACTIVITIES['time'], _LAST_ACTIVITIES['data'] = float(shared['time']), shared['data']
            return shared['data']
    except:
        pass
    data = getTrakt('/sync/last_activities')
    if data:
        _LAST_ACTIVITIES['time'] = now
        _LAST_ACTIVITIES['data'] = data
        try: control.window.setProperty(_ACTIVITIES_PROP, json.dumps({'time': now, 'data': data}))
        except: pass
    return data


def _activity(keys):
    # Newest of the given /sync/last_activities timestamps.
    # 0 when the call failed: callers compare it with the cache date
    # (activity > cache.timeout(...)), so 0 means "keep the cached list".
    # Before, the failure returned None and Python 3 raised on the
    # comparison, which forced a fresh download of every list exactly when
    # Trakt was failing. A missing field is skipped instead of failing the
    # whole answer, so a change in Trakt's response cannot freeze the cache.
    i = _last_activities()
    if not isinstance(i, dict): return 0
    activity = []
    for group, field in keys:
        try: activity.append(int(cleandate.iso_2_utc(i[group][field])))
        except: pass
    return max(activity) if activity else 0


def getActivity():
    return _activity((('movies', 'collected_at'), ('episodes', 'collected_at'),
                      ('movies', 'watchlisted_at'), ('shows', 'watchlisted_at'), ('seasons', 'watchlisted_at'), ('episodes', 'watchlisted_at'),
                      ('movies', 'hidden_at'), ('shows', 'hidden_at'), ('seasons', 'hidden_at'),
                      ('movies', 'favorited_at'), ('shows', 'favorited_at'), ('shows', 'dropped_at'),
                      ('lists', 'updated_at'), ('lists', 'liked_at')))


def getWatchedActivity():
    return _activity((('movies', 'watched_at'), ('episodes', 'watched_at')))


def cachesyncMovies(timeout=0):
    indicators = cache.get(syncMovies, timeout, control.setting('trakt.user').strip())
    return indicators


def timeoutsyncMovies():
    timeout = cache.timeout(syncMovies, control.setting('trakt.user').strip())
    return timeout


def syncMovies(user):
    try:
        if getTraktCredentialsInfo() == False: return
        indicators = getPaginatedResponse('/users/me/watched/movies?page=1&limit=250')
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
        indicators = getPaginatedResponse('/users/me/watched/shows?page=1&limit=100&extended=progress')
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


def _season_post(imdb, season, episodes):
    season = int('%01d' % int(season))
    return {"shows": [{"seasons": [{"number": season, "episodes": [{"number": int('%01d' % int(e))} for e in episodes]}], "ids": {"imdb": imdb}}]}


def markEpisodesAsWatched(imdb, season, episodes):
    # The episodes of one season in one request (/sync/history takes a list).
    if not episodes: return None
    return getTrakt('/sync/history', _season_post(imdb, season, episodes))


def markEpisodesAsNotWatched(imdb, season, episodes):
    if not episodes: return None
    return getTrakt('/sync/history/remove', _season_post(imdb, season, episodes))


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


def getEpisodeTranslation(id, lang, season, episode):
    # For cache.get(): a dict when Trakt answered, also when it has no
    # translation (so that answer is cached too), None when the call failed
    # (not cached, asked again next time).
    result = getTrakt('/shows/%s/seasons/%s/episodes/%s/translations/%s' % (id, season, episode, lang))
    if not isinstance(result, list): return None
    item = result[0] if result else {}
    return {'title': item.get('title') or '', 'overview': item.get('overview') or ''}


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
