# -*- coding: utf-8 -*-

'''
    Skai Player Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

# Playback resolution is delegated to ResolveURL, using the SkaiResolver
# from PluginsGR. That resolver targets the current site (live m3u8,
# episode/show media_item_file through the videostream player, YouTube
# embeds through YouTubeGR), so the add-on only has to hand over the
# video page url. Radio episodes resolve straight to their mp3.
import inspect

from resolveurl import add_plugin_dirs
from resolveurl.hmf import HostedMediaFile
from tulip import kodi
from tulip.log import log

from .constants import PLUGINS_PATH


def _plugins_registered():

    add_plugin_dirs(kodi.transPath(PLUGINS_PATH))


def resolve(url, subs=True):
    """
    Returns (stream, subtitles) for a video page url.

    ``subtitles`` is a list of {'url', 'lang'} dicts, or an empty list.
    """

    _plugins_registered()

    hmf = HostedMediaFile(url)

    if not hmf.valid_url():
        raise ValueError('No resolver handles {}'.format(url))

    subtitle_list = []
    last_error = ''

    for resolver in hmf.get_resolvers(validated=True):
        try:
            host, media_id = resolver.get_host_and_id(url)
            spec = inspect.getfullargspec(resolver.get_media_url)
            wanted = 'subs' in (spec.args or []) + (spec.kwonlyargs or [])

            if wanted:
                result = resolver.get_media_url(host, media_id, subs=subs)
            else:
                result = resolver.get_media_url(host, media_id)

            if isinstance(result, (tuple, list)):
                stream = result[0]
                if len(result) > 1 and result[1]:
                    subtitle_list = _normalize_subs(result[1])
            else:
                stream = result

            if stream:
                log('Resolved with {0}: {1}'.format(getattr(resolver, 'name', resolver), url))
                return stream, subtitle_list

        except Exception as e:
            last_error = str(e) or e.__class__.__name__
            log('Resolver {0} failed: {1}'.format(getattr(resolver, 'name', resolver), e))
            continue

    raise ValueError(last_error or 'No resolver produced a stream for {}'.format(url))


def _normalize_subs(raw):

    """ResolveURL resolvers return either {'lang': url} or a list of dicts."""

    out = []

    if isinstance(raw, dict):
        raw = [{'lang': lang, 'url': value} for lang, value in raw.items()]

    for entry in raw or []:
        if isinstance(entry, dict) and entry.get('url'):
            out.append({'url': entry['url'], 'lang': entry.get('lang') or 'Greek'})
        elif isinstance(entry, str):
            out.append({'url': entry, 'lang': 'Greek'})

    return out
