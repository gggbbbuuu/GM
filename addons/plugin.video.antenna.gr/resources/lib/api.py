# -*- coding: utf-8 -*-

'''
    ANT1 Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

import json
import re
from html import unescape

from . import constants as c

try:
    from tulip import kodi
except ImportError:  # pragma: no cover - only when run outside Kodi
    kodi = None

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

    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'el-GR,el;q=0.9,en;q=0.8',
        'Referer': c.BASE + '/',
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

            import time

            time.sleep(3 * (attempt + 1))


def _fetch_json(url, timeout=30):

    return json.loads(fetch(url, timeout=timeout))


def _throttled(error):
    """True for the HTTP 429 the site answers bursts with."""

    return getattr(error, 'code', None) == 429 or '429' in str(error)


def _clean(value):
    """Unescapes entities and flattens the whitespace of a scraped string."""

    if not value:
        return ''

    return WS_RE.sub(' ', unescape(value)).strip()


def _dedupe(cards):

    out = []
    seen = set()

    for card in cards:
        url = card.get('url')

        if not url or url in seen or not card.get('title'):
            continue

        seen.add(url)
        out.append(card)

    return out


# ---------------------------------------------------------------------------
# Cards
#
# The whole site is one card grid with two flavours: video cards link to
# /watch/<cid>/<slug> (playable) while the rest link to text articles
# (info only). Every parser below returns both, flagged accordingly.
# ---------------------------------------------------------------------------

def _watch_cards(html):
    """
    Parses ``entry-small`` cards pointing at /watch/ urls:

        <article class="entry-small ...">
          <a href="/watch/<cid>/<slug>"><img src="IMAGE" ...></a>
          ...<span class="date">...</span>...
          <a href="/watch/<cid>/<slug>"><h3 ...>TITLE</h3></a>
    """

    cards = []

    for match in re.finditer(r'<article[^>]*>.*?</article>', html, re.S):
        block = match.group(0)

        link = re.search(r'href="(/watch/[a-zA-Z0-9]+/[a-zA-Z0-9_\-]+)"', block)

        if not link:
            continue

        title = re.search(r'<h[23][^>]*>(.*?)</h[23]>', block, re.S)
        image = re.search(r'<img[^>]+src="([^"]+)"', block)
        date = re.search(r'class="date"[^>]*>([^<]+)<', block)

        cards.append({
            'title': _clean(TAG_RE.sub('', title.group(1))) if title else '',
            'url': c.BASE + link.group(1),
            'image': unescape(image.group(1)) if image else '',
            'date': _clean(date.group(1)) if date else '',
            'playable': True,
        })

    return _dedupe(cards)


def _article_cards(html):
    """Same grid but pointing at text articles (/news/, /f-latest/, ...)."""

    cards = []

    for match in re.finditer(r'<article[^>]*>.*?</article>', html, re.S):
        block = match.group(0)

        if '/watch/' in block:
            continue

        link = re.search(r'href="((?:/[a-z0-9\-/]+?)?/(?:news|f-latest|celebrity|eidiseis)/[^"]+)"', block)

        if not link:
            continue

        title = re.search(r'<h[23][^>]*>(.*?)</h[23]>', block, re.S)
        image = re.search(r'<img[^>]+src="([^"]+)"', block)
        date = re.search(r'class="date"[^>]*>([^<]+)<', block)

        cards.append({
            'title': _clean(TAG_RE.sub('', title.group(1))) if title else '',
            'url': c.BASE + link.group(1) if link.group(1).startswith('/') else link.group(1),
            'image': unescape(image.group(1)) if image else '',
            'date': _clean(date.group(1)) if date else '',
            'playable': False,
        })

    return _dedupe(cards)


def _mixed_cards(html):
    """Video and text cards interleaved, video first when both exist."""

    videos = _watch_cards(html)
    articles = _article_cards(html)

    return videos + articles


def _page_count(html):
    """Reads 'Σελίδα N από M'; 1 when the pager is absent."""

    match = re.search(r'Σελίδα\s+\d+\s+από\s+(\d+)', html)

    return int(match.group(1)) if match else 1


# ---------------------------------------------------------------------------
# Live
# ---------------------------------------------------------------------------

def live(channel):
    """Returns the live JSON dict for one of the four channels."""

    return _fetch_json(c.LIVE_JSON.format(channel=channel))


# ---------------------------------------------------------------------------
# Shows
# ---------------------------------------------------------------------------

def shows(url=None):
    """The full shows index (or one server-side category of it)."""

    html = fetch(url or c.SHOWS_PAGE)

    shows = []
    seen = set()

    for match in re.finditer(r'<article[^>]*>.*?</article>', html, re.S):
        block = match.group(0)

        # Some category archives (e.g. eidiseis) render an empty grid; the
        # videos still live on each show's own page, so fall back to that.
        link = re.search(r'href="(https://www\.antenna\.gr/[a-z0-9]+)"', block)

        if not link or link.group(1) in seen:
            continue

        cat = re.search(r'data-category-id="(\d+)"', block) or \
            re.search(r'cat="([^"]+)"', block)

        if not cat:
            continue

        title_m = re.search(r'<h2[^>]*>(.*?)</h2>', block, re.S)
        title = _clean(title_m.group(1)) if title_m else ''

        if title:
            seen.add(link.group(1))

            image = re.search(r'<img[^>]+src="([^"]+)"', block)
            category = re.search(r'cat="([^"]+)"', block)

            shows.append({
                'title': title,
                'url': link.group(1),
                'image': unescape(image.group(1)) if image else '',
                'category': _clean(category.group(1)) if category else '',
            })
        else:
            # Empty card: resolve the show slug from the category page itself
            # by reusing the full index instead of failing the folder.
            pass

    if not shows:
        all_shows = shows_index_fallback()
        wanted = _category_id(url)
        shows = [s for s in all_shows if s.get('category_id') == wanted] if wanted else []

    return _dedupe(shows)


def _category_id(url):
    """Reads the /shows/ALL/<id>/<slug> id from a category url."""

    match = re.search(r'/shows/ALL/(\d+)/', url or '')

    return match.group(1) if match else ''


def shows_index_fallback():
    """The full, unfiltered shows index with category ids attached."""

    html = fetch(c.SHOWS_PAGE)

    out = []

    for match in re.finditer(r'<article[^>]*>.*?</article>', html, re.S):
        block = match.group(0)
        link = re.search(r'href="(https://www\.antenna\.gr/[a-z0-9]+)"', block)

        if not link:
            continue

        cat = re.search(r'data-category-id="(\d+)"', block)
        title_m = re.search(r'<h2[^>]*>(.*?)</h2>', block, re.S)
        title = _clean(title_m.group(1)) if title_m else ''

        if not title:
            continue

        image = re.search(r'<img[^>]+src="([^"]+)"', block)
        category = re.search(r'cat="([^"]+)"', block)

        out.append({
            'title': title,
            'url': link.group(1),
            'image': unescape(image.group(1)) if image else '',
            'category': _clean(category.group(1)) if category else '',
            'category_id': cat.group(1) if cat else '',
        })

    return _dedupe(out)


def show_videos(show_slug):
    """
    A show's archive: the inlined first page plus the one-shot "load more"
    dump (morevideos.aspx), keyed by the currentShowId in the videos page.
    """

    html = fetch(c.SHOW_VIDEOS.format(slug=show_slug))

    cards = _watch_cards(html)

    show_id = re.search(r"currentShowId\s*=\s*'([^']+)'", html)

    if show_id and show_id.group(1):
        try:
            rest = fetch(c.MORE_VIDEOS.format(show_id=show_id.group(1)))
            cards.extend(_watch_cards(rest))
        except Exception:
            pass

    return _dedupe(cards)


# ---------------------------------------------------------------------------
# News / lifestyle (paginated categories)
# ---------------------------------------------------------------------------

def category(link, page=1):
    """
    One page of a categories.aspx / fthis_categories.aspx archive.
    Returns (items, total_pages); video and text items flagged accordingly.
    """

    url = link.format(page=page)
    html = fetch(url)

    return _mixed_cards(html), _page_count(html)


def related_videos(section_url):
    """The 'related videos' rail some section pages carry."""

    html = fetch(section_url)

    marker = html.find('category-videos')

    if marker == -1:
        return []

    return _watch_cards(html[marker:marker + 60000])


# ---------------------------------------------------------------------------
# Sports highlights
# ---------------------------------------------------------------------------

def sports(section):
    """Videoplay fragment cids embedded in the /f1 and /football hubs."""

    html = fetch(c.BASE + '/' + section)

    cids = []
    seen = set()

    for cid in re.findall(r'videoplay\?cid=([a-z0-9]+)', html):
        if cid not in seen:
            seen.add(cid)
            cids.append(cid)

    cards = []

    for cid in cids:
        info = player_info(cid)

        if info.get('url'):
            cards.append({
                'title': info.get('title', ''),
                'url': '{0}/watch/{1}/video'.format(c.BASE, cid),
                'image': info.get('thumb', ''),
                'date': '',
                'playable': True,
            })

    return cards


# ---------------------------------------------------------------------------
# Radio
# ---------------------------------------------------------------------------

def stations():
    """
    The soundis general-config (no auth) carries every station with a direct
    revma stream url. Read fresh per call: edge tokens expire in seconds.
    """

    data = _fetch_json(c.RADIO_CONFIG)

    out = []

    for station in (data.get('data') or {}).get('stream_list') or []:
        url = station.get('url_stream')

        if not url:
            continue

        out.append({
            'title': station.get('title', ''),
            'subtitle': station.get('subtitle', ''),
            'url': url,
            'image': ((station.get('playing_now') or {}).get('photo_url')) or '',
            'slug': station.get('main_slug', ''),
        })

    return out


# ---------------------------------------------------------------------------
# Cyprus (ant1live.com, Drupal)
#
# Portrait-teaser cards shaped like /webtv/<section>/<slug>. Most open a
# sub-index (shows, movies, podcasts); episode/news/movie pages carry the
# videojs player (<source src>) or a lazy YouTube iframe instead.
# ---------------------------------------------------------------------------

def _cy_cards(html):
    """Parses the CY portrait-teaser card grid."""

    cards = []

    for match in re.finditer(r'<article[^>]*>.*?</article>', html, re.S):
        block = match.group(0)
        link = re.search(r'href="(/webtv/[a-z0-9\-/]+)"', block)

        if not link:
            continue

        title = re.search(r'<h4[^>]*>(.*?)</h4>', block, re.S)
        image = re.search(r'<img[^>]+src="([^"]+)"', block)

        cards.append({
            'title': _clean(title.group(1)) if title else '',
            'url': c.CY_BASE + link.group(1),
            'image': c.CY_BASE + image.group(1) if image and image.group(1).startswith('/') else (unescape(image.group(1)) if image else ''),
            'playable': True,
            'subindex': False,
        })

    return _dedupe(cards)


def cy_section(section):
    """One CY section index: cards that are folders, episodes or clips."""

    html = fetch(c.CY_SECTION_PAGE.format(section=section))

    return _cy_cards(html)


def cy_subindex(section, slug):
    """
    A /webtv/<section>/<slug> page: either a card sub-index (shows/movies)
    or a playable episode, told apart by which markup the page carries.
    """

    from urllib.parse import urljoin

    url = c.CY_SUBINDEX_PAGE.format(section=section, slug=slug)
    html = fetch(url)

    # Player pages carry the videojs player or a YouTube embed...
    source = re.search(r'''<source\s+src=["']([^"']+)["']''', html)
    yt = re.search(r'''(?:data-src|src)=["']https?://www\.youtube\.com/embed/([\w-]{6,})''', html)

    if source or yt:
        title_m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        image_m = re.search(r'<meta property="og:image" content="([^"]+)"', html)

        if yt and not source:
            stream = 'https://www.youtube.com/watch?v={}'.format(yt.group(1))
        else:
            stream = urljoin(c.CY_BASE + '/', source.group(1))

        return {
            'playable': True,
            'url': stream,
            'title': _clean(title_m.group(1)) if title_m else '',
            'image': c.CY_BASE + image_m.group(1) if image_m and image_m.group(1).startswith('/') else (image_m.group(1) if image_m else ''),
            'meta': _cy_detail_meta(html),
        }

    # ...otherwise it is a card sub-index exactly like a section page.
    return {'playable': False, 'items': _cy_cards(html)}


def _cy_detail_meta(html):
    """
    Movie/show detail block: cover fanart, poster, air date, type and the
    structured synopsis (genre/year line, director, cast, ΥΠΟΘΕΣΗ + plot).
    """

    meta = {}
    TAG = re.compile(r'<[^>]+>')

    def clean(value):
        return WS_RE.sub(' ', unescape(value or '')).strip()

    cover = re.search(r'<picture>.*?<source[^>]+srcset="([^"\s]+)', html, re.S)

    if cover:
        meta['fanart'] = cover.group(1) if cover.group(1).startswith('http') else c.CY_BASE + cover.group(1)

    poster = re.search(r'class="show__poster"[^>]*>.*?<img[^>]+src="([^"]+)"', html, re.S)

    if poster:
        meta['poster'] = poster.group(1) if poster.group(1).startswith('http') else c.CY_BASE + poster.group(1)

    airdate = re.search(r'class="[^"]*show__time[^"]*"[^>]*>.*?<span>([^<]+)</span>', html, re.S)

    if airdate:
        meta['aired'] = clean(airdate.group(1))

    show_type = re.search(r'class="show__type"[^>]*>\s*<span>([^<]+)</span>', html)

    if show_type:
        meta['type'] = clean(show_type.group(1))

    details = re.search(r'class="show__details[^"]*"[^>]*>(.*?)</div>\s*<div class="views-element-container">', html, re.S)

    if not details:
        return meta

    paragraphs = [clean(TAG.sub('', p)) for p in re.findall(r'<p>(.*?)</p>', details.group(1), re.S)]
    paragraphs = [p for p in paragraphs if p and p != 'ΥΠΟΘΕΣΗ:' and not p.startswith('ΥΠΟΘΕΣΗ')]

    plot_lines = []

    for para in paragraphs:
        if para.startswith('Σκηνοθεσία:'):
            meta['director'] = [clean(d) for d in para.split(':', 1)[1].split(',') if clean(d)]
        elif para.startswith('Με τους:'):
            meta['cast'] = [clean(a) for a in para.split(':', 1)[1].split(',') if clean(a)]
        elif 'παραγωγής' in para and not plot_lines:
            year = re.search(r'(19|20)\d{2}', para)
            if year:
                meta['year'] = int(year.group(0))
            meta['genre'] = para
        else:
            plot_lines.append(para)

    if plot_lines:
        meta['plot'] = '\n\n'.join(plot_lines)

    return meta


def cy_live_url():
    """The CY live page inlines a signed cloudskep playlist, read fresh."""

    html = fetch(c.CY_LIVE_PAGE)

    match = re.search(r'''<source\s+src=["']([^"']+?\.m3u8)["']''', html)

    return match.group(1) if match else ''


# ---------------------------------------------------------------------------
# Web TV latest
# ---------------------------------------------------------------------------

def webtv():
    """The /webtv landing page: latest clips, no paging."""

    html = fetch(c.WEBTV_PAGE)

    return _watch_cards(html)


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

def player_info(cid):
    """
    The PlayerDataGraphQL_v2 record for a /watch/ cid. Either a direct mp4
    (``url``) or a bounce to ANT1+ originals (``video_url`` + should_redirect).
    """

    try:
        data = _fetch_json(c.PLAYER_JSON.format(cid=cid))
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}

    return data


def is_redirected(info):
    """True when the clip lives behind ANT1+ and the page only bounces."""

    return bool(info.get('should_redirect')) and bool(info.get('video_url'))
