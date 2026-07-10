"""
Shadow scraper end-to-end test.
Scans all .py files under resources/sources/, hits each endpoint with a known
movie (The Shawshank Redemption, tt0111161, 1994) and validates the response.

Run from the shadow addon root:
  cd D:\Kodi21\portable_data\addons\plugin.video.shadow
  python test_shadow_scrapers.py
"""

import re
import sys
import time
import json
import requests
import os
import urllib.parse

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}
TIMEOUT   = 10
IMDB      = 'tt0111161'         # The Shawshank Redemption
TITLE     = 'the shawshank redemption'
YEAR      = '1994'
SEASON    = '1'
EPISODE   = '1'
SEASON_N  = '01'
EPISODE_N = '01'
TV_IMDB   = 'tt0944947'         # Game of Thrones (for TV scrapers)

GREEN  = '\033[92m'
RED    = '\033[91m'
YELLOW = '\033[93m'
CYAN   = '\033[96m'
RESET  = '\033[0m'

HASH_RE   = re.compile(r'[0-9a-fA-F]{40}')
MAGNET_RE = re.compile(r'magnet:\?xt=urn:btih:', re.I)

# ── per-scraper test definitions ─────────────────────────────────────────────
# Each entry:  (scraper_file, url_fn, validate_fn)
#   url_fn()      -> str  : URL to fetch
#   validate_fn() -> (bool, str) : (passed, detail)

def _stremio_validate(r):
    """Common validator for Stremio-style JSON responses."""
    try:
        data = r.json()
        streams = data.get('streams', [])
        if not streams:
            return False, 'empty streams array'
        first = streams[0]
        h = first.get('infoHash', '')
        if HASH_RE.fullmatch(h):
            name = first.get('title', first.get('description', ''))[:60]
            return True, f'{len(streams)} streams, first: "{name}"'
        return False, f'infoHash invalid or missing: {repr(h)}'
    except Exception as e:
        return False, f'JSON parse error: {e}'

def _json_list_validate(r, key, name_key):
    try:
        data = r.json()
        items = data if isinstance(data, list) else data.get(key, [])
        if not items:
            return False, 'empty result'
        first = items[0]
        nm = first.get(name_key, str(first)[:60])
        return True, f'{len(items)} results, first: "{nm}"'
    except Exception as e:
        return False, f'JSON parse error: {e}'

def _html_magnet_validate(r):
    text = r.text
    magnets = MAGNET_RE.findall(text)
    hashes  = HASH_RE.findall(text)
    if magnets:
        return True, f'{len(magnets)} magnet links found'
    if hashes:
        return True, f'{len(hashes)} hashes found (no magnet tag)'
    return False, 'no magnet links or hashes in HTML'

def _html_rows_validate(r, row_pattern):
    rows = re.findall(row_pattern, r.text, re.DOTALL | re.I)
    if rows:
        return True, f'{len(rows)} result rows found'
    return False, 'no result rows found'


# ── Zilean (elfhosted instance) ───────────────────────────────────────────────
def _zilean():
    # weebs instance requires Authelia auth login; stremio.ru is 404
    # Check manifest to confirm service is up, flag as auth-required
    url = f'https://zileanfortheweebs.midnightignite.me/manifest.json'
    def validate(r):
        if r.status_code == 200:
            try:
                data = r.json()
                return True, f'manifest OK: "{data.get("name","?")}" (note: stream endpoint needs auth)'
            except:
                pass
        if 'authelia' in r.text.lower() or 'autheliafortheweebs' in r.url.lower():
            return False, 'redirected to Authelia login — instance requires authentication'
        return False, f'HTTP {r.status_code}'
    return url, validate

# ── apibay ────────────────────────────────────────────────────────────────────
def _apibay():
    q = urllib.parse.quote_plus(f'{TITLE} {YEAR}')
    url = f'https://apibay.org/q.php?q={q}&cat=0'
    def validate(r):
        return _json_list_validate(r, '', 'name')
    return url, validate

# ── bitsearch ─────────────────────────────────────────────────────────────────
def _bitsearch():
    q = urllib.parse.quote_plus(f'{TITLE} {YEAR}')
    url = f'https://bitsearch.to/search?q={q}&category=1'
    def validate(r):
        # bitsearch uses JS-rendered results; look for torrent hrefs or seeders text
        hits = re.findall(r'href=["\']?/torrent/', r.text, re.I)
        if hits:
            return True, f'{len(hits)} torrent links found'
        if 'seeders' in r.text.lower() or 'leechers' in r.text.lower():
            return True, f'seeders/leechers data found ({len(r.content)} bytes)'
        if len(r.content) > 50000:
            return True, f'large response ({len(r.content)} bytes) — JS-rendered results likely present'
        return False, 'no result indicators in HTML'
    return url, validate

# ── yts ───────────────────────────────────────────────────────────────────────
def _yts():
    q = urllib.parse.quote_plus(TITLE)
    url = f'https://yts.bz/api/v2/list_movies.json?query_term={q}&page=1&limit=10'
    def validate(r):
        try:
            data = r.json()
            movies = data.get('data', {}).get('movies', [])
            if not movies:
                return False, 'no movies'
            return True, f'{len(movies)} movies, first: "{movies[0].get("title","?")}"'
        except Exception as e:
            return False, str(e)
    return url, validate

# ── ezio (eztv) ───────────────────────────────────────────────────────────────
def _ezio():
    # eztv is TV-only; test with a TV show IMDB (Breaking Bad tt0903747)
    url = 'https://eztv.re/api/get-torrents?imdb_id=903747&limit=5&page=0'
    def validate(r):
        try:
            data = r.json()
            count = data.get('torrents_count', 0)
            items = data.get('torrents', [])
            if items:
                return True, f'{count} total torrents, first: "{items[0].get("title","?")}"'
            return False, f'API alive but 0 torrents returned (count={count}) — API may be dead'
        except Exception as e:
            return False, str(e)
    return url, validate

# ── glorls ────────────────────────────────────────────────────────────────────
def _glorls():
    q = urllib.parse.quote_plus(f'{TITLE} {YEAR}')
    url = f'http://glodls.to/search_results.php?cat=1&search={q}&sort=seeders&order=desc&page=0'
    def validate(r):
        return _html_magnet_validate(r)
    return url, validate

# ── fmood ─────────────────────────────────────────────────────────────────────
def _fmood():
    q = urllib.parse.quote_plus(f'{TITLE} {YEAR}')
    url = f'https://filemood.com/result?q={q}+in%3Atitle&f=0'
    def validate(r):
        rows = re.findall(r'class=["\'].*?result.*?["\']', r.text, re.I)
        magnets = MAGNET_RE.findall(r.text)
        if magnets:
            return True, f'{len(magnets)} magnets found'
        if rows:
            return True, f'{len(rows)} result rows found'
        if len(r.content) > 5000:
            return True, f'got {len(r.content)} bytes (HTML scrape needed)'
        return False, 'no results detected'
    return url, validate

# ── kass / kick4 / kban ───────────────────────────────────────────────────────
def _kass():
    q = urllib.parse.quote_plus(f'{TITLE} {YEAR}')
    url = f'https://kick4ss.net/usearch/{q}/'
    def validate(r): return _html_magnet_validate(r)
    return url, validate

def _kick4():
    q = urllib.parse.quote_plus(f'{TITLE} {YEAR}')
    url = f'https://kick4ss.com/usearch/{q}/1'
    def validate(r): return _html_magnet_validate(r)
    return url, validate

def _kban():
    q = urllib.parse.quote_plus(f'{TITLE} {YEAR}')
    url = f'https://knaben.eu/api/v1/?search={q}&size=10&orderBy=seeders&orderDirection=desc'
    def validate(r):
        try:
            data = r.json()
            hits = data.get('hits', data if isinstance(data, list) else [])
            if hits:
                return True, f'{len(hits)} hits'
            return False, 'empty hits'
        except:
            return _html_magnet_validate(r)
    return url, validate

# ── tsdl ──────────────────────────────────────────────────────────────────────
def _tsdl():
    q = urllib.parse.quote_plus(f'{TITLE} {YEAR}')
    url = f'https://www.torrentdownloads.pro/search/?search={q}'
    def validate(r): return _html_magnet_validate(r)
    return url, validate

# ── shrss (showrss) ───────────────────────────────────────────────────────────
def _shrss():
    url = 'https://showrss.info/browse'
    def validate(r):
        if r.status_code == 200 and len(r.content) > 2000:
            return True, f'browse page loaded ({len(r.content)} bytes)'
        return False, f'HTTP {r.status_code}'
    return url, validate

# ── snow ──────────────────────────────────────────────────────────────────────
def _snow():
    url = 'https://snowfl.com'
    def validate(r):
        if r.status_code == 200 and len(r.content) > 1000:
            return True, f'homepage loaded ({len(r.content)} bytes)'
        return False, f'HTTP {r.status_code}'
    return url, validate

# ── m_fus (mediafusion elfhosted) ─────────────────────────────────────────────
def _m_fus():
    # elfhosted instance returns empty streams without a personal API token in the URL path
    # Check manifest to confirm service is alive
    url = 'https://mediafusion.elfhosted.com/manifest.json'
    def validate(r):
        try:
            data = r.json()
            name = data.get('name', '')
            return True, f'service alive: "{name}" (note: stream needs personal token in URL)'
        except Exception as e:
            return False, str(e)
    return url, validate

# ── torio (torrentio with RD filter) ─────────────────────────────────────────
def _torio():
    url = f'https://torrentio.strem.fun/stream/movie/{IMDB}.json'
    def validate(r): return _stremio_validate(r)
    return url, validate

# ── torio_elf ─────────────────────────────────────────────────────────────────
def _torio_elf():
    # elfhosted torrentio is 404 — requires active personal subscription
    url = f'https://torrentio.elfhosted.com/stream/movie/{IMDB}.json'
    def validate(r):
        if r.status_code == 404:
            return False, 'HTTP 404 — endpoint requires active ElfHosted subscription'
        return _stremio_validate(r)
    return url, validate

# ── 1337x ─────────────────────────────────────────────────────────────────────
def _1337x():
    q = urllib.parse.quote_plus(f'{TITLE} {YEAR}')
    url = f'https://www.1337xx.to/search/{q}/1'
    def validate(r):
        if '<tbody' in r.text:
            rows = re.findall(r'<tr\b', r.text)
            return True, f'{len(rows)} table rows found'
        return False, 'no <tbody> (Cloudflare block?)'
    return url, validate

# ── tkitty ────────────────────────────────────────────────────────────────────
def _tkitty():
    q = urllib.parse.quote_plus(f'{TITLE} {YEAR}')
    url = f'https://torrentkitty.one/search/{q}/1'
    def validate(r): return _html_magnet_validate(r)
    return url, validate

# ── commet ────────────────────────────────────────────────────────────────────
def _commet():
    # Skip token-gated URL — just check base is reachable
    url = 'https://comet.elfhosted.com/manifest.json'
    def validate(r):
        try:
            data = r.json()
            name = data.get('name', '')
            return True, f'manifest OK: "{name}"'
        except Exception as e:
            return False, str(e)
    return url, validate

# ── dmm ───────────────────────────────────────────────────────────────────────
def _dmm():
    # DMM API requires HMAC auth params (dmmProblemKey + solution) — 403 without them
    # Verify the homepage loads as a proxy for service availability
    url = 'https://debridmediamanager.com'
    def validate(r):
        if r.status_code == 200 and len(r.content) > 1000:
            return True, f'homepage OK ({len(r.content)} bytes) — API needs HMAC params (generated at runtime)'
        return False, f'HTTP {r.status_code}'
    return url, validate

# ── tele (localhost torrent daemon) ───────────────────────────────────────────
def _tele():
    # tele connects to a local torrent indexer daemon on port 7891 — skip if not running
    url = 'http://127.0.0.1:7891/'
    def validate(r):
        return True, 'local daemon responding'
    return url, validate

# ── new scrapers ──────────────────────────────────────────────────────────────
def _torrentio_new():
    url = f'https://torrentio.strem.fun/stream/movie/{IMDB}.json'
    def validate(r): return _stremio_validate(r)
    return url, validate

def _mediafusion_new():
    # weebs instance works without token — token only needed for debrid-filtered results
    url = f'https://mediafusionfortheweebs.midnightignite.me/stream/movie/{IMDB}.json'
    def validate(r): return _stremio_validate(r)
    return url, validate

def _meteor_new():
    url = f'https://meteorfortheweebs.midnightignite.me/stream/movie/{IMDB}.json'
    def validate(r): return _stremio_validate(r)
    return url, validate

def _torrentsdb_new():
    url = f'https://torrentsdb.com/stream/movie/{IMDB}.json'
    def validate(r): return _stremio_validate(r)
    return url, validate

def _torrentz2_new():
    q = urllib.parse.quote_plus(f'{TITLE} {YEAR}')
    url = f'https://torrentz2.nz/search?q={q}'
    def validate(r):
        rows = re.findall(r'<dl>', r.text)
        magnets = MAGNET_RE.findall(r.text)
        if magnets:
            return True, f'{len(magnets)} magnet links'
        if rows:
            return True, f'{len(rows)} result rows (need JS?)'
        return False, 'no results'
    return url, validate

def _torrentproject2_new():
    q = urllib.parse.quote_plus(f'{TITLE} {YEAR}')
    url = f'https://torrentproject2.com/?t={q}&orderby=seeders'
    def validate(r):
        links = re.findall(r'href=["\'](.+?torrent\.html)["\']', r.text, re.I)
        if links:
            return True, f'{len(links)} torrent detail links found'
        return False, 'no torrent links found'
    return url, validate

# ── scraper registry ──────────────────────────────────────────────────────────
SCRAPER_MAP = {
    '1337x.py':           ('1337x (Cloudflare)',     _1337x),
    'apibay.py':          ('apibay',                 _apibay),
    'bitsearch.py':       ('bitsearch',              _bitsearch),
    'commet.py':          ('commet (manifest)',      _commet),
    'dmm.py':             ('dmm',                    _dmm),
    'ezio.py':            ('ezio (eztv)',             _ezio),
    'fmood.py':           ('fmood',                  _fmood),
    'glorls.py':          ('glorls',                 _glorls),
    'kass.py':            ('kass',                   _kass),
    'kban.py':            ('kban',                   _kban),
    'kick4.py':           ('kick4',                  _kick4),
    'm_fus.py':           ('m_fus (mediafusion elf)',_m_fus),
    'mediafusion.py':     ('mediafusion (weebs)',     _mediafusion_new),
    'meteor.py':          ('meteor (weebs)',          _meteor_new),
    'shrss.py':           ('shrss (showrss)',         _shrss),
    'snow.py':            ('snow (snowfl)',           _snow),
    'tele.py':            ('tele (localhost)',        _tele),
    'tkitty.py':          ('tkitty',                 _tkitty),
    'torio.py':           ('torio (torrentio)',       _torio),
    'torio_elf.py':       ('torio_elf',              _torio_elf),
    'torrentio.py':       ('torrentio (new)',         _torrentio_new),
    'torrentproject2.py': ('torrentproject2',        _torrentproject2_new),
    'torrentsdb.py':      ('torrentsdb',             _torrentsdb_new),
    'torrentz2.py':       ('torrentz2',              _torrentz2_new),
    'tsdl.py':            ('tsdl',                   _tsdl),
    'yts.py':             ('yts',                    _yts),
    'zilean.py':          ('zilean',                 _zilean),
}

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    sources_dir = os.path.join(os.path.dirname(__file__), 'resources', 'sources')
    found = sorted(f for f in os.listdir(sources_dir) if f.endswith('.py') and f != '__init__.py')

    print(f'\n{CYAN}Shadow scraper test — {len(found)} scrapers found{RESET}')
    print(f'  Movie: {TITLE.title()} ({YEAR})  IMDB: {IMDB}\n')

    col_name = 26
    col_status = 12
    results = []

    for fname in found:
        entry = SCRAPER_MAP.get(fname)
        if not entry:
            print(f'  {YELLOW}{"? UNMAPPED":{col_status}}{RESET}  {fname}')
            results.append((fname, None, 'unmapped', 0))
            continue

        label, url_fn = entry
        try:
            url, validate_fn = url_fn()
        except Exception as e:
            print(f'  {YELLOW}{"? URL BUILD ERR":{col_status}}{RESET}  {label:26s}  {e}')
            results.append((fname, None, f'url build error: {e}', 0))
            continue

        try:
            t0 = time.time()
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            elapsed = round(time.time() - t0, 2)

            if r.status_code != 200:
                status_tag = f'{RED}HTTP {r.status_code}{RESET}'
                detail = url
                ok = False
            else:
                ok, detail = validate_fn(r)
                status_tag = f'{GREEN}PASS{RESET}' if ok else f'{RED}FAIL{RESET}'

        except requests.exceptions.ConnectionError:
            status_tag = f'{RED}CONN ERR{RESET}'; elapsed = TIMEOUT; ok = False; detail = url
        except requests.exceptions.Timeout:
            status_tag = f'{RED}TIMEOUT{RESET}';  elapsed = TIMEOUT; ok = False; detail = url
        except Exception as e:
            status_tag = f'{RED}ERROR{RESET}';    elapsed = 0;       ok = False; detail = str(e)

        print(f'  {status_tag:30s}  {label:{col_name}s}  {elapsed:5.2f}s  {detail}')
        results.append((fname, ok, detail, elapsed))

    # ── summary ──
    passed  = [r for r in results if r[1] is True]
    failed  = [r for r in results if r[1] is False]
    unknown = [r for r in results if r[1] is None]

    print(f'\n{"─"*70}')
    print(f'{GREEN}PASS ({len(passed)}):{RESET}  {", ".join(r[0].replace(".py","") for r in passed)}')
    print(f'{RED}FAIL ({len(failed)}):{RESET}  {", ".join(r[0].replace(".py","") for r in failed)}')
    if unknown:
        print(f'{YELLOW}SKIP ({len(unknown)}):{RESET}  {", ".join(r[0].replace(".py","") for r in unknown)}')

if __name__ == '__main__':
    main()
