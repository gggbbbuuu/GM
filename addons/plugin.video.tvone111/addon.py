# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 RACC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import unicode_literals, absolute_import

import sys
from xbmcgui import ListItem
from kodi_six import xbmcgui, xbmcaddon, xbmcplugin
from routing import Plugin
import os
from socket import gethostbyname
from future.moves.urllib.parse import urlencode, urlparse
from resources.lib.rbtv import RBTV

try:
    from xbmcvfs import translatePath
except ImportError:
    from kodi_six.xbmc import translatePath

addon = xbmcaddon.Addon()
plugin = Plugin()
plugin.name = addon.getAddonInfo("name")
USER_DATA_DIR = translatePath(addon.getAddonInfo("profile"))
if not os.path.exists(USER_DATA_DIR):
    os.makedirs(USER_DATA_DIR)
RB = RBTV(USER_DATA_DIR)


def xbmc_curl_encode(url):
    return "{0}|{1}".format(url[0], urlencode(url[1]))


def encode_liveproxy_url(stream):
    streamlink_command = []
    for header in stream[1].items():
        streamlink_command.append(("http-header", "{0}={1}".format(*header)))
    streamlink_command.append(("url", stream[0]))
    streamlink_command.append(("q", addon.getSetting("streamlink_stream")))
    liveproxy_url = urlparse(addon.getSetting("plugin_liveproxy"))
    return liveproxy_url._replace(path="/play/", query=urlencode(streamlink_command)).geturl()


@plugin.route("/")
def root():
    list_items = []
    for item in RB.get_categories():
        li = ListItem(item.title)
        url = plugin.url_for(list_channels, cat=item.category_id)
        list_items.append((url, li, True))
    xbmcplugin.addDirectoryItems(plugin.handle, list_items)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route("/list_channels/<cat>")
def list_channels(cat):
    list_items = []
    for item in RB.get_category_by_id(int(cat)).videos:
        li = ListItem(item.title)
        li.setProperty("IsPlayable", "true")
        li.setInfo(type="Video", infoLabels={"Title": item.title, "mediatype": "video"})
        image = xbmc_curl_encode(RB.resolve_logo(item.logo_url))
        li.setArt({"thumb": image, "icon": image})
        url = plugin.url_for(play, c_id=item.video_id)
        list_items.append((url, li, False))
    xbmcplugin.addDirectoryItems(plugin.handle, list_items)
    xbmcplugin.setContent(plugin.handle, "videos")
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route("/play/<c_id>/play.pvr")
def play(c_id):
    item = RB.get_video_by_id(int(c_id))
    if item.streams.count() > 1:
        select_list = []
        for stream in item.streams:
            select_list.append("Stream {0} {1}".format(stream.token, stream.stream_id))
        dialog = xbmcgui.Dialog()
        ret = dialog.select("Choose Stream", select_list)
        if ret >= 0:
            selected_stream = item.streams[ret]
        else:
            selected_stream = ""
    else:
        selected_stream = item.streams[0]

    if selected_stream:
        image = xbmc_curl_encode(RB.resolve_logo(item.logo_url))
        stream, headers = RB.resolve_stream(selected_stream)
        if "playlist.m3u8" in stream:
            stream_plugin = addon.getSetting("stream_plugin")
            if stream_plugin == "inputstream.adaptive":
                headers["connection"] = "keep-alive"
                li = ListItem(item.title, path=xbmc_curl_encode((stream, headers)))
                li.setContentLookup(False)
                li.setMimeType("application/vnd.apple.mpegurl")
                if sys.version_info[0] == 2:
                    li.setProperty("inputstreamaddon", "inputstream.adaptive")
                else:
                    li.setProperty("inputstream", "inputstream.adaptive")
                li.setProperty("inputstream.adaptive.manifest_type", "hls")
                li.setProperty("inputstream.adaptive.stream_headers", urlencode(headers))
                li.setProperty("inputstream.adaptive.license_key", "|" + urlencode(headers))
            elif stream_plugin == "service.liveproxy":
                _parsed = urlparse(stream)
                _host = _parsed.netloc.split(":")
                _host[0] = gethostbyname(_host[0])
                _stream_url = _parsed._replace(netloc=":".join(_host)).geturl()
                headers["Host"] = _parsed.netloc
                li = ListItem(item.title, path=encode_liveproxy_url((_stream_url, headers)))
                li.setContentLookup(False)
                li.setMimeType("video/mp2t")
        else:
            li = ListItem(item.title, path=xbmc_curl_encode((stream, headers)))
        li.setArt({"thumb": image, "icon": image})
        xbmcplugin.setResolvedUrl(plugin.handle, True, li)
    else:
        xbmcplugin.setResolvedUrl(plugin.handle, False, ListItem())


if __name__ == "__main__":
    plugin.run(sys.argv)
    del RB
