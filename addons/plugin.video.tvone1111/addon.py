# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 RACC
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
from kodi_six import xbmc, xbmcgui, xbmcaddon, xbmcplugin
from routing import Plugin

import os
import json
from future.moves.urllib.parse import urlencode

from datetime import datetime
from dateutil.parser import parse
from dateutil.tz import gettz, tzlocal

from resources.lib.lntv import LnTv, LiveStream

try:
    from xbmcvfs import translatePath
except ImportError:
    from kodi_six.xbmc import translatePath

addon = xbmcaddon.Addon()
plugin = Plugin()
plugin.name = addon.getAddonInfo("name")
USER_DATA_DIR = translatePath(addon.getAddonInfo("profile"))
ADDON_DATA_DIR = translatePath(addon.getAddonInfo("path"))
RESOURCES_DIR = os.path.join(ADDON_DATA_DIR, "resources")
if not os.path.exists(USER_DATA_DIR):
    os.makedirs(USER_DATA_DIR)

cert_file = os.path.join(RESOURCES_DIR, "com.playnet.androidtv.ads.crt")
cert_key_file = os.path.join(RESOURCES_DIR, "com.playnet.androidtv.ads.key")

mytv = LnTv(USER_DATA_DIR, cert_file, cert_key_file)


try:
    locale_timezone = json.loads(
        xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Settings.GetSettingValue", "params": {"setting": "locale.timezone"}, "id": 1}'
        )
    )
    if "result" in locale_timezone:
        if locale_timezone["result"]["value"]:
            local_tzinfo = gettz(locale_timezone["result"]["value"])
        else:
            local_tzinfo = tzlocal()
    else:
        local_tzinfo = tzlocal()
except:
    local_tzinfo = ""


def xbmc_curl_encode(url):
    return "{0}|{1}".format(url[0], urlencode(url[1]))


def time_from_zone(timestring, newfrmt="default", in_zone="UTC"):
    try:
        if newfrmt == "default":
            newfrmt = xbmc.getRegion("time").replace(":%S", "")
        in_time = parse(timestring)
        in_time_with_timezone = in_time.replace(tzinfo=gettz(in_zone))
        local_time = in_time_with_timezone.astimezone(local_tzinfo)
        return local_time.strftime(newfrmt)
    except:
        return timestring


@plugin.route("/")
def root():
    mytv.update_live_channels()
    list_items = []
    li = ListItem("[Live]", offscreen=True)
    url = plugin.url_for(list_live)
    list_items.append((url, li, True))

    for category in mytv.get_live_categories():
        li = ListItem(category.cat_name, offscreen=True)
        url = plugin.url_for(list_channels, cat=category.cat_id)
        list_items.append((url, li, True))

    xbmcplugin.addDirectoryItems(plugin.handle, list_items)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route("/vod")
def vod():
    mytv.update_vod_channels()
    list_items = []
    for category in mytv.get_vod_categories():
        li = ListItem(category.cat_name, offscreen=True)
        url = plugin.url_for(vod_list, cat=category.cat_id)
        list_items.append((url, li, True))

    xbmcplugin.addDirectoryItems(plugin.handle, list_items)
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route("/vod_list/<cat>")
def vod_list(cat):
    mytv.update_vod_channels()
    image_headers = {"User-Agent": mytv.user_agent}
    list_items = []
    for channel in mytv.get_vod_channels_by_category(int(cat)):
        li = ListItem(channel.name, offscreen=True)
        image = xbmc_curl_encode((channel.image_path, image_headers))
        li.setProperty("IsPlayable", "true")
        li.setInfo(type="Video", infoLabels={"Title": channel.name, "mediatype": "video"})
        li.setArt({"thumb": image, "icon": image})
        url = plugin.url_for(play_vod, channel=channel.channel_id)
        list_items.append((url, li, False))

    xbmcplugin.addDirectoryItems(plugin.handle, list_items)
    xbmcplugin.setContent(plugin.handle, "videos")
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route("/list_live")
def list_live():
    live_data = mytv.get_live_events()
    list_items = []
    for day, events in live_data.items():
        for event in events:
            if len(event["channel_list"]) == 0:
                continue
            event_time = time_from_zone(datetime.utcfromtimestamp(int(event["start"])).strftime("%c"), "%Y-%m-%d %H:%M")
            title = "[{0}] {1}".format(event_time, event["title"])
            li = ListItem(title, offscreen=True)
            li.setProperty("IsPlayable", "true")
            li.setInfo(type="Video", infoLabels={"Title": title, "mediatype": "video"})
            url = plugin.url_for(event_resolve, title=event["title"].encode("utf-8"))
            list_items.append((url, li, False))

    xbmcplugin.addSortMethod(plugin.handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.addDirectoryItems(plugin.handle, list_items)
    xbmcplugin.setContent(plugin.handle, "videos")
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route("/event_resolve.pvr")
def event_resolve():
    def find_event(data, title):
        for day, events in live_data.items():
            for event in events:
                if event["title"] == title:
                    return event

    live_data = mytv.get_live_events()

    live_event = find_event(live_data, plugin.args["title"][0])
    if len(live_event["channel_list"]) > 1:
        select_list = []
        for channel in live_event["channel_list"]:
            select_list.append(channel["c_name"])
        dialog = xbmcgui.Dialog()
        ret = dialog.select("Choose Stream", select_list)
        selected_channel = live_event["channel_list"][ret]
    else:
        selected_channel = live_event["channel_list"][0]

    link = selected_channel["links"][0]
    stream = mytv.get_live_link(link)
    live_stream = LiveStream(
        url=stream.get("link"),
        token=stream.get("token"),
        user_agent=stream.get("user_agent"),
        referer=stream.get("referer"),
        player_referer=stream.get("player_referer"),
        player_user_agent=stream.get("player_user_agent"),
    )
    link_list = [live_stream]
    link_list.extend(mytv.get_streams_by_channel_name(selected_channel["c_name"]))
    if len(link_list) > 1:
        select_list = []
        for link in link_list:
            select_list.append("Stream {0} {1}".format(link.token, link.stream_id))
        dialog = xbmcgui.Dialog()
        ret = dialog.select("Choose Stream", select_list)
        # if not
        selected_stream = link_list[ret]
    else:
        selected_stream = link_list[0]

    resolved_stream = mytv.resolve_stream(selected_stream)
    li = ListItem(path=xbmc_curl_encode(resolved_stream))
    if "playlist.m3u8" in resolved_stream[0]:
        li.setContentLookup(False)
        li.setMimeType("application/vnd.apple.mpegurl")
        if addon.getSetting("inputstream") == "true":
            if sys.version_info[0] == 2:
                li.setProperty("inputstreamaddon", "inputstream.adaptive")
            else:
                li.setProperty("inputstream", "inputstream.adaptive")
            li.setProperty("inputstream.adaptive.manifest_type", "hls")
            li.setProperty("inputstream.adaptive.stream_headers", urlencode(resolved_stream[1]))
    xbmcplugin.setResolvedUrl(plugin.handle, True, li)


@plugin.route("/list_channels/<cat>")
def list_channels(cat=None):
    mytv.update_live_channels()
    image_headers = {"User-Agent": mytv.user_agent}
    list_items = []
    for channel in mytv.get_live_channels_by_category(int(cat)):
        li = ListItem(channel.name, offscreen=True)
        image = xbmc_curl_encode((channel.image_path, image_headers))
        li.setProperty("IsPlayable", "true")
        li.setInfo(type="Video", infoLabels={"Title": channel.name, "mediatype": "video"})
        li.setArt({"thumb": image, "icon": image})
        url = plugin.url_for(play, c_id=channel.channel_id)
        list_items.append((url, li, False))

    xbmcplugin.addDirectoryItems(plugin.handle, list_items)
    xbmcplugin.setContent(plugin.handle, "videos")
    xbmcplugin.endOfDirectory(plugin.handle)


@plugin.route("/play/<c_id>/play.pvr")
def play(c_id):
    mytv.update_live_channels()
    image_headers = {"User-Agent": mytv.user_agent}
    stream_list = mytv.get_streams_by_channel_id(int(c_id))
    if stream_list.count() > 1:
        select_list = []
        for stream in stream_list:
            select_list.append("Stream {0} {1}".format(stream.token, stream.stream_id))
        dialog = xbmcgui.Dialog()
        ret = dialog.select("Choose Stream", select_list)
        # if not
        selected_stream = stream_list[ret]
    else:
        selected_stream = stream_list[0]

    resolved_stream = mytv.resolve_stream(selected_stream)
    image = xbmc_curl_encode((selected_stream.livechannel.image_path, image_headers))
    title = selected_stream.livechannel.name
    li = ListItem(title, path=xbmc_curl_encode(resolved_stream))
    li.setArt({"thumb": image, "icon": image})
    if "playlist.m3u8" in resolved_stream[0]:
        li.setContentLookup(False)
        li.setMimeType("application/vnd.apple.mpegurl")
        if addon.getSetting("inputstream") == "true":
            if sys.version_info[0] == 2:
                li.setProperty("inputstreamaddon", "inputstream.adaptive")
            else:
                li.setProperty("inputstream", "inputstream.adaptive")
            li.setProperty("inputstream.adaptive.manifest_type", "hls")
            li.setProperty("inputstream.adaptive.stream_headers", urlencode(resolved_stream[1]))
    xbmcplugin.setResolvedUrl(plugin.handle, True, li)


@plugin.route("/play_vod")
def play_vod():
    mytv.update_vod_channels()
    image_headers = {"User-Agent": mytv.user_agent}
    channel = int(plugin.args["channel"][0])
    stream_list = mytv.get_vodstreams_by_channel_id(channel)
    if stream_list.count() > 1:
        select_list = []
        for stream in stream_list:
            select_list.append(stream.quality)
        dialog = xbmcgui.Dialog()
        ret = dialog.select("Choose Stream", select_list)
        # if not
        selected_stream = stream_list[ret]
    else:
        selected_stream = stream_list[0]

    resolved_stream = mytv.resolve_stream(selected_stream)
    image = xbmc_curl_encode((selected_stream.vodchannel.image_path, image_headers))
    title = selected_stream.vodchannel.name
    li = ListItem(title, path=xbmc_curl_encode(resolved_stream))
    li.setArt({"thumb": image, "icon": image})
    if "playlist.m3u8" in resolved_stream[0]:
        li.setContentLookup(False)
        li.setMimeType("application/vnd.apple.mpegurl")
        if addon.getSetting("inputstream") == "true":
            if sys.version_info[0] == 2:
                li.setProperty("inputstreamaddon", "inputstream.adaptive")
            else:
                li.setProperty("inputstream", "inputstream.adaptive")
            li.setProperty("inputstream.adaptive.manifest_type", "hls")
            li.setProperty("inputstream.adaptive.stream_headers", urlencode(resolved_stream[1]))
    xbmcplugin.setResolvedUrl(plugin.handle, True, li)


if __name__ == "__main__":
    plugin.run(sys.argv)
    del mytv
