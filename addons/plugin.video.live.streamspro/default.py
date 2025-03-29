# -*- coding: utf-8 -*-
import re
import os
import base64
from zlib import decompress
import json
import time
import six
import traceback
import sys
from kodi_six import xbmcplugin, xbmcgui, xbmcaddon, xbmcvfs, xbmc
from six.moves import urllib_request, urllib_parse, urllib_error, http_cookiejar, html_parser
from xml.sax.saxutils import escape
from xml.etree import ElementTree


class NoRedirection(urllib_error.HTTPError):
    def http_response(self, request, response):
        return response
    https_response = http_response


global gLSProDynamicCodeNumber
viewmode = None
tsdownloader = False
hlsretry = False
TRANSLATEPATH = xbmc.translatePath if six.PY2 else xbmcvfs.translatePath
LOGINFO = xbmc.LOGNOTICE if six.PY2 else xbmc.LOGINFO
resolve_url = ['180upload.com', 'allmyvideos.net', 'bestreams.net', 'clicknupload.com', 'cloudzilla.to', 'movshare.net', 'novamov.com', 'nowvideo.sx', 'videoweed.es', 'daclips.in', 'datemule.com', 'fastvideo.in', 'faststream.in', 'filehoot.com', 'filenuke.com', 'sharesix.com', 'plus.google.com', 'picasaweb.google.com', 'gorillavid.com', 'gorillavid.in', 'grifthost.com', 'hugefiles.net', 'ipithos.to', 'ishared.eu', 'kingfiles.net', 'mail.ru', 'my.mail.ru', 'videoapi.my.mail.ru', 'mightyupload.com', 'mooshare.biz', 'movdivx.com', 'movpod.net', 'movpod.in', 'movreel.com', 'mrfile.me', 'nosvideo.com', 'openload.io', 'played.to', 'bitshare.com', 'filefactory.com', 'k2s.cc', 'oboom.com', 'rapidgator.net', 'primeshare.tv', 'bitshare.com', 'filefactory.com', 'k2s.cc', 'oboom.com', 'rapidgator.net', 'sharerepo.com', 'stagevu.com', 'streamcloud.eu', 'streamin.to', 'thefile.me', 'thevideo.me', 'tusfiles.net', 'uploadc.com', 'zalaa.com', 'uploadrocket.net', 'uptobox.com', 'v-vids.com', 'veehd.com', 'vidbull.com', 'videomega.tv', 'vidplay.net', 'vidspot.net', 'vidto.me', 'vidzi.tv', 'vimeo.com', 'vk.com', 'vodlocker.com', 'xfileload.com', 'xvidstage.com', 'zettahost.tv']
g_ignoreSetResolved = ['plugin.video.f4mTester', 'plugin.video.SportsDevil', 'plugin.video.sportsdevil', 'plugin.video.ZemTV-shani']
gLSProDynamicCodeNumber = 0
addon = xbmcaddon.Addon()
addon_name = addon.getAddonInfo('name')
addon_version = addon.getAddonInfo('version')
profile = TRANSLATEPATH(addon.getAddonInfo('profile'))
home = TRANSLATEPATH(addon.getAddonInfo('path'))
sys.path.append(os.path.join(home, 'resources', 'lib'))
favorites = os.path.join(profile, 'favorites')
history = os.path.join(profile, 'history')
REV = os.path.join(profile, 'list_revision')
icon = os.path.join(home, 'icon.png')
FANART = os.path.join(home, 'fanart.jpg')
homesources_file = os.path.join(home, 'source_file')
source_file = os.path.join(profile, 'source_file')
functions_dir = profile
debug = addon.getSetting('debug')
if os.path.exists(favorites):
    FAV = xbmcvfs.File(favorites).read()
else:
    FAV = []
if os.path.exists(source_file):
    SOURCES = xbmcvfs.File(source_file).read()
else:
    SOURCES = []
if not os.path.exists(functions_dir):
    xbmcvfs.mkdir(functions_dir)

def addon_log(string, level=xbmc.LOGDEBUG):
    if debug == 'true':
        xbmc.log("[plugin.video.live.streamspro-{0}]: {1}".format(addon_version, string), LOGINFO)
    else:
        xbmc.log("[plugin.video.live.streamspro-{0}]: {1}".format(addon_version, string), level)


def makeRequest(url, headers=None):
    try:
        if headers is None:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'}

        if '|' in url:
            url, header_in_page = url.split('|')
            header_in_page = header_in_page.split('&')

            for h in header_in_page:
                if len(h.split('=')) == 2:
                    n, v = h.split('=')
                else:
                    vals = h.split('=')
                    n = vals[0]
                    v = '='.join(vals[1:])
                headers[n] = v

        req = urllib_request.Request(url, None, headers)
        response = urllib_request.urlopen(req)
        result = response.read()

        encoding = None
        content_type = response.headers.get('content-type', '')
        if 'charset=' in content_type:
            encoding = content_type.split('charset=')[-1]

        if encoding is None:
            epattern = r'<meta\s+http-equiv="Content-Type"\s+content="(?:.+?);\s+charset=(.+?)"'
            epattern = epattern.encode('utf8') if six.PY3 else epattern
            r = re.search(epattern, result, re.IGNORECASE)
            if r:
                encoding = r.group(1).decode('utf8') if six.PY3 else r.group(1)
            else:
                epattern = r'''<meta\s+charset=["']?([^"'>]+)'''
                epattern = epattern.encode('utf8') if six.PY3 else epattern
                r = re.search(epattern, result, re.IGNORECASE)
                if r:
                    encoding = r.group(1).decode('utf8') if six.PY3 else r.group(1)

        if encoding is not None:
            result = result.decode(encoding.lower(), errors='ignore')
            result = result.encode('utf8') if six.PY2 else result
        else:
            result = result.decode('utf-8', errors='ignore') if six.PY3 else result.encode('utf-8')
        response.close()
    except urllib_error.URLError as e:
        addon_log('URL: {0}'.format(url))
        if hasattr(e, 'code'):
            msg = 'We failed with error code - {0}'.format(e.code)
            addon_log(msg)
            xbmcgui.Dialog().notification(addon_name, msg, icon, 10000, False)
        elif hasattr(e, 'reason'):
            addon_log('We failed to reach a server.')
            addon_log('Reason: {0}'.format(e.reason))
            msg = 'We failed to reach a server. - {0}'.format(e.reason)
            xbmcgui.Dialog().notification(addon_name, msg, icon, 10000, False)

    return result


def getSources():
    try:
        if os.path.exists(favorites):
            addDir('Favorites', 'url', 4, os.path.join(home, 'resources', 'favorite.png'), FANART, '', '', '', '')
        if addon.getSetting("browse_community") == "true":
            addDir('Community Files', 'community_files', 16, icon, FANART, '', '', '', '')
        if addon.getSetting("searchotherplugins") == "true":
            addDir('Search Other Plugins', 'Search Plugins', 25, icon, FANART, '', '', '', '')
        if os.path.exists(source_file):
            sources = json.loads(xbmcvfs.File(source_file, "r").read())
        else:
            sources = []
        if os.path.exists(homesources_file):
            homesources = json.loads(xbmcvfs.File(homesources_file, "r").read())
            sources.extend(homesources)
        if len(sources) > 1:
            for i in sources:
                try:
                    thumb = icon
                    fanart = FANART
                    desc = ''
                    date = ''
                    credits = ''
                    genre = ''
                    if 'thumbnail' in i:
                        thumb = i['thumbnail']
                    if 'fanart' in i:
                        fanart = i['fanart']
                    if 'description' in i:
                        desc = i['description']
                    if 'date' in i:
                        date = i['date']
                    if 'genre' in i:
                        genre = i['genre']
                    if 'credits' in i:
                        credits = i['credits']
                    title = i['title'].encode('utf-8') if six.PY2 else i['title']
                    url = i['url'].encode('utf-8') if six.PY2 else i['url']
                    # url = url + "fix" if url.endswith(".xml") and six.PY3 else url
                    addDir(title, url, 1, thumb, fanart, desc, genre, date, credits, 'source')
                except:
                    traceback.print_exc()
        else:
            if len(sources) == 1:
                if isinstance(sources[0], list):
                    getData(sources[0][1].encode('utf-8'), FANART) if six.PY2 else sources[0][1]
                else:
                    getData(sources[0]['url'], sources[0]['fanart'])
    except:
        traceback.print_exc()


def addSource(url=None):
    if url is None:
        if addon.getSetting("new_file_source") != "":
            source_url = addon.getSetting('new_file_source')
        elif addon.getSetting("new_url_source") != "":
            source_url = addon.getSetting('new_url_source')
    else:
        source_url = url
    if source_url == '' or source_url is None:
        return
    addon_log('Adding New Source: {0}'.format(source_url))

    media_info = None
    data = getSoup(source_url)
    if isinstance(data, ElementTree.ElementTree) or isinstance(data, ElementTree.Element):
        if data.find('channels_info') is not None:
            media_info = data.find('channels_info')
        elif data.find('items_info') is not None:
            media_info = data.find('items_info')

    if media_info:
        source_media = {}
        source_media['url'] = source_url
        try:
            source_media['title'] = media_info.find('title').text
        except:
            pass
        try:
            source_media['thumbnail'] = media_info.find('thumbnail').text
        except:
            pass
        try:
            source_media['fanart'] = media_info.find('fanart').text
        except:
            pass
        try:
            source_media['genre'] = media_info.find('genre').text
        except:
            pass
        try:
            source_media['description'] = media_info.find('description').text
        except:
            pass
        try:
            source_media['date'] = media_info.find('date').text
        except:
            pass
        try:
            source_media['credits'] = media_info.find('credits').text
        except:
            pass
    else:
        if '/' in source_url:
            nameStr = source_url.split('/')[-1].split('.')[0]
        if '\\' in source_url:
            nameStr = source_url.split('\\')[-1].split('.')[0]
        if '%' in nameStr:
            nameStr = urllib_parse.unquote_plus(nameStr)
        keyboard = xbmc.Keyboard(nameStr, 'Displayed Name, Rename?')
        keyboard.doModal()
        if (keyboard.isConfirmed() is False):
            return
        newStr = keyboard.getText()
        if len(newStr) == 0:
            return
        source_media = {}
        source_media['title'] = newStr
        source_media['url'] = source_url
        source_media['fanart'] = fanart

    if os.path.exists(source_file) is False:
        source_list = []
        source_list.append(source_media)
        with xbmcvfs.File(source_file, "w") as b:
            b.write(json.dumps(source_list))
    else:
        sources = json.loads(xbmcvfs.File(source_file, "r").read())
        sources.append(source_media)
        with xbmcvfs.File(source_file, "w") as b:
            b.write(json.dumps(sources))
    addon.setSetting('new_url_source', "")
    addon.setSetting('new_file_source', "")
    xbmcgui.Dialog().notification(addon_name, 'New source added', icon, 5000, False)

    if url is not None:
        if 'community-links' in url:
            xbmc.executebuiltin("Container.Update({0}?mode=10,replace)".format(sys.argv[0]))
    else:
        addon.openSettings()


def rmSource(name):
    sources = json.loads(xbmcvfs.File(source_file, "r").read())
    for index in range(len(sources)):
        if isinstance(sources[index], list):
            if sources[index][0] == name:
                del sources[index]
                with xbmcvfs.File(source_file, "w") as b:
                    b.write(json.dumps(sources))
                break
        else:
            if sources[index]['title'] == name:
                del sources[index]
                with xbmcvfs.File(source_file, "w") as b:
                    b.write(json.dumps(sources))
                break
    xbmc.executebuiltin("Container.Refresh")


def getSoup(url, data=None):
    global viewmode, tsdownloader, hlsretry
    tsdownloader = False
    hlsretry = False
    if url.startswith('http://') or url.startswith('https://'):
        enckey = False
        if '$$TSDOWNLOADER$$' in url:
            tsdownloader = True
            url = url.replace("$$TSDOWNLOADER$$", "")
        if '$$HLSRETRY$$' in url:
            hlsretry = True
            url = url.replace("$$HLSRETRY$$", "")
        if '$$LSProEncKey=' in url:
            enckey = url.split('$$LSProEncKey=')[1].split('$$')[0]
            rp = '$$LSProEncKey={0}$$'.format(enckey)
            url = url.replace(rp, "")

        data = makeRequest(url)
        try:
            data = decompress(base64.b64decode(data)).decode("utf-8")
        except:
            pass
        if enckey:
            import pyaes
            enckey = enckey.encode("ascii")
            missingbytes = 16 - len(enckey)
            enckey = enckey + (chr(0) * (missingbytes))
            data = base64.b64decode(data)
            decryptor = pyaes.new(enckey, pyaes.MODE_ECB, IV=None)
            data = decryptor.decrypt(data).split('\0')[0]

        if re.search("#EXTM3U", data) or 'm3u' in url:
            return data
    elif data is None:
        if xbmcvfs.exists(url):
            if url.startswith("smb://") or url.startswith("nfs://"):
                copy = xbmcvfs.copy(url, os.path.join(profile, 'temp', 'source_temp.txt'))
                if copy:
                    # if six.PY2:
                        # data = open(os.path.join(profile, 'temp', 'source_temp.txt'), "r").read()
                    # else:
                        # data = open(os.path.join(profile, 'temp', 'source_temp.txt'), "r", encoding='utf-8').read()
                    data = xbmcvfs.File(os.path.join(profile, 'temp', 'source_temp.txt'), "r").read()
                    xbmcvfs.delete(os.path.join(profile, 'temp', 'source_temp.txt'))
                else:
                    addon_log("failed to copy from smb:")
            else:
                # if six.PY2:
                    # data = open(url, 'r').read()
                # else:
                    # data = open(url, 'r', encoding='utf-8').read()
                data = xbmcvfs.File(url, 'r').read()
                if re.match("#EXTM3U", data) or 'm3u' in url:
                    return data
        else:
            addon_log("Soup Data not found!")
            return
    if '<SetViewMode>' in data:
        try:
            viewmode = re.findall('<SetViewMode>(.*?)<', data)[0]
            xbmc.executebuiltin("Container.SetViewMode({0})".format(viewmode))
        except:
            pass

    xml = None

    try:
        xml = ElementTree.fromstring(data)
    except ElementTree.ParseError as err:
        xbmcgui.Dialog().notification(addon_name, 'Failed to parse xml: {0}'.format(err.msg), icon, 10000, False)
    except Exception as err:
        xbmcgui.Dialog().notification(addon_name, 'An error occurred: {0}'.format(err), icon, 10000, False)

    return xml


def processPyFunction(data):
    try:
        if data and len(data) > 0 and data.startswith('$pyFunction:'):
            data = doEval(data.split('$pyFunction:')[1], '', None, None)
    except:
        pass

    return data


def getData(url, fanart, data=None):
    soup = getSoup(url, data)
    channels = None
    if isinstance(soup, ElementTree.Element):
        if (soup.tag == 'channels' and len(soup) > 0 and addon.getSetting('donotshowbychannels') == 'false') or (soup.tag == 'items' and len(soup) > 0):
            channels = soup.findall('channel')
            tepg = None
            media_info = None
            if soup.find('channels_info') is not None:
                media_info = soup.find('channels_info')
            elif soup.find('items_info') is not None:
                media_info = soup.find('items_info')

            if media_info:
                try:
                    if media_info.find('epg') is not None:
                        epg = media_info.find('epg').text
                        reg_item = media_info.find('epg_regex')
                        regexs = parse_regex(reg_item)

                        if '$doregex' in epg and getRegexParsed is not None:
                            tepg, setres = getRegexParsed(regexs, epg)

                        if tepg:
                            try:
                                tepg = json.dumps(tepg)
                            except:
                                tepg = str(tepg)

                            if functions_dir not in sys.path:
                                sys.path.append(functions_dir)

                            filename = 'LSProPageEPG.txt'
                            filenamewithpath = os.path.join(functions_dir, filename)
                            with xbmcvfs.File(filenamewithpath, 'w') as f:
                                f.write(tepg)
                except BaseException as err:
                    addon_log('error getting EPG page data: {0}'.format(str(err)))

            for channel in channels:
                linkedUrl = ''
                lcount = 0
                if channel.findall('externallink'):
                    linkedUrl = channel.findall('externallink')[0].text
                    # lcount = len(channel.findall('externallink'))  # gujal

                if lcount > 1:
                    linkedUrl = ''

                name = channel.find('name').text
                name = processPyFunction(name)

                if channel.find('thumbnail') is not None:
                    thumbnail = channel.find('thumbnail').text
                else:
                    thumbnail = ''
                thumbnail = processPyFunction(thumbnail)

                if channel.find('fanart') is not None:
                    fanArt = channel.find('fanart').text
                elif addon.getSetting('use_thumb') == "true":
                    fanArt = thumbnail
                else:
                    fanArt = fanart

                if channel.find('info') is not None:
                    desc = channel.find('info').text
                else:
                    desc = ''

                if channel.find('genre') is not None:
                    genre = channel.find('genre').text
                else:
                    genre = ''

                if channel.find('date') is not None:
                    date = channel.find('date').text
                else:
                    date = ''

                if channel.find('credits') is not None:
                    credits = channel.find('credits').text
                else:
                    credits = ''

                try:
                    name = name.encode('utf-8') if six.PY2 else name
                    if linkedUrl == '':
                        url = url.encode('utf-8') if six.PY2 else url
                        addDir(name, url, 2, thumbnail, fanArt, desc, genre, date, credits, True)
                    else:
                        linkedUrl = linkedUrl.encode('utf-8') if six.PY2 else linkedUrl
                        addDir(name, linkedUrl, 1, thumbnail, fanArt, desc, genre, date, None, 'source')
                except:
                    addon_log('There was a problem adding directory from getData(): {0}'.format(name))

        if channels is None or len(channels) == 0:
            addon_log('No Channels: getItems')
            getItems(soup.findall('item'), fanart)

    else:
        parse_m3u(soup)


# borrow from https://github.com/enen92/P2P-Streams-XBMC/blob/master/plugin.video.p2p-streams/resources/core/livestreams.py
# This will not go through the getItems functions ( means you must have ready to play url, no regex)
def parse_m3u(data):
    content = data.rstrip()
    match = re.compile(r'#EXTINF:(.+?),(.*?)[\n\r]+([^\r\n]+)').findall(content)
    total = len(match)
    for other, channel_name, stream_url in match:
        if 'tvg-logo' in other:
            thumbnail = re_me(other, 'tvg-logo=[\'"](.*?)[\'"]')
            if thumbnail:
                if thumbnail.startswith('http'):
                    thumbnail = thumbnail
                elif addon.getSetting('logo-folderPath') != "":
                    logo_url = addon.getSetting('logo-folderPath')
                    thumbnail = logo_url + thumbnail
                else:
                    thumbnail = thumbnail
        else:
            thumbnail = ''

        if 'type' in other:
            mode_type = re_me(other, 'type=[\'"](.*?)[\'"]')
            if mode_type == 'yt-dl':
                stream_url = stream_url + "&mode=18"
            elif mode_type == 'regex':
                url = stream_url.split('&regexs=')
                regexs = parse_regex(getSoup('', data=url[1]))

                addLink(url[0], channel_name, thumbnail, '', '', '', '', '', None, regexs, total)
                continue
        elif tsdownloader and '.ts' in stream_url:
            stream_url = 'plugin://plugin.video.f4mTester/?url={0}&amp;streamtype=TSDOWNLOADER&name={1}'.format(urllib_parse.quote_plus(stream_url), urllib_parse.quote(channel_name))
        elif hlsretry and '.m3u8' in stream_url:
            stream_url = 'plugin://plugin.video.f4mTester/?url={0}&amp;streamtype=HLSRETRY&name={1}'.format(urllib_parse.quote_plus(stream_url), urllib_parse.quote(channel_name))
        addLink(stream_url, channel_name, thumbnail, '', '', '', '', '', None, '', total)


def getChannelItems(name, url, fanart):
    soup = getSoup(url)
    channel_list = soup.find('./channel/[name="{0}"]'.format(name))
    if channel_list.find('items') is not None:
        items = channel_list.find('items').findall('item')
    else:
        items = channel_list.findall('item')
    if channel_list.find('fanart') is not None:
        fanArt = channel_list.find('fanart').text
    else:
        fanArt = fanart
    for channel in channel_list.findall('subchannel'):
        name = channel.find('name').text
        name = processPyFunction(name)

        if channel.find('thumbnail') is not None:
            thumbnail = channel.find('thumbnail').text
            thumbnail = processPyFunction(thumbnail)
        else:
            thumbnail = ''

        if channel.find('fanart') is not None:
            fanArt = channel.find('fanart').text
        elif addon.getSetting('use_thumb') == "true":
            fanArt = thumbnail
        else:
            fanArt = ''

        if channel.find('info') is not None:
            desc = channel.find('info').text
        else:
            desc = ''

        if channel.find('genre') is not None:
            genre = channel.find('genre').text
        else:
            genre = ''

        if channel.find('date') is not None:
            date = channel.find('date').text
        else:
            date = ''

        if channel.find('credits') is not None:
            credits = channel.find('credits').text
        else:
            credits = ''

        try:
            if six.PY2:
                name = name.encode('utf-8')
                url = url.encode('utf-8')
            addDir(name, url, 3, thumbnail, fanArt, desc, genre, credits, date)
        except:
            addon_log('There was a problem adding directory - {0}'.format(name))
    getItems(items, fanArt)


def getSubChannelItems(name, url, fanart):
    soup = getSoup(url)
    channel_list = soup.find('./channel/subchannel/[name="{0}"]'.format(name))
    items = channel_list.find('subitems').findall('subitem')
    getItems(items, fanart)


def getItems(items, fanart, dontLink=False):
    total = len(items)
    # addon_log('Total Items: {0}'.format(total))
    add_playlist = addon.getSetting('add_playlist')
    ask_playlist_items = addon.getSetting('ask_playlist_items')
    parentalblock = addon.getSetting('parentalblocked')
    parentalblock = parentalblock == "true"
    for item in items:
        isXMLSource = False
        isJsonrpc = False

        if isinstance(item.find('parentalblock'), ElementTree.Element):
            applyblock = item.find('parentalblock').text
        else:
            applyblock = 'false'
        if applyblock == 'true' and parentalblock:
            continue

        if isinstance(item.find('title'), ElementTree.Element):
            name = item.find('title').text
            if name == '':
                name = 'unknown?'
            name = processPyFunction(name)
        else:
            addon_log('Name Error')
            name = ''

        regexs = None
        if isinstance(item.find('regex'), ElementTree.Element):
            regexs = parse_regex(item.findall('regex'))

        iepg = None
        try:
            if isinstance(item.find('epg'), ElementTree.Element):
                # addon_log('xxxxxxxxxxxxxxitemEPG')
                # ** basic regex on epg_url tag for epg added to item name ** #
                if isinstance(item.find('epg_url'), ElementTree.Element) and item.find('epg_url').text is not None:
                    try:
                        epg_url = item.find('epg_url').text
                        epg_regex = item.find('epg_regex').text
                        epg_name = get_epg(epg_url, epg_regex)
                        if epg_name:
                            name += ' - ' + epg_name
                    except:
                        pass

                # ** py function block regex to generate epg for item plot ** #
                elif item.find('epg').text:
                    epg = item.find('epg').text

                    if '$doregex' in epg:
                        reg_item = item.find('epg_regex')

                        # if page tag is not provided use epg generated in channel info or items info
                        if isinstance(reg_item.find('page'), ElementTree.Element):
                            if reg_item.find('page').text is None or reg_item.find('page').text == "":
                                filename = 'LSProPageEPG.txt'
                                filenamewithpath = os.path.join(functions_dir, filename)
                                reg_item.find('page').text = filenamewithpath

                            regexs = parse_regex(reg_item)
                            iepg, setres = getRegexParsed(regexs, epg)

                    # ** or add static epg to item name ** #
                    else:
                        name += getepg(item.find('epg').text)

            else:
                pass

        except BaseException as err:
            addon_log('Error getting item EPG: {0}'.format(str(err)))

        try:
            url = []
            if len(item.findall('link')) > 0:
                for i in item.findall('link'):
                    if i.text is not None:
                        url.append(i.text)
            elif len(item.findall('sportsdevil')) > 0:
                for i in item.findall('sportsdevil'):
                    if i.text is not None:
                        sd_plugin = "plugin://plugin.video.SportsDevil" if six.PY2 else "plugin://plugin.video.sportsdevil"
                        sportsdevil = sd_plugin + '/?mode=1&amp;item=catcher%3dstreams%26url=' + i.text + '%26videoTitle=' + name
                        if item.find('referer'):
                            sportsdevil = sportsdevil + '%26referer=' + item.find('referer').text
                        url.append(sportsdevil)
            elif len(item.findall('yt-dl')) > 0:
                for i in item.findall('yt-dl'):
                    if i.text is not None:
                        ytdl = i.text + '&mode=18'
                        url.append(ytdl)
            elif len(item.findall('dm')) > 0:
                for i in item.findall('dm'):
                    if i.text is not None:
                        dm = "plugin://plugin.video.dailymotion_com/?mode=playVideo&url=" + i.text
                        url.append(dm)
            elif len(item.findall('dmlive')) > 0:
                for i in item.findall('dmlive'):
                    if i.text is not None:
                        dm = "plugin://plugin.video.dailymotion_com/?mode=playLiveVideo&url=" + i.text
                        url.append(dm)
            elif len(item.findall('utube')) > 0:
                for i in item.findall('utube'):
                    if i.text is not None:
                        if ' ' in i.text:
                            utube = 'plugin://plugin.video.youtube/search/?q=' + urllib_parse.quote_plus(i.text)
                            isJsonrpc = utube
                        elif len(i.text) == 11:
                            utube = 'plugin://plugin.video.youtube/play/?video_id=' + i.text
                        elif (i.text.startswith('PL') and '&order=' not in i.text) or i.text.startswith('UU'):
                            utube = 'plugin://plugin.video.youtube/play/?&order=default&playlist_id=' + i.text
                        elif i.text.startswith('PL') or i.text.startswith('UU'):
                            utube = 'plugin://plugin.video.youtube/play/?playlist_id=' + i.text
                        elif i.text.startswith('UC') and len(i.text) > 12:
                            utube = 'plugin://plugin.video.youtube/channel/' + i.text + '/'
                            isJsonrpc = utube
                        elif not i.text.startswith('UC') and not (i.text.startswith('PL')):
                            utube = 'plugin://plugin.video.youtube/user/' + i.text + '/'
                            isJsonrpc = utube
                    url.append(utube)
            elif len(item.findall('f4m')) > 0:
                for i in item.findall('f4m'):
                    if i.text is not None:
                        if '.f4m' in i.text:
                            f4m = 'plugin://plugin.video.f4mTester/?url=' + urllib_parse.quote_plus(i.text)
                        elif '.m3u8' in i.text:
                            f4m = 'plugin://plugin.video.f4mTester/?url=' + urllib_parse.quote_plus(i.text) + '&amp;streamtype=HLS'
                        else:
                            f4m = 'plugin://plugin.video.f4mTester/?url=' + urllib_parse.quote_plus(i.text) + '&amp;streamtype=SIMPLE'
                    url.append(f4m)

            elif len(item.findall('urlsolve')) > 0:
                for i in item.findall('urlsolve'):
                    if i.text is not None:
                        resolver = i.text + '&mode=19'
                        url.append(resolver)

            elif len(item.findall('inputstream')) > 0:
                for i in item.findall('inputstream'):
                    if i.text is not None:
                        istream = i.text + '&mode=20'
                        url.append(istream)

            elif len(item.findall('slproxy')) > 0:
                for i in item.findall('slproxy'):
                    if i.text is not None:
                        istream = i.text + '&mode=22'
                        url.append(istream)

            if len(url) < 1:
                # continue
                raise Exception()
        except:
            addon_log('Error <link> element, Passing: {0}'.format(name.encode('utf-8') if six.PY2 else name))
            traceback.print_exc()
            continue

        if isinstance(item.find('externallink'), ElementTree.Element):
            isXMLSource = item.find('externallink').text

        if isXMLSource:
            ext_url = [isXMLSource]
            isXMLSource = True

        if isinstance(item.find('jsonrpc'), ElementTree.Element):
            isJsonrpc = item.find('jsonrpc').text

        if isJsonrpc:
            ext_url = [isJsonrpc]
            isJsonrpc = True

        if isinstance(item.find('thumbnail'), ElementTree.Element):
            thumbnail = item.find('thumbnail').text
            thumbnail = processPyFunction(thumbnail)
        else:
            thumbnail = ''

        if isinstance(item.find('fanart'), ElementTree.Element):
            fanArt = item.find('fanart').text
        elif addon.getSetting('use_thumb') == "true":
            fanArt = thumbnail
        else:
            fanArt = fanart

        if isinstance(item.find('info'), ElementTree.Element):
            desc = item.find('info').text
        else:
            # ** use item epg in plot if present ** #
            if iepg:
                desc = iepg
            else:
                desc = ''

        if isinstance(item.find('genre'), ElementTree.Element):
            genre = item.find('genre').text
        else:
            genre = ''

        if isinstance(item.find('date'), ElementTree.Element):
            date = item.find('date').text
        else:
            date = ''

        try:
            if len(url) > 1:
                alt = 0
                playlist = []
                ignorelistsetting = True if '$$LSPlayOnlyOne$$' in url[0] else False

                for i in url:
                    if add_playlist == "false" and not ignorelistsetting:
                        alt += 1
                        addLink(i, '{0}) {1}'.format(alt, name.encode('utf-8', 'ignore') if six.PY2 else name), thumbnail, fanArt, desc, genre, date, True, playlist, regexs, total)
                    elif (add_playlist == "true" and ask_playlist_items == 'true') or ignorelistsetting:
                        if regexs:
                            playlist.append(i + '&regexs=' + regexs)
                        elif any(x in i for x in resolve_url) and i.startswith('http'):
                            playlist.append(i + '&mode=19')
                        else:
                            playlist.append(i)
                    else:
                        playlist.append(i)

                if len(playlist) > 1:
                    addLink('', name.encode('utf-8') if six.PY2 else name, thumbnail, fanArt, desc, genre, date, True, playlist, regexs, total)
            else:
                if dontLink:
                    return name, url[0], regexs
                if isXMLSource:
                    if six.PY2:
                        name = name.encode('utf-8')
                        ext_url[0] = ext_url[0].encode('utf-8')
                        url[0] = url[0].encode('utf-8')
                    if regexs is not None:  # <externallink> and <regex>
                        addDir(name, ext_url[0], 1, thumbnail, fanArt, desc, genre, date, None, '!!update', regexs, url[0])
                    else:
                        addDir(name, ext_url[0], 1, thumbnail, fanArt, desc, genre, date, None, 'source', None, None)
                elif isJsonrpc:
                    addDir(name.encode('utf-8') if six.PY2 else name, ext_url[0], 53, thumbnail, fanArt, desc, genre, date, None, 'source')
                else:
                    try:
                        if '$doregex' in name and getRegexParsed is not None:
                            tname, setres = getRegexParsed(regexs, name)
                            if tname is not None:
                                name = tname
                    except:
                        pass
                    try:
                        if '$doregex' in thumbnail and getRegexParsed is not None:
                            tname, setres = getRegexParsed(regexs, thumbnail)
                            if tname is not None:
                                thumbnail = tname
                    except:
                        pass
                    addLink(url[0], name.encode('utf-8') if six.PY2 else name, thumbnail, fanArt, desc, genre, date, True, None, regexs, total)
        except:
            traceback.print_exc()
            addon_log('There was a problem adding item - {0}'.format(repr(name)))


def parse_regex(reg_items):
    reg_tags = ['name', 'expres', 'page', 'referer', 'connection', 'notplayable', 'noredirect', 'origin', 'agent',
                'accept', 'includeheaders', 'listrepeat', 'proxy', 'x-req', 'x-addr', 'x-forward', 'post', 'rawpost',
                'htmlunescape', 'readcookieonly', 'cookiejar', 'setcookie', 'appendcookie', 'ignorecache', 'thumbnail']
    regexs = {}

    if isinstance(reg_items, ElementTree.Element):
        reg_items = [reg_items]

    for reg_item in reg_items:

        rname = reg_item.find('name').text
        sregexs = {}
        for i in reg_item:
            if i.tag in reg_tags:
                sregexs.update({i.tag: i.text})
            else:
                addon_log('Unsupported tag: {0}'.format(i.tag), LOGINFO)
        if not sregexs.get('expres'):
            sregexs.update({'expres': ''})
        if not sregexs.get('cookiejar'):
            sregexs.update({'cookiejar': ''})
        regexs.update({rname: sregexs})

    regexs = urllib_parse.quote(repr(regexs))
    return regexs


# copies from lamda's implementation
def get_ustream(url):
    try:
        for i in range(1, 51):
            result = getUrl(url)
            if "EXT-X-STREAM-INF" in result:
                return url
            if "EXTM3U" not in result:
                return
            xbmc.sleep(2000)
        return
    except:
        return


def getRegexParsed(regexs, url, cookieJar=None, forCookieJarOnly=False, recursiveCall=False, cachedPages={}, rawPost=False, cookie_jar_file=None):  # 0,1,2 = URL, regexOnly, CookieJarOnly
    if not recursiveCall:
        regexs = eval(urllib_parse.unquote(regexs))

    doRegexs = re.compile(r'\$doregex\[([^\]]*)\]').findall(url)
    setresolved = True
    for k in doRegexs:
        if k in regexs:
            m = regexs[k]
            cookieJarParam = False
            if 'cookiejar' in m:  # so either create or reuse existing jar
                cookieJarParam = m['cookiejar']
                if '$doregex' in cookieJarParam:
                    cookieJar = getRegexParsed(regexs, m['cookiejar'], cookieJar, True, True, cachedPages)
                    cookieJarParam = True
                else:
                    cookieJarParam = True

            if cookieJarParam:
                if cookieJar is None:
                    cookie_jar_file = None
                    if 'open[' in m['cookiejar']:
                        cookie_jar_file = m['cookiejar'].split('open[')[1].split(']')[0]
                    cookieJar = getCookieJar(cookie_jar_file)
                    if cookie_jar_file:
                        saveCookieJar(cookieJar, cookie_jar_file)
                elif 'save[' in m['cookiejar']:
                    cookie_jar_file = m['cookiejar'].split('save[')[1].split(']')[0]
                    complete_path = os.path.join(profile, cookie_jar_file)
                    # saveCookieJar(cookieJar, cookie_jar_file)  # gujal
                    saveCookieJar(cookieJar, complete_path)
            if m['page'] and '$doregex' in m['page']:
                pg = getRegexParsed(regexs, m['page'], cookieJar, recursiveCall=True, cachedPages=cachedPages)
                if len(pg) == 0:
                    pg = 'http://regexfailed'
                m['page'] = pg

            if 'setcookie' in m and m['setcookie'] and '$doregex' in m['setcookie']:
                m['setcookie'] = getRegexParsed(regexs, m['setcookie'], cookieJar, recursiveCall=True, cachedPages=cachedPages)
            if 'appendcookie' in m and m['appendcookie'] and '$doregex' in m['appendcookie']:
                m['appendcookie'] = getRegexParsed(regexs, m['appendcookie'], cookieJar, recursiveCall=True, cachedPages=cachedPages)

            if 'post' in m and '$doregex' in m['post']:
                m['post'] = getRegexParsed(regexs, m['post'], cookieJar, recursiveCall=True, cachedPages=cachedPages)

            if 'rawpost' in m and '$doregex' in m['rawpost']:
                m['rawpost'] = getRegexParsed(regexs, m['rawpost'], cookieJar, recursiveCall=True, cachedPages=cachedPages, rawPost=True)

            if 'rawpost' in m and '$epoctime$' in m['rawpost']:
                m['rawpost'] = m['rawpost'].replace('$epoctime$', getEpocTime())

            if 'rawpost' in m and '$epoctime2$' in m['rawpost']:
                m['rawpost'] = m['rawpost'].replace('$epoctime2$', getEpocTime2())

            link = ''
            if m['page'] and m['page'] in cachedPages and 'ignorecache' not in m and forCookieJarOnly is False:
                link = cachedPages[m['page']]
            else:
                if m['page'] and m['page'] != '' and m['page'].startswith('http'):
                    if '$epoctime$' in m['page']:
                        m['page'] = m['page'].replace('$epoctime$', getEpocTime())
                    if '$epoctime2$' in m['page']:
                        m['page'] = m['page'].replace('$epoctime2$', getEpocTime2())

                    page_split = m['page'].split('|')
                    pageUrl = page_split[0]
                    header_in_page = None
                    if len(page_split) > 1:
                        header_in_page = page_split[1]

                    current_proxies = urllib_request.ProxyHandler(urllib_request.getproxies())
                    req = urllib_request.Request(pageUrl)
                    if 'proxy' in m:
                        proxytouse = m['proxy']
                        if pageUrl[:5] == "https":
                            proxy = urllib_request.ProxyHandler({'https': proxytouse})
                        else:
                            proxy = urllib_request.ProxyHandler({'http': proxytouse})
                        opener = urllib_request.build_opener(proxy)
                        urllib_request.install_opener(opener)

                    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:14.0) Gecko/20100101 Firefox/14.0.1')
                    proxytouse = None

                    if 'referer' in m:
                        req.add_header('Referer', m['referer'])
                    if 'accept' in m:
                        req.add_header('Accept', m['accept'])
                    if 'agent' in m:
                        req.add_header('User-agent', m['agent'])
                    if 'x-req' in m:
                        req.add_header('X-Requested-With', m['x-req'])
                    if 'x-addr' in m:
                        req.add_header('x-addr', m['x-addr'])
                    if 'x-forward' in m:
                        req.add_header('X-Forwarded-For', m['x-forward'])
                    if 'setcookie' in m:
                        req.add_header('Cookie', m['setcookie'])
                    if 'appendcookie' in m:
                        cookiestoApend = m['appendcookie']
                        cookiestoApend = cookiestoApend.split(';')
                        for h in cookiestoApend:
                            n, v = h.split('=')
                            w, n = n.split(':')
                            ck = http_cookiejar.Cookie(version=0, name=n, value=v, port=None, port_specified=False, domain=w, domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
                            cookieJar.set_cookie(ck)
                    if 'origin' in m:
                        req.add_header('Origin', m['origin'])
                    if header_in_page:
                        header_in_page = header_in_page.split('&')
                        for h in header_in_page:
                            if h.split('=') == 2:
                                n, v = h.split('=')
                            else:
                                vals = h.split('=')
                                n = vals[0]
                                v = '='.join(vals[1:])
                            req.add_header(n, v)

                    if cookieJar is not None:
                        cookie_handler = urllib_request.HTTPCookieProcessor(cookieJar)
                        opener = urllib_request.build_opener(cookie_handler, urllib_request.HTTPBasicAuthHandler(), urllib_request.HTTPHandler())
                        opener = urllib_request.install_opener(opener)

                        if 'noredirect' in m:
                            opener = urllib_request.build_opener(cookie_handler, NoRedirection, urllib_request.HTTPBasicAuthHandler(), urllib_request.HTTPHandler())
                            opener = urllib_request.install_opener(opener)
                    elif 'noredirect' in m:
                        opener = urllib_request.build_opener(NoRedirection, urllib_request.HTTPBasicAuthHandler(), urllib_request.HTTPHandler())
                        opener = urllib_request.install_opener(opener)

                    if 'connection' in m:
                        from keepalive import HTTPHandler
                        keepalive_handler = HTTPHandler()
                        opener = urllib_request.build_opener(keepalive_handler)
                        urllib_request.install_opener(opener)

                    post = None
                    if 'post' in m:
                        postData = m['post']
                        splitpost = postData.split(',')
                        post = {}
                        for p in splitpost:
                            n = p.split(':')[0]
                            v = p.split(':')[1]
                            post[n] = v
                        post = urllib_parse.urlencode(post)

                    if 'rawpost' in m:
                        post = m['rawpost']

                    link = ''

                    try:
                        if post is not None:
                            response = urllib_request.urlopen(req, post.encode('utf-8'))
                        else:
                            response = urllib_request.urlopen(req)
                        if response.info().get('Content-Encoding') == 'gzip':
                            import gzip
                            buf = six.StringIO(response.read())
                            f = gzip.GzipFile(fileobj=buf)
                            link = f.read()
                        else:
                            link = response.read()

                        encoding = None
                        content_type = response.headers.get('content-type', '')
                        if 'charset=' in content_type:
                            encoding = content_type.split('charset=')[-1]

                        if encoding is None:
                            epattern = r'<meta\s+http-equiv="Content-Type"\s+content="(?:.+?);\s+charset=(.+?)"'
                            epattern = epattern.encode('utf8') if six.PY3 else epattern
                            r = re.search(epattern, link, re.IGNORECASE)
                            if r:
                                encoding = r.group(1).decode('utf8') if six.PY3 else r.group(1)
                            else:
                                epattern = r'''<meta\s+charset=["']?([^"'>]+)'''
                                epattern = epattern.encode('utf8') if six.PY3 else epattern
                                r = re.search(epattern, link, re.IGNORECASE)
                                if r:
                                    encoding = r.group(1).decode('utf8') if six.PY3 else r.group(1)

                        if encoding is not None:
                            link = link.decode(encoding.lower(), errors='ignore')
                            link = link.encode('utf8') if six.PY2 else link
                        else:
                            link = link.decode('utf-8', errors='ignore') if six.PY3 else link.encode('utf-8')

                        if 'proxy' in m and current_proxies is not None:
                            urllib_request.install_opener(urllib_request.build_opener(current_proxies))

                        link = javascriptUnEscape(link)

                        if 'includeheaders' in m:
                            link += '$$HEADERS_START$$:'
                            for b in response.headers:
                                link += b + ':' + response.headers.get(b) + '\n'
                            link += '$$HEADERS_END$$:'

                        # addon_log(link)
                        addon_log(cookieJar)

                        response.close()
                    except:
                        # traceback.print_exc()
                        pass
                    cachedPages[m['page']] = link

                    if forCookieJarOnly:
                        return cookieJar  # do nothing
                elif m['page'] and not m['page'].startswith('http'):
                    if m['page'].startswith('$pyFunction:'):
                        val = doEval(m['page'].split('$pyFunction:')[1], '', cookieJar, m)
                        if forCookieJarOnly:
                            return cookieJar  # do nothing
                        link = val
                        link = javascriptUnEscape(link)
                    else:
                        link = m['page']

            if '$pyFunction:playmedia(' in m['expres'] or 'ActivateWindow' in m['expres'] or 'RunPlugin' in m['expres'] or '$PLAYERPROXY$=' in url or any(x in url for x in g_ignoreSetResolved):
                setresolved = False
            if '$doregex' in m['expres']:
                m['expres'] = getRegexParsed(regexs, m['expres'], cookieJar, recursiveCall=True, cachedPages=cachedPages)

            if m['expres'] != '':
                if '$LiveStreamCaptcha' in m['expres']:
                    val = askCaptcha(m, link, cookieJar)
                    url = url.replace("$doregex[" + k + "]", val)

                elif m['expres'].startswith('$pyFunction:') or '#$pyFunction' in m['expres']:
                    val = ''
                    if m['expres'].startswith('$pyFunction:'):
                        val = doEval(m['expres'].split('$pyFunction:')[1], link, cookieJar, m)
                    else:
                        val = doEvalFunction(m['expres'], link, cookieJar, m)
                    
                    if 'ActivateWindow' in m['expres'] or 'RunPlugin' in m['expres']:
                        return '', False
                    if forCookieJarOnly:
                        return cookieJar  # do nothing
                    if 'listrepeat' in m:
                        listrepeat = m['listrepeat']
                        return listrepeat, eval(val), m, regexs, cookieJar

                    try:
                        url = url.replace(u"$doregex[" + k + "]", val)
                    except:
                        url = url.replace("$doregex[" + k + "]", val.decode("utf-8"))
                else:
                    if 'listrepeat' in m:
                        listrepeat = m['listrepeat']
                        ret = re.findall(m['expres'], link)
                        return listrepeat, ret, m, regexs, cookieJar

                    val = ''
                    if link != '':
                        reg = re.compile(m['expres']).search(link)
                        if reg:
                            val = reg.group(1).strip()

                    elif m['page'] == '' or m['page'] is None:
                        val = m['expres']

                    if rawPost:
                        val = urllib_parse.quote_plus(val)
                    if 'htmlunescape' in m:
                        val = html_parser.HTMLParser().unescape(val)
                    try:
                        url = url.replace("$doregex[" + k + "]", val)
                    except:
                        url = url.replace("$doregex[" + k + "]", val.decode("utf-8"))

            else:
                url = url.replace("$doregex[" + k + "]", '')

    if '$epoctime$' in url:
        url = url.replace('$epoctime$', getEpocTime())
    if '$epoctime2$' in url:
        url = url.replace('$epoctime2$', getEpocTime2())

    if '$GUID$' in url:
        import uuid
        url = url.replace('$GUID$', str(uuid.uuid1()).upper())
    if '$get_cookies$' in url:
        url = url.replace('$get_cookies$', getCookiesString(cookieJar))

    if recursiveCall:
        return url

    if url == "":
        return
    else:
        return url, setresolved


def getmd5(t):
    import hashlib
    h = hashlib.md5()
    h.update(t)
    return h.hexdigest()


def playmedia(media_url):
    try:
        import CustomPlayer
        player = CustomPlayer.MyXBMCPlayer()
        listitem = xbmcgui.ListItem(label=str(name), path=media_url)
        listitem.setArt({'thumb': xbmc.getInfoImage("ListItem.Thumb"),
                         'icon': "DefaultVideo.png"})
        player.play(media_url, listitem)
        xbmc.sleep(1000)
        while player.is_active:
            xbmc.sleep(200)
    except:
        traceback.print_exc()
    return ''


def kodiJsonRequest(params):
    data = json.dumps(params)
    request = xbmc.executeJSONRPC(data)

    try:
        response = json.loads(request)
    except UnicodeDecodeError:
        response = json.loads(request.decode('utf-8', 'ignore'))

    try:
        if 'result' in response:
            return response['result']
        return None
    except KeyError:
        addon_log("[%s] %s" % (params['method'], response['error']['message']))
        return None


def setKodiProxy(proxysettings=None):

    if proxysettings is None:
        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"network.usehttpproxy", "value":false}, "id":1}')
    else:
        ps = proxysettings.split(':')
        proxyURL = ps[0]
        proxyPort = ps[1]
        proxyType = ps[2]
        proxyUsername = None
        proxyPassword = None

        if len(ps) > 3 and '@' in ps[3]:  # jairox ###proxysettings
            proxyUsername = ps[3].split('@')[0]  # jairox ###ps[3]
            proxyPassword = ps[3].split('@')[1]  # jairox ###proxysettings.split('@')[-1]

        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"network.usehttpproxy", "value":true}, "id":1}')
        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"network.httpproxytype", "value":' + str(proxyType) + '}, "id":1}')
        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"network.httpproxyserver", "value":"' + str(proxyURL) + '"}, "id":1}')
        xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"network.httpproxyport", "value":' + str(proxyPort) + '}, "id":1}')

        if proxyUsername is not None:
            xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"network.httpproxyusername", "value":"' + str(proxyUsername) + '"}, "id":1}')
            xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Settings.SetSettingValue", "params":{"setting":"network.httpproxypassword", "value":"' + str(proxyPassword) + '"}, "id":1}')


def getConfiguredProxy():
    proxyActive = kodiJsonRequest({'jsonrpc': '2.0', "method": "Settings.GetSettingValue", "params": {"setting": "network.usehttpproxy"}, 'id': 1})['value']
    proxyType = kodiJsonRequest({'jsonrpc': '2.0', "method": "Settings.GetSettingValue", "params": {"setting": "network.httpproxytype"}, 'id': 1})['value']

    if proxyActive:  # PROXY_HTTP
        proxyURL = kodiJsonRequest({'jsonrpc': '2.0', "method": "Settings.GetSettingValue", "params": {"setting": "network.httpproxyserver"}, 'id': 1})['value']
        proxyPort = six.text_type(kodiJsonRequest({'jsonrpc': '2.0', "method": "Settings.GetSettingValue", "params": {"setting": "network.httpproxyport"}, 'id': 1})['value'])
        proxyUsername = kodiJsonRequest({'jsonrpc': '2.0', "method": "Settings.GetSettingValue", "params": {"setting": "network.httpproxyusername"}, 'id': 1})['value']
        proxyPassword = kodiJsonRequest({'jsonrpc': '2.0', "method": "Settings.GetSettingValue", "params": {"setting": "network.httpproxypassword"}, 'id': 1})['value']

        if proxyUsername and proxyPassword and proxyURL and proxyPort:
            return proxyURL + ':' + str(proxyPort) + ':' + str(proxyType) + ':' + proxyUsername + '@' + proxyPassword
        elif proxyURL and proxyPort:
            return proxyURL + ':' + str(proxyPort) + ':' + str(proxyType)
    else:
        return None


def playmediawithproxy(media_url, name, iconImage, proxyip, port, proxyuser=None, proxypass=None):  # jairox

    if media_url is None or media_url == '':
        xbmcgui.Dialog().notification(addon_name, 'Unable to play empty Url', icon, 5000, False)
        return
    progress = xbmcgui.DialogProgress()
    progress.create('Progress', 'Playing with custom proxy')
    progress.update(10, "", "setting proxy..", "")
    proxyset = False
    existing_proxy = ''
    try:
        existing_proxy = getConfiguredProxy()
        # read and set here
        # jairox
        if proxyuser is not None:
            setKodiProxy(proxyip + ':' + port + ':0:' + proxyuser + '@' + proxypass)
        else:
            setKodiProxy(proxyip + ':' + port + ':0')

        proxyset = True
        progress.update(80, "", "setting proxy complete, now playing", "")

        import CustomPlayer
        player = CustomPlayer.MyXBMCPlayer()
        player.pdialogue == progress
        listitem = xbmcgui.ListItem(label=str(name), path=media_url)
        listitem.setArt({'thumb': xbmc.getInfoImage("ListItem.Thumb"),
                         'icon': iconImage})
        player.play(media_url, listitem)
        xbmc.sleep(1000)
        beforestart = time.time()
        try:
            while player.is_active:
                xbmc.sleep(1000)
                if player.urlplayed is False and time.time() - beforestart > 12:
                    xbmcgui.Dialog().notification(addon_name, 'Unable to play, check proxy', icon, 5000, False)
                    break
        except:
            pass

        progress.close()
        progress = None
    except:
        traceback.print_exc()
    if progress:
        progress.close()
    if proxyset:
        setKodiProxy(existing_proxy)
    return ''


def createM3uForDash(url, useragent=None):
    str = '#EXTM3U'
    str += '\n#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=361816'
    str += '\n' + url + '&bytes=0-200000'
    source_file = os.path.join(profile, 'testfile.m3u')
    str += '\n'
    SaveToFile(source_file, str)
    return source_file


def SaveToFile(file_name, page_data, append=False):
    if append:
        f = open(file_name, 'a')
        f.write(page_data)
        f.close()
    else:
        f = open(file_name, 'wb')
        f.write(page_data)
        f.close()
        return ''


def LoadFile(file_name):
    f = open(file_name, 'rb')
    d = f.read()
    f.close()
    return d


def re_me(data, re_patten):
    match = ''
    m = re.search(re_patten, data)
    if m is not None:
        match = m.group(1)
    else:
        match = ''
    return match


def get_unwise(str_eval):
    global w, i, s, e
    page_value = ""
    w, i, s, e = None
    try:
        ss = "w,i,s,e=(" + str_eval + ')'
        six.exec_(ss, globals())
        page_value = unwise_func(w, i, s, e)  # noQA
    except:
        traceback.print_exc(file=sys.stdout)
    return page_value


def unwise_func(w, i, s, e):
    lIll = 0
    ll1I = 0
    Il1l = 0
    ll1l = []
    l1lI = []
    while True:
        if (lIll < 5):
            l1lI.append(w[lIll])
        elif (lIll < len(w)):
            ll1l.append(w[lIll])
        lIll += 1
        if (ll1I < 5):
            l1lI.append(i[ll1I])
        elif (ll1I < len(i)):
            ll1l.append(i[ll1I])
        ll1I += 1
        if (Il1l < 5):
            l1lI.append(s[Il1l])
        elif (Il1l < len(s)):
            ll1l.append(s[Il1l])
        Il1l += 1
        if (len(w) + len(i) + len(s) + len(e) == len(ll1l) + len(l1lI) + len(e)):
            break

    lI1l = ''.join(ll1l)
    I1lI = ''.join(l1lI)
    ll1I = 0
    l1ll = []
    for lIll in range(0, len(ll1l), 2):
        ll11 = -1
        if (ord(I1lI[ll1I]) % 2):
            ll11 = 1
        l1ll.append(chr(int(lI1l[lIll: lIll + 2], 36) - ll11))
        ll1I += 1
        if (ll1I >= len(l1lI)):
            ll1I = 0
    ret = ''.join(l1ll)
    if 'eval(function(w,i,s,e)' in ret:
        ret = re.compile(r'eval\(function\(w,i,s,e\).*}\((.*?)\)').findall(ret)[0]
        return get_unwise(ret)
    else:
        return ret


def get_unpacked(page_value, regex_for_text='', iterations=1, total_iteration=1):
    try:
        if page_value.startswith("http"):
            page_value = getUrl(page_value)
        if regex_for_text and len(regex_for_text) > 0:
            try:
                page_value = re.compile(regex_for_text).findall(page_value)[0]  # get the js variable
            except:
                return 'NOTPACKED'
        page_value = unpack(page_value, iterations, total_iteration)
    except:
        page_value = 'UNPACKEDFAILED'
        traceback.print_exc(file=sys.stdout)

    return page_value


def unpack(sJavascript, iteration=1, totaliterations=2):
    global myarray, p1, a1, c1, k1
    if sJavascript.startswith('var _0xcb8a='):
        aSplit = sJavascript.split('var _0xcb8a=')
        myarray = []
        ss = "myarray=" + aSplit[1].split("eval(")[0]
        six.exec_(ss, globals())
        a1 = 62
        c1 = int(aSplit[1].split(",62,")[1].split(',')[0])
        p1 = myarray[0]  # noQA
        k1 = myarray[3]  # noQA
        with xbmcvfs.File('temp file' + str(iteration) + '.js', "wb") as filewriter:
            filewriter.write(str(k1))
    else:
        if "rn p}('" in sJavascript:
            aSplit = sJavascript.split("rn p}('")
        else:
            aSplit = sJavascript.split("rn A}('")

        p1, a1, c1, k1 = ('', '0', '0', '')
        ss = "p1,a1,c1,k1=('" + aSplit[1].split(".spli")[0] + ')'
        six.exec_(ss, globals())
    
    k1 = k1.split('|')
    aSplit = aSplit[1].split("))'")
    e = ''
    d = ''
    sUnpacked1 = str(__unpack(p1, a1, c1, k1, e, d, iteration))

    if iteration >= totaliterations:
        return sUnpacked1
    else:
        return unpack(sUnpacked1, iteration + 1)


def __unpack(p, a, c, k, e, d, iteration, v=1):
    while (c >= 1):
        c = c - 1
        if (k[c]):
            aa = str(__itoaNew(c, a))
            if v == 1:
                p = re.sub('\\b' + aa + '\\b', k[c], p)  # THIS IS Bloody slow!
            else:
                p = findAndReplaceWord(p, aa, k[c])
    return p


# function equalavent to re.sub('\\b' + aa +'\\b', k[c], p)
def findAndReplaceWord(source_str, word_to_find, replace_with):
    splits = None
    splits = source_str.split(word_to_find)
    if len(splits) > 1:
        new_string = []
        current_index = 0
        for current_split in splits:
            new_string.append(current_split)
            val = word_to_find  # by default assume it was wrong to split

            # if its first one and item is blank then check next item is valid or not
            if current_index == len(splits) - 1:
                val = ''  # last one nothing to append normally
            else:
                if len(current_split) == 0:  # if blank check next one with current split value
                    if (len(splits[current_index + 1]) == 0 and word_to_find[0].lower() not in 'abcdefghijklmnopqrstuvwxyz1234567890_') \
                            or (len(splits[current_index + 1]) > 0 and splits[current_index + 1][0].lower() not in 'abcdefghijklmnopqrstuvwxyz1234567890_'):  # first just just check next
                        val = replace_with
                else:
                    if (splits[current_index][-1].lower() not in 'abcdefghijklmnopqrstuvwxyz1234567890_') \
                        and ((len(splits[current_index + 1]) == 0 and word_to_find[0].lower() not in 'abcdefghijklmnopqrstuvwxyz1234567890_')
                             or (len(splits[current_index + 1]) > 0 and splits[current_index + 1][0].lower() not in 'abcdefghijklmnopqrstuvwxyz1234567890_')):  # first just just check next
                        val = replace_with

            new_string.append(val)
            current_index += 1

        source_str = ' '.join(new_string)
    return source_str


def __itoa(num, radix):
    result = ""
    if num == 0:
        return '0'
    while num > 0:
        result = "0123456789abcdefghijklmnopqrstuvwxyz"[num % radix] + result
        num = int(num / radix)
    return result


def __itoaNew(cc, a):
    aa = "" if cc < a else __itoaNew(int(cc / a), a)
    cc = (cc % a)
    bb = chr(cc + 29) if cc > 35 else str(__itoa(cc, 36))
    return aa + bb


def getCookiesString(cookieJar):
    try:
        cookieString = ""
        for index, cookie in enumerate(cookieJar):
            cookieString += cookie.name + "=" + cookie.value + ";"
    except:
        pass

    return cookieString


def saveCookieJar(cookieJar, COOKIEFILE):
    try:
        complete_path = os.path.join(profile, COOKIEFILE)
        cookieJar.save(complete_path, ignore_discard=True)
    except:
        pass


def getCookieJar(COOKIEFILE):
    cookieJar = None
    if COOKIEFILE:
        try:
            complete_path = os.path.join(profile, COOKIEFILE)
            cookieJar = http_cookiejar.LWPCookieJar()
            cookieJar.load(complete_path, ignore_discard=True)
        except:
            cookieJar = None

    if not cookieJar:
        cookieJar = http_cookiejar.LWPCookieJar()

    return cookieJar


def doEval(fun_call, page_data, Cookie_Jar, m):
    global ret_val
    ret_val = ''
    globals()["page_data"] = page_data
    globals()["Cookie_Jar"] = Cookie_Jar
    globals()["m"] = m

    if functions_dir not in sys.path:
        sys.path.append(functions_dir)
    try:
        py_file = 'import ' + fun_call.split('.')[0]
        six.exec_(py_file, globals())
    except:
        #traceback.print_exc(file=sys.stdout)
        pass
    six.exec_('ret_val=' + fun_call, globals())
    return six.ensure_str(ret_val)


def doEvalFunction(fun_call, page_data, Cookie_Jar, m):
    try:
        global gLSProDynamicCodeNumber
        gLSProDynamicCodeNumber = gLSProDynamicCodeNumber + 1
        ret_val = ''

        if functions_dir not in sys.path:
            sys.path.append(functions_dir)

        filename = 'LSProdynamicCode{0}.py'.format(gLSProDynamicCodeNumber)
        filenamewithpath = os.path.join(functions_dir, filename)
        with xbmcvfs.File(filenamewithpath, "w") as f:
            f.write(six.ensure_binary("# -*- coding: utf-8 -*-\n"))
            f.write(fun_call.encode("utf-8"))

        LSProdynamicCode = import_by_string(filename.split('.')[0], filenamewithpath)
        ret_val = LSProdynamicCode.GetLSProData(page_data, Cookie_Jar, m)
        try:
            return str(ret_val)
        except:
            return ret_val
    except:
        pass
        # traceback.print_exc()
    return ""


def import_by_string(full_name, filenamewithpath):
    try:
        import importlib
        return importlib.import_module(full_name, package=None)
    except:
        import imp
        return imp.load_source(full_name, filenamewithpath)


def getGoogleRecaptchaResponse(captchakey, cj, type=1):  # 1 for get, 2 for post, 3 for rawpost
    recapChallenge = ""
    solution = ""
    captcha_reload_response_chall = None
    solution = None
    if len(captchakey) > 0:  # new shiny captcha!
        captcha_url = captchakey
        if not captcha_url.startswith('http'):
            captcha_url = 'https://www.google.com/recaptcha/api/challenge?k=' + captcha_url + '&ajax=1'
        cap_chall_reg = 'challenge.*?\'(.*?)\''
        cap_image_reg = '\'(.*?)\''
        captcha_script = getUrl(captcha_url, cookieJar=cj)
        recapChallenge = re.findall(cap_chall_reg, captcha_script)[0]
        captcha_reload = 'http://www.google.com/recaptcha/api/reload?c='
        captcha_k = captcha_url.split('k=')[1]
        captcha_reload += recapChallenge + '&k=' + captcha_k + '&reason=i&type=image&lang=en'
        captcha_reload_js = getUrl(captcha_reload, cookieJar=cj)
        captcha_reload_response_chall = re.findall(cap_image_reg, captcha_reload_js)[0]
        captcha_image_url = 'https://www.google.com/recaptcha/api/image?c=' + captcha_reload_response_chall
        if not captcha_image_url.startswith("http"):
            captcha_image_url = 'https://www.google.com/recaptcha/api/' + captcha_image_url
        import random
        n = random.randrange(100, 1000, 5)
        local_captcha = os.path.join(profile, str(n) + "captcha.img")
        with xbmcvfs.File(local_captcha, "w") as localFile:
            localFile.write(getUrl(captcha_image_url, cookieJar=cj))
        solver = InputWindow(captcha=local_captcha)
        solution = solver.get()
        os.remove(local_captcha)

    if captcha_reload_response_chall:
        if type == 1:
            return 'recaptcha_challenge_field=' + urllib_parse.quote_plus(captcha_reload_response_chall) + '&recaptcha_response_field=' + urllib_parse.quote_plus(solution)
        elif type == 2:
            return 'recaptcha_challenge_field:' + captcha_reload_response_chall + ',recaptcha_response_field:' + solution
        else:
            return 'recaptcha_challenge_field=' + urllib_parse.quote_plus(captcha_reload_response_chall) + '&recaptcha_response_field=' + urllib_parse.quote_plus(solution)
    else:
        return ''


def getUrl(url, cookieJar=None, post=None, timeout=20, headers=None, noredir=False):
    cookie_handler = urllib_request.HTTPCookieProcessor(cookieJar)

    if post is not None:
        post = post.encode('utf-8')

    if noredir:
        opener = urllib_request.build_opener(NoRedirection, cookie_handler, urllib_request.HTTPBasicAuthHandler(), urllib_request.HTTPHandler())
    else:
        opener = urllib_request.build_opener(cookie_handler, urllib_request.HTTPBasicAuthHandler(), urllib_request.HTTPHandler())

    req = urllib_request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36')
    if headers:
        for h, hv in headers:
            req.add_header(h, hv)

    response = opener.open(req, post, timeout=timeout)
    link = response.read()
    encoding = None
    content_type = response.headers.get('content-type', '')
    if 'charset=' in content_type:
        encoding = content_type.split('charset=')[-1]

    if encoding is None:
        epattern = r'<meta\s+http-equiv="Content-Type"\s+content="(?:.+?);\s+charset=(.+?)"'
        epattern = epattern.encode('utf8') if six.PY3 else epattern
        r = re.search(epattern, link, re.IGNORECASE)
        if r:
            encoding = r.group(1).decode('utf8') if six.PY3 else r.group(1)
        else:
            epattern = r'''<meta\s+charset=["']?([^"'>]+)'''
            epattern = epattern.encode('utf8') if six.PY3 else epattern
            r = re.search(epattern, link, re.IGNORECASE)
            if r:
                encoding = r.group(1).decode('utf8') if six.PY3 else r.group(1)

    if encoding is not None:
        link = link.decode(encoding.lower(), errors='ignore')
        link = link.encode('utf8') if six.PY2 else link
    else:
        link = link.decode('utf-8', errors='ignore') if six.PY3 else link.encode('utf-8')

    response.close()
    return link


def get_decode(str, reg=None):
    if reg:
        str = re.findall(reg, str)[0]
    s1 = urllib_parse.unquote(str[0: len(str) - 1])
    t = ''
    for i in range(len(s1)):
        t += chr(ord(s1[i]) - s1[len(s1) - 1])
    t = urllib_parse.unquote(t)
    return t


def javascriptUnEscape(str):
    js = re.findall(r'unescape\(\'(.*?)\'', str)
    if js is not None and len(js) > 0:
        for j in js:
            str = str.replace(j, urllib_parse.unquote(j))
    return str


def askCaptcha(m, html_page, cookieJar):
    global iid
    iid += 1
    expre = m['expres']
    page_url = m['page']
    captcha_regex = re.compile(r'\$LiveStreamCaptcha\[([^\]]*)\]').findall(expre)[0]

    captcha_url = re.compile(captcha_regex).findall(html_page)[0]

    if not captcha_url.startswith("http"):
        page_ = 'http://' + "".join(page_url.split('/')[2:3])
        if captcha_url.startswith("/"):
            captcha_url = page_ + captcha_url
        else:
            captcha_url = page_ + '/' + captcha_url

    local_captcha = os.path.join(profile, str(iid) + "captcha.jpg")
    localFile = open(local_captcha, "wb")

    req = urllib_request.Request(captcha_url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:14.0) Gecko/20100101 Firefox/14.0.1')
    if 'referer' in m:
        req.add_header('Referer', m['referer'])
    if 'agent' in m:
        req.add_header('User-agent', m['agent'])
    if 'setcookie' in m:
        req.add_header('Cookie', m['setcookie'])

    urllib_request.urlopen(req)
    response = urllib_request.urlopen(req)
    link = response.read()
    encoding = None
    content_type = response.headers.get('content-type', '')
    if 'charset=' in content_type:
        encoding = content_type.split('charset=')[-1]

    if encoding is None:
        epattern = r'<meta\s+http-equiv="Content-Type"\s+content="(?:.+?);\s+charset=(.+?)"'
        epattern = epattern.encode('utf8') if six.PY3 else epattern
        r = re.search(epattern, link, re.IGNORECASE)
        if r:
            encoding = r.group(1).decode('utf8') if six.PY3 else r.group(1)
        else:
            epattern = r'''<meta\s+charset=["']?([^"'>]+)'''
            epattern = epattern.encode('utf8') if six.PY3 else epattern
            r = re.search(epattern, link, re.IGNORECASE)
            if r:
                encoding = r.group(1).decode('utf8') if six.PY3 else r.group(1)

    if encoding is not None:
        link = link.decode(encoding.lower(), errors='ignore')
        link = link.encode('utf8') if six.PY2 else link
    else:
        link = link.decode('utf-8', errors='ignore') if six.PY3 else link.encode('utf-8')

    localFile.write(link)
    response.close()
    localFile.close()
    solver = InputWindow(captcha=local_captcha)
    solution = solver.get()
    return solution


def askCaptchaNew(imageregex, html_page, cookieJar, m):
    global iid
    iid += 1

    if imageregex != '':
        if html_page.startswith("http"):
            page_ = getUrl(html_page, cookieJar=cookieJar)
        else:
            page_ = html_page
        captcha_url = re.compile(imageregex).findall(page_)[0]
    else:
        captcha_url = html_page

    local_captcha = os.path.join(profile, str(iid) + "captcha.jpg")
    localFile = open(local_captcha, "wb")

    req = urllib_request.Request(captcha_url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:14.0) Gecko/20100101 Firefox/14.0.1')
    if 'referer' in m:
        req.add_header('Referer', m['referer'])
    if 'agent' in m:
        req.add_header('User-agent', m['agent'])
    if 'accept' in m:
        req.add_header('Accept', m['accept'])
    if 'setcookie' in m:
        req.add_header('Cookie', m['setcookie'])

    response = urllib_request.urlopen(req)
    link = response.read()
    encoding = None
    content_type = response.headers.get('content-type', '')
    if 'charset=' in content_type:
        encoding = content_type.split('charset=')[-1]

    if encoding is None:
        epattern = r'<meta\s+http-equiv="Content-Type"\s+content="(?:.+?);\s+charset=(.+?)"'
        epattern = epattern.encode('utf8') if six.PY3 else epattern
        r = re.search(epattern, link, re.IGNORECASE)
        if r:
            encoding = r.group(1).decode('utf8') if six.PY3 else r.group(1)
        else:
            epattern = r'''<meta\s+charset=["']?([^"'>]+)'''
            epattern = epattern.encode('utf8') if six.PY3 else epattern
            r = re.search(epattern, link, re.IGNORECASE)
            if r:
                encoding = r.group(1).decode('utf8') if six.PY3 else r.group(1)

    if encoding is not None:
        link = link.decode(encoding.lower(), errors='ignore')
        link = link.encode('utf8') if six.PY2 else link
    else:
        link = link.decode('utf-8', errors='ignore') if six.PY3 else link.encode('utf-8')

    localFile.write(link)
    response.close()
    localFile.close()
    solver = InputWindow(captcha=local_captcha)
    solution = solver.get()
    return solution


def TakeInput(name, headname):
    kb = xbmc.Keyboard('default', 'heading', True)
    kb.setDefault(name)
    kb.setHeading(headname)
    kb.setHiddenInput(False)
    return kb.getText()


class InputWindow(xbmcgui.WindowDialog):
    def __init__(self, *args, **kwargs):
        self.cptloc = kwargs.get('captcha')
        self.img = xbmcgui.ControlImage(335, 30, 624, 60, self.cptloc)
        self.addControl(self.img)
        self.kbd = xbmc.Keyboard()

    def get(self):
        self.show()
        time.sleep(2)
        self.kbd.doModal()
        if (self.kbd.isConfirmed()):
            text = self.kbd.getText()
            self.close()
            return text
        self.close()
        return False


def getEpocTime():
    return str(int(time.time() * 1000))


def getEpocTime2():
    return str(int(time.time()))


def get_params():
    param = []
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = sys.argv[2]
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]
    return param


def getFavorites():
    items = json.loads(xbmcvfs.File(favorites).read())
    total = len(items)
    for i in items:
        name = i[0]
        url = i[1]
        iconimage = i[2]
        try:
            fanArt = i[3]
            if fanArt is None:
                raise Exception()
        except:
            if addon.getSetting('use_thumb') == "true":
                fanArt = iconimage
            else:
                fanArt = fanart
        try:
            playlist = i[5]
        except:
            playlist = None
        try:
            regexs = i[6]
        except:
            regexs = None

        if i[4] == 0:
            addLink(url, name, iconimage, fanArt, '', '', '', 'fav', playlist, regexs, total)
        else:
            addDir(name, url, i[4], iconimage, fanart, '', '', '', '', 'fav')


def addFavorite(name, url, iconimage, fanart, mode, playlist=None, regexs=None):
    favList = []
    try:
        # seems that after
        name = name.encode('utf-8', 'ignore') if six.PY2 else name
    except:
        pass
    if os.path.exists(favorites) is False:
        addon_log('Making Favorites File')
        favList.append((name, url, iconimage, fanart, mode, playlist, regexs))
        with xbmcvfs.File(favorites, "w") as a:
            a.write(json.dumps(favList))
    else:
        addon_log('Appending Favorites')
        a = xbmcvfs.File(favorites).read()
        data = json.loads(a)
        data.append((name, url, iconimage, fanart, mode))
        with xbmcvfs.File(favorites, "w") as b:
            b.write(json.dumps(data))


def rmFavorite(name):
    data = json.loads(xbmcvfs.File(favorites).read())
    for index in range(len(data)):
        if data[index][0] == name:
            del data[index]
            with xbmcvfs.File(favorites, "w") as b:
                b.write(json.dumps(data))
            break
    xbmc.executebuiltin("Container.Refresh")


def urlsolver(url):
    try:
        import resolveurl
    except:
        import urlresolver as resolveurl

    if resolveurl.HostedMediaFile(url).valid_url():
        resolved = resolveurl.resolve(url)
    else:
        xbmcgui.Dialog().notification(addon_name, 'ResolveUrl does not support this domain.', icon, 5000, False)
        resolved = url
    return resolved


def tryplay(url, listitem, pdialogue=None):
    if url.lower().startswith('plugin') and 'youtube' not in url.lower():
        xbmc.executebuiltin('RunPlugin(' + url + ')')
        for i in range(8):
            xbmc.sleep(500)  # sleep for 10 seconds, half each time
            try:
                if xbmc.getCondVisibility("Player.HasMedia") and xbmc.Player().isPlaying():
                    return True
            except:
                pass
        return False

    import CustomPlayer
    player = CustomPlayer.MyXBMCPlayer()
    player.pdialogue = pdialogue
    beforestart = time.time()
    player.play(url, listitem)
    xbmc.sleep(1000)

    try:
        while player.is_active:
            xbmc.sleep(400)
            if player.urlplayed:
                return True
            if time.time() - beforestart > 4:
                return False
    except:
        pass
    return False


def play_playlist(name, mu_playlist, queueVideo=None):
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    if '$$LSPlayOnlyOne$$' in mu_playlist[0]:
        mu_playlist[0] = mu_playlist[0].replace('$$LSPlayOnlyOne$$', '')
        names = []
        iloop = 0
        progress = xbmcgui.DialogProgress()
        progress.create('Progress', 'Trying Multiple Links')
        for i in mu_playlist:
            if '$$lsname=' in i:
                d_name = i.split('$$lsname=')[1].split('&regexs')[0]
                names.append(d_name)
                mu_playlist[iloop] = i.split('$$lsname=')[0] + ('&regexs' + i.split('&regexs')[1] if '&regexs' in i else '')
            else:
                d_name = urllib_parse.urlparse(i).netloc
                if d_name == '':
                    names.append(name)
                else:
                    names.append(d_name)
            index = iloop
            iloop += 1

            playname = names[index]
            if progress.iscanceled():
                return
            progress.update(iloop / len(mu_playlist) * 100, "", "Link#%d" % (iloop), playname)

            if "&mode=19" in mu_playlist[index]:
                liz = xbmcgui.ListItem(playname)
                liz.setArt({'thumb': iconimage,
                            'icon': iconimage})
                liz.setInfo(type='Video', infoLabels={'Title': playname, 'mediatype': 'video'})
                liz.setProperty("IsPlayable", "true")
                urltoplay = urlsolver(mu_playlist[index].replace('&mode=19', '').replace(';', ''))
                liz.setPath(urltoplay)
                played = tryplay(urltoplay, liz)
            elif "$doregex" in mu_playlist[index]:
                sepate = mu_playlist[index].split('&regexs=')
                url, setresolved = getRegexParsed(sepate[1], sepate[0])
                url2 = url.replace(';', '')
                liz = xbmcgui.ListItem(playname)
                liz.setArt({'thumb': iconimage,
                            'icon': iconimage})
                liz.setInfo(type='Video', infoLabels={'Title': playname, 'mediatype': 'video'})
                liz.setProperty("IsPlayable", "true")
                liz.setPath(url2)
                played = tryplay(url2, liz)

            else:
                url = mu_playlist[index]
                url = url.split('&regexs=')[0]
                liz = xbmcgui.ListItem(playname)
                liz.setArt({'thumb': iconimage,
                            'icon': iconimage})
                liz.setInfo(type='Video', infoLabels={'Title': playname, 'mediatype': 'video'})
                liz.setProperty("IsPlayable", "true")
                liz.setPath(url)
                played = tryplay(url, liz)

            if played:
                return
        return
    if addon.getSetting('ask_playlist_items') == 'true' and not queueVideo:
        names = []
        iloop = 0
        for i in mu_playlist:
            if '$$lsname=' in i:
                d_name = i.split('$$lsname=')[1].split('&regexs')[0]
                names.append(d_name)
                mu_playlist[iloop] = i.split('$$lsname=')[0] + ('&regexs' + i.split('&regexs')[1] if '&regexs' in i else '')
            else:
                d_name = urllib_parse.urlparse(i).netloc
                if d_name == '':
                    names.append(name)
                else:
                    names.append(d_name)

            iloop += 1
        dialog = xbmcgui.Dialog()
        index = dialog.select('Choose a video source', names)
        if index >= 0:
            playname = names[index]
            if "&mode=19" in mu_playlist[index]:
                liz = xbmcgui.ListItem(playname)
                liz.setArt({'thumb': iconimage,
                            'icon': iconimage})
                liz.setInfo(type='Video', infoLabels={'Title': playname, 'mediatype': 'video'})
                liz.setProperty("IsPlayable", "true")
                urltoplay = urlsolver(mu_playlist[index].replace('&mode=19', '').replace(';', ''))
                liz.setPath(urltoplay)
                xbmc.Player().play(urltoplay, liz)
            elif "$doregex" in mu_playlist[index]:
                sepate = mu_playlist[index].split('&regexs=')
                url, setresolved = getRegexParsed(sepate[1], sepate[0])
                url2 = url.replace(';', '')
                liz = xbmcgui.ListItem(playname)
                liz.setArt({'thumb': iconimage,
                            'icon': iconimage})
                liz.setInfo(type='Video', infoLabels={'Title': playname, 'mediatype': 'video'})
                liz.setProperty("IsPlayable", "true")
                liz.setPath(url2)
                xbmc.Player().play(url2, liz)

            else:
                url = mu_playlist[index]
                url = url.split('&regexs=')[0]
                liz = xbmcgui.ListItem(playname)
                liz.setArt({'thumb': iconimage,
                            'icon': iconimage})
                liz.setInfo(type='Video', infoLabels={'Title': playname, 'mediatype': 'video'})
                liz.setProperty("IsPlayable", "true")
                liz.setPath(url)
                xbmc.Player().play(url, liz)
    elif not queueVideo:
        playlist.clear()
        item = 0
        for i in mu_playlist:
            item += 1
            info = xbmcgui.ListItem('%s) %s' % (str(item), name))
            try:
                if "$doregex" in i:
                    sepate = i.split('&regexs=')
                    url, setresolved = getRegexParsed(sepate[1], sepate[0])
                elif "&mode=19" in i:
                    url = urlsolver(i.replace('&mode=19', '').replace(';', ''))
                if url:
                    playlist.add(url, info)
                else:
                    raise Exception()
            except Exception:
                playlist.add(i, info)
                pass

        xbmc.executebuiltin('playlist.playoffset(video,0)')
    else:
        listitem = xbmcgui.ListItem(name)
        playlist.add(mu_playlist, listitem)


def download_file(name, url):
    xbmcgui.Dialog().notification(addon_name, 'Function not implemented yet.', icon, 15000, False)
    # if addon.getSetting('save_location') == "":
    #     xbmcgui.Dialog().notification(addon_name, 'Choose a location to save files.', icon, 15000, False)
    #     addon.openSettings()
    # params = {'url': url, 'download_path': addon.getSetting('save_location')}
    # downloader.download(name, params)
    # dialog = xbmcgui.Dialog()
    # ret = dialog.yesno(addon_name, 'Do you want to add this file as a source?')
    # if ret:
    #     addSource(os.path.join(addon.getSetting('save_location'), name))


def _search(url, name):
    pluginsearchurls = ['plugin://plugin.video.youtube/kodion/search/list/',
                        'plugin://plugin.video.dailymotion_com/?mode=search&amp;url',
                        'plugin://plugin.video.vimeo/kodion/search/list/']
    names = ['Youtube', 'DailyMotion', 'Vimeo']
    dialog = xbmcgui.Dialog()
    index = dialog.select('Choose a video source', names)

    if index >= 0:
        url = pluginsearchurls[index]
        pluginquerybyJSON(url)


def addDir(name, url, mode, iconimage, fanart, description, genre, date, credits, showcontext=False, regexs=None, reg_url=None, allinfo={}):
    # addon_log("addDir: %s %s" % (iconimage, fanart))
    """
        Needed in Kodi 19 Matrix as paths ending in .xml seem to be blacklisted causing the parent path to always be root.
    """
    url = url + "/" if url.endswith(".xml") else url
    if regexs and len(regexs) > 0:
        u = sys.argv[0] + "?url=" + urllib_parse.quote_plus(url) + "&mode=" + str(mode) + "&name=" + urllib_parse.quote_plus(name) + "&fanart=" + urllib_parse.quote_plus(fanart) + "&regexs=" + regexs
    else:
        u = sys.argv[0] + "?url=" + urllib_parse.quote_plus(url) + "&mode=" + str(mode) + "&name=" + urllib_parse.quote_plus(name) + "&fanart=" + urllib_parse.quote_plus(fanart)

    ok = True
    if date == '':
        date = None
    else:
        description += '\n\nDate: %s' % date
    liz = xbmcgui.ListItem(name)
    # liz.setArt({'thumb': "DefaultFolder.png",
    #            'icon': iconimage})
    liz.setArt({'fanart': fanart, 'thumb': iconimage, 'icon': "DefaultFolder.png"})

    if len(allinfo) < 1:
        liz.setInfo(type="Video", infoLabels={"Title": name, 'mediatype': 'video', "Plot": description, "Genre": genre, "dateadded": date, "credits": credits})
    else:
        allinfo.update({'mediatype': 'video'})
        liz.setInfo(type="Video", infoLabels=allinfo)

    liz.setProperty('IsPlayable', 'false')

    if showcontext:
        contextMenu = []
        parentalblock = addon.getSetting('parentalblocked')
        parentalblock = parentalblock == "true"
        parentalblockedpin = addon.getSetting('parentalblockedpin')
        if len(parentalblockedpin) > 0:
            if parentalblock:
                contextMenu.append(('Disable Parental Block', 'RunPlugin(%s?mode=55&name=%s)' % (sys.argv[0], urllib_parse.quote_plus(name))))
            else:
                contextMenu.append(('Enable Parental Block', 'RunPlugin(%s?mode=56&name=%s)' % (sys.argv[0], urllib_parse.quote_plus(name))))

        if showcontext == 'source':
            if name in str(SOURCES):
                contextMenu.append(('Remove from Sources', 'RunPlugin(%s?mode=8&name=%s)' % (sys.argv[0], urllib_parse.quote_plus(name))))
        elif showcontext == 'download':
            contextMenu.append(('Download', 'RunPlugin(%s?url=%s&mode=9&name=%s)'
                                % (sys.argv[0], urllib_parse.quote_plus(url), urllib_parse.quote_plus(name))))
        elif showcontext == 'fav':
            contextMenu.append(('Remove from LiveStreamsPro Favorites', 'RunPlugin(%s?mode=6&name=%s)'
                                % (sys.argv[0], urllib_parse.quote_plus(name))))
        if showcontext == '!!update':
            fav_params2 = (
                '%s?url=%s&mode=17&regexs=%s'
                % (sys.argv[0], urllib_parse.quote_plus(reg_url), regexs)
            )
            contextMenu.append(('[COLOR yellow]!!update[/COLOR]', 'RunPlugin(%s)' % fav_params2))
        if name not in FAV:
            contextMenu.append(('Add to LiveStreamsPro Favorites', 'RunPlugin(%s?mode=5&name=%s&url=%s&iconimage=%s&fanart=%s&fav_mode=%s)'
                               % (sys.argv[0], urllib_parse.quote_plus(name), urllib_parse.quote_plus(url), urllib_parse.quote_plus(iconimage), urllib_parse.quote_plus(fanart), mode)))
        liz.addContextMenuItems(contextMenu)
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)
    return ok


def ytdl_download(url, title, media_type='video'):
    # play in xbmc while playing go back to contextMenu(c) to "!!Download!!"
    # Trial yasceen: seperate |User-Agent=
    import youtubedl

    if url != '':
        if media_type == 'audio':
            youtubedl.single_YD(url, download=True, audio=True)
        else:
            youtubedl.single_YD(url, download=True)
    elif xbmc.Player().isPlaying():
        import YDStreamExtractor
        if YDStreamExtractor.isDownloading():
            YDStreamExtractor.manageDownloads()
        else:
            xbmc_url = xbmc.Player().getPlayingFile()
            xbmc_url = xbmc_url.split('|User-Agent=')[0]
            info = {'url': xbmc_url, 'title': title, 'media_type': media_type}
            youtubedl.single_YD('', download=True, dl_info=info)
    else:
        xbmcgui.Dialog().notification(addon_name, 'First Play, [COLOR yellow]WHILE playing download[/COLOR]', icon, 10000, False)


# Lunatixz PseudoTV feature
def ascii(string):
    if isinstance(string, six.string_types):
        if isinstance(string, six.text_type) and six.PY2:
            string = string.encode('ascii', 'ignore')
    return string


def uni(string, encoding='utf-8'):
    if isinstance(string, six.string_types):
        if not isinstance(string, six.text_type) and six.PY2:
            string = six.text_type(string, encoding, 'ignore')
    return string


def removeNonAscii(s):
    return "".join(filter(lambda x: ord(x) < 128, s))


def sendJSON(command):
    data = ''
    try:
        data = xbmc.executeJSONRPC(uni(command))
    except UnicodeEncodeError:
        data = xbmc.executeJSONRPC(ascii(command))

    return uni(data)


def pluginquerybyJSON(url, give_me_result=None, playlist=False):
    if 'audio' in url:
        json_query = uni('{"jsonrpc":"2.0","method":"Files.GetDirectory","params": {"directory":"%s","media":"video", "properties": ["title", "album", "artist", "duration","thumbnail", "year"]}, "id": 1}') % url
    else:
        json_query = uni('{"jsonrpc":"2.0","method":"Files.GetDirectory","params":{"directory":"%s","media":"video","properties":[ "plot","playcount","director", "genre","votes","duration","trailer","premiered","thumbnail","title","year","dateadded","fanart","rating","season","episode","studio","mpaa"]},"id":1}') % url
    json_folder_detail = json.loads(sendJSON(json_query))

    if give_me_result:
        return json_folder_detail
    if 'error' in json_folder_detail:
        return
    else:
        for i in json_folder_detail['result']['files']:
            meta = {}
            url = i['file']
            name = removeNonAscii(i['label'])
            thumbnail = removeNonAscii(i['thumbnail'])
            fanart = removeNonAscii(i['fanart'])
            meta = dict((k, v) for k, v in six.iteritems(i) if not v == '0' or not v == -1 or v == '')
            meta.pop("file", None)
            if i['filetype'] == 'file':
                if playlist:
                    play_playlist(name, url, queueVideo='1')
                    continue
                else:
                    addLink(url, name, thumbnail, fanart, '', '', '', '', None, '', total=len(json_folder_detail['result']['files']), allinfo=meta)
                    if i['type'] and i['type'] == 'tvshow':
                        xbmcplugin.setContent(int(sys.argv[1]), 'tvshows')
                    elif i['episode'] > 0:
                        xbmcplugin.setContent(int(sys.argv[1]), 'episodes')

            else:
                addDir(name, url, 53, thumbnail, fanart, '', '', '', '', allinfo=meta)
        xbmcplugin.endOfDirectory(int(sys.argv[1]))


def addLink(url, name, iconimage, fanart, description, genre, date, showcontext, playlist, regexs, total, setCookie="", allinfo={}):
    # addon_log('addLink: %s, %s' % (iconimage, fanart))
    contextMenu = []
    parentalblock = addon.getSetting('parentalblocked')
    parentalblock = parentalblock == "true"
    parentalblockedpin = addon.getSetting('parentalblockedpin')

    if len(parentalblockedpin) > 0:
        if parentalblock:
            contextMenu.append(('Disable Parental Block', 'RunPlugin(%s?mode=55&name=%s)' % (sys.argv[0], urllib_parse.quote_plus(name))))
        else:
            contextMenu.append(('Enable Parental Block', 'RunPlugin(%s?mode=56&name=%s)' % (sys.argv[0], urllib_parse.quote_plus(name))))

    try:
        name = name.encode('utf-8') if six.PY2 else name
    except:
        pass
    ok = True
    isFolder = False
    if regexs:
        mode = '17'
        if 'listrepeat' in regexs:
            isFolder = True
        contextMenu.append(('[COLOR white]!!Download Currently Playing!![/COLOR]', 'RunPlugin(%s?url=%s&mode=21&name=%s)'
                            % (sys.argv[0], urllib_parse.quote_plus(url), urllib_parse.quote_plus(name))))
    elif (any(x in url for x in resolve_url) and url.startswith('http')) or url.endswith('&mode=19'):
        url = url.replace('&mode=19', '')
        mode = '19'
        contextMenu.append(('[COLOR white]!!Download Currently Playing!![/COLOR]', 'RunPlugin(%s?url=%s&mode=21&name=%s)'
                            % (sys.argv[0], urllib_parse.quote_plus(url), urllib_parse.quote_plus(name))))
    elif url.endswith('&mode=18'):
        url = url.replace('&mode=18', '')
        mode = '18'
        contextMenu.append(('[COLOR white]!!Download!![/COLOR]', 'RunPlugin(%s?url=%s&mode=23&name=%s)'
                            % (sys.argv[0], urllib_parse.quote_plus(url), urllib_parse.quote_plus(name))))
        if addon.getSetting('dlaudioonly') == 'true':
            contextMenu.append(('!!Download [COLOR seablue]Audio!![/COLOR]', 'RunPlugin(%s?url=%s&mode=24&name=%s)'
                                % (sys.argv[0], urllib_parse.quote_plus(url), urllib_parse.quote_plus(name))))
    elif url.endswith('&mode=20'):
        url = url.replace('&mode=20', '')
        mode = '20'
    elif url.endswith('&mode=22'):
        url = url.replace('&mode=22', '')
        mode = '22'
    else:
        mode = '12'
        contextMenu.append(('[COLOR white]!!Download Currently Playing!![/COLOR]', 'RunPlugin(%s?url=%s&mode=21&name=%s)'
                            % (sys.argv[0], urllib_parse.quote_plus(url), urllib_parse.quote_plus(name))))
    if 'plugin://plugin.video.youtube/play/?video_id=' in url:
        yt_audio_url = url.replace('plugin://plugin.video.youtube/play/?video_id=', 'https://www.youtube.com/watch?v=')
        contextMenu.append(('!!Download [COLOR blue]Audio!![/COLOR]', 'RunPlugin(%s?url=%s&mode=24&name=%s)'
                            % (sys.argv[0], urllib_parse.quote_plus(yt_audio_url), urllib_parse.quote_plus(name))))
    u = sys.argv[0] + "?"
    play_list = False

    if playlist:
        if addon.getSetting('add_playlist') == "false" and '$$LSPlayOnlyOne$$' not in playlist[0]:
            u += "url=" + urllib_parse.quote_plus(url) + "&mode=" + mode
        else:
            u += "mode=13&name=%s&playlist=%s" % (urllib_parse.quote_plus(name), urllib_parse.quote_plus(str(playlist).replace(',', '||')))
            name = name + '[COLOR magenta] (' + str(len(playlist)) + ' items )[/COLOR]'
            play_list = True
    elif mode == '22' or (mode == '17' and url.endswith('&mode=22')):
        u += "url=" + urllib_parse.quote_plus(url) + "&name=" + urllib_parse.quote(name) + "&mode=" + mode
    else:
        u += "url=" + urllib_parse.quote_plus(url) + "&mode=" + mode
    if regexs:
        u += "&regexs=" + regexs
    if not setCookie == '':
        u += "&setCookie=" + urllib_parse.quote_plus(setCookie)
    if iconimage and iconimage != '':
        u += "&iconimage=" + urllib_parse.quote_plus(iconimage)

    if date == '':
        date = None
    else:
        description += '\n\nDate: %s' % date
    liz = xbmcgui.ListItem(name)
    liz.setArt({'thumb': iconimage,
                'fanart': fanart,
                'icon': "DefaultVideo.png"})

    if allinfo is None or len(allinfo) < 1:
        liz.setInfo(type="Video", infoLabels={"Title": name, 'mediatype': 'video', "Plot": description, "Genre": genre, "dateadded": date})
    else:
        allinfo.update({'mediatype': 'video'})
        liz.setInfo(type="Video", infoLabels=allinfo)

    if '$$RESOLVEONLY$$' in url:
        liz.setProperty('IsPlayable', 'true')

    if (not play_list) and not any(x in url for x in g_ignoreSetResolved) and '$PLAYERPROXY$=' not in url and not (mode == '22' or (mode == '17' and url.endswith('&mode=22'))):
        if regexs:
            if '$pyFunction:playmedia(' not in urllib_parse.unquote_plus(regexs) and 'notplayable' not in urllib_parse.unquote_plus(regexs) and 'listrepeat' not in urllib_parse.unquote_plus(regexs):
                liz.setProperty('IsPlayable', 'true')
        else:
            liz.setProperty('IsPlayable', 'true')

    else:
        addon_log('NOT setting isplayable for url   ' + url)

    if showcontext:
        if showcontext == 'fav':
            contextMenu.append(
                ('Remove from LiveStreamsPro Favorites', 'RunPlugin(%s?mode=6&name=%s)'
                 % (sys.argv[0], urllib_parse.quote_plus(name)))
            )
        elif name not in FAV:
            iconimage = iconimage if iconimage else ''
            fanart = fanart if fanart else ''
            try:
                fav_params = (
                    '%s?mode=5&name=%s&url=%s&iconimage=%s&fanart=%s&fav_mode=0'
                    % (sys.argv[0], urllib_parse.quote_plus(name), urllib_parse.quote_plus(url), urllib_parse.quote_plus(iconimage), urllib_parse.quote_plus(fanart))
                )
            except:
                fav_params = (
                    '%s?mode=5&name=%s&url=%s&iconimage=%s&fanart=%s&fav_mode=0'
                    % (sys.argv[0], urllib_parse.quote_plus(name), urllib_parse.quote_plus(url),
                       urllib_parse.quote_plus(iconimage.encode("utf-8") if six.PY2 else iconimage),
                       urllib_parse.quote_plus(fanart.encode("utf-8") if six.PY2 else fanart))
                )
            if playlist:
                fav_params += 'playlist=' + urllib_parse.quote_plus(str(playlist).replace(',', '||'))
            if regexs:
                fav_params += "&regexs=" + regexs
            contextMenu.append(('Add to LiveStreamsPro Favorites', 'RunPlugin(%s)' % fav_params))
        liz.addContextMenuItems(contextMenu)
    try:
        if playlist is not None:
            if addon.getSetting('add_playlist') == "false":
                playlist_name = name.split(') ')[1]
                contextMenu_ = [
                    ('Play ' + playlist_name + ' PlayList', 'RunPlugin(%s?mode=13&name=%s&playlist=%s)'
                        % (sys.argv[0], urllib_parse.quote_plus(playlist_name), urllib_parse.quote_plus(str(playlist).replace(',', '||'))))
                ]
                liz.addContextMenuItems(contextMenu_)
    except:
        pass

    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, totalItems=total, isFolder=isFolder)
    return ok


def playsetresolved(url, name, iconimage, setresolved=True, reg=None):
    if url is None:
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
        return

    if '&mode=22' in url:
        setresolved = False
        url = url.replace('&mode=22', '')
        u = sys.argv[0] + "?"
        u += "url=" + urllib_parse.quote_plus(url) + "&name=" + urllib_parse.quote(name) + "&mode=22"
        url = u

    if setresolved:
        setres = True
        if '$$LSDirect$$' in url:
            url = url.replace('$$LSDirect$$', '')
            setres = False
        if reg and 'notplayable' in reg:
            setres = False

        liz = xbmcgui.ListItem(name)
        liz.setArt({'thumb': iconimage,
                    'icon': iconimage})
        liz.setInfo(type='Video', infoLabels={'Title': name, 'mediatype': 'video'})
        liz.setProperty("IsPlayable", "true")
        if '&mode=19' in url:
            url = urlsolver(url.replace('&mode=19', '').replace(';', ''))
        elif '&mode=20' in url:
            url = url.replace('&mode=20', '')
            if '$$lic' in url:
                url, lic = url.split('$$lic=')
                lic = urllib_parse.unquote_plus(lic)
                if '{SSM}' not in lic:
                    lic += '||R{SSM}|'
                liz.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
                liz.setProperty('inputstream.adaptive.license_key', lic)

            if '|' in url:
                url, strhdr = url.split('|')
                liz.setProperty('inputstream.adaptive.stream_headers', strhdr)

            if '.m3u8' in url:
                if six.PY2:
                    liz.setProperty('inputstreamaddon', 'inputstream.adaptive')
                else:
                    liz.setProperty('inputstream', 'inputstream.adaptive')
                liz.setProperty('inputstream.adaptive.manifest_type', 'hls')
                liz.setMimeType('application/vnd.apple.mpegstream_url')
                liz.setContentLookup(False)

            elif '.mpd' in url or 'format=mpd' in url:
                if six.PY2:
                    liz.setProperty('inputstreamaddon', 'inputstream.adaptive')
                else:
                    liz.setProperty('inputstream', 'inputstream.adaptive')
                liz.setProperty('inputstream.adaptive.manifest_type', 'mpd')
                liz.setMimeType('application/dash+xml')
                liz.setContentLookup(False)

            elif '.ism' in url:
                if six.PY2:
                    liz.setProperty('inputstreamaddon', 'inputstream.adaptive')
                else:
                    liz.setProperty('inputstream', 'inputstream.adaptive')
                liz.setProperty('inputstream.adaptive.manifest_type', 'ism')
                liz.setMimeType('application/vnd.ms-sstr+xml')
                liz.setContentLookup(False)

        liz.setPath(url)
        if not setres:
            xbmc.Player().play(url)
        else:
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)

    else:
        xbmc.executebuiltin('RunPlugin(' + url + ')')


# Thanks to daschacka, an epg scraper for http://i.teleboy.ch/programm/station_select.php
#  http://forum.xbmc.org/post.php?p=936228&postcount=1076
def getepg(link):
    url = urllib_request.urlopen(link)
    source = url.read()
    url.close()
    source2 = source.split("Jetzt")
    source3 = source2[1].split('programm/detail.php?const_id=')
    sourceuhrzeit = source3[1].split('<br /><a href="/')
    nowtime = sourceuhrzeit[0][40:len(sourceuhrzeit[0])]
    sourcetitle = source3[2].split("</a></p></div>")
    nowtitle = sourcetitle[0][17:len(sourcetitle[0])]
    nowtitle = nowtitle.encode('utf-8') if six.PY2 else nowtitle
    return "  - " + nowtitle + " - " + nowtime


def get_epg(url, regex):
    data = makeRequest(url)
    try:
        item = re.findall(regex, data)[0]
        return item
    except:
        addon_log('regex failed')
        addon_log(regex)
        return


# not a generic implemenation as it needs to convert
def d2x(d, root="root", nested=0):
    op = lambda tag: '<' + tag + '>'  # noQA
    cl = lambda tag: '</' + tag + '>\n'  # noQA
    ml = lambda v, xml: xml + op(key) + str(v) + cl(key)  # noQA
    xml = op(root) + '\n' if root else ""

    for key, vl in six.iteritems(d):
        vtype = type(vl)
        if nested == 0:
            key = 'regex'  # enforcing all top level tags to be named as regex
        if vtype is list:
            for v in vl:
                v = escape(v)
                xml = ml(v, xml)

        if vtype is dict:
            xml = ml('\n' + d2x(vl, None, nested + 1), xml)
        if vtype is not list and vtype is not dict:
            if vl is not None:
                vl = escape(vl)

            if vl is None:
                xml = ml(vl, xml)
            else:
                xml = ml(vl.encode("utf-8") if six.PY2 else vl, xml)

    xml += cl(root) if root else ""

    return xml


xbmcplugin.setContent(int(sys.argv[1]), 'movies')

try:
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
except:
    pass
try:
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_LABEL)
except:
    pass
try:
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)
except:
    pass
try:
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_GENRE)
except:
    pass

params = get_params()

url = None
name = None
mode = None
playlist = None
iconimage = None
fanart = FANART
playlist = None
fav_mode = None
regexs = None

try:
    url = urllib_parse.unquote_plus(params["url"])
    url = url.decode('utf-8') if six.PY2 else url
    # url = url.rstrip("fix") if url.endswith(".xmlfix") and six.PY3 else url
    """
       Need to now strip the / off .xml to allow the file to be processed correcty.
    """
    url = url.rstrip("/") if url.endswith(".xml/") else url
except:
    pass
try:
    name = urllib_parse.unquote_plus(params["name"])
except:
    pass
try:
    iconimage = urllib_parse.unquote_plus(params["iconimage"])
except:
    pass
try:
    fanart = urllib_parse.unquote_plus(params["fanart"])
except:
    pass
try:
    mode = int(params["mode"])
except:
    pass
try:
    playlist = eval(urllib_parse.unquote_plus(params["playlist"]).replace('||', ','))
except:
    pass
try:
    fav_mode = int(params["fav_mode"])
except:
    pass
try:
    regexs = params["regexs"]
except:
    pass
playitem = ''
try:
    playitem = urllib_parse.unquote_plus(params["playitem"])
except:
    pass

addon_log("Mode: {0}".format(mode))

if url is not None:
    addon_log("URL: {0}".format(url))
addon_log("Name: {0}".format(name))

if playitem != '':
    s = getSoup('', data=playitem)
    name, url, regexs = getItems(s, None, dontLink=True)
    mode = 117

if mode is None:
    addon_log("getSources")
    getSources()
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode == 1:
    addon_log("getData")
    data = None
    if regexs and len(regexs) > 0:
        data, setresolved = getRegexParsed(regexs, url)
        if data.startswith('http') or data.startswith('smb') or data.startswith('nfs') or data.startswith('/'):
            url = data
            data = None
    getData(url, fanart, data)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode == 2:
    addon_log("getChannelItems")
    getChannelItems(name, url, fanart)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode == 3:
    addon_log("getSubChannelItems")
    getSubChannelItems(name, url, fanart)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode == 4:
    addon_log("getFavorites")
    getFavorites()
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode == 5:
    addon_log("addFavorite")
    try:
        name = name.split('\\ ')[1]
    except:
        pass
    try:
        name = name.split('  - ')[0]
    except:
        pass
    addFavorite(name, url, iconimage, fanart, fav_mode)

elif mode == 6:
    addon_log("rmFavorite")
    try:
        name = name.split('\\ ')[1]
    except:
        pass
    try:
        name = name.split('  - ')[0]
    except:
        pass
    rmFavorite(name)

elif mode == 7:
    addon_log("addSource")
    addSource(url)

elif mode == 8:
    addon_log("rmSource")
    rmSource(name)

elif mode == 9:
    addon_log("download_file")
    download_file(name, url)

elif mode == 11:
    addon_log("addSource")
    addSource(url)

elif mode == 12:
    addon_log("setResolvedUrl")
    if not url.startswith("plugin://plugin") or not any(x in url for x in g_ignoreSetResolved):
        setres = True
        if '$$LSDirect$$' in url:
            url = url.replace('$$LSDirect$$', '')
            setres = False
        if '$PLAYERPROXY$=' in url:
            url, proxy = url.split('$PLAYERPROXY$=')
            # Jairox mod for proxy auth
            proxyuser = None
            proxypass = None
            if len(proxy) > 0 and '@' in proxy:
                proxy = proxy.split(':')
                proxyuser = proxy[0]
                proxypass = proxy[1].split('@')[0]
                proxyip = proxy[1].split('@')[1]
                port = proxy[2]
            else:
                proxyip, port = proxy.split(':')
            playmediawithproxy(url, name, iconimage, proxyip, port, proxyuser, proxypass)  # jairox

        item = xbmcgui.ListItem(path=url)
        if not setres:
            xbmc.Player().play(url)
        else:
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)
    else:
        xbmc.executebuiltin('RunPlugin(' + url + ')')

elif mode == 13:
    addon_log("play_playlist")
    play_playlist(name, playlist)

elif mode == 17 or mode == 117:
    addon_log("getRegexParsed")
    data = None
    if regexs and 'listrepeat' in urllib_parse.unquote_plus(regexs):
        listrepeat, ret, m, regexs, cookieJar = getRegexParsed(regexs, url)
        d = ''
        regexname = m['name']
        existing_list = regexs.pop(regexname)
        url = ''
        import copy
        ln = ''
        rnumber = 0
        for obj in ret:
            try:
                rnumber += 1
                newcopy = copy.deepcopy(regexs)
                listrepeatT = listrepeat
                i = 0
                for i in range(len(obj)):
                    if len(newcopy) > 0:
                        for the_keyO, the_valueO in six.iteritems(newcopy):
                            if the_valueO is not None:
                                for the_key, the_value in six.iteritems(the_valueO):
                                    if the_value is not None:
                                        if type(the_value) is dict:
                                            for the_keyl, the_valuel in six.iteritems(the_value):
                                                if the_valuel is not None:
                                                    val = None
                                                    if isinstance(obj, tuple):
                                                        try:
                                                            val = obj[i].decode('utf-8')
                                                        except:
                                                            val = obj[i]
                                                    else:
                                                        try:
                                                            val = obj.decode('utf-8')
                                                        except:
                                                            val = obj

                                                    if '[' + regexname + '.param' + str(i + 1) + '][DE]' in the_valuel:
                                                        the_valuel = the_valuel.replace('[' + regexname + '.param' + str(i + 1) + '][DE]', urllib_parse.unquote(val))
                                                    the_value[the_keyl] = the_valuel.replace('[' + regexname + '.param' + str(i + 1) + ']', val)

                                        else:
                                            val = None
                                            if isinstance(obj, tuple):
                                                try:
                                                    val = obj[i].decode('utf-8')
                                                except:
                                                    val = obj[i]
                                            else:
                                                try:
                                                    val = obj.decode('utf-8')
                                                except:
                                                    val = obj
                                            if '[' + regexname + '.param' + str(i + 1) + '][DE]' in the_value:
                                                the_value = the_value.replace('[' + regexname + '.param' + str(i + 1) + '][DE]', urllib_parse.unquote(val))

                                            the_valueO[the_key] = the_value.replace('[' + regexname + '.param' + str(i + 1) + ']', val)

                    val = None
                    if isinstance(obj, tuple):
                        try:
                            val = obj[i].decode('utf-8')
                        except:
                            val = obj[i]
                    else:
                        try:
                            val = obj.decode('utf-8')
                        except:
                            val = obj
                    if '[' + regexname + '.param' + str(i + 1) + '][DE]' in listrepeatT:
                        listrepeatT = listrepeatT.replace('[' + regexname + '.param' + str(i + 1) + '][DE]', val)
                    listrepeatT = listrepeatT.replace('[' + regexname + '.param' + str(i + 1) + ']', escape(val))

                listrepeatT = listrepeatT.replace('[' + regexname + '.param' + str(0) + ']', str(rnumber))
                try:
                    if cookieJar and '[' + regexname + '.cookies]' in listrepeatT:
                        listrepeatT = listrepeatT.replace('[' + regexname + '.cookies]', getCookiesString(cookieJar))
                except:
                    pass

                regex_xml = ''
                if len(newcopy) > 0:
                    regex_xml = d2x(newcopy, 'lsproroot')
                    regex_xml = regex_xml.split('<lsproroot>')[1].split('</lsproroot')[0]
                try:
                    ln += '\n<item>%s\n%s</item>' % (listrepeatT, regex_xml)
                except:
                    ln += '\n<item>%s\n%s</item>' % (listrepeatT.encode("utf-8"), regex_xml)
            except:
                traceback.print_exc(file=sys.stdout)

        # addon_log(repr(ln))
        getData('', '', '<items>\n{0}\n</items>\n'.format(ln))
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
    else:
        url, setresolved = getRegexParsed(regexs, url)
        if not (regexs and 'notplayable' in regexs and not url):
            if url:
                if '$PLAYERPROXY$=' in url:
                    url, proxy = url.split('$PLAYERPROXY$=')
                    # Jairox mod for proxy auth
                    proxyuser = None
                    proxypass = None
                    if len(proxy) > 0 and '@' in proxy:
                        proxy = proxy.split(':')
                        proxyuser = proxy[0]
                        proxypass = proxy[1].split('@')[0]
                        proxyip = proxy[1].split('@')[1]
                        port = proxy[2]
                    else:
                        proxyip, port = proxy.split(':')

                    playmediawithproxy(url, name, iconimage, proxyip, port, proxyuser, proxypass)  # jairox
                else:
                    playsetresolved(url, name, iconimage, setresolved, regexs)
            else:
                xbmcgui.Dialog().notification(addon_name, 'Failed to extract regex.', icon, 4000, False)

elif mode == 18:
    addon_log("youtubedl")
    try:
        import youtubedl
    except Exception:
        xbmcgui.Dialog().notification(addon_name, 'Please [COLOR yellow]install Youtube-dl[/COLOR] module', icon, 10000, False)
    stream_url = youtubedl.single_YD(url)
    playsetresolved(stream_url, name, iconimage)

elif mode == 19:
    addon_log("Genesiscommonresolvers")
    playsetresolved(urlsolver(url), name, iconimage, True)

elif mode == 20:
    addon_log("setResolvedUrl")
    item = xbmcgui.ListItem(name)
    if '$$lic' in url:
        url, lic = url.split('$$lic=')
        lic = urllib_parse.unquote_plus(lic)
        if '{SSM}' not in lic:
            lic += '||R{SSM}|'
        item.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
        item.setProperty('inputstream.adaptive.license_key', lic)
    if '|' in url:
        url, strhdr = url.split('|')
        item.setProperty('inputstream.adaptive.stream_headers', strhdr)
        item.setPath(url)
    if '.m3u8' in url:
        if six.PY2:
            item.setProperty('inputstreamaddon', 'inputstream.adaptive')
        else:
            item.setProperty('inputstream', 'inputstream.adaptive')
        item.setProperty('inputstream.adaptive.manifest_type', 'hls')
        item.setMimeType('application/vnd.apple.mpegstream_url')
        item.setContentLookup(False)

    elif '.mpd' in url or 'format=mpd' in url:
        if six.PY2:
            item.setProperty('inputstreamaddon', 'inputstream.adaptive')
        else:
            item.setProperty('inputstream', 'inputstream.adaptive')
        item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        item.setMimeType('application/dash+xml')
        item.setContentLookup(False)

    elif '.ism' in url:
        if six.PY2:
            item.setProperty('inputstreamaddon', 'inputstream.adaptive')
        else:
            item.setProperty('inputstream', 'inputstream.adaptive')
        item.setProperty('inputstream.adaptive.manifest_type', 'ism')
        item.setMimeType('application/vnd.ms-sstr+xml')
        item.setContentLookup(False)
    item.setPath(url)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)

elif mode == 21:
    addon_log("download current file using youtube-dl service")
    mtype = 'video'
    if '[mp3]' in name:
        mtype = 'audio'
        name = name.replace('[mp3]', '')
    ytdl_download('', name, mtype)

elif mode == 22:
    addon_log("slproxy")
    try:
        from dsp import streamlink_proxy
        try:
            q = re.findall(r'\$\$QUALITY=(.+?)\$\$', url)[0]
        except:
            q = '' if re.search(r'\$\$RESOLVEONLY\$\$', url) else 'best'
        url = re.sub(r'\$\$QUALITY=.*?\$\$', '', url)

        try:
            m3u8mod = re.findall(r'\$\$M3U8MOD=(.+?)\$\$', url)[0]
        except:
            m3u8mod = None
        url = re.sub(r'\$\$M3U8MOD=.*?\$\$', '', url)

        try:
            prxy = re.findall(r'\$\$HTTPPROXY=(.+?)\$\$', url)[0]
        except:
            prxy = ''
        url = re.sub(r'\$\$HTTPPROXY=.*?\$\$', '', url)
        prxy = '' if prxy == '' else '&amp;p=%s' % prxy

        if re.search(r'\$\$RESOLVEONLY\$\$', url):
            url = re.sub(r'\$\$RESOLVEONLY\$\$', '', url)
            slProxy = streamlink_proxy.SLProxy_Helper()
            q = '' if q == '' else '&amp;q=%s' % q
            url = slProxy.resolve_url(urllib_parse.quote(url) + q + prxy)
            addon_log("setResolvedUrl")
            listitem = xbmcgui.ListItem(str(name))
            listitem.setInfo('video', {'Title': str(name)})
            listitem.setPath(url)
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem)

        else:
            slProxy = streamlink_proxy.SLProxy_Helper()
            if m3u8mod:
                url = urllib_parse.quote(url) + '&amp;m3u8mod=%s' % m3u8mod + prxy
            else:
                url = urllib_parse.quote(url) + '&amp;q=%s' % q + prxy
            listitem = xbmcgui.ListItem(str(name))
            listitem.setInfo('video', {'Title': str(name)})
            listitem.setPath(url)
            slProxy.playSLink(url, listitem)
    except:
        traceback.print_exc(file=sys.stdout)
        pass

elif mode == 23:
    addon_log("get info then download")
    mtype = 'video'
    if '[mp3]' in name:
        mtype = 'audio'
        name = name.replace('[mp3]', '')
    ytdl_download(url, name, mtype)

elif mode == 24:
    addon_log("Audio only youtube download")
    ytdl_download(url, name, 'audio')

elif mode == 25:
    addon_log("Searchin Other plugins")
    _search(url, name)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode == 55:
    addon_log("enabled lock")
    parentalblockedpin = addon.getSetting('parentalblockedpin')
    keyboard = xbmc.Keyboard('', 'Enter Pin')
    keyboard.doModal()
    if keyboard.isConfirmed():
        newStr = keyboard.getText()
        if newStr == parentalblockedpin:
            addon.setSetting('parentalblocked', "false")
            xbmcgui.Dialog().notification(addon_name, 'Parental Block Disabled', icon, 5000, False)
        else:
            xbmcgui.Dialog().notification(addon_name, 'Wrong Pin??', icon, 5000, False)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode == 56:
    addon_log("disable lock")
    addon.setSetting('parentalblocked', "true")
    xbmcgui.Dialog().notification(addon_name, 'Parental block enabled', icon, 5000, False)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

elif mode == 53:
    addon_log("Requesting JSON-RPC Items")
    pluginquerybyJSON(url)

if viewmode is not None:
    xbmc.executebuiltin("Container.SetViewMode(%s)" % viewmode)
