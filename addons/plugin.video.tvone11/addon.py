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
from __future__ import unicode_literals

import sys
from xbmcgui import ListItem
from kodi_six import xbmc, xbmcgui, xbmcaddon, xbmcplugin
from routing import Plugin

import os
from requests.exceptions import RequestException
from future.moves.urllib.parse import urlencode
from resources.lib.swift import SwiftStream

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


def log(msg, level=xbmc.LOGDEBUG):
    xbmc.log("[{0}] {1}".format(plugin.name, msg), level=level)


def xbmc_curl_encode(url):
    return "{0}|{1}".format(url[0], urlencode(url[1]))


TV = SwiftStream(USER_DATA_DIR)


@plugin.route("/")
def root():
    list_items = []
    for cat in TV.get_categories():
        image = xbmc_curl_encode((cat.c_image, {"User-Agent": "okhttp/3.10.0"}))
        li = ListItem(cat.c_name, offscreen=True)
        li.setArt({"thumb": image, "icon": image})
        url = plugin.url_for(list_channels, cat_id=cat.c_id)
        list_items.append((url, li, True))
    xbmcplugin.addDirectoryItems(plugin.handle, list_items)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route("/list_channels/<cat_id>")
def list_channels(cat_id):
    list_items = []
    try:
        for channel in TV.get_category(cat_id):
            title = channel.title
            image = xbmc_curl_encode((channel.thumbnail, {"User-Agent": "okhttp/3.10.0"}))
            li = ListItem(title, offscreen=True)
            li.setProperty("IsPlayable", "true")
            li.setArt({"thumb": image, "icon": image})
            li.setInfo(type="Video", infoLabels={"Title": title, "mediatype": "video"})
            url = plugin.url_for(play, cat_id=channel.c_id, channel_id=channel._id)
            list_items.append((url, li, False))
        xbmcplugin.addDirectoryItems(plugin.handle, list_items)
        xbmcplugin.setContent(plugin.handle, "videos")
        xbmcplugin.endOfDirectory(plugin.handle)
    except (ValueError, RequestException) as e:
        """No data"""
        log(e)
        dialog = xbmcgui.Dialog()
        dialog.notification(plugin.name, "Remote Server Error", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(plugin.handle, False)


@plugin.route("/play/<cat_id>/<channel_id>/play.pvr")
def play(cat_id, channel_id):
    channel = TV.get_channel_by_id(cat_id, channel_id)
    try:
        if len(channel.streams) > 1:
            dialog = xbmcgui.Dialog()
            ret = dialog.select("Choose Stream", [s.name for s in channel.streams])
            stream = channel.streams[ret]
        else:
            stream = channel.streams[0]
        media_url = TV.get_stream_link(stream)

        image = xbmc_curl_encode((channel.thumbnail, {"User-Agent": "okhttp/3.10.0"}))
        li = ListItem(channel.title, path=xbmc_curl_encode(media_url))
        li.setArt({"thumb": image, "icon": image})
        if "playlist.m3u8" in media_url[0]:
            li.setContentLookup(False)
            li.setMimeType("application/vnd.apple.mpegurl")
            if addon.getSetting("inputstream") == "true":
                if sys.version_info[0] == 2:
                    li.setProperty("inputstreamaddon", "inputstream.adaptive")
                else:
                    li.setProperty("inputstream", "inputstream.adaptive")
                li.setProperty("inputstream.adaptive.manifest_type", "hls")
                li.setProperty("inputstream.adaptive.stream_headers", urlencode(media_url[1]))
                li.setProperty("inputstream.adaptive.manifest_headers", urlencode(media_url[1]))
                li.setProperty("inputstream.adaptive.license_key", "|" + urlencode(media_url[1]))
        xbmcplugin.setResolvedUrl(plugin.handle, True, li)
    except (ValueError, RequestException) as e:
        log(e)
        dialog = xbmcgui.Dialog()
        dialog.notification(plugin.name, "Remote Server Error", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(plugin.handle, False, ListItem())


if __name__ == "__main__":
    plugin.run(sys.argv)
    del TV
