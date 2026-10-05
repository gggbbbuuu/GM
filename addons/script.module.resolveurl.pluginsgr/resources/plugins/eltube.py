# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re
from six.moves import urllib_error, urllib_parse, urllib_request
from resolveurl import common
from resolveurl.lib import helpers
from resolveurl.resolver import ResolveUrl, ResolverError


class EltubeResolver(ResolveUrl):
    """Resolves eltube.gr watch pages that carry a DIRECT playback source.

    When an eltube page merely wraps a third-party host (dailymotion,
    voe.sx, ...) the embedded URL is handed back to ResolveURL dispatch
    (`resolveurl.resolve`), which automatically selects the owning plugin
    by priority. Only if nothing can resolve it do we raise, telling the
    scraper which host the title belongs to.

    Resolution path for eltube-hosted media:
        embed.php  ->  JS player.src([{src: ".../videos.php?vid=...", ...}])
                    ->  videos.php answers 302 to the real file
    """

    name = 'eltube'
    domains = ['eltube.gr']
    pattern = r'(?://|\.)(eltube\.gr)/(?:watch\.php\?vid=|embed\.php\?vid=)([0-9a-zA-Z]+)'

    def get_media_url(self, host, media_id):

        headers = {'User-Agent': common.RAND_UA}
        watch_url = self.get_url(host, media_id)
        res = self.net.http_GET(watch_url, headers=headers).content

        # If eltube only iframes somebody else, let ResolveURL dispatch it
        # to the owning plugin automatically (priority order, user settings
        # honoured). Lazy import: runs at resolve time, after all plugins
        # are loaded, so no load-order issues.
        import resolveurl
        for src in re.findall(r'''<iframe[^>]*src=["']([^"']+)''', res, re.I):
            if 'eltube.gr' not in src:
                if src.startswith('//'):
                    src = 'https:' + src
                resolved = resolveurl.resolve(src)
                if resolved:
                    return resolved
                netloc = urllib_parse.urlparse(src).netloc
                raise ResolverError(
                    'eltube only mirrors this title from %s - record it as a '
                    '%s stream instead of an eltube one.' % (netloc, netloc))

        # eltubе-hosted: the embed page carries the real source in JS
        embed_url = 'https://www.eltube.gr/embed.php?vid=%s' % media_id
        embed = self.net.http_GET(embed_url, headers=headers).content
        match = re.search(r'''player\.src\(\[\{\s*src:\s*["']([^"']+)["']''', embed)

        if not match:
            raise ResolverError('Video not found')

        stream = match.group(1).replace('\\/', '/')
        if 'videos.php' in stream:
            # 302 -> the real file; resolve the Location without downloading it
            target = self._redirect_target(stream, headers)
            if target:
                stream = target

        return stream + helpers.append_headers(headers)

    def _redirect_target(self, url, headers):
        """Location header of the first 30x, without pulling the body."""
        class _NoRedirect(urllib_request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                raise urllib_error.HTTPError(req.full_url, code, msg, headers, fp)

        opener = urllib_request.build_opener(_NoRedirect)
        try:
            with opener.open(urllib_request.Request(url, headers=headers), timeout=20):
                return None
        except urllib_error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                location = exc.headers.get('Location')
                return urllib_parse.urljoin(url, location) if location else None
        return None

    def get_url(self, host, media_id):

        return self._default_get_url(host, media_id, template='https://www.{host}/watch.php?vid={media_id}')

    @classmethod
    def _is_enabled(cls):
        return True