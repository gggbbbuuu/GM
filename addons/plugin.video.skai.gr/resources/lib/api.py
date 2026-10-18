# -*- coding: utf-8 -*-

'''
    Skai Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from . import constants as c

try:
    from netclient import Net

    _net = Net()
except ImportError:  # pragma: no cover - only when run outside Kodi
    _net = None


USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36')

TAG_RE = re.compile(r'<[^>]+>')
WS_RE = re.compile(r'\s+')


# ---------------------------------------------------------------------------
# HTTP plumbing
# ---------------------------------------------------------------------------

def fetch(url, timeout=30, retries=2):
    """
    The site rate limits bursts with a 429, which happens when a user pages
    through a long archive quickly. Back off and try again rather than
    surfacing an empty listing.
    """

    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'el-GR,el;q=0.9,en;q=0.8',
    }

    for attempt in range(retries + 1):

        try:
            if _net is not None:
                response = _net.http_GET(url, headers=headers, timeout=timeout)
                # netclient falls back to ascii when a response carries no
                # charset, which mangles the Greek titles, so always decode
                # the raw bytes.
                return response.nodecode(True).content.decode('utf-8', 'replace')

            import urllib.request

            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read().decode('utf-8', 'replace')

        except Exception as error:
            if not _throttled(error) or attempt == retries:
                raise

            time.sleep(3 * (attempt + 1))


def _throttled(error):
    """True for the HTTP 429 the site answers bursts with."""

    return getattr(error, 'code', None) == 429 or '429' in str(error)


def _clean(value):
    """Unescapes entities and flattens the whitespace of a scraped string."""

    if not value:
        return ''

    return WS_RE.sub(' ', unescape(value)).strip()


def _abs(url, base=c.BASE):
    """Makes a site-relative path absolute."""

    if not url:
        return ''

    url = unescape(url)

    if url.startswith('//'):
        url = 'https:' + url
    elif url.startswith('/'):
        url = base + url

    # Quote the path only: site paths mix raw UTF-8 and pre-encoded
    # entities (unquote first so quoting twice cannot corrupt the
    # latter), while the query (e.g. Drupal ?itok= image tokens) must
    # pass through untouched.
    parts = urlsplit(url)

    return urlunsplit((parts.scheme, parts.netloc, quote(unquote(parts.path)),
                       parts.query, ''))


def _humanize(slug):
    """Turns a url slug into a readable title when no better one exists."""

    return _clean(slug.replace('-', ' ')).capitalize()


# ---------------------------------------------------------------------------
# TV catalogue (/tv/shows/ sections and show pages)
#
# Section pages render the line-up as rows:
#   <div class="... list1 ...">
#     <a href="/tv/show/<section>/<show>/sezon-..."><img src="IMAGE">
#     <div class="h2">TITLE</div> ... description ...
#     <div class="last-epi"><a href="/tv/episode/...">...
# Show pages embed their episodes in the player payload:
#   var data = {"show": {...}, "episodes": [{"link": "/episode/...",
#     "title": ..., "img": ..., "start": ..., "short_descr": ...}]}
# ---------------------------------------------------------------------------

def _show_rows(html):
    """Parses the list1 rows of a section page into show dicts."""

    shows = []
    seen = set()

    for chunk in re.split(r'<div class="col-12 pl-0 pr-0 list1', html)[1:]:
        link = re.search(r'<a href="(/tv/show/[a-z0-9\-/]+?)"', chunk)

        if not link:
            continue

        url = _abs(link.group(1).rstrip('/'))

        if url in seen:
            continue

        seen.add(url)

        title = re.search(r'<div class="h2">(.*?)</div>', chunk, re.S)
        image = re.search(r'<img src="([^"]+)"', chunk)

        shows.append({
            'title': _clean(TAG_RE.sub('', title.group(1))) if title
            else _humanize(url.rstrip('/').rsplit('/', 1)[-1]),
            'url': url,
            'image': _abs(image.group(1)) if image else '',
        })

    return shows


def tv_shows(section):
    """
    Returns [{'title', 'url', 'image', 'seasons'}] for one /tv/shows/
    section. Sections mix two layouts: list1 rows (news) and listimg
    cards (series, entertainment), so both are merged with rows first.
    Long-running shows span one page per season (e.g. eleven Happy
    Traveller seasons), which are grouped into a single entry whose
    ``seasons`` list carries every season url, newest first.
    """

    html = fetch(c.SHOWS_PAGE.format(section))

    shows = _show_rows(html)
    seen = set(show['url'] for show in shows)

    for card in _cards(html, kinds=('show',)):
        if card['url'] not in seen:
            seen.add(card['url'])
            shows.append(card)

    grouped = {}
    order = []

    for show in shows:
        base = re.sub(r'/(?:sezon-[\d-]+|\d+os-kuklos)/?$', '', show['url'])
        season = re.search(r'/(sezon-[\d-]+|\d+os-kuklos)/?$', show['url'])

        if base not in grouped:
            grouped[base] = dict(show)
            grouped[base]['seasons'] = []
            order.append(base)

        if season:
            grouped[base]['seasons'].append({
                'url': show['url'],
                'label': _season_label(season.group(1)),
            })
        elif not grouped[base]['seasons']:
            grouped[base]['url'] = show['url']

    for base in order:
        seasons = grouped[base]['seasons']
        seasons.sort(key=lambda season: season['label'], reverse=True)
        if seasons:
            grouped[base]['url'] = seasons[0]['url']
            grouped[base]['image'] = next(
                (show['image'] for show in shows
                 if show['url'] in set(s['url'] for s in seasons) and show.get('image')),
                grouped[base].get('image', ''))

    grouped_shows = [grouped[base] for base in order]

    if section == 'psuchagogia':
        # My Style Rocks keeps no pages on skai.gr; its dedicated
        # YouTube channel is appended as a regular show entry.
        grouped_shows.append({
            'title': 'My Style Rocks',
            'url': c.MSR_CHANNEL,
            'image': _channel_avatar(c.MSR_CHANNEL),
            'seasons': [],
            'yt_channel': True,
        })

    return grouped_shows


def _channel_avatar(channel_url):
    """Reads a YouTube channel page's avatar for the show entry."""

    try:
        html = fetch(channel_url, timeout=15)
    except Exception:
        return ''

    avatar = re.search(r'<meta property="og:image"\s*content="([^"]+)"', html)

    return _abs(avatar.group(1)) if avatar else ''


def _season_label(slug):
    """Turns a season slug into a readable label."""

    kuklos = re.match(r'(\d+)os-kuklos$', slug)

    if kuklos:
        return '{0}ος Κύκλος'.format(kuklos.group(1))

    return slug.replace('sezon-', '').replace('-', ' - ')


def _air_date(entry, link):
    """
    Normalizes an episode's air moment to Greek display format.
    Episode links end in ``YYYY-MM-DD-HH`` (date plus air hour);
    the payload's ``start`` field carries the same moment as
    ``YYYY-MM-DD HH:MM:SS`` and wins when present.
    """

    start = re.match(r'(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?',
                     entry.get('start') or '')

    if start:
        date = '{2}/{1}/{0}'.format(*start.groups()[:3])
        if start.group(4):
            return '{0} {1}:{2}'.format(date, start.group(4), start.group(5))
        return date

    slug = re.search(r'/(\d{4})-(\d{2})-(\d{2})(?:-(\d{2}))?(?:/[^/]*)?/?$', link or '')

    if slug:
        date = '{2}/{1}/{0}'.format(*slug.groups()[:3])
        if slug.group(4):
            return '{0} {1}:00'.format(date, slug.group(4))
        return date

    return ''


def _player_payloads(html):
    """
    Yields every parsed ``var data`` JSON blob of a TV page. The blobs
    are single-line by construction; matching must stay single-line too,
    otherwise a match opening at the ad stub's ``var data = {};`` bleeds
    across newlines into unparseable garbage.
    """

    for match in re.finditer(r'var data = ({.+?});', html):
        try:
            yield json.loads(match.group(1))
        except Exception:
            continue


def show_episodes(show_url):
    """
    Returns [{'title', 'url', 'image', 'plot'}] for one show page, read
    from its embedded player payload (``episodes`` list).
    """

    html = fetch(show_url)

    episodes = []

    for payload in _player_payloads(html):
        entries = payload.get('episodes')

        if not isinstance(entries, list):
            continue

        for entry in entries:
            link = entry.get('link')

            if not link:
                continue

            title = _clean(entry.get('title') or entry.get('media_item_title') or '')
            date = _air_date(entry, link)

            if date and title and date not in title:
                title = '{0} ({1})'.format(title, date)

            episodes.append({
                'title': title or _humanize(link.rstrip('/').rsplit('/', 1)[-1]),
                'url': _abs('/tv' + link if link.startswith('/episode/') else link),
                'image': _abs(entry.get('img') or ''),
                'plot': _clean(TAG_RE.sub('', entry.get('short_descr') or '')),
            })

        if episodes:
            break

    return episodes


def episode_plot(url):
    """Reads an episode page's own description for the plot field."""

    try:
        html = fetch(url)
    except Exception:
        return ''

    plot = re.search(r'<meta property="og:description"\s*content="([^"]+)"', html)

    return _clean(plot.group(1)) if plot else ''


# ---------------------------------------------------------------------------
# Trending (/tv/trending) and cinema (/tv/cinema) cards
#
# Both render server-side cards:
#   <div class="col-lg-4 listimg ">
#     <a href="/tv/<episode|show>/..." class="resio">
#       <h3 class="title_r">TITLE</h3><img src="IMAGE" ...
# The cinema entries are movietime show pages whose embedded trailer
# resolves through PluginsGR, like the alpha add-on's movie listings.
# ---------------------------------------------------------------------------

def _cards(html, kinds=('episode', 'show')):
    """Parses the listimg cards of the trending/cinema/section pages."""

    kinds = '|'.join(kinds)
    cards = []
    seen = set()

    for chunk in re.split(r'<div class="[^"]*listimg', html)[1:]:
        link = re.search(r'<a href="(/tv/(?:{0})/[^"]+)"'.format(kinds), chunk)

        if not link:
            continue

        url = _abs(link.group(1))

        if url in seen:
            continue

        seen.add(url)

        title = re.search(r'<h3 class="title_r">(.*?)</h3>', chunk, re.S)
        image = re.search(r'<img src="([^"]+)"', chunk)

        cards.append({
            'title': _clean(TAG_RE.sub('', title.group(1))) if title
            else _humanize(url.rstrip('/').rsplit('/', 1)[-1]),
            'url': url,
            'image': _abs(image.group(1)) if image else '',
        })

    return cards


def trending():
    """Returns the newest trending episodes, in page order."""

    return _cards(fetch(c.TRENDING_PAGE))


def cinema():
    """Returns the cinema (movietime) entries, in page order."""

    return _cards(fetch(c.CINEMA_PAGE))


def _movie_meta(url):
    """Reads a cinema page's og: metatags plus its trailer flag."""

    try:
        html = fetch(url, timeout=15)
    except Exception:
        return None

    title = re.search(r'<meta property="og:title"\s*content="([^"]+)"', html)
    image = re.search(r'<meta property="og:image"\s*content="([^"]+)"', html)
    plot = re.search(r'<meta property="og:description"\s*content="([^"]+)"', html)

    playable = bool(re.search(r'media_item_file', html))

    return {
        'title': _clean(title.group(1)) if title else '',
        'image': _abs(image.group(1)) if image else '',
        'plot': _clean(plot.group(1)) if plot else '',
        'playable': playable,
    }


def cinema_detailed():
    """
    Returns cinema entries enriched with their own page metadata,
    like the alpha add-on's movie deep scrape.
    """

    items = cinema()
    urls = [item['url'] for item in items]
    enriched = {}

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_movie_meta, url): url for url in urls}

        for future in as_completed(futures):
            try:
                meta = future.result()
            except Exception:
                continue

            if meta:
                enriched[futures[future]] = meta

    order = {url: index for index, url in enumerate(urls)}
    detailed = []

    for item in items:
        meta = enriched.get(item['url'], {})

        if not meta.get('playable', True):
            continue

        merged = dict(item)
        merged.update({k: v for k, v in meta.items() if v and k != 'playable'})
        detailed.append(merged)

    detailed.sort(key=lambda item: order.get(item['url'], 0))

    return detailed


# ---------------------------------------------------------------------------
# Programme (/tv/programma[/YYYY-MM-DD])
#
# Day pages render rows with the air time, an optional LIVE badge for the
# now-airing entry, the episode link with its thumbnail, and the title:
#   <div class="col-md-12 ... list1 ...">
#     <div class="bgbox"><span>HH:MM</span></div>
#     [<div class="live-img ..."><a href="/tv/live"><span>LIVE</span></a>]
#     <a href="/tv/episode/..."><img src="IMAGE">
#     <a href="/tv/episode/...">TITLE</a> ... description ...
# ---------------------------------------------------------------------------

def programma_dates():
    """Returns [{'label', 'date', 'today'}] for every day in the nav."""

    html = fetch(c.PROGRAMMA_PAGE)

    dates = []
    today = None

    for match in re.finditer(r'href="(/tv/programma/(\d{4}-\d{2}-\d{2}))"', html):
        url, iso = match.group(1), match.group(2)

        if iso not in [day['date'] for day in dates]:
            dates.append({'label': iso, 'date': iso, 'today': False, 'url': _abs(url)})

    # The nav carries no weekday labels, so build Greek day labels and
    # flag the page the site itself serves as today.
    try:
        from datetime import datetime

        current = re.search(r'<title>Πρόγραμμα (\d{2}-\d{2}-\d{4})</title>', html)
        if current:
            today = datetime.strptime(current.group(1), '%d-%m-%Y').strftime('%Y-%m-%d')
    except Exception:
        today = None

    weekdays = ['Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ']

    for day in dates:
        try:
            from datetime import datetime

            parsed = datetime.strptime(day['date'], '%Y-%m-%d')
            day['label'] = '{0} {1}'.format(
                weekdays[parsed.weekday()], parsed.strftime('%d/%m'))
            day['today'] = day['date'] == today
        except Exception:
            pass

    dates.sort(key=lambda day: day['date'])

    return dates


def programma_rows(date=None):
    """Returns [{'time', 'now', 'title', 'plot', 'url', 'image'}] for one day."""

    url = c.PROGRAMMA_PAGE if not date \
        else '{0}/{1}'.format(c.PROGRAMMA_PAGE, date)

    html = fetch(url)
    rows = []

    for chunk in re.split(r'<div class="col-md-12 pl-0 pr-0 list1', html)[1:]:
        time = re.search(r'<div class="bgbox">.*?<span>([\d:]+)</span>', chunk, re.S)
        image = re.search(r'<img src="([^"]+)"', chunk)

        if not time:
            continue

        # A row carries several anchors (LIVE badge, thumbnail, title);
        # the episode/show link wins, the bare live link is the fallback.
        links = re.findall(r'<a href="(/tv/(?:episode|show|live)[^"]*)"', chunk)
        target = next((u for u in links if '/tv/live' not in u), links[0] if links else '')

        if not target:
            continue

        title = ''
        for anchor in re.finditer(
                r'<a href="(/tv/(?:episode|show)[^"]*)"(?: class="[^"]*")?>(.*?)</a>',
                chunk, re.S):
            text = _clean(TAG_RE.sub('', anchor.group(2)))
            if text and '<img' not in anchor.group(2):
                title = text
                target = anchor.group(1)
                break

        plot = re.search(r'<div class="padd23">.*?</a>\s*(.*?)\s*</div>', chunk, re.S)

        rows.append({
            'time': time.group(1),
            'now': 'live-img' in chunk or '>LIVE<' in chunk,
            'title': title,
            'plot': _clean(TAG_RE.sub('', plot.group(1))) if plot else '',
            'url': _abs(target),
            'image': _abs(image.group(1)) if image else '',
        })

    return [row for row in rows if row['title']]


# ---------------------------------------------------------------------------
# Podcasts (skairadio.gr archive)
#
# The show index is Drupal-paginated (?page=N); each show page carries its
# episodes as <option value="id" data-url="/<show>/episode-...">DATE</option>
# and every episode page inlines its mp3 as ``url: '...mp3'``.
# ---------------------------------------------------------------------------

def pod_shows(page=0):
    """Returns (items, has_next) for one radio archive index page."""

    html = fetch(c.RADIO_SHOWS_PAGE.format(page))

    items = []
    seen = set()

    for chunk in re.split(r'<div class="row border-bottom pt-4 m-0 show-item', html)[1:]:
        link = re.search(r'<a href="(/[^"]+?)"', chunk)

        if not link:
            continue

        path = link.group(1)

        if path.startswith(('/contact', '/history', '/network', '/producers',
                             '/cdn-cgi', '/node', '/taxonomy')):
            continue

        # Index rows link straight at the latest episode; trim those down
        # to the show archive so every show lists once.
        show = re.sub(r'/episode-[^/"]*$', '', path).rstrip('/') or '/'

        if show in seen:
            continue

        seen.add(show)

        title = re.search(r'<h3[^>]*>(.*?)</h3>', chunk, re.S)
        image = re.search(r'<img[^>]+src="([^"]+)"', chunk)

        items.append({
            'title': _clean(TAG_RE.sub('', title.group(1))) if title
            else _humanize(show.strip('/')),
            'url': _abs(show, base=c.RADIO_BASE),
            'image': _abs(image.group(1), base=c.RADIO_BASE) if image else '',
        })

    has_next = bool(re.search(r'rel="next"|pager__item--next|page={0}'.format(page + 1), html))

    return items, has_next


def pod_episodes(show_url):
    """Returns [{'title', 'url'}] for one radio show archive page."""

    html = fetch(show_url)
    show_title = re.search(r'<title>(.*?)</title>', html, re.S)

    show_title = _clean(TAG_RE.sub('', show_title.group(1))).split('|')[0].strip() \
        if show_title else ''

    episodes = []

    for match in re.finditer(
            r'<option[^>]+data-url\s*=\s*"([^"]+)"[^>]*>(.*?)</option>', html, re.S):
        path, label = match.group(1), _clean(TAG_RE.sub('', match.group(2)))

        if not path or path == '#':
            continue

        episodes.append({
            'title': '{0} - {1}'.format(show_title, label) if show_title and
            label not in show_title else (label or show_title),
            'url': _abs(path, base=c.RADIO_BASE),
        })

    return episodes


def pod_file(episode_url):
    """Reads a radio episode page's inlined mp3 url."""

    html = fetch(episode_url)

    match = re.search(r'''\burl:\s*['"](https?://[^'"]+\.mp3[^'"]*)['"]''', html)

    return match.group(1) if match else ''


# ---------------------------------------------------------------------------
# My Style Rocks (dedicated YouTube channel)
#
# The show keeps no pages on skai.gr, so its channel is listed through
# scrapetube (no API key needed) and playback resolves natively through
# ResolveURL's YouTubeGR resolver.
# ---------------------------------------------------------------------------

def _scrapetube():
    try:
        from scrapetube import wrapper
    except ImportError:
        raise RuntimeError('script.module.scrapetube is not installed')

    return wrapper


def _yt_item(entry):
    """Normalizes a scrapetube video dict into a listing dict."""

    url = entry.get('url')

    if not url:
        return None

    duration = entry.get('duration') or 0

    try:
        duration = int(duration)
    except Exception:
        duration = 0

    return {
        'title': _clean(entry.get('title') or ''),
        'url': url,
        'image': entry.get('image') or '',
        'duration': duration,
    }


def mystyle_rocks(tab='videos', limit=c.MSR_LIMIT):
    """Returns [{'title', 'url', 'image', 'duration'}], newest first."""

    wrapper = _scrapetube()

    items = []

    for entry in wrapper.list_channel_videos(
            channel_url=c.MSR_CHANNEL, limit=limit, sleep=0,
            content_type=tab):
        item = _yt_item(entry)
        if item:
            items.append(item)

    return items


def mystyle_playlists(limit=50):
    """Returns [{'title', 'url', 'image'}] for the channel's playlists."""

    wrapper = _scrapetube()

    items = []

    for entry in wrapper.list_playlists(
            c.MSR_CHANNEL.rstrip('/') + '/playlists', limit=limit, sleep=0):
        if entry.get('url') and entry.get('title'):
            items.append({
                'title': _clean(entry['title']),
                'url': entry['url'],
                'image': entry.get('image') or '',
            })

    return items


def mystyle_playlist_videos(playlist_id, limit=c.MSR_LIMIT):
    """Returns [{'title', 'url', 'image', 'duration'}] for one playlist."""

    wrapper = _scrapetube()

    items = []

    for entry in wrapper.list_playlist_videos(playlist_id, limit=limit, sleep=0):
        item = _yt_item(entry)
        if item and item['title']:
            items.append(item)

    return items


def yt_titles(entries):
    """
    Fills in blank titles (shorts carry none) through YouTube oEmbed,
    which answers each video with a tiny json record.
    """

    pending = [entry for entry in entries if not entry.get('title')]

    if not pending:
        return entries

    def _oembed(entry):
        try:
            import json as _json
            import urllib.parse
            import urllib.request

            lookup = 'https://www.youtube.com/oembed?url={0}&format=json'.format(
                urllib.parse.quote(entry['url'], safe=''))
            request = urllib.request.Request(
                lookup, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(request, timeout=15) as response:
                entry['title'] = _clean(
                    _json.loads(response.read().decode('utf-8', 'replace')).get('title', ''))
        except Exception:
            pass

        return entry

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(_oembed, pending))

    return entries
