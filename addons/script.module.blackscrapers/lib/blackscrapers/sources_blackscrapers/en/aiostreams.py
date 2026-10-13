# -*- coding: utf-8 -*-

"""AIOStreams provider.

Self-contained: the only things it needs are an AIOStreams instance base URL
and that instance's UUID and password.  Settings used:

    provider.aiostreams   on / off
    aio.instance          public instance (index into INSTANCES) or Custom
    url.aiostreams        instance URL, used only when Instance is Custom
    aio.uuid              instance UUID   (HTTP Basic user)
    aio.password          instance password
    aio.colour            colour of the provider column, or Off
    aio.mark_cached       mark rows the instance reports as cached with +

Only finished links are returned.  The instance has already resolved each one
against its own debrid / usenet account, so the URL goes straight to the
player as a direct source.  Nothing peer to peer ever leaves this file:

    type contains "p2p"   dropped.
    cached is false       dropped.  An uncached row answers with a short
                                    "it is downloading" clip, not the film.
    no http url           dropped.  A url carrying `magnet:` or `btih:` counts
                                    as no url: the host addon reads either as
                                    a torrent and would take the info hash
                                    from it to the viewer's debrid API.

Each row names where it came from: the service that served it, then the
provider that found it.  A row naming no service at all is labelled AIO, not
guessed at.

    104 | TB  | 1080P | AIOSTREAMS | COMET
    105 | TB  | 1080P | AIOSTREAMS | USENET
    106 | AIO | 1080P | AIOSTREAMS | USENET

Rows are returned as `direct: True, debridonly: True` as in the EasyNews
provider, plus `prelinked: True`.  `debridonly` is what stops a host addon's
catch-all from listing the row a second time; `prelinked` says the link is
already finished and must not be sent to a debrid resolver.

HOST ADDON: requires a host that honours `prelinked` (e.g. plugin.video.blacklodge
1.06.39g2 or later).  A host without that support may list a row once per
configured debrid service and hand the finished link to a resolver, which
breaks it.

Why `requests` and not the module's own client: client.request(redirect=False)
calls urllib2.install_opener() with a NoRedirectHandler, and install_opener
sets the process-wide default opener.  A later plain client.request(url) from
any other provider installs no opener of its own, so it would inherit that one
and silently stop following redirects.  `requests` keeps no global state.
"""

import base64
import re

import requests
import six

try:
    import simplejson as json
except ImportError:
    import json

from blackscrapers import parse_qs, unquote, urlencode, urljoin, urlparse
from blackscrapers.modules import cleantitle
from blackscrapers.modules import source_utils
from blackscrapers.modules import log_utils

from blackscrapers import custom_base_link
custom_base = custom_base_link(__name__)

try:
    from kodi_six import xbmcaddon
except ImportError:
    xbmcaddon = None


MODULE_ID = 'script.module.blackscrapers'
SEARCH_PATH = '/api/v1/search'

# (connect, read).  The read budget stays on the instance, which does the
# scraping itself and is the slow part.
SEARCH_TIMEOUT = (8, 20)
RESOLVE_TIMEOUT = (8, 12)

MAX_REDIRECT_HOPS = 5

USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# Last line of defence behind the cached filter.  When a debrid request fails
# before the first byte, the instance does not answer with an error: it answers
# `302 -> /static/<clip>.mp4` and serves a short clip that says what went
# wrong.  Kodi plays that clip happily, so the host addon counts a successful
# playback and runs next-episode off a file nobody watched.
#
# THE RULE IS THE PATH, not the file name.  The instance mounts its whole
# asset directory there -- `app.use('/static', ..., express.static(staticRoot))`
# in packages/server/src/app.ts -- and a real stream is never served from it.
# Matching the directory means a clip added upstream tomorrow is caught today,
# without waiting for this list to be updated.
PLACEHOLDER_PATH = '/static/'

# The names in that directory as of AIOStreams 2.17, from the StaticFiles enum
# and mapDebridErrorToStaticFile() in packages/server/src/app.ts.  Kept as the
# fallback for an instance or proxy that serves them from somewhere else, and
# as the record of what is being refused and why:
#
#   downloading.mp4                    not finished yet (also used for TIMEOUT)
#   download_failed.mp4                the debrid download failed
#   no_matching_file.mp4               nothing in the torrent matched
#   payment_required.mp4               the viewer's debrid account has lapsed
#   store_limit_exceeded.mp4           their store quota is used up
#   content_proxy_limit_reached.mp4    too many active connections
#   unavailable_for_legal_reasons.mp4  blocked content
#   401.mp4 403.mp4 429.mp4 500.mp4    unauthorized / forbidden / rate limited
#   200.mp4                            the enum calls this one OK; it is still
#                                      a static clip, so it is still not a film
PLACEHOLDER_MARKERS = (
    'downloading.mp4', 'download_failed.mp4', 'no_matching_file.mp4',
    'payment_required.mp4', 'store_limit_exceeded.mp4',
    'content_proxy_limit_reached.mp4', 'unavailable_for_legal_reasons.mp4',
    '401.mp4', '403.mp4', '429.mp4', '500.mp4', '200.mp4',
)

# Offered in the settings so the colour can suit any skin, or be turned off.
COLOURS = {'Off': '', 'Deep sky blue': 'FF00BFFF', 'Gold': 'FFFFD700',
           'Spring green': 'FF00FF7F', 'Orange': 'FFFFA500',
           'Violet': 'FFEE82EE', 'White': 'FFFFFFFF'}
DEFAULT_COLOUR_NAME = 'Deep sky blue'

# Public instances, named as the project's own Public Instances page names
# them.  The picker stores an INDEX, so these are positional: append new
# entries, never insert one, or every saved setting silently repoints at a
# different host.  settings.xml lists the same instances (aio.instance and
# the read-only aio_url.N lines): keep both in the same order.
INSTANCES = (
    ('Kuu', 'https://aiostreams.stremio.ru'),
    ('Kuu nightly', 'https://aiostreams-nightly.stremio.ru'),
    ('Viren nightly', 'https://aiostreams.viren070.me'),
    ('Yeb', 'https://aiostreams.fortheweak.cloud'),
    ('Yeb nightly', 'https://aiostreams-nightly.fortheweak.cloud'),
    ('Midnight', 'https://aiostreamsfortheweebsstable.midnightignite.me'),
    ('Midnight nightly', 'https://aiostreamsfortheweebs.midnightignite.me'),
    ('ElfHosted', 'https://aiostreams.elfhosted.com'),
    ('ATBP', 'https://aio.atbphosting.com'),
    ('Omni', 'https://aiostreams.12312023.xyz'),
)

# Short labels for the debrid column; RD, AD, PM and TB are the ones the host
# addon uses for its own rows.
SERVICE_TAGS = (
    ('realdebrid', 'RD'), ('alldebrid', 'AD'), ('premiumize', 'PM'),
    ('torbox', 'TB'), ('debridlink', 'DL'), ('offcloud', 'OC'),
    ('easydebrid', 'ED'), ('debrider', 'DR'), ('easynews', 'EN'),
    ('putio', 'PUTIO'), ('pikpak', 'PIKPAK'), ('seedr', 'SEEDR'),
    ('nzbdav', 'NZB'), ('altmount', 'ALT'), ('stremthru', 'STHRU'),
)

ADDON_NAMES = (
    ('torrentio', 'Torrentio'), ('comet', 'Comet'),
    ('mediafusion', 'MediaFusion'), ('jackett', 'Jackett'),
    ('prowlarr', 'Prowlarr'), ('peerflix', 'Peerflix'),
    ('debridio', 'Debridio'), ('stremthru', 'StremThru'),
)


def _setting(setting_id):
    if xbmcaddon is None:
        return ''
    try:
        return xbmcaddon.Addon(id=MODULE_ID).getSetting(setting_id) or ''
    except Exception:
        return ''


def _diag(message):
    """Diagnostics through the module's own logger, like every other provider
    here.  Lands in the host addon's log when its debug setting is on.

    Callers keep the argument cheap: the logger drops the message when debug
    is off, but the string is built either way, and this runs per row.
    """
    log_utils.log('aiostreams: %s' % message)


def _auth_header():
    """Pre-built Authorization header.

    Deliberately not client.request(username=, password=): that path uses
    HTTPBasicAuthHandler, which only sends credentials after a 401 carrying a
    usable WWW-Authenticate.  An instance that answers 401 without it would
    never be retried.  A header sent up front always works.
    """
    uuid = _setting('aio.uuid').strip()
    password = _setting('aio.password').strip()
    if not uuid or uuid == 'empty_setting':
        return None
    if password == 'empty_setting':
        password = ''
    raw = six.ensure_binary('%s:%s' % (uuid, password), 'utf-8')
    return 'Basic %s' % base64.b64encode(raw).decode('ascii')


def _base_url():
    """The instance to talk to.

    The Custom URL is used ONLY while Custom is the chosen entry.  Letting a
    leftover value win regardless would keep sending the UUID and password to
    a host the viewer had already switched away from -- the field is hidden
    the moment they leave Custom, so they would never see where their
    credentials were going.

    An unrecognised value returns nothing rather than falling back to a
    public instance, so the credentials never go to a host nobody chose.
    """
    chosen = _setting('aio.instance').strip()
    if not chosen:
        return INSTANCES[0][1]

    # The picker stores an index, so the settings screen can show the active
    # URL on its own read-only line underneath without that URL ever becoming
    # the stored value.  Indexes are therefore FIXED: new instances are
    # appended, never inserted, or every saved setting shifts to a different
    # host.
    if chosen.isdigit():
        index = int(chosen)
        if 0 <= index < len(INSTANCES):
            return INSTANCES[index][1]
        if index == len(INSTANCES):
            return str(custom_base or '').strip()       # Custom
        log_utils.log('aiostreams: instance index %s is out of range' % index)
        return ''

    log_utils.log('aiostreams: unknown instance %r, refusing to guess one' % chosen)
    return ''


def _search_id(imdb, tmdb):
    """Prefer IMDb (tt...); fall back to tmdb:NNNN when IMDb is missing."""
    imdb = str(imdb or '').strip()
    if imdb.lower().startswith('tt'):
        return imdb
    tmdb = str(tmdb or '').strip()
    if tmdb and tmdb not in ('0', 'None', 'empty_setting'):
        try:
            return 'tmdb:%s' % int(tmdb)
        except ValueError:
            pass
    return None


def _read_bool(value):
    """A JSON boolean, however the instance spelled it, or None.

    Booleans arrive as booleans, but an instance that builds its payload by
    hand may send the strings `"false"` / `"true"`, and `'false' is False` is
    False.  The recognised spellings are converted; anything else reads as
    None, which every caller treats as silence rather than as a refusal.
    """
    if isinstance(value, bool) or value is None:
        return value
    text = _text(value).strip().lower()
    if text in ('false', '0', 'no'):
        return False
    if text in ('true', '1', 'yes'):
        return True
    return None


def _flatten(raw):
    """Merge the nested blocks up into one flat row.

    `behaviorHints` is in here for a reason: on rows proxied through the
    instance the real file name is ONLY in there, and reading `name` instead
    gets the addon's display label.
    """
    item = dict(raw)
    item.pop('sources', None)
    merged = {}
    nested_services = []
    for key in ('parsedFile', 'streamData', 'info', 'behaviorHints'):
        part = item.pop(key, None)
        if isinstance(part, dict):
            if isinstance(part.get('service'), dict):
                nested_services.append(part.get('service'))
            merged.update(part)
            if key == 'behaviorHints' and part.get('filename'):
                merged['behaviorFilename'] = part.get('filename')
    merged.update(item)

    # Lift a nested `service.cached` (as `flatten_result` in
    # plugin.video.redlight does) from every `service` seen on the way in, not
    # only the one that survived the merge. `merged.update(item)` lets a
    # top-level `service` win, and that one may be a bare string, a list, or a
    # dict with no `cached` key; it must not hide an explicit `cached: false`
    # underneath it.
    if _read_bool(merged.get('cached')) is None:
        for candidate in nested_services + [merged.get('service')]:
            if isinstance(candidate, dict) and 'cached' in candidate:
                merged['cached'] = candidate.get('cached')
                break
    return merged


def _release_name(item, raw=None):
    """The release name to match the title against.

    `filename` is the field everyone reaches for first and the field that is
    missing exactly where it matters.  On a proxied row the name lives in
    behaviorHints, or in folderName, and the top-level `name` is the addon's
    display label -- "Torrentio\\n4k", "[AD+] Comet" -- which cleans to
    nonsense, matches no title and takes the row down with it.

    So `name` is the LAST resort, first line only, and anything too short to
    be a release name is discarded.

    `title` is Stremio's display block: a release or folder name on the first
    line, then the instance's own summary line with size, tracker and emoji.
    Only its FIRST line is read, and only after every real file-name field has
    been tried: the whole block run together would weld `23.0 GB ThePirateBay
    42` onto the name.
    """
    nested = {}
    if isinstance(raw, dict):
        for key in ('behaviorHints', 'parsedFile', 'streamData'):
            part = raw.get(key)
            if isinstance(part, dict):
                nested.update(part)

    for value in (item.get('filename'), item.get('behaviorFilename'),
                  nested.get('filename'), item.get('folderName'),
                  nested.get('folderName')):
        value = _text(value).strip()
        if len(value) >= 5:
            return value

    for field in ('title', 'name'):
        line = _text(item.get(field)).replace('\r', '\n')
        line = line.split('\n')[0].strip()
        if len(line) >= 5:
            return line
    return ''


def _text(value):
    """Text from the instance as unicode on Python 2 and 3: on Python 2 a
    non-ASCII name arrives as `unicode`, and str() would raise on it."""
    if value is None:
        return u''
    if isinstance(value, six.binary_type):
        return value.decode('utf-8', 'replace')
    return six.text_type(value)


def _norm(value):
    return re.sub(r'[^a-z0-9]', '', _text(value).lower())


def _stated_numbers(item, field):
    """The season or episode numbers the INSTANCE parsed, as a set of ints.

    `parsedFile.seasons` and `parsedFile.episodes` are the instance's own
    structured parse of the file, and `_flatten` lifts them to the top level.
    They are better evidence than any regex over the name: the instance
    already expanded `S01-S03` into `[1, 2, 3]`, which is exactly the case a
    regex over the name gets wrong.

    Anything that is not a list of plain numbers is ignored rather than
    guessed at, so a malformed field costs nothing.
    """
    value = item.get(field)
    if not isinstance(value, (list, tuple)):
        return set()
    numbers = set()
    for one in value:
        if isinstance(one, bool):
            continue
        try:
            numbers.add(int(one))
        except (TypeError, ValueError):
            continue
    return numbers


def _episode_ok(name, season, episode, item=None):
    """Does this release name really hold the episode that was asked for?

    Because the row is prelinked, the host addon sends it to no resolver and
    re-checks nothing: this is the only place what came back is compared with
    what was asked.  `source_utils.is_match` tests the `SxxEyy` token as a bare
    substring, so `Severance.S02E035.mkv` answers a request for S02E03, and its
    `is_season_match` fallback drops the episode requirement altogether, so
    `Frieren.S02.-.05.mkv` answers it too.

    The shape of this check is taken from `seas_ep_filter` in
    `plugin.video.redlight`'s source_utils:

      * separators are collapsed to `.` but KEPT, and every pattern ends on a
        separator or end-of-string.  That trailing boundary is what stops
        `s02e03` matching the front of `s02e035` -- and keeping the separators
        is what stops `s02e03.1080p` being read as `s02e031080p`;
      * an explicit season tag that disagrees with the request is fatal, so a
        complete-series pack cannot answer for a season it does not contain;
      * `sXXeYYeZZ` is matched for both halves, so a legitimate double episode
        is not thrown away.

    A name with no episode number of any kind -- a folder or season-pack name --
    is kept: the instance resolved a file for the episode it was asked for, and
    there is simply nothing in the name to verify it against.
    """
    try:
        want_s, want_e = int(season), int(episode)
    except (TypeError, ValueError):
        return True

    # The instance's own parse first, when it sent one. It is authoritative in
    # a way a regex over the name is not, and it has already expanded ranges.
    if item is not None:
        stated_s = _stated_numbers(item, 'seasons')
        if stated_s and want_s not in stated_s:
            return False
        stated_e = _stated_numbers(item, 'episodes')
        if stated_e and want_e not in stated_e:
            return False

    title = re.sub(r"[^A-Za-z0-9-]+", '.',
                   _text(name).replace("'", '')).lower()

    # An explicit season tag must agree with the request.
    #
    # `sNN` followed by `e`, a separator or the end, so a pack name such as
    # `Severance.S01.COMPLETE.1080p` counts as naming season 1 (otherwise it
    # would reach the "nothing to verify against" rule at the bottom and be
    # kept for any season). The trailing part is a LOOKAHEAD, not a group, so
    # findall() still sees the `-` in front of the second half of `s01-s03`.
    tags = [int(t) for t in
            re.findall(r'(?:^|[.-])s(\d{1,2})(?=[.-]?e|[.-]|$)', title)]
    tags += [int(t) for t in re.findall(r'(?:^|[.-])(\d{1,2})x\d', title)]
    if tags:
        # A multi-season pack states its ENDS, not its middle: `S01-S03` gives
        # 1 and 3 and does contain season 2. So several distinct tags are read
        # as a span; a single tag is read as the one season it names.
        if len(set(tags)) > 1:
            if not min(tags) <= want_s <= max(tags):
                return False
        elif tags[0] != want_s:
            return False

    season_fill = str(want_s).zfill(2)
    episode_fill = str(want_e).zfill(2)
    spellings_s = {str(want_s), season_fill}
    spellings_e = {str(want_e), episode_fill}
    edge = r'(?=[.-]|$)'
    patterns = []
    for one_s in spellings_s:
        for one_e in spellings_e:
            patterns.append(r's%s[.-]?e[p]?[.-]?%s%s' % (one_s, one_e, edge))
            patterns.append(r'season[.-]?%s[.-]?episode[.-]?%s%s'
                            % (one_s, one_e, edge))
            patterns.append(r's?%sx%s%s' % (one_s, one_e, edge))
        # The bare `<season><sep><episode>` form takes the PADDED episode only,
        # as redlight's does. With the unpadded spelling as well, `[.-]2[.-]?3`
        # matches `One.Piece.S02.-.23`, whose stated episode is 23, and the row
        # is accepted for a request for episode 3 -- the digits happen to spell
        # season-then-episode for that one pair.
        patterns.append(r'[.-]%s[.-]?%s%s' % (one_s, episode_fill, edge))

    # sXXeYYeZZ -- a legitimate double episode, our episode on either side.
    #
    # Two shapes, and both are needed. As in redlight, the CONCATENATED
    # spelling (`s02e0304`) is accepted only with the adjacent episode, so the
    # `5` of `s02e035` cannot pose as a second episode. The separator form also
    # covers a non-adjacent pair (`s02e03-e05`).
    adjacent = (str(want_e - 1).zfill(2), str(want_e + 1).zfill(2))
    patterns.append(r's%se%s[.-]?e?%s%s'
                    % (season_fill, adjacent[0], episode_fill, edge))
    patterns.append(r's%se%s[.-]?e?%s%s'
                    % (season_fill, episode_fill, adjacent[1], edge))
    between = r'(?:[.-]e?|e)'
    patterns.append(r's%se\d{1,4}%s%s%s'
                    % (season_fill, between, episode_fill, edge))
    patterns.append(r's%se%s%s\d{1,4}%s'
                    % (season_fill, episode_fill, between, edge))
    if re.search('|'.join(patterns), title):
        return True

    # No match. Is there an episode number for a DIFFERENT episode of this
    # season? Then the name names some other episode, and the row is not ours.
    # `(?![0-9p])` keeps a resolution (`s02.1080p`) from reading as one.
    others = (r'(?:^|[.-])s0*%d[.-]?e[p]?[.-]?(\d{1,4})%s' % (want_s, edge),
              r'(?:^|[.-])0*%dx(\d{1,4})%s' % (want_s, edge),
              r'(?:^|[.-])s0*%d[.-]+(?:e|ep|episode)?[.-]*(\d{1,3})(?![0-9p])'
              % want_s)
    for pattern in others:
        for match in re.finditer(pattern, title):
            if int(match.group(1)) != want_e:
                return False

    return True


# The stream types this provider is willing to offer, out of the twelve the
# API defines (`p2p, live, stremio-usenet, archive, usenet, debrid, http,
# external, youtube, error, statistic, info`).
#
# A WHITELIST, deliberately.  `http` and `live` rows carry an ordinary url
# with `service: null`: they would pass every other gate, and a viewer with
# "Debrid only" switched on would be served a free direct link presented as a
# debrid result.
#
# A new type added upstream is refused until it is listed here, which is the
# right way round for this provider: it exists to offer finished debrid links,
# and a type nobody has looked at is not one of those.
_OFFERED_TYPES = frozenset(('debrid', 'usenet', 'stremio-usenet'))


def _wrong_type(item):
    """True for a row that STATES a type we do not offer.

    A row with no type, or an empty one, is NOT refused here.  That is the
    difference between a filter and a blackout: the field is required by the
    API's own schema, so a row without it comes from a fork, an older build or
    a proxy -- and refusing those would leave such a viewer with zero results
    from every search, which is a far worse failure than the one this check
    exists to fix.  An unlabelled row goes on to the gates that decide on
    evidence instead: it must carry a finished http link, it must not be
    uncached, and it must match the title and episode asked for.

    An info hash is NOT part of this test either: a debrid row carries the
    hash of the torrent it was built from as provenance, so a hash does not
    mean the row is unresolved.
    """
    stated = _text(item.get('type')).strip().lower()
    return bool(stated) and stated not in _OFFERED_TYPES


def _service_name(item):
    """Whatever the instance calls the service that served this row.

    Used for the label only.  An unrecognised name is still a name -- it gets
    shown rather than thrown away, because no label is worth losing a result
    over.  The literal 'None' the instance sometimes sends is the one value
    treated as absent.
    """
    service = item.get('service')
    if isinstance(service, dict):
        service = service.get('id') or service.get('name')
    if not service:
        for key in ('serviceId', 'service_id', 'debridService', 'debrid_service'):
            service = item.get(key)
            if service:
                break
    key = _norm(service)
    if not key or key in ('none', 'null', 'false') or key.startswith('aiostream'):
        return ''
    return key


def _cached(item):
    """True, False, or None when the row says nothing.

    The spellings are read by _read_bool; anything unrecognised stays None,
    which the caller reads as silence rather than as a refusal.
    """
    cached = _read_bool(item.get('cached'))
    if cached is None:
        # Fall through on anything unreadable, not only on a missing key, so a
        # top-level `"cached": ""` does not hide an explicit
        # `service: {cached: false}` underneath it.
        service = item.get('service')
        if isinstance(service, dict):
            cached = _read_bool(service.get('cached'))
    return cached


def _request_headers(item):
    """The headers Kodi should send for this link, filtered to what we send.

    Only names in `_SENT_HEADER_KEYS` are kept, and they are filtered HERE
    rather than on the way back out.  _split_pipe refuses a tail unless EVERY
    key in it is one we send, so a single unrecognised name -- an instance's
    own `X-AIO-Proxy`, say -- would otherwise lose the whole tail, and a row
    that looked fine in the list would fail the moment it was clicked.

    `behaviorHints.proxyHeaders.request` is Stremio's own spelling and is read
    too, so a row that needs a particular Referer or User-Agent gets it.
    """
    candidates = []
    for field in ('request_headers', 'requestHeaders'):
        value = item.get(field)
        if isinstance(value, dict) and value:
            # Some instances nest them one deeper, Stremio-style.
            inner = value.get('request')
            candidates.append(inner if isinstance(inner, dict) else value)
    proxy = item.get('proxyHeaders')
    if isinstance(proxy, dict):
        inner = proxy.get('request')
        candidates.append(inner if isinstance(inner, dict) else proxy)

    headers = {}
    for candidate in candidates:
        for key, value in candidate.items():
            name = _text(key).strip()
            if name not in _SENT_HEADER_KEYS or name in headers:
                continue
            if isinstance(value, (dict, list, tuple)) or value is None:
                continue
            text = _text(value).strip()
            # A newline here would be header injection on any client that
            # writes these out verbatim.
            if text and not any(c.isspace() and c != ' ' for c in text):
                headers[name] = text
    return headers or None


def _is_usenet(item):
    return 'usenet' in _text(item.get('type')).lower() or bool(item.get('nzbUrl'))


# Kodi reads these as markup, and the host addon splits its two-line labels
# on [CR].  A row carrying one in a name would take the whole source list
# down with it, so nothing from the instance reaches a label unfiltered.
_LABEL_UNSAFE = re.compile(r'[\[\]|\r\n\t]|\[CR\]|[\x00-\x1f]')


def _label_safe(text, limit=14):
    """Anything from the instance that ends up in a Kodi label goes through
    here.  Markup characters out, control characters out, length capped."""
    clean = _LABEL_UNSAFE.sub(' ', _text(text))
    clean = ' '.join(clean.split())
    return clean[:limit].strip()


def _mark_cached():
    """Should the debrid column mark an outright `cached: true` with `+`?

    Read ONCE per scrape, like the colour: this runs per row otherwise.

    Defaults to ON. The three states behind the column are not equally solid
    (see _debrid_label), and a viewer who cannot tell them apart cannot tell
    whether a row that will not start was ever claimed to be ready.
    """
    return _setting('aio.mark_cached').strip().lower() != 'false'


def _row_colour():
    """Hex for the provider column, from our own setting so a viewer on any
    skin can change it or switch it off without editing the module."""
    chosen = _setting('aio.colour').strip() or DEFAULT_COLOUR_NAME
    return COLOURS.get(chosen, '')


# CDN hosts do not always spell the service out: TorBox serves from
# store-*.tb-cdn.io, which contains no "torbox" anywhere.
URL_SERVICE_TAGS = SERVICE_TAGS + (
    ('tbcdn', 'TB'), ('torboxapp', 'TB'),
    ('realdebridcom', 'RD'), ('rdcdn', 'RD'),
    ('alldebridcom', 'AD'), ('debridit', 'AD'),
    ('premiumizeme', 'PM'), ('easynewscom', 'EN'),
)


def _service_from_url(item):
    """Recognise the service from the link's own host.

    Proxied rows sometimes arrive with no service field at all, and the host
    is right there in the URL.  Without this they are all stamped AIO, which
    reads on screen exactly like the service having gone missing.
    """
    url = _norm(_text(item.get('url') or item.get('url_dl'))[:200])
    for token, tag in URL_SERVICE_TAGS:
        if token in url:
            return tag
    return ''


def _service_tag(item):
    """Short code for the service that served the link: TB, AD, RD, PM..."""
    key = _service_name(item)
    if key:
        for token, tag in SERVICE_TAGS:
            if token in key:
                return tag
        return key[:8].upper()
    tag = _service_from_url(item)
    if tag:
        return tag
    # A usenet row that names no service at all is NOT assumed to be EasyNews.
    # Usenet reaches the instance by several roads -- nzbdav, altmount, a
    # debrid service's own usenet support -- and each of those names itself in
    # `service` or in the URL, both already handled above.  What is left here
    # named nothing, so the caller's neutral 'AIO' is the honest answer; 'EN'
    # would print a service the row never claimed.  That it is usenet is said
    # by the source column, which _source_label fills from the same test.
    return ''


def _addon_name(item):
    for field in ('addon', 'addonName', 'addon_name'):
        value = item.get(field)
        if isinstance(value, dict):
            value = value.get('name') or value.get('id')
        key = _norm(value)
        if not key or key.startswith('aiostream'):
            continue
        for token, name in ADDON_NAMES:
            if token in key:
                return name
        return _text(value).strip()[:14]
    return ''


def _inner_name(item):
    """Which provider found it, or '' when the instance does not say."""
    name = _addon_name(item)
    if name:
        return name
    indexer = _text(item.get('indexer')).strip()
    if indexer:
        return indexer[:14]
    return ''


def _debrid_label(item, mark_cached=False):
    """The host addon's debrid column: which service served the link.

    Left plain and uncoloured so the column reads exactly like the host
    addon's own rows -- TB is TB, whichever road it came by.  That the row
    arrived through AIOStreams is said by the provider column, which the host
    tints from the `row_colour` field.

    `mark_cached` appends `+` when the row says `cached: true` OUTRIGHT, the
    way plugin.video.redlight marks the same rows.  It is worth having because
    the three states behind this column are not equally solid:

        TB+   the instance said cached.  On TorBox that is a real answer: it
              has an instant-availability API and AIOStreams caches it.
        AD+   the instance said cached -- but AllDebrid and Real-Debrid
              removed their availability endpoints, so for those the answer is
              an educated guess from crowdsourced hashlists, not a check
              against the viewer's own account.
        AD    the row said nothing.  Kept, because silence is not a refusal,
              but it may not start at once.

    A row that said `cached: false` never gets this far; it is dropped.
    """
    tag = _service_tag(item) or 'AIO'
    if mark_cached and _cached(item) is True:
        return '%s+' % tag
    return tag


def _source_label(item):
    """The host addon's source column: which provider found the release.

        Comet        found by the Comet addon inside the instance
        Usenet       a usenet row, no finder named
        Direct       a finished link, the instance did not say by whom
    """
    name = _inner_name(item)
    if not name:
        name = 'Usenet' if _is_usenet(item) else 'Direct'
    return _label_safe(name)


# A cam or screener is a cam whatever its pixel count, and the host addon's
# "remove CAM" filter keys on exactly these two strings.
_CAM_QUALITIES = ('cam', 'scr')

# AIOStreams states the SOURCE TYPE in its own `quality` field, from a closed
# vocabulary (`QUALITIES` upstream): these four are its cam-grade values, the
# other ten are release types. Matched by EXACT equality on the whole field:
# a token search would match `TS` inside a `.ts` container and `CAM` inside
# the title of the film *Cam* (2018).
_CAM_STATED = frozenset(('CAM', 'TS', 'TC', 'SCR'))


def _quality_of(item, name):
    """The quality to show, which `resolution` may refine but never launder.

    A row whose name says HDCAM and whose `resolution` says 1080p stays a
    cam: otherwise the provider's own cam drop and the host addon's
    `remove.cam` would not fire, and a viewer who asked for 4K only could be
    handed a cam.  AIOStreams fills `resolution` from the same file name on
    most rows, so this is the ordinary case.

    `source_utils.get_release_quality` is the authority on what the name says,
    exactly as it is for every sibling provider -- including where it is
    surprising (a `.ts` container reads as a cam, because `.ts.` is in the
    module's own CAM list).  Diverging from it here would make these rows
    behave unlike every other row in the list.  All this does is stop
    `resolution` overruling it.
    """
    quality = source_utils.get_release_quality(name)[0]
    if quality in _CAM_QUALITIES:
        return quality
    stated = _text(item.get('quality')).strip().upper()
    if stated in _CAM_STATED:
        # Keep the distinction the host addon makes: it filters on both, and
        # `get_release_quality` returns both, so a screener reads the same
        # whichever signal spotted it.
        return 'scr' if stated == 'SCR' else 'cam'

    # `quality` is the SOURCE TYPE, not a resolution -- it is read above for
    # exactly that, and is not used as a resolution fallback (a 1080p release
    # whose row states `quality: SD` stays 1080p).
    resolution = _text(item.get('resolution')).upper()
    if resolution in ('4K', '2160P', '2160', 'UHD'):
        quality = '4k'
    elif resolution in ('1080P', '1080'):
        quality = '1080p'
    elif resolution in ('720P', '720'):
        quality = '720p'
    elif resolution == 'SD':
        quality = 'sd'
    return quality


def _size_of(item):
    value = item.get('size')
    if not value:
        return 0.0, ''
    try:
        return source_utils._size(int(float(value)), is_bytes=True)
    except Exception:
        pass
    try:
        return source_utils._size(_text(value))
    except Exception:
        return 0.0, ''


# The only header names we ever attach, so a query tail that merely looks
# like `key=value` is not mistaken for one.
_SENT_HEADER_KEYS = frozenset((
    'Authorization', 'User-Agent', 'Referer', 'Cookie', 'Origin',
    'X-Api-Key', 'Accept', 'Range', 'Proxy-Authorization',
))


def _join_pipe(url, headers):
    if not headers:
        return url
    return '%s|%s' % (url, urlencode(headers))


def _split_pipe(url):
    """Undo _join_pipe.

    A signed CDN link can legitimately carry a `|` inside its query, so the
    tail is only treated as headers when it looks like one: no path separator,
    and at least one `key=value`.  Otherwise the whole string is the URL.
    """
    if '|' not in url:
        return url, None
    base, _, tail = url.rpartition('|')
    if not base or '/' in tail:
        return url, None
    # Every part must be a real key=value with a header-shaped key.  A signed
    # CDN link can carry a bare `|` inside its query, and `?sig=a|b&x=1` would
    # otherwise be torn in half and half of it turned into headers.
    parts = [p for p in tail.split('&') if p]
    if not parts:
        return url, None
    for part in parts:
        key, sep, _value = part.partition('=')
        if not sep or not re.match(r'^[A-Za-z][A-Za-z0-9-]*$', key):
            return url, None
    # A query string can look like headers too (`?sig=a|b=c`).  Only treat the
    # tail as headers when every key is one we actually send.
    if not all(part.partition('=')[0] in _SENT_HEADER_KEYS for part in parts):
        return url, None
    try:
        headers = dict((k, v[0]) for k, v in parse_qs(tail).items() if v)
    except Exception:
        return url, None
    return (base, headers) if headers else (url, None)


def _foreign_pipe_options(url):
    """True when the url carries a `|` tail that is not headers we send.

    Kodi reads everything after a `|` in a path as protocol options, not as
    part of the url, and some of those options change how the stream is
    fetched rather than merely describing it -- `verifypeer=false` turns off
    TLS certificate verification for that stream.  `_split_pipe` refuses such
    a tail as headers, which leaves it on the url, so it is refused here:
    otherwise it would reach Kodi as protocol options.

    The test starts at the FIRST `|`, because that is where Kodi starts
    reading options, while _split_pipe works from the last one.

    A tail that is not option-shaped at all is left alone: a signed CDN link
    may carry a bare `|` inside its query (`?sig=a|b`), and refusing those
    would throw away real rows over a character the instance did not choose
    as an option.

    THE DELIBERATE COST: a signed query whose `|` happens to be followed by
    something `key=value`-shaped (`?sig=abc|def=xyz`) is refused too.  A base64
    signature can produce that.  It is accepted as the cheaper mistake,
    because such a url is already broken the moment Kodi reads it -- Kodi
    starts reading options at that same `|` -- so what is lost is a row that
    would not have played.  The refusal is logged, so a real one is findable
    rather than silent.
    """
    if '|' not in url:
        return False
    tail = url.split('|', 1)[1]
    parts = [p for p in tail.split('&') if p]
    if not parts:
        return False
    for part in parts:
        key, sep, _value = part.partition('=')
        if not sep or not re.match(r'^[A-Za-z][A-Za-z0-9-]*$', key):
            # Not option-shaped. Not ours to judge.
            return False
    if all(part.partition('=')[0] in _SENT_HEADER_KEYS for part in parts):
        return False
    _diag('refused a url carrying protocol options we do not send | tail=%r'
          % tail[:120])
    return True


def _host(url):
    """A url's origin: scheme, host, and the port when it is not the default.

    The comparison this feeds decides whether a link is still on the instance
    -- which decides whether the placeholder check runs and whether the
    instance's Authorization stays attached to what Kodi opens.  Two things
    that comparison has to get right:

    The port must not break it: an instance that spells its own default port
    (`host:443` against a base of `host`) is still the instance, not a
    third-party CDN.

    The scheme must be part of it: otherwise `https://host` and `http://host`
    compare equal, and a redirect to the instance itself over plain http would
    carry the row's headers there in clear text.  Spelling the scheme makes
    that hop read as off-instance: the link is handed over unopened and the
    headers stay behind.
    """
    try:
        parts = urlparse(_text(url).split('|', 1)[0])
        host = (parts.hostname or '').lower()
        scheme = (parts.scheme or '').lower()
        if not host or not scheme:
            return ''
        port = parts.port
    except Exception:
        return ''
    if port is None or (scheme == 'http' and port == 80) \
            or (scheme == 'https' and port == 443):
        return '%s://%s' % (scheme, host)
    return '%s://%s:%s' % (scheme, host, port)


def _is_placeholder(url):
    """True for one of the instance's own "here is what went wrong" clips.

    The path is tested on its own, so a token in the query cannot trip it and
    a self-hosted instance under a subpath (`/aiostreams/static/...`) is still
    caught.  The file names are the fallback, for a proxy that rehosts them.
    """
    bare = _text(url).split('|', 1)[0]
    try:
        path = unquote(urlparse(bare).path or '').lower()
    except Exception:
        path = bare.lower()
    if PLACEHOLDER_PATH in path:
        return True
    name = path.rsplit('/', 1)[-1]
    return any(name == marker for marker in PLACEHOLDER_MARKERS)


def _search(base, params, auth):
    link = '%s%s' % (base, SEARCH_PATH)
    headers = {'Authorization': auth, 'Accept': 'application/json',
               'User-Agent': USER_AGENT, 'Connection': 'close'}
    try:
        response = requests.get(link, params=params, headers=headers,
                                timeout=SEARCH_TIMEOUT)
    except Exception as error:
        log_utils.log('aiostreams: search request failed (%s): %s' % (base, error))
        return []
    try:
        if not response.ok:
            log_utils.log('aiostreams: HTTP %s from %s' % (response.status_code, base))
            return []
        body = json.loads(response.text)
    except Exception as error:
        log_utils.log('aiostreams: unreadable search payload: %s' % error)
        return []
    finally:
        try:
            response.close()
        except Exception:
            pass
    if not isinstance(body, dict):
        return []
    if body.get('success') is False:
        error = body.get('error') or {}
        if isinstance(error, dict):
            log_utils.log('aiostreams: %s %s' % (error.get('code', ''),
                                                 error.get('message', '')))
        else:
            log_utils.log('aiostreams: %s' % error)
        return []
    payload = body.get('data') or {}
    if not isinstance(payload, dict):
        return []
    for entry in payload.get('errors') or ():
        if isinstance(entry, dict):
            log_utils.log('aiostreams source error: %s %s'
                          % (entry.get('title', ''), entry.get('description', '')))
    return payload.get('results') or []


def _is_private_host(host):
    """True for an address on the viewer's own machine or network.

    A redirect there is never a stream: Kodi's JSON-RPC listens on loopback
    and a home network is one hop away.  The address is parsed rather than
    prefix-matched, because 127.0.0.1 also spells itself 2130706433,
    0x7f000001, 017700000001 and ::ffff:127.0.0.1.
    """
    host = _text(host).strip().lower().strip('[]')
    # A trailing dot makes a name fully qualified, not different: `localhost.`
    # and `127.0.0.1.` reach exactly the same place.
    host = host.rstrip('.')
    # A zone id names an interface, not an address: `fe80::1%eth0` is the same
    # link-local address as `fe80::1`, which ip_address refuses to parse while
    # the socket layer accepts it.
    if '%' in host:
        host = host.split('%', 1)[0]
    if not host or host == 'localhost' or host.endswith('.local') \
            or host.endswith('.internal') or host.endswith('.localhost'):
        return True
    try:
        import ipaddress
    except ImportError:
        # Python 2 has no ipaddress module.
        return _is_private_literal(host)
    candidates = [host]
    if ':' not in host:
        candidates.append('::ffff:' + host)
        # inet_aton is what the platform resolver actually applies to a
        # numeric host, and it accepts three forms ipaddress rejects outright:
        # two parts (`127.1`), three parts (`127.0.1`), and octal with a
        # leading zero (`0177.0.0.1`).  All three reach loopback on the device,
        # so each is normalised to a dotted quad before being judged
        # rather than falling through as "not an address, must be a name".
        try:
            import socket
            candidates.append(socket.inet_ntoa(socket.inet_aton(host)))
        except Exception:
            pass
    for candidate in candidates:
        try:
            address = ipaddress.ip_address(six.text_type(candidate))
        except ValueError:
            continue
        mapped = getattr(address, 'ipv4_mapped', None) or address
        if (mapped.is_private or mapped.is_loopback or mapped.is_reserved
                or mapped.is_link_local or mapped.is_multicast
                or mapped.is_unspecified):
            return True
        # 100.64.0.0/10, carrier-grade NAT, is not "private" to ipaddress.
        if mapped.version == 4 and mapped in ipaddress.ip_network('100.64.0.0/10'):
            return True
    # A bare integer, hex or octal literal is a valid host to many resolvers:
    # 127.0.0.1 also spells itself 2130706433, 0x7f000001 and 017700000001.
    # Every base has to be checked, not just the first that parses.
    for base in (10, 16, 8):
        try:
            number = int(host, base)
        except ValueError:
            continue
        if 0 <= number < 2 ** 32:
            try:
                if _is_private_host(six.text_type(ipaddress.ip_address(number))):
                    return True
            except ValueError:
                continue
    return False


# IPv4 ranges that are never a stream host: this network, private, carrier
# NAT, loopback, link-local, multicast and reserved.  (network, prefix bits)
_PRIVATE_V4 = (
    (0x00000000, 8), (0x0A000000, 8), (0x64400000, 10), (0x7F000000, 8),
    (0xA9FE0000, 16), (0xAC100000, 12), (0xC0A80000, 16), (0xE0000000, 4),
    (0xF0000000, 4),
)


def _is_private_literal(host):
    """_is_private_host without the ipaddress module (Python 2).

    A numeric IPv4 host in any spelling the resolver accepts (dotted, short,
    octal, a bare decimal or hex number) is judged against _PRIVATE_V4.  An
    IPv6 literal cannot be judged here and is treated as private; the
    configured instance's own address is still allowed by _http_only.
    """
    if ':' in host:
        return True
    number = None
    try:
        import socket
        import struct
        number = struct.unpack('!I', socket.inet_aton(host))[0]
    except Exception:
        for base in (10, 16, 8):
            try:
                number = int(host, base)
                break
            except ValueError:
                continue
    if number is None or not 0 <= number < 2 ** 32:
        return False
    return any(number >> (32 - bits) == network >> (32 - bits)
               for network, bits in _PRIVATE_V4)


# A finished link never needs either of these words.  The host addon tests
# `'magnet:' in url` as a plain substring and pulls such a row in among the
# torrents, then lifts `btih:<40 hex>` out of it and posts the hash to the
# viewer's debrid cache-check API.  Neither belongs in anything this provider
# emits, so a url carrying one is refused rather than explained.
_TORRENT_WORDS = ('magnet:', 'btih:')


# Extensions that make Kodi treat the body as something other than a stream.
#
# The host addon plays a prelinked row with `xbmc.Player().play()` after
# calling `setContentLookup(False)` on the item, so Kodi never asks the server
# what the url IS -- it decides from the extension.  A playlist extension makes
# it read the body as a list of items and play what it finds there, and a
# `.strm` body may hold ANY Kodi path, `plugin://...` included, which runs addon
# code with arguments the instance chose.  An archive extension is the same
# shape of problem one layer down.
#
# Nothing this provider emits is ever a playlist or an archive: a finished
# debrid link is a file.  So these are refused rather than trusted.
_UNPLAYABLE_EXTENSIONS = frozenset((
    # read by Kodi as a list of items to play
    '.strm', '.m3u', '.pls', '.xsp', '.b4s', '.wpl', '.asx', '.ram', '.cue',
    # read by Kodi as something to look inside
    '.zip', '.rar', '.7z', '.tar',
))


def _unplayable_extension(path):
    """True when the url's own path ends in one of the above.

    The query string takes no part in the decision: a signed CDN link carries
    tokens that happen to contain dots, and judging those would refuse real
    rows.  The path is percent-decoded first, because `%2Estrm` names the same
    file to the server as `.strm`.

    `.m3u8` is deliberately NOT on the list.  HLS is a legitimate thing for a
    debrid CDN to serve, and refusing it would throw away real streams; the
    match is on the whole extension, so `.m3u` does not catch it.
    """
    try:
        name = unquote(_text(path)).rsplit('/', 1)[-1].strip().lower()
    except Exception:
        return False
    dot = name.rfind('.')
    if dot < 0:
        return False
    return name[dot:] in _UNPLAYABLE_EXTENSIONS


def _http_only(url, home=''):
    """A link we are willing to hand to the player, or ''.

    urljoin passes unknown schemes through untouched, so a Location of
    `magnet:?xt=...`, `file:///...` or `//other.host/x` becomes the next hop
    and, having no netloc, reads as "off the instance -- this is the CDN".
    A hostile or compromised instance could hand the player a magnet, a local
    file or a loopback address that way.  Only http(s) leaves this function.

    `home` is the instance the viewer configured.  Its own address is allowed
    to be a private one: a self-hosted instance on a LAN serves its playback
    links from `192.168.x`, `10.x` or a `.local` name.  A redirect to any OTHER
    private address is still refused -- that is the case the guard is for.
    """
    url = _text(url).strip()
    if not url:
        return ''
    lower = url.lower()
    if any(word in lower for word in _TORRENT_WORDS):
        return ''
    # The host addon reads ' , ' in a url as a list of parts and builds a
    # `stack://` from them, so only the FIRST part would ever be checked here.
    # A second part could be a `file://` path or the viewer's own loopback --
    # past every guard below, since urlparse only ever sees part one. Any
    # whitespace is refused: a finished link has none, and percent-encoding is
    # how a real one would carry a space.
    if any(character.isspace() for character in url):
        return ''
    try:
        parts = urlparse(url.split('|', 1)[0])
        scheme = (parts.scheme or '').lower()
        host = (parts.hostname or '').lower()
    except Exception:
        return ''
    if scheme not in ('http', 'https') or not host:
        return ''
    if _unplayable_extension(parts.path):
        return ''
    if _foreign_pipe_options(url):
        return ''
    home = _text(home).lower()
    # Without a known instance there is nothing a private address could be
    # excused as, so it is refused rather than let through.
    if _is_private_host(host) and (not home or _host(url) != home):
        return ''
    return url


def _follow(start_url, headers=None, home=None):
    """Walk the instance's own redirects; hand back the first link off it.

    Three rules:

    The last hop is a debrid CDN (store-*.tb-cdn.io and the like) that can sit
    well past any sane timeout before the first byte.  So the walk STOPS at the
    first Location pointing off the instance and returns it UNOPENED, and a
    URL that is already off the instance is never opened at all -- Kodi opens
    it itself.  Fetching it here would cost a failover the player never
    needed, open a signed one-shot link twice, and bill the viewer's debrid
    account for a download nobody watched.

    Headers declared by the row go ONLY to the instance's own host; a
    third-party CDN never sees them.

    And every hop, including the one we return, must be http(s).
    """
    bare = _http_only(start_url, home)
    if not bare:
        return None
    home = _text(home).lower()
    if not home:
        # Without a known instance host there is no way to tell "still ours"
        # from "already the CDN".  Guessing would open a signed link and send
        # the row's headers to a stranger, so do neither.
        return bare

    # Already somewhere else: nothing of ours to resolve, and nothing of ours
    # to send. Hand it over untouched.
    if _host(bare) != home:
        return bare

    request_headers = dict(headers or {})
    request_headers.setdefault('User-Agent', USER_AGENT)

    current = bare
    for _ in range(MAX_REDIRECT_HOPS):
        try:
            response = requests.get(current, headers=request_headers,
                                    allow_redirects=False, stream=True,
                                    timeout=RESOLVE_TIMEOUT)
        except Exception as error:
            log_utils.log('aiostreams: resolve request failed: %s' % error)
            return None
        try:
            if response.status_code >= 400:
                log_utils.log('aiostreams: resolve answered HTTP %s from %s'
                              % (response.status_code, _host(current)))
                return None
            if not response.is_redirect:
                return _http_only(response.url or current, home) or None
            location = _text(response.headers.get('Location')).strip()
            if not location:
                log_utils.log('aiostreams: HTTP %s with no Location from %s'
                              % (response.status_code, _host(current)))
                return None
            nxt = _http_only(urljoin(current, location), home)
            if not nxt:
                log_utils.log('aiostreams: refused a non-http redirect from %s'
                              % _host(current))
                return None
            # A failed debrid request answers `302 -> /static/<clip>.mp4`.
            # Recognising it HERE rather than after the walk saves opening it:
            # the row fails back to the list one request sooner, which is the
            # whole value of catching it at all.
            if _is_placeholder(nxt):
                log_utils.log('aiostreams: the instance redirected to its own '
                              'error clip, the link is not ready or not '
                              'available')
                return None
        finally:
            try:
                response.close()
            except Exception:
                pass

        if _host(nxt) != home:
            # Off the instance -- this is the CDN. Hand it over unopened.
            return nxt
        current = nxt

    log_utils.log('aiostreams: more than %s redirects, giving up on %s'
                  % (MAX_REDIRECT_HOPS, home))
    return None


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']
        self.domains = [urlparse(url).netloc for _, url in INSTANCES]
        self.base_link = _base_url()
        self.aliases = []

    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'tmdb': tmdb, 'title': title,
                   'aliases': aliases, 'year': year}
            url = urlencode(url)
            return url
        except Exception:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        # The second argument is named tvdb by every provider in this module,
        # but the host addon passes its TMDb id there: call.tvshow(imdb, tmdb,
        # ...).  Store it under the name it actually carries, or the TMDb
        # fallback below is dead for every show without an IMDb id.
        try:
            self.aliases.extend(aliases)
            url = {'imdb': imdb, 'tmdb': tvdb, 'tvshowtitle': tvshowtitle,
                   'aliases': aliases, 'year': year}
            url = urlencode(url)
            return url
        except Exception:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None:
                return

            url = parse_qs(url)
            url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
            url['title'], url['premiered'] = title, premiered
            url['season'], url['episode'] = season, episode
            url = urlencode(url)
            return url
        except Exception:
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if not url:
                return sources

            auth = _auth_header()
            if not auth:
                # No UUID set: nothing to say, and nothing worth logging on
                # every single scrape.
                return sources

            base = str(self.base_link or _base_url() or '').strip().rstrip('/')
            if not base:
                log_utils.log('aiostreams: no instance chosen and no custom URL set')
                return sources
            # The instance the viewer chose.  A self-hosted one is often on
            # their own network, so its address is the one private host a row
            # is allowed to point at.
            home = _host(base)

            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])

            is_show = 'tvshowtitle' in data
            title = data['tvshowtitle'] if is_show else data['title']
            aliases = self.aliases or data.get('aliases')

            media_id = _search_id(data.get('imdb'), data.get('tmdb'))
            if not media_id:
                return sources

            if is_show:
                season, episode = data['season'], data['episode']
                hdlr = 'S%02dE%02d' % (int(season), int(episode))
                params = {'type': 'series',
                          'id': '%s:%s:%s' % (media_id, season, episode)}
            else:
                season = episode = None
                hdlr = data['year']
                params = {'type': 'movie', 'id': media_id}

            results = _search(base, params, auth)
            if not results:
                return sources

            colour = _row_colour()
            mark_cached = _mark_cached()

            dropped = {'type': 0, 'uncached': 0, 'no_url': 0, 'no_name': 0,
                       'title': 0, 'episode': 0, 'cam': 0, 'error': 0}

            for raw in results:
                try:
                    if not isinstance(raw, dict):
                        continue
                    item = _flatten(raw)

                    # Only the types we offer, whatever else the row carries.
                    if _wrong_type(item):
                        dropped['type'] += 1
                        _diag('dropped on type | service=%r type=%r'
                              % (item.get('service'), item.get('type')))
                        continue

                    direct_url = _http_only(item.get('url') or item.get('url_dl'),
                                            home)
                    if not direct_url:
                        dropped['no_url'] += 1
                        continue

                    # Only an explicit "not cached" is a reason to drop here.
                    #
                    # Silence is NOT: most instances say nothing about cache
                    # state, and the services whose links are proxied through
                    # the instance (/debrid/playback/) are precisely the ones
                    # that stay silent -- AllDebrid, Real-Debrid, Premiumize.
                    #
                    # The placeholder clip an uncached row really does serve is
                    # caught in resolve(), after the redirects, before Kodi
                    # ever sees it.
                    if _cached(item) is False:
                        dropped['uncached'] += 1
                        _diag('dropped uncached | service=%r type=%r'
                              % (item.get('service'), item.get('type')))
                        continue

                    release = _release_name(item, raw)
                    name = cleantitle.get_title(release)
                    if not name:
                        dropped['no_name'] += 1
                        _diag('dropped no_name | service=%r' % (item.get('service'),))
                        continue

                    if is_show:
                        matched = (source_utils.is_match(name, title, hdlr, aliases)
                                   or source_utils.is_season_match(name, title, season, aliases))
                    else:
                        matched = source_utils.is_match(name, title, hdlr, aliases)
                    if not matched:
                        dropped['title'] += 1
                        _diag('dropped title | service=%r name=%r (from %r)'
                              % (item.get('service'), name, release))
                        continue

                    # The title test alone is too loose for an episode: it
                    # matches s02e03 inside s02e035, and its season fallback
                    # drops the episode requirement entirely.
                    if is_show and not _episode_ok(name, season, episode, item):
                        dropped['episode'] += 1
                        _diag('dropped wrong episode | asked S%sE%s name=%r'
                              % (season, episode, name))
                        continue

                    quality = _quality_of(item, name)
                    if quality in _CAM_QUALITIES and not is_show:
                        dropped['cam'] += 1
                        continue

                    dsize, isize = _size_of(item)

                    # No 'pack': the instance resolved one finished file for
                    # the episode that was asked for, so there is nothing for
                    # the host addon to go hunting inside.
                    sources.append({'source': _source_label(item),
                                    'debrid': _debrid_label(item, mark_cached),
                                    'prelinked': True,
                                    'row_colour': colour,
                                    'quality': quality, 'language': 'en',
                                    'url': _join_pipe(direct_url, _request_headers(item)),
                                    'info': isize, 'direct': True,
                                    'debridonly': True, 'name': name,
                                    'size': dsize})
                except Exception as error:
                    _diag('row raised %s' % error)
                    dropped['error'] += 1
                    log_utils.log('aiostreams_row_exc', 1)

            summary = ', '.join('%s=%s' % (k, v) for k, v in dropped.items() if v)
            if results and not sources:
                log_utils.log('aiostreams: %s rows, none kept (%s)'
                              % (len(results), summary))
            else:
                _diag('%s rows, %s kept%s'
                      % (len(results), len(sources),
                         ' | dropped: %s' % summary if summary else ''))

            return sources
        except Exception:
            log_utils.log('aiostreams exc', 1)
            return sources

    def resolve(self, url):
        try:
            if not url:
                return None

            bare, headers = _split_pipe(url)
            final = _follow(bare, headers, home=_host(self.base_link))
            if not final:
                return None
            if _is_placeholder(final):
                log_utils.log('aiostreams: placeholder stream rejected, the '
                              'instance has not finished this one yet')
                return None

            # Do the headers still belong to the host that is about to get
            # them?  The comparison is against the host THE ROW NAMED, not
            # against the instance setting.
            #
            # Most rows arrive already pointing at the debrid CDN, and the
            # `Referer` and `User-Agent` the instance declared FOR that CDN
            # must reach it, or the row fails on play with a 403.
            #
            # Nothing of the viewer's is in that tail.  The instance's own
            # Basic credential is built in _auth_header() and goes only to
            # _search(); it never enters a row url.  What is here is what the
            # instance declared for this link, and the only party receiving it
            # is the host the instance itself chose.
            #
            # The three cases this gets right:
            #   row on the instance, no redirect   bare == final  -> keep
            #   row on the instance -> CDN         bare != final  -> drop,
            #                                      they were the instance's
            #   row already on the CDN             bare == final  -> keep
            on_instance = _host(final) == _host(bare)
            return _join_pipe(final, headers if on_instance else None)
        except Exception:
            # Never hand back the raw row url: it has passed none of the
            # checks above.
            log_utils.log('aiostreams resolve exc', 1)
            return None
