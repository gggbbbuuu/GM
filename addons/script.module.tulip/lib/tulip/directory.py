# -*- coding: utf-8 -*-

'''
    Tulip library
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

from __future__ import absolute_import, print_function

import traceback, sys
from tulip.compat import urlencode, quote_plus, iteritems, basestring, parse_qsl, is_py2
from tulip.utils import percent
from tulip import control
from kodi_six.xbmc import log


def add(
    items, cacheToDisc=True, content=None, mediatype=None, infotype='video', argv=None, as_playlist=False,
    auto_play=False, pd_heading=None, pd_message='', clear_first=True, progress=False, category=None, artwork=None,
    offscreen=False
):

    if argv is None:

        from tulip.init import sysaddon, syshandle

    else:

        sysaddon = argv[0]
        syshandle = int(argv[1])

    if items is None or len(items) == 0:
        log('Directory not added, reason of failure: ' + 'Empty or null list of items')
        return

    # sysicon = control.join(control.addonInfo('path'), 'resources', 'media')
    sysimage = control.addonInfo('icon')
    sysfanart = control.addonInfo('fanart')

    if progress:

        pd = control.progressDialogGB
        pd.create(heading=control.name() if not pd_heading else pd_heading, message=pd_message)

    else:

        pd = None

    if as_playlist and clear_first:

        control.playlist(1 if infotype == 'video' else 0).clear()

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

    for c, i in list(enumerate(items)):

        try:

            if progress:

                p = percent(c, len(items))
                pd.update(p)

            try:
                label = control.lang(i['title']).encode('utf-8')
            except Exception:
                label = i['title']

            if 'label' in i and not i['label'] == '0':
                label = i['label']

            if 'image' in i and not i['image'] == '0':
                image = i['image']
            elif 'poster' in i and not i['poster'] == '0':
                image = i['poster']
            elif 'icon' in i and not i['icon'] == '0':
                image = control.addonmedia(i['icon'])
            else:
                image = sysimage

            if 'banner' in i and not i['banner'] == '0':
                banner = i['banner']
            elif 'fanart' in i and not i['fanart'] == '0':
                banner = i['fanart']
            else:
                banner = image

            fanart = i['fanart'] if 'fanart' in i and not i['fanart'] == '0' else sysfanart

            isFolder = False if 'isFolder' in i and not i['isFolder'] == '0' else True

            try:
                is_play_boolean = i.get('isPlayable') in ['True', 'true', '1', 'yes', 'Yes']
            except Exception:
                is_play_boolean = False

            isPlayable = True if not isFolder and 'isPlayable' not in i else is_play_boolean

            if isPlayable:

                isFolder = False

            try:
                action = '{0}?action={1}'.format(sysaddon, i['action'])
            except KeyError:
                return

            try:
                url = 'url={0}'.format(quote_plus(i['url']))
            except Exception:
                url = None

            try:
                title = 'title={0}'.format(quote_plus(i['title']))
            except KeyError:
                try:
                    title = 'title={0}'.format(quote_plus(i['title'].encode('utf-8')))
                except KeyError:
                    title = None
            except Exception:
                title = None

            try:
                icon = 'image={0}'.format(quote_plus(i['image']))
            except KeyError:
                try:
                    icon = 'image={0}'.format(quote_plus(i['image'].encode('utf-8')))
                except KeyError:
                    icon = None
            except Exception:
                icon = None
            try:
                name = 'name={0}'.format(quote_plus(i['name']))
            except KeyError:
                try:
                    name = 'name={0}'.format(quote_plus(i['name'].encode('utf-8')))
                except KeyError:
                    name = None
            except Exception:
                name = None
            try:
                year = 'year={0}'.format(quote_plus(i['year']))
            except Exception:
                year = None
            try:
                plot = 'plot={0}'.format(quote_plus(i['plot']))
            except KeyError:
                try:
                    plot = 'plot={0}'.format(quote_plus(i['plot'].encode('utf-8')))
                except KeyError:
                    plot = None
            except Exception:
                plot = None
            try:
                genre = 'genre={0}'.format(quote_plus(i['genre']))
            except KeyError:
                try:
                    genre = 'genre={0}'.format(quote_plus(i['genre'].encode('utf-8')))
                except KeyError:
                    genre = None
            except Exception:
                genre = None
            try:
                dash = 'dash={0}'.format(quote_plus(i['dash']))
            except Exception:
                dash = None
            try:
                query = 'query={0}'.format(quote_plus(i['query']))
            except Exception:
                query = None

            parts = [foo for foo in [action, url, title, icon, name, year, plot, genre, dash, query] if foo]

            uri = '&'.join(parts)

            cm = []
            menus = i['cm'] if 'cm' in i else []

            for menu in menus:

                try:

                    try:
                        tmenu = control.lang(menu['title']).encode('utf-8')
                    except Exception:
                        tmenu = menu['title']
                    try:
                        qmenu = urlencode(menu['query'])
                    except Exception:
                        qmenu = urlencode(dict((k, v.encode('utf-8')) for k, v in menu['query'].items()))
                    cm.append((tmenu, 'RunPlugin({0}?{1})'.format(sysaddon, qmenu)))

                except Exception:

                    pass

            meta = dict((k, v) for k, v in iteritems(i) if k in meta_tags and (not v == '0' or v is None))

            if mediatype is not None:
                meta['mediatype'] = mediatype

            item = control.item(label=label)

            item.setArt(
                {
                    'icon': image, 'thumb': image, 'poster': image, 'tvshow.poster': image, 'season.poster': image,
                    'banner': banner, 'tvshow.banner': banner, 'season.banner': banner, 'fanart': fanart
                }
            )

            item.addContextMenuItems(cm)
            item.setInfo(type=infotype if 'infotype' not in i else i['infotype'], infoLabels=meta)

            if isPlayable:

                if not i['action'] == 'pvr_client':
                    item.setProperty('IsPlayable', 'true')
                else:
                    item.setProperty('IsPlayable', 'false')

                if not i['action'] == 'pvr_client':
                    if 'streaminfo' not in i and infotype == 'video':
                        item.addStreamInfo(infotype, {'codec': 'h264'})
                    else:
                        item.addStreamInfo(infotype, i.get('streaminfo'))

            if as_playlist and isPlayable:
                control.playlist(1 if infotype == 'video' else 0).add(url=uri, listitem=item, index=c)
            else:
                control.addItem(handle=syshandle, url=uri, listitem=item, isFolder=isFolder, totalItems=len(items))

        except Exception as reason:

            _, __, tb = sys.exc_info()

            print(traceback.print_tb(tb))
            log('Directory not added, reason of failure: ' + repr(reason))

    if progress:

        pd.update(100)
        pd.close()

    if as_playlist:

        if not auto_play:
            control.openPlaylist(1 if infotype == 'video' else 0)
        else:
            control.execute('Action(Play)')

        return

    try:

        i = items[0]
        if i['next'] == '':
            raise Exception()

        url = '{0}?action={1}&url={2}'.format(sysaddon, i['nextaction'], quote_plus(i['next']))
        if 'name' in i:
            url += '&name={0}'.format(quote_plus(i['name'].encode('utf-8')))
        if 'title' in i:
            url += '&title={0}'.format(quote_plus(i['title'].encode('utf-8')))
        icon = i['nexticon'] if 'nexticon' in i else control.addonmedia('next.png')
        fanart = i['nextfanart'] if 'nextfanart' in i else sysfanart

        try:
            label = control.lang(i['nextlabel']).encode('utf-8')
        except Exception:
            label = 'Next'

        item = control.item(label=label, offscreen=offscreen)

        if artwork is not None:
            item.setArt(artwork)
        else:
            item.setArt(
                {
                    'icon': icon, 'thumb': icon, 'poster': icon, 'tvshow.poster': icon, 'season.poster': icon,
                    'banner': icon, 'tvshow.banner': icon, 'season.banner': icon, 'fanart': fanart
                }
            )

        control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True, totalItems=len(items))

    except Exception:

        pass

    if content is not None:
        control.content(syshandle, content)

    if category is not None:
        control.setcategory(syshandle, category)

    control.directory(syshandle, cacheToDisc=cacheToDisc)


def playlist_maker(items=None, argv=None):

    if items is None:
        return

    if argv is None:

        from tulip.init import sysaddon

    else:

        sysaddon = argv[0]

    m3u_list = [u'#EXTM3U\n']

    for i in items:

        try:
            action = '{0}?action={1}'.format(sysaddon, i['action'])
        except KeyError:
            return
        try:
            url = '&url={0}'.format(quote_plus(i['url']))
        except Exception:
            url = None
        try:
            title = '&title={0}'.format(quote_plus(i['title']))
        except KeyError:
            try:
                title = '&title={}'.format(quote_plus(i['title'].encode('utf-8')))
            except KeyError:
                title = None
        except Exception:
            title = None

        try:
            icon = '&image={0}'.format(quote_plus(i['image']))
        except KeyError:
            try:
                icon = '&image={0}'.format(quote_plus(i['image'].encode('utf-8')))
            except KeyError:
                icon = None
        except Exception:
            icon = None

        try:
            name = '&name={0}'.format(quote_plus(i['name']))
        except KeyError:
            try:
                name = '&name={0}'.format(quote_plus(i['name'].encode('utf-8')))
            except KeyError:
                name = None
        except Exception:
            name = None
        try:
            year = '&year={0}'.format(quote_plus(i['year']))
        except Exception:
            year = None
        try:
            plot = '&plot={0}'.format(quote_plus(i['plot']))
        except KeyError:
            try:
                plot = '&plot={0}'.format(quote_plus(i['plot'].encode('utf-8')))
            except KeyError:
                plot = None
        except Exception:
            plot = None

        parts = [foo for foo in [action, url, title, icon, name, year, plot] if foo]

        uri = '&'.join(parts)

        if icon:
            m3u_list.append(u'#EXTINF:0 tvg-logo="{0}",{1}\n'.format(icon, i['title']) + uri + '\n')
        else:
            m3u_list.append(u'#EXTINF:0,{0}\n'.format(i['title']) + uri + '\n')

    return ''.join(m3u_list)


def resolve(
        url, meta=None, icon=None, dash=False, manifest_type=None, inputstream_type='adaptive', headers=None,
        mimetype=None, resolved_mode=True, live=False, verify=True
):

    """
    Prepares a resolved url into a listitem for playback

    :param url: Requires a string or unicode, append required urlencoded headers with pipe |
    :param meta: a dictionary with listitem keys: values
    :param icon: String
    :param dash: Boolean
    :param manifest_type: String
    :param inputstream_type: String 99.9% of the time it is adaptive
    :param headers: dictionary or urlencoded string
    :param mimetype: String
    :return: None
    """

    from tulip.init import syshandle

    # Fail gracefully instead of making Kodi complain.
    if not url:
        from kodi_six.xbmc import log
        log('URL was not provided, failure to resolve stream')
        return

    if not headers and '|' in url:
        url, sep, headers = url.rpartition('|')
    elif headers:
        if isinstance(headers, basestring):
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

    if is_py2:
        item = control.item(path=url)
    else:
        item = control.item()
        item.setPath(url)

    if icon is not None:
        if isinstance(icon, dict):
            item.setArt(icon)
        else:
            item.setArt({'icon': icon, 'thumb': icon})

    if meta is not None:
        item.setInfo(type='video', infoLabels=meta)

    krypton_plus = control.kodi_version() >= 17.0

    try:
        isa_enabled = control.addon_details('inputstream.adaptive').get('enabled')
    except KeyError:
        isa_enabled = False

    if dash and krypton_plus and isa_enabled:

        if not manifest_type:

            manifest_type = 'mpd'

        if not mimetype:

            mimetype = 'application/xml+dash'

        inputstream_property = 'inputstream'
        if is_py2:
            inputstream_property += 'addon'

        item.setContentLookup(False)
        item.setMimeType('{0}'.format(mimetype))
        item.setProperty(inputstream_property, 'inputstream.{}'.format(inputstream_type))
        item.setProperty('inputstream.{0}.manifest_type'.format(inputstream_type), manifest_type)

        if headers:

            item.setProperty("inputstream.{0}.stream_headers".format(inputstream_type), headers)

    elif mimetype:

        item.setContentLookup(False)
        item.setMimeType('{0}'.format(mimetype))

    if dash and live:
        item.setProperty('inputstream.{}.manifest_update_parameter'.format(inputstream_type), '&start_seq=$START_NUMBER$')

    if resolved_mode:
        control.resolve(syshandle, True, item)
    else:
        control.player().play(url, item)


def run_builtin(
        addon_id=control.addonInfo('id'), action=None, mode=None, content_type=None, url=None, query=None, image=None,
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

            query_string += 'content_type={0}{1}'.format(content_type, '' if action is None and mode is None and query is None and args is None and kwargs is None else '&')

        if action:

            query_string += 'action={0}'.format(action)

        if mode:

            query_string += 'mode={0}'.format(mode)

        if url:

            query_string += '&url={0}'.format(quote_plus(url))

        if query:

            query_string += '&query={0}'.format(query)

        if image:

            query_string += '&image={0}'.format(query)

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

        control.execute(executable)


__all__ = ["add", "resolve", "playlist_maker", "run_builtin"]
