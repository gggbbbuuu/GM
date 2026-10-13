# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.

    Instagram resolver. Meta serves no media data anonymously (oEmbed is
    token-gated, pages serve a static login wall), so every path needs a
    user session. Cookies come per-call (the consumer addon passes a file
    location) with the `instagram_cookies` setting as fallback. Supported
    file formats: Netscape/cURL cookie files and JSON (list of
    {name,value} objects or plain {name:value} dicts); a raw Cookie header
    string is also accepted.
'''

import json
import os
import re
import sys
from resolveurl.resolver import ResolveUrl, ResolverError

try:
    import xbmcaddon
except ImportError:
    xbmcaddon = None

try:
    import xbmcgui
except ImportError:
    xbmcgui = None

ADDON_ID = 'script.module.resolveurl.pluginsgr'

APP_ID = '936619743392459'
APP_ID_IOS = '124024574287414'
UA_WEB = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
          '(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36')
UA_IPHONE = ('Instagram 361.0.0.35.82 (iPad13,8; iOS 18_0; en_US; en-US; '
             'scale=2.00; 2048x2732; 674117118) AppleWebKit/420+')
DOC_ID = '27128499623469141'

_SHORTCODE_RES = (
    r'instagram\.com/p/([A-Za-z0-9_-]+)',
    r'instagram\.com/reel/([A-Za-z0-9_-]+)',
    r'instagram\.com/tv/([A-Za-z0-9_-]+)',
    r'instagr\.am/p/([A-Za-z0-9_-]+)',
    r'instagr\.am/reel/([A-Za-z0-9_-]+)',
)

_SHORTCODE_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'

_SETTING_COOKIES = 'instagram_cookies'
_SETTING_CAROUSEL = 'instagram_carousel_select'


def _setting_cookies_path():
    return get_setting(_SETTING_COOKIES, '')


def _item_area(item):
    '''Pixel area of a collected item, from the size hint in its thumb URL
    (s1080x1350/p640x640). 0 when the URL carries no hint.'''
    thumb = item.get('thumb') or ''
    match = re.search(r'[sp](\d+)x(\d+)', thumb)
    if not match:
        return 0
    return int(match.group(1)) * int(match.group(2))


def load_cookies(source):
    '''Load session cookies from a file location or a raw Cookie string.

    Returns a {name: value} dict (possibly empty). Never raises.
    '''
    if not source:
        return {}
    if isinstance(source, dict):
        return {str(k): str(v) for k, v in source.items()}
    text = ''
    if os.path.exists(source):
        try:
            with open(source, 'r', encoding='utf-8') as f:
                text = f.read()
        except (OSError, UnicodeError):
            return {}
    else:
        text = source
    text = text.strip()
    if not text:
        return {}
    # JSON: [{name,value}, ...] or {name: value, ...}.
    if text[:1] in '{[':
        try:
            data = json.loads(text)
        except ValueError:
            return {}
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
        jar = {}
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict) and entry.get('name') is not None:
                    jar[str(entry['name'])] = str(entry.get('value', ''))
        return jar
    # Netscape / cURL cookie file.
    jar = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) >= 7:
            jar[parts[5]] = parts[6]
        elif '=' in line and ' ' not in line.split('=', 1)[0]:
            # Raw "Cookie" header fallback: name=value pairs.
            for pair in line.split(';'):
                pair = pair.strip()
                if '=' in pair:
                    name, _, value = pair.partition('=')
                    jar[name.strip()] = value.strip()
    return jar


def _shortcode_to_media_id(shortcode):
    media_id = 0
    for char in shortcode:
        idx = _SHORTCODE_ALPHABET.find(char)
        if idx == -1:
            return None
        media_id = media_id * 64 + idx
    return str(media_id)


_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from plugin_settings import get_setting, plugin_enabled

class InstagramResolver(ResolveUrl):
    name = 'Instagram'
    domains = ['instagram.com', 'instagr.am']
    pattern = r'(?://|\.)(instagram\.com|instagr\.am)/(?:p|reel|tv)/([A-Za-z0-9_-]+)'

    def get_media_url(self, host, media_id, subs=False, cookies=None):
        jar = load_cookies(cookies) or load_cookies(_setting_cookies_path())

        shortcode = media_id

        # 1. GraphQL (public + authenticated media alike, when it answers).
        url = self._fetch_graphql(shortcode, jar)
        if url:
            return self._result(url, subs)

        # 2. iPhone v1 API (authenticated posts only).
        if jar:
            url = self._fetch_iphone(shortcode, jar)
            if url:
                return self._result(url, subs)

        # 3. Embed page scrape (last resort).
        url = self._fetch_embed(shortcode, jar)
        if url:
            return self._result(url, subs)

        if not jar:
            # Without a session cookie every endpoint above is anonymous,
            # so this is by far the likeliest cause: say so plainly instead
            # of the generic failure.
            raise ResolverError(
                'Instagram requires cookies to view this post. '
                'Set them via the cookies parameter or the plugin setting.')
        raise ResolverError('Could not extract media from Instagram post.')

    @staticmethod
    def _result(url, subs):
        if subs:
            return url, {}
        return url

    def _graphql_headers(self, jar, csrf_token=''):
        headers = {
            'User-Agent': UA_WEB,
            'x-ig-app-id': APP_ID,
            'x-requested-with': 'XMLHttpRequest',
            'Referer': 'https://www.instagram.com/',
        }
        if csrf_token:
            headers['x-csrftoken'] = csrf_token
        if jar:
            headers['Cookie'] = '; '.join(
                ['ig_pr=1', 'ig_vw=1920', 'ig_cb=1']
                + [f'{k}={v}' for k, v in jar.items()])
        return headers

    def _fetch_graphql(self, shortcode, jar):
        form = {
            'variables': json.dumps({
                'shortcode': shortcode,
                '__relay_internal__pv__PolarisAIGMMediaWebLabelEnabledrelayprovider': False,
            }),
            'doc_id': DOC_ID,
            'server_timestamps': 'true',
        }
        try:
            resp = self.net.http_POST(
                'https://www.instagram.com/graphql/query/', form_data=form,
                headers=self._graphql_headers(jar, jar.get('csrftoken', '')))
            data = resp.json
        except Exception:
            return None
        if not isinstance(data, dict) or ('errors' in data and not data.get('data')):
            return None
        items = (data.get('data') or {}).get(
            'xdt_api__v1__media__shortcode__web_info', {}).get('items', [])
        if not items:
            return None
        choice = self._choose_media(self._collect_media(items[0]))
        return choice['url'] if choice else None

    def _fetch_iphone(self, shortcode, jar):
        media_id = _shortcode_to_media_id(shortcode)
        if not media_id:
            return None
        headers = {
            'User-Agent': UA_IPHONE,
            'x-ig-app-id': APP_ID_IOS,
            'x-ig-www-claim': '0',
            'Cookie': '; '.join(f'{k}={v}' for k, v in jar.items()),
        }
        try:
            resp = self.net.http_GET(
                f'https://www.instagram.com/api/v1/media/{media_id}/info/',
                headers=headers)
            data = resp.json
        except Exception:
            return None
        if not isinstance(data, dict):
            return None
        items = data.get('items', [])
        if not items:
            return None
        choice = self._choose_media(self._collect_media(items[0]))
        return choice['url'] if choice else None

    def _fetch_embed(self, shortcode, jar):
        headers = {'User-Agent': UA_WEB}
        if jar:
            headers['Cookie'] = '; '.join(f'{k}={v}' for k, v in jar.items())
        for path in ('/p/', '/reel/'):
            try:
                resp = self.net.http_GET(
                    f'https://www.instagram.com{path}{shortcode}/embed/',
                    headers=headers)
                html = resp.content
            except Exception:
                continue
            if not isinstance(html, str):
                continue
            for found in re.findall(r'"video_url"\s*:\s*"([^"]+)"', html):
                url = found.replace('\\/', '/').replace('\\u0026', '&')
                if url.startswith('http'):
                    return url
            img_urls = []
            for found in re.findall(r'"display_url"\s*:\s*"([^"]+)"', html):
                url = found.replace('\\/', '/').replace('\\u0026', '&')
                if url not in img_urls:
                    img_urls.append(url)
            best = InstagramResolver._largest_embed_url(img_urls)
            if best:
                return best
        return None

    @staticmethod
    def _largest_image(candidates):
        '''Full-size photo: largest by pixel area, first as fallback.'''
        best, best_area = None, -1
        for cand in candidates:
            if not isinstance(cand, dict) or not cand.get('url'):
                continue
            try:
                area = int(cand.get('width', 0)) * int(cand.get('height', 0))
            except (TypeError, ValueError):
                area = 0
            if best is None or area > best_area:
                best, best_area = cand['url'], area
        return best

    @staticmethod
    def _largest_embed_url(urls):
        '''Same idea from bare URLs: size hints like s1080x1350/p640x640.'''
        import re as _re

        def area(url):
            match = _re.search(r'[sp](\d+)x(\d+)', url)
            if not match:
                return -1
            return int(match.group(1)) * int(match.group(2))

        best, best_area = None, -1
        for url in urls:
            if url.startswith('http') and area(url) >= best_area:
                best, best_area = url, area(url)
        return best or (urls[0] if urls and urls[0].startswith('http') else None)

    @staticmethod
    def _collect_media(node):
        '''Flatten a media node into choosable items with thumbnails.

        Returns [{url, thumb, label, is_video}]: video children first
        (playback-first ordering), then photos at full size.
        '''
        videos, photos = [], []

        def _photo_entries(item, index):
            cands = [c for c in
                     item.get('image_versions2', {}).get('candidates', [])
                     if isinstance(c, dict) and c.get('url')]
            if not cands:
                return

            def _area(cand):
                try:
                    return int(cand.get('width', 0)) * int(cand.get('height', 0))
                except (TypeError, ValueError):
                    return 0

            ordered = sorted(cands, key=_area, reverse=True)
            full = ordered[0]['url']
            thumb = ordered[-1]['url']
            width = ordered[0].get('width')
            height = ordered[0].get('height')
            if width and height:
                label = f'Photo {index} ({width}x{height})'
            else:
                label = f'Photo {index}'
            photos.append({'url': full, 'thumb': thumb, 'label': label,
                           'is_video': False})

        def _video_entries(item, index):
            versions = item.get('video_versions', [])
            if not versions or not versions[0].get('url'):
                return
            thumbs = [c.get('url') for c in
                      item.get('image_versions2', {}).get('candidates', [])
                      if isinstance(c, dict) and c.get('url')]
            videos.append({'url': versions[0]['url'],
                           'thumb': thumbs[0] if thumbs else None,
                           'label': f'Video {index}',
                           'is_video': True})

        if isinstance(node, dict):
            if node.get('media_type') == 8:
                children = node.get('carousel_media') or node.get('children', [])
                for pos, child in enumerate(children, 1):
                    if not isinstance(child, dict):
                        continue
                    if child.get('media_type') == 2:
                        _video_entries(child, pos)
                    else:
                        _photo_entries(child, pos)
            elif node.get('media_type') == 2:
                _video_entries(node, 1)
            else:
                _photo_entries(node, 1)
        return videos + photos

    @staticmethod
    def _choose_media(items):
        '''Single item returns directly; multiples go through a thumbnail
        select dialog.

        Honours instagram_carousel_select:
          'ask'    (default) show the dialog
          'first'  always take the first entry, no dialog
          'largest'always take the highest-resolution entry, no dialog
        '''
        if len(items) == 1:
            return items[0]
        mode = get_setting(_SETTING_CAROUSEL, 'ask').strip().lower()
        if mode == 'first':
            return items[0]
        if mode == 'largest':
            return max(items, key=_item_area)
        if xbmcgui is None:
            return items[0]
        listitems = []
        for item in items:
            listitem = xbmcgui.ListItem(label=item['label'])
            if item.get('thumb'):
                listitem.setArt({'thumb': item['thumb'], 'icon': item['thumb']})
            listitems.append(listitem)
        dialog = xbmcgui.Dialog()
        index = dialog.select('Select media', listitems, useDetails=True)
        if index is None or index < 0:
            raise ResolverError('No media selected.')
        return items[index]

    def get_url(self, host, media_id):
        return self._default_get_url(host, media_id, template='https://www.instagram.com/reel/{media_id}/')

    @classmethod
    def _is_enabled(cls):
        return plugin_enabled('InstagramResolver')

    @classmethod
    def _get_priority(cls):

        return 80
