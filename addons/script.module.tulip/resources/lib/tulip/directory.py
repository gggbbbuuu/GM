# -*- coding: utf-8 -*-

'''
    Tulip library
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import json
from urllib.parse import parse_qsl, urlencode, quote_plus
from tulip.utils import iteritems, convert_to_bool
from tulip import kodi
from tulip.log import log


# Listing entry-dict contract (Listing.add + builder flat dicts):
# Keys (all optional except label/title): label|title (str or int i18n id),
# image/icon/thumb/poster/banner/fanart/clearlogo/clearart, artwork (dict, wins
# over individual art keys), info (dict of infoLabels), meta (dict, merged into
# infoLabels), streaminfo (dict -> addStreamInfo/stream detail),
# cm (list of (title, query) tuples; title int->i18n else str, query dict->urlencode
# or str; becomes (label, 'RunPlugin(sysaddon?query)')),
# query (raw str appended to url), isFolder (bool, default True),
# isPlayable (bool; sets IsPlayable property and forces isFolder False),
# fanart_property (bool, default True sets Fanart_Image property),
# properties (dict of setProperty calls).
# Normalization (_normalize_meta): drops values == '0'; poster resolved with
# priority poster3 > poster2 > poster (poster2/3 keys removed afterwards);
# fanart2 overrides fanart (fanart2 key removed). int labels via kodi.i18n.


def _normalize_meta(meta):

    if not meta:
        return {}

    normalized = dict((k, v) for k, v in iteritems(meta) if not v == '0' or v is None)

    if normalized.get('poster3') not in (None, '', '0'):
        normalized['poster'] = normalized['poster3']
    elif normalized.get('poster2') not in (None, '', '0'):
        normalized['poster'] = normalized['poster2']

    for _key in ('poster2', 'poster3'):
        normalized.pop(_key, None)

    if normalized.get('fanart2') not in (None, '', '0'):
        normalized['fanart'] = normalized['fanart2']

    normalized.pop('fanart2', None)

    return normalized


def _set_info(item, meta, info_type):

    tag_set = False

    if info_type == 'video' and hasattr(item, 'getVideoInfoTag'):
        try:
            v_tag = item.getVideoInfoTag()
            if 'title' in meta:
                v_tag.setTitle(meta['title'])
            if 'originaltitle' in meta:
                v_tag.setOriginalTitle(meta['originaltitle'])
            if 'plot' in meta:
                v_tag.setPlot(meta['plot'])
            if 'plotoutline' in meta:
                v_tag.setPlotOutline(meta['plotoutline'])
            if 'tagline' in meta:
                v_tag.setTagLine(meta['tagline'])
            if 'genre' in meta:
                genres = meta['genre'] if isinstance(meta['genre'], list) else [meta['genre']]
                v_tag.setGenres(genres)
            if 'year' in meta and str(meta['year']).isdigit():
                v_tag.setYear(int(meta['year']))
            if 'premiered' in meta:
                v_tag.setPremiered(str(meta['premiered']))
            if 'duration' in meta and str(meta['duration']).isdigit():
                v_tag.setDuration(int(meta['duration']))
            if 'rating' in meta:
                try:
                    v_tag.setRating(float(meta['rating']))
                except (ValueError, TypeError):
                    pass
            if 'userrating' in meta:
                try:
                    v_tag.setUserRating(int(meta['userrating']))
                except (ValueError, TypeError):
                    pass
            if 'playcount' in meta and str(meta['playcount']).isdigit():
                v_tag.setPlaycount(int(meta['playcount']))
            if 'director' in meta:
                directors = meta['director'] if isinstance(meta['director'], list) else [meta['director']]
                v_tag.setDirectors(directors)
            if 'writer' in meta:
                writers = meta['writer'] if isinstance(meta['writer'], list) else [meta['writer']]
                v_tag.setWriters(writers)
            if 'cast' in meta and isinstance(meta['cast'], list):
                v_tag.setCast(meta['cast'])
            if 'studio' in meta:
                studios = meta['studio'] if isinstance(meta['studio'], list) else [meta['studio']]
                v_tag.setStudios(studios)
            if 'country' in meta:
                countries = meta['country'] if isinstance(meta['country'], list) else [meta['country']]
                v_tag.setCountries(countries)
            if 'mpaa' in meta:
                v_tag.setMpaa(str(meta['mpaa']))
            if 'season' in meta and str(meta['season']).isdigit():
                v_tag.setSeason(int(meta['season']))
            if 'episode' in meta and str(meta['episode']).isdigit():
                v_tag.setEpisode(int(meta['episode']))
            if 'tvshowtitle' in meta:
                v_tag.setTvShowTitle(meta['tvshowtitle'])
            if 'mediatype' in meta:
                v_tag.setMediaType(meta['mediatype'])
            if 'trailer' in meta:
                v_tag.setTrailer(meta['trailer'])
            tag_set = True
        except Exception:
            tag_set = False

    elif info_type in ('music', 'audio') and hasattr(item, 'getMusicInfoTag'):
        try:
            m_tag = item.getMusicInfoTag()
            if 'title' in meta:
                m_tag.setTitle(meta['title'])
            if 'artist' in meta:
                artists = meta['artist'] if isinstance(meta['artist'], list) else [meta['artist']]
                m_tag.setArtist(artists[0] if artists else '')
            if 'album' in meta:
                m_tag.setAlbum(meta['album'])
            if 'genre' in meta:
                genres = meta['genre'] if isinstance(meta['genre'], list) else [meta['genre']]
                m_tag.setGenre(genres[0] if genres else '')
            if 'year' in meta and str(meta['year']).isdigit():
                m_tag.setYear(int(meta['year']))
            if 'duration' in meta and str(meta['duration']).isdigit():
                m_tag.setDuration(int(meta['duration']))
            if 'tracknumber' in meta and str(meta['tracknumber']).isdigit():
                m_tag.setTrack(int(meta['tracknumber']))
            tag_set = True
        except Exception:
            tag_set = False

    if not tag_set:
        item.setInfo(type=info_type, infoLabels=meta)

    return tag_set


class Listing:

    """Incremental directory listing; entries flushed at once via finish()."""

    def __init__(self, argv=None):

        if argv is None:
            from tulip.init import sysaddon as _sysaddon, syshandle as _syshandle
            self.sysaddon = _sysaddon
            self.syshandle = _syshandle
        else:
            self.sysaddon = argv[0]
            self.syshandle = int(argv[1])

        self._items = []
        self.sysimage = kodi.addonInfo('icon')
        self.sysfanart = kodi.addonInfo('fanart')

    def add(self, action_or_url, entry=None):

        if entry is None:
            if isinstance(action_or_url, dict):
                action_or_url, entry = action_or_url, dict(action_or_url)
            else:
                entry = {}

        if isinstance(entry, dict):
            url_field = entry.pop('url', None)
            action_field = entry.pop('action', None)
            if url_field is not None:
                action_or_url = url_field
            elif action_field is not None and not (
                    isinstance(action_or_url, str) and ('://' in action_or_url or action_or_url.startswith('/'))):
                action_or_url = action_field

        label = entry.get('label', entry.get('title', ''))

        if isinstance(label, int):
            label = kodi.i18n(label)
        elif label is None:
            label = ''
        else:
            label = str(label)

        action_or_url = str(action_or_url)

        if '://' in action_or_url or action_or_url.startswith('/'):
            url = action_or_url
        else:
            url = '{0}?action={1}'.format(self.sysaddon, action_or_url)

        if entry.get('query'):
            raw_query = str(entry['query']).lstrip('?&')
            url = url + ('&' if '?' in url else '?') + raw_query

        fanart = entry.get('fanart', self.sysfanart)

        directory_item = kodi.item(label=label)

        if isinstance(entry.get('artwork'), dict):
            directory_item.setArt(dict(entry['artwork']))
        else:
            image = entry.get('image')
            icon = entry.get('icon', image)
            thumb = entry.get('thumb', image)
            poster = entry.get('poster', image)
            banner = entry.get('banner', image)
            artwork = {}
            artwork['icon'] = icon if icon else self.sysimage
            if thumb:
                artwork['thumb'] = thumb
            if poster:
                artwork['poster'] = poster
            if banner:
                artwork['banner'] = banner
            if entry.get('clearlogo'):
                artwork['clearlogo'] = entry['clearlogo']
            if entry.get('clearart'):
                artwork['clearart'] = entry['clearart']
            artwork['fanart'] = fanart
            directory_item.setArt(artwork)

        info = dict(entry['info']) if isinstance(entry.get('info'), dict) else {}
        meta = _normalize_meta(entry['meta']) if isinstance(entry.get('meta'), dict) else {}
        combined = dict(meta)
        combined.update(info)

        if 'title' not in combined and label:
            combined['title'] = label

        info_type = entry.get('infotype', 'video')
        _set_info(directory_item, combined, info_type)

        cm_list = []

        for cm in entry.get('cm') or []:
            try:
                if isinstance(cm, dict):
                    cm_title = cm.get('title')
                    cm_query = cm.get('query')
                else:
                    cm_title, cm_query = cm
                if isinstance(cm_title, int):
                    cm_title = kodi.i18n(cm_title)
                else:
                    cm_title = str(cm_title)
                if isinstance(cm_query, dict):
                    try:
                        cm_query = urlencode(cm_query)
                    except Exception:
                        cm_query = urlencode(
                            dict((k, v.encode('utf-8') if isinstance(v, str) else v) for k, v in cm_query.items())
                        )
                else:
                    cm_query = str(cm_query).lstrip('?&')
                cm_list.append((cm_title, 'RunPlugin({0}?{1})'.format(self.sysaddon, cm_query)))
            except Exception:
                continue

        if cm_list:
            directory_item.addContextMenuItems(cm_list)

        is_folder = convert_to_bool(entry.get('isFolder', True))
        is_playable = convert_to_bool(entry.get('isPlayable', False))

        if is_playable:
            is_folder = False
            directory_item.setProperty('IsPlayable', 'true')

        if convert_to_bool(entry.get('fanart_property', True)):
            try:
                directory_item.setProperty('Fanart_Image', fanart)
            except Exception:
                pass

        if isinstance(entry.get('properties'), dict):
            for prop_key, prop_value in iteritems(entry['properties']):
                directory_item.setProperty(str(prop_key), str(prop_value))

        if isinstance(entry.get('streaminfo'), dict):
            try:
                directory_item.addStreamInfo('music' if info_type in ('music', 'audio') else 'video', entry['streaminfo'])
            except Exception:
                pass

        directory_item.setIsFolder(is_folder)
        self._items.append((url, directory_item, is_folder))

        return url, directory_item, is_folder

    def finish(self, content=None, category=None, view=None, cacheToDisc=True):

        kodi.addItems(handle=self.syshandle, items=self._items)

        if content is not None:
            kodi.content(self.syshandle, content)

        if category is not None:
            kodi.setcategory(self.syshandle, category)

        kodi.directory(self.syshandle, cacheToDisc=cacheToDisc)

        if view is not None:
            kodi.set_view_mode(view)

        return self._items


def builder(
    items, content=None, mediatype=None, infotype='video', argv=None, as_playlist=False,
    autoplay=False, clear_first=True, category=None, updateListing=False, cacheToDisc=True,
    end_directory=True, add_all_at_once=True
):
    """Render a directory listing.

    Items are flushed in one addDirectoryItems batch by default
    (add_all_at_once=True); pass add_all_at_once=False for the legacy
    per-item addDirectoryItem loop.
    """

    if argv is None:

        from tulip.init import sysaddon, syshandle

    else:

        sysaddon = argv[0]
        syshandle = int(argv[1])

    if not items:
        log('Directory not added, reason of failure: ' + 'Empty or null list of items')
        kodi.directory(syshandle, updateListing=updateListing, cacheToDisc=cacheToDisc)
        return

    sysimage = kodi.addonInfo('icon')
    sysfanart = kodi.addonInfo('fanart')

    if as_playlist and clear_first:

        kodi.playlist(1 if infotype == 'video' else 0).clear()

    meta_tags = [
        'count', 'size', 'date', 'genre', 'country', 'year', 'episode', 'season', 'sortepisode', 'sortseason',
        'episodeguide', 'showlink', 'top250', 'setid', 'tracknumber', 'rating', 'userrating', 'watched', 'playcount',
        'overlay', 'cast', 'castandrole', 'director', 'mpaa', 'plot', 'plotoutline', 'title', 'originaltitle',
        'sorttitle', 'duration', 'studio', 'tagline', 'writer', 'tvshowtitle', 'premiered', 'status', 'set',
        'setoverview', 'tag', 'imdbnumber', 'code', 'aired', 'credits', 'lastplayed', 'album', 'artist', 'votes',
        'path', 'trailer', 'dateadded', 'mediatype', 'dbid', 'tracknumber', 'discnumber', 'lyrics', 'listeners',
        'musicbrainztrackid', 'comment', 'picturepath', 'platform', 'genres', 'publisher', 'developer', 'overview',
        'gameclient'
    ]

    directory_items = []

    for count, list_item in enumerate(items):

        if list_item.get('label'):
            if isinstance(list_item['label'], int):
                label = kodi.i18n(list_item['label'])
            else:
                label = list_item['label']
        else:
            if isinstance(list_item.get('title'), int):
                label = kodi.i18n(list_item.get('title'))
            else:
                label = list_item.get('title')

        if list_item.get('image'):
            image = 'image={0}'.format(quote_plus(list_item['image'].encode('utf-8')))
        else:
            if not list_item.get('icon'):
                list_item['image'] = sysimage
            image = 'image={0}'.format(quote_plus(sysimage.encode('utf-8')))

        fanart = list_item.get('fanart', sysfanart)

        isFolder = convert_to_bool(list_item.get('isFolder', 'False'))
        isPlayable = convert_to_bool(list_item.get('isPlayable', 'False')) and not isFolder

        if list_item.get('action'):
            action = '{0}?action={1}'.format(sysaddon, list_item['action'])
        else:
            action = None

        if list_item.get('url'):
            url = 'url={0}'.format(quote_plus(list_item['url']))
        else:
            url = None

        if list_item.get('title'):
            if isinstance(list_item['title'], int):
                title = kodi.i18n(list_item['title'])
            else:
                title = list_item['title']
            title = 'title={0}'.format(quote_plus(title.encode('utf-8')))
        else:
            title = None

        if list_item.get('name'):
            name = 'name={0}'.format(quote_plus(list_item['name'].encode('utf-8')))
        else:
            name = None

        if list_item.get('year'):
            year = 'year={0}'.format(list_item['year'])
        else:
            year = None

        if list_item.get('plot'):
            plot = 'plot={0}'.format(quote_plus(list_item['plot'].encode('utf-8')))
        else:
            plot = None

        if list_item.get('genre'):
            try:
                genre = 'genre={0}'.format(quote_plus(list_item['genre'].encode('utf-8')))
            except AttributeError:
                genre = 'genre={0}'.format(quote_plus(json.dumps(list_item['genre'])))
        else:
            genre = None

        if list_item.get('dash'):
            dash = 'dash={0}'.format(list_item['dash'])
        else:
            dash = None

        if list_item.get('query'):
            query = 'query={0}'.format(quote_plus(list_item['query'].encode('utf-8')))
        else:
            query = None

        parts = [q for q in [action, url, title, image, name, year, plot, genre, dash, query] if q]

        url_query = '&'.join(parts)

        cm_list = []
        context_menu = list_item.get('cm')

        if context_menu:

            for cm in context_menu:

                try:

                    if isinstance(cm['title'], int):
                        tmenu = kodi.i18n(cm['title']).encode('utf-8')
                    else:
                        tmenu = cm['title'].encode('utf-8')
                    try:
                        qmenu = urlencode(cm['query'])
                    except Exception:
                        qmenu = urlencode(dict((k, v.encode('utf-8')) for k, v in cm['query'].items()))

                    cm_list.append((tmenu, 'RunPlugin({0}?{1})'.format(sysaddon, qmenu)))

                except Exception:

                    pass

        meta = dict((k, v) for k, v in iteritems(list_item) if k in meta_tags and (not v == '0' or v is None))

        if isinstance(list_item.get('meta'), dict):
            meta.update(dict(iteritems(list_item['meta'])))

        meta = _normalize_meta(meta)

        if mediatype is not None:
            meta['mediatype'] = mediatype

        directory_item = kodi.item(label=label)

        if not list_item.get('artwork'):
            artwork = {
                'icon': list_item.get('icon', list_item.get('image')), 'thumb': list_item.get('image'),
                'poster': list_item.get('image'), 'tvshow.poster': list_item.get('image'),
                'season.poster': list_item.get('image'), 'banner': list_item.get('image'),
                'tvshow.banner': list_item.get('image'), 'season.banner': list_item.get('image'),
                'fanart': fanart
            }
            directory_item.setArt(artwork)
        else:
            directory_item.setArt(list_item.get('artwork'))

        if cm_list:
            directory_item.addContextMenuItems(cm_list)

        info_type = list_item.get('infotype', infotype)

        _set_info(directory_item, meta, info_type)

        if isinstance(list_item.get('properties'), dict):
            for prop_key, prop_value in iteritems(list_item['properties']):
                directory_item.setProperty(str(prop_key), str(prop_value))

        if isPlayable:

            directory_item.setProperty('IsPlayable', 'true')

            if 'streaminfo' not in list_item and infotype == 'video':
                kodi.videostreamdetail(codec='h264')
            elif 'streaminfo' in list_item:
                kodi.videostreamdetail(**list_item['streaminfo'])

        if add_all_at_once:
            directory_item.setIsFolder(isFolder)

        if as_playlist and isPlayable:
            kodi.playlist(1 if infotype == 'video' else 0).add(url=url_query, listitem=directory_item, index=count)
        elif add_all_at_once:
            directory_items.append((url_query, directory_item, isFolder))
        else:
            kodi.addItem(handle=syshandle, url=url_query, listitem=directory_item, isFolder=isFolder)

    if content is not None:
        kodi.content(syshandle, content)

    if category is not None:
        kodi.setcategory(syshandle, category)

    if as_playlist:

        if not autoplay:
            kodi.openPlaylist(1 if infotype == 'video' else 0)
        else:
            kodi.execute('Action(Play)')

    else:

        if add_all_at_once:
            kodi.addItems(handle=syshandle, items=directory_items)

        if end_directory:
            kodi.directory(syshandle, updateListing=updateListing, cacheToDisc=cacheToDisc)

    return


def playlist_maker(items=None, argv=None):

    if items is None:
        return

    if argv is None:

        from tulip.init import sysaddon

    else:

        sysaddon = argv[0]

    m3u_list = [u'#EXTM3U\n']

    for item in items:

        try:
            action = '{0}?action={1}'.format(sysaddon, item['action'])
        except KeyError:
            return
        try:
            url = '&url={0}'.format(quote_plus(item['url']))
        except Exception:
            url = None
        try:
            title = '&title={0}'.format(quote_plus(item['title']))
        except KeyError:
            try:
                title = '&title={}'.format(quote_plus(item['title'].encode('utf-8')))
            except KeyError:
                title = None
        except Exception:
            title = None

        try:
            icon = '&image={0}'.format(quote_plus(item['image']))
        except KeyError:
            try:
                icon = '&image={0}'.format(quote_plus(item['image'].encode('utf-8')))
            except KeyError:
                icon = None
        except Exception:
            icon = None

        try:
            name = '&name={0}'.format(quote_plus(item['name']))
        except KeyError:
            try:
                name = '&name={0}'.format(quote_plus(item['name'].encode('utf-8')))
            except KeyError:
                name = None
        except Exception:
            name = None
        try:
            year = '&year={0}'.format(quote_plus(item['year']))
        except Exception:
            year = None
        try:
            plot = '&plot={0}'.format(quote_plus(item['plot']))
        except KeyError:
            try:
                plot = '&plot={0}'.format(quote_plus(item['plot'].encode('utf-8')))
            except KeyError:
                plot = None
        except Exception:
            plot = None

        parts = [foo for foo in [action, url, title, icon, name, year, plot] if foo]

        uri = '&'.join(parts)

        if icon:
            m3u_list.append(u'#EXTINF:0 tvg-logo="{0}",{1}\n'.format(icon, item['title']) + uri + '\n')
        else:
            m3u_list.append(u'#EXTINF:0,{0}\n'.format(item['title']) + uri + '\n')

    return ''.join(m3u_list)


def resolve(
        url, meta=None, icon=None, dash=False, manifest_type=None, inputstream_type='adaptive', headers=None,
        mimetype=None, resolved_mode=True, live=False, verify=True, licence_type=None, licence_key=None,
        inputstream_properties=None
):

    """
    Prepares a resolved url into a listitem for playback

    :param licence_key:
    :param licence_type:
    :param verify:
    :param live:
    :param resolved_mode:
    :param url: Requires a string or unicode, append required urlencoded headers with pipe |
    :param meta: a dictionary with listitem keys: values
    :param icon: String
    :param dash: Boolean
    :param manifest_type: String
    :param inputstream_type: String 99.9% of the time it is adaptive
    :param headers: dictionary or urlencoded string
    :param mimetype: String
    :param inputstream_properties: Dictionary of InputStream listitem properties
    :return: None
    """

    from tulip.init import syshandle

    # Fail gracefully instead of making Kodi complain.
    if not url:
        log('URL was not provided, failure to resolve stream')
        return

    if not headers and '|' in url:
        url, _, headers = url.rpartition('|')
    elif headers:
        if isinstance(headers, str):
            if headers.startswith('|'):
                headers = headers[1:]
        elif isinstance(headers, dict):
            headers = urlencode(headers)

    if not verify:

        if headers and 'verifypeer' not in headers:
            headers += '&verifypeer=false'
        else:
            headers = 'verifypeer=false'

    if not dash and headers:
        url = '|'.join([url, headers])

    item = kodi.item(path=url)
    item.setPath(url)

    if icon is not None:
        if isinstance(icon, dict):
            item.setArt(icon)
        else:
            item.setArt({'icon': icon, 'thumb': icon})

    if meta is not None:
        item.setInfo(type='video', infoLabels=meta)

    try:
        isa_enabled = kodi.addon_details('inputstream.adaptive').get('enabled')
    except KeyError:
        isa_enabled = False

    if dash and isa_enabled:

        if not manifest_type:

            if '.mpd' in url:
                manifest_type = 'mpd'
            elif '.m3u8' in url:
                manifest_type = 'hls'

        if not mimetype:

            if '.mpd' in url:
                mimetype = 'application/xml+dash'
            elif '.m3u8' in url:
                # mimetype = 'application/vnd.apple.mpegurl'
                mimetype = 'application/x-mpegURL'

        inputstream_property = 'inputstream'
        # inputstream_property += 'addon'

        item.setContentLookup(False)
        item.setMimeType('{0}'.format(mimetype))
        # Kodi 21's InputStream Adaptive explicitly declares ``manifest_type``
        # as a ListItem property. Set it before selecting the inputstream so
        # every HLS-specific property is present at instance creation.
        if manifest_type:
            item.setProperty('inputstream.{0}.manifest_type'.format(inputstream_type), manifest_type)

        # Some HLS manifests carry multiple qualities.  Let callers apply an
        # explicit per-item chooser limit instead of relying on the Android
        # screen resolution, which may be much higher than the add-on setting.
        if isinstance(inputstream_properties, dict):
            for property_name, property_value in inputstream_properties.items():
                if property_name and property_value is not None:
                    item.setProperty(str(property_name), str(property_value))

        if headers:

            item.setProperty("inputstream.{0}.stream_headers".format(inputstream_type), headers)

            if kodi.kodi_version() > 21.8:
                item.setProperty('inputstream.adaptive.common_headers', headers)
            elif kodi.kodi_version() > 19.8:
                item.setProperty('inputstream.adaptive.manifest_headers', headers)
                item.setProperty('inputstream.adaptive.stream_params', headers)
            elif kodi.kodi_version() > 19:
                item.setProperty('inputstream.adaptive.manifest_headers', headers)

        item.setProperty(inputstream_property, 'inputstream.{}'.format(inputstream_type))

        if licence_key and licence_type:
            if licence_type == 'org.w3.clearkey':
                try:
                    k_dict = json.loads(licence_key) if isinstance(licence_key, str) else licence_key
                    if isinstance(k_dict, dict):
                        pairs = '|'.join([f'{k}:{v}' for k, v in k_dict.items()])
                        item.setProperty('inputstream.adaptive.drm_legacy', f'org.w3.clearkey|{pairs}')
                except Exception:
                    pass
                if kodi.kodi_version() < 21:
                    item.setProperty('inputstream.adaptive.license_type', licence_type)
                    item.setProperty('inputstream.adaptive.license_key', licence_key)
            else:
                item.setProperty('inputstream.adaptive.license_type', licence_type)
                item.setProperty('inputstream.adaptive.license_key', licence_key)

    elif mimetype:

        item.setContentLookup(False)
        item.setMimeType('{0}'.format(mimetype))

    if dash and live:
        item.setProperty(
            'inputstream.{}.manifest_update_parameter'.format(inputstream_type), '&start_seq=$START_NUMBER$'
        )

    if resolved_mode:
        kodi.resolve(syshandle, True, item)
    else:
        kodi.player().play(url, item)


def run_builtin(
        addon_id=kodi.addonInfo('id'), action=None, mode=None, content_type=None, url=None, query=None, image=None,
        path_history='', get_url=False, command=('ActivateWindow', 'Container.Update'), *args, **kwargs
):

    """
    This function will construct a url starting with plugin:// attached to the addon_id, then passed into either
    the ActivateWindow built-in command or Container.Update for listing/container manipulation. You have to either pass action,
    mode, content_type or query, otherwise TypeError will be raised. Can also apply the "PlayMedia".
    Query will override action, mode, url and content_type arguments if passed as dictionary
    path_history can also be either ",return" or ",replace"
    """

    if not query and not action and not mode and not content_type and not args and not kwargs:

        raise TypeError('Cannot manipulate container without arguments')

    if isinstance(query, dict):

        query_string = urlencode(query)

    else:

        query_string = ''

        if content_type:

            query_string += 'content_type={0}{1}'.format(
                content_type, '&' if any([action, mode, url, query, image, args, kwargs]) else ''
            )

        if action:

            query_string += 'action={0}'.format(action)

        if mode:

            query_string += 'mode={0}'.format(mode)

        if url:

            query_string += '&url={0}'.format(quote_plus(url))

        if query:

            query_string += '&query={0}'.format(query)

        if image:

            query_string += '&image={0}'.format(image)

        if args:

            query_string += '&' + '&'.join(args)

        if kwargs:

            query_string += '&' + urlencode(kwargs)

    if 'content_type=video' in query_string:
        window_id = 'videos'
    elif 'content_type=audio' in query_string:
        window_id = 'music'
    elif 'content_type=image' in query_string:
        window_id = 'pictures'
    elif 'content_type=executable' in query_string:
        window_id = 'programs'
    elif 'content_type' in query_string and dict(parse_qsl(query_string))['content_type'] not in ['video', 'audio', 'image', 'executable']:
        raise AttributeError('Incorrect content_type specified')

    addon_url = ''.join(['plugin://', addon_id, '/'])

    if 'content_type' in query_string and isinstance(command, tuple):

        # noinspection PyUnboundLocalVariable
        executable = '{0}({1},"{2}?{3}"{4})'.format(command[0], window_id, addon_url, query_string, ',return' if not path_history else ',' + path_history)

    else:

        if isinstance(command, tuple):

            executable = '{0}({1}?{2}{3})'.format(command[1], addon_url, query_string, ',return' if not path_history else ',' + path_history)

        else:

            executable = '{0}({1}?{2}{3})'.format(command, addon_url, query_string, ',return' if not path_history else ',' + path_history)

    if get_url:

        return executable

    else:

        kodi.execute(executable)


__all__ = ["Listing", "builder", "resolve", "playlist_maker", "run_builtin"]
