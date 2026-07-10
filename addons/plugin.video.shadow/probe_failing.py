"""
Probe failing scrapers to understand their actual response format.
Run from shadow addon root: python probe_failing.py
"""
import requests, re, json

H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'}
IMDB = 'tt0111161'

def probe(label, url, show_bytes=400):
    print(f'\n{"="*60}')
    print(f'  {label}')
    print(f'  {url}')
    try:
        r = requests.get(url, headers=H, timeout=10, allow_redirects=True)
        print(f'  HTTP {r.status_code}  ({len(r.content)} bytes)')
        sample = r.text[:show_bytes]
        print(f'  {sample}')
    except Exception as e:
        print(f'  ERROR: {e}')

# bitsearch - what does the HTML actually look like?
probe('bitsearch', 'https://bitsearch.to/search?q=shawshank+1994&category=1', 600)

# ezio - eztv is TV only, test with a TV show IMDB (GoT)
probe('ezio (TV show GoT)', 'https://eztv.re/api/get-torrents?imdb_id=944947&limit=5&page=0', 400)

# zilean - check both endpoints
probe('zilean weebs - movie', f'https://zileanfortheweebs.midnightignite.me/search/movie/imdb/{IMDB}', 400)
probe('zilean weebs - series', f'https://zileanfortheweebs.midnightignite.me/search/series/imdb/{IMDB}/1/1', 400)
probe('zilean stremio.ru - movie', f'https://zilean.stremio.ru/search/movie/imdb/{IMDB}', 400)

# mediafusion - without token (should fail) vs weebs with no path
probe('mediafusion weebs no-token', 'https://mediafusionfortheweebs.midnightignite.me/stream/movie/tt0111161.json', 400)
probe('mediafusion weebs manifest', 'https://mediafusionfortheweebs.midnightignite.me/manifest.json', 400)

# m_fus elfhosted - what does it return?
probe('m_fus elfhosted manifest', 'https://mediafusion.elfhosted.com/manifest.json', 400)
probe('m_fus elfhosted no-token stream', f'https://mediafusion.elfhosted.com/stream/movie/{IMDB}.json', 400)

# torio_elf - check if endpoint moved
probe('torio_elf old URL', f'https://torrentio.elfhosted.com/stream/movie/{IMDB}.json', 300)
probe('torio_elf no-slash', f'https://torrentio.elfhosted.com/stream/movie/{IMDB}.json', 300)
