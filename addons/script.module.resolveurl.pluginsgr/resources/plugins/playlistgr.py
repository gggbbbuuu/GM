# -*- coding: utf-8 -*-

'''
    PluginsGR Module
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import json
import re

from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError


class PlaylistGRResolver(ResolveUrl):

    name = 'PlaylistGR'
    domains = ['playlist.gr']
    pattern = r'(?://|\.)(playlist\.gr)/(?:ajax\.php\?action=get_video&id=|\?id=)([\w-]+)'

    def get_host_and_id(self, url):
        m = re.search(self.pattern, url)
        if m:
            return m.group(1), m.group(2)
        return False

    def get_media_url(self, host, media_id, subs=False, audio_only=False):

        headers = {'User-Agent': common.RAND_UA}
        web_url = self.get_url(host, media_id)
        res = self.net.http_GET(web_url, headers=headers).content

        try:
            data = json.loads(res)
            html = data.get('html', res)
        except Exception:
            html = res

        m = re.search(r'''(?:src|href)=["'](?:https?:)?//(?:www\.)?youtube\.com/(?:embed/|watch\?v=)([\w-]+)''', html)
        if m:
            yt_url = f'https://www.youtube.com/watch?v={m.group(1)}'
            if audio_only:
                import inspect
                from resolveurl.hmf import HostedMediaFile
                hmf = HostedMediaFile(yt_url)
                if hmf.valid_url():
                    for r in hmf.get_resolvers(validated=True):
                        if hasattr(r, 'get_media_url'):
                            spec = inspect.getfullargspec(r.get_media_url)
                            if 'audio_only' in (spec.args or []) or 'audio_only' in (spec.kwonlyargs or []):
                                h, mid = r.get_host_and_id(yt_url)
                                return r.get_media_url(h, mid, subs=subs, audio_only=True)
            import resolveurl
            return resolveurl.resolve(yt_url)

        for src in re.findall(r'''(?:src|href)=["']((?:https?:)?//[^\s"']+)''', html, re.I):
            if src.startswith('//'):
                src = 'https:' + src
            if 'playlist.gr' in src:
                continue
            import resolveurl
            resolved = resolveurl.resolve(src)
            if resolved:
                if subs and not isinstance(resolved, tuple):
                    return resolved, {}
                return resolved

        raise ResolverError('No playable video found.')

    def get_url(self, host, media_id):

        return 'https://playlist.gr/ajax.php?action=get_video&id={0}'.format(media_id)

    @classmethod
    def _is_enabled(cls):
        return True
