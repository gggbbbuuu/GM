# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import os
import sys
import re
from six.moves import urllib_parse

from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError


# Cloudflare Worker proxy endpoint (CapSolver API key is stored securely in Worker environment)
PROXY_ENDPOINT = 'https://anacon-token-proxy.twilight0.workers.dev'
PROXY_SIGNATURE = 'alivegr-proxy-auth-987234'


_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from plugin_settings import plugin_enabled

class AnaconResolver(ResolveUrl):

    name = 'anacon'
    domains = ['anacon.org', 'lakatamia.tv']
    pattern = r'(?://|\.)(anacon\.org|lakatamia\.tv)/app/chans/(?:gr|cy)/([a-zA-Z0-9_\-]+(?:image|img|cyprus|greece)?\.php)'

    # File-backed resolve cache (ResolveURL's own): the minted WMSAuth token
    # is valid ~20 minutes, so 0.25h keeps replays/zaps/retries on one token
    # instead of re-minting (and re-hitting the edge) every play. No-op when
    # the host addon's use_cache setting is off.
    @common.cache.cache_method(cache_limit=0.25)
    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)

        # Step 1: Request Turnstile token from secure Cloudflare Worker proxy via self.net
        try:
            proxy_headers = {
                'Content-Type': 'application/json',
                'X-Client-Signature': PROXY_SIGNATURE
            }
            proxy_res = self.net.http_POST(
                PROXY_ENDPOINT,
                form_data={'url': web_url},
                headers=proxy_headers,
                jdata=True,
                timeout=30
            )
            data = proxy_res.json
            if not data or data.get('status') != 'ok':
                err_msg = data.get('error', 'Unknown error') if isinstance(data, dict) else 'Invalid proxy response'
                raise ResolverError(f"Turnstile proxy error: {err_msg}")

            token = data.get('token')
            user_agent = data.get('userAgent') or common.RAND_UA
        except Exception as e:
            raise ResolverError(f"Turnstile resolution failed: {e}")

        # Step 2: POST solved token to target PHP page via self.net
        target_name = media_id.replace('image.php', '.php').replace('img.php', '.php')
        post_url = urllib_parse.urljoin(web_url, target_name)

        post_headers = {
            'User-Agent': user_agent,
            'Referer': web_url,
            'Origin': f"https://{host}"
        }
        post_data = {
            'cf-turnstile-response': token
        }

        try:
            resp = self.net.http_POST(post_url, form_data=post_data, headers=post_headers, timeout=15)
            html = resp.content
        except Exception as e:
            raise ResolverError(f"Failed to submit token to {post_url}: {e}")

        # Step 3: Extract the fresh signed Wowza/Nimble stream URL
        stream_match = re.search(r'https?://s\d?\.cystream\.net/live/[^\s\'\"<]+', html)
        if not stream_match:
            stream_match = re.search(r'(https?://[^\s\'\"<]+\.m3u8[^\s\'\"<]*)', html)

        if stream_match:
            stream_url = stream_match.group(0).replace('\\', '')
            stream_headers = {'User-Agent': user_agent}
            return stream_url + helpers.append_headers(stream_headers)

        raise ResolverError("Could not extract playable stream URL from Anacon response")

    def get_url(self, host, media_id):
        region = 'cy' if 'cy' in media_id.lower() else 'gr'
        return f"https://{host}/app/chans/{region}/{media_id}"

    @classmethod
    def _is_enabled(cls):
        return plugin_enabled('AnaconResolver')
