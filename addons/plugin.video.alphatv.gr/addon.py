# -*- coding: utf-8 -*-
import os
import sys
import json
import urllib.request
import urllib.parse
import re
import html

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_URL = sys.argv[0]
ADDON_HANDLE = int(sys.argv[1])
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# -------------------------------------------------------------------
# ΑΠΕΥΘΕΙΑΣ LINKS ΓΙΑ ΤΑ LIVE
# -------------------------------------------------------------------
DIRECT_LIVE_LINKS = {
    'alpha_gr': 'https://alphatvlive2.siliconweb.com/alphatvlive/live_abr/playlist.m3u8',
    'alpha_cy': 'https://alphatvlive2.siliconweb.com/alphatvlive/live_abr/playlist.m3u8'
}

# -------------------------------------------------------------------
# ΒΟΗΘΗΤΙΚΕΣ ΣΥΝΑΡΤΗΣΕΙΣ
# -------------------------------------------------------------------
def get_local_icon(icon_name):
    """Βρίσκει τις εικόνες σου μέσα στο resources/media"""
    return os.path.join(ADDON_PATH, 'resources', 'media', icon_name)

def fetch(url):
    """Κατεβάζει τον κώδικα HTML από τη σελίδα"""
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        return urllib.request.urlopen(req).read().decode('utf-8')
    except Exception as e:
        xbmc.log(f"Alpha TV Fetch Error: {str(e)}", xbmc.LOGERROR)
        return ""

def add_dir(title, action, url='', icon='DefaultFolder.png', is_folder=True, is_playable=False, **kwargs):
    """Φτιάχνει το μενού του Kodi"""
    list_item = xbmcgui.ListItem(label=title)
    list_item.setArt({'icon': icon, 'thumb': icon})
    
    if is_playable:
        list_item.setInfo('video', {'title': title})
        list_item.setProperty('IsPlayable', 'true')
        is_folder = False
        
    u = f"{ADDON_URL}?action={action}&url={urllib.parse.quote_plus(str(url))}&title={urllib.parse.quote_plus(title)}"
    for k, v in kwargs.items():
        u += f"&{k}={urllib.parse.quote_plus(str(v))}"
        
    xbmcplugin.addDirectoryItem(ADDON_HANDLE, u, list_item, is_folder)

# -------------------------------------------------------------------
# ΚΕΝΤΡΙΚΟ ΜΕΝΟΥ
# -------------------------------------------------------------------
def root():
    xbmcplugin.setPluginCategory(ADDON_HANDLE, 'ALPHA Player')
    
    # Ζωντανά Κανάλια
    add_dir('ALPHA TV (Ελλάδα) - LIVE', 'play_live', 'alpha_gr', icon=get_local_icon('live.png'), is_playable=True)
    add_dir('ALPHA Κύπρου - LIVE', 'play_live', 'alpha_cy', icon=get_local_icon('live.png'), is_playable=True)
    
    # Ειδήσεις (Με το σωστό /broadcasts/ url!)
    add_dir('Ειδήσεις (Ελλάδα)', 'gr_episodes', 'https://www.alphatv.gr/newscast/alpha-news/broadcasts/', icon=get_local_icon('news.png'))
    
    # On-Demand Ελλάδα
    add_dir('Σειρές (Ελλάδα)', 'gr_shows', 'https://www.alphatv.gr/series/', icon=get_local_icon('series.png'))
    add_dir('Εκπομπές (Ελλάδα)', 'gr_shows', 'https://www.alphatv.gr/shows/', icon=get_local_icon('shows.png'))
    
    # On-Demand Κύπρος
    add_dir('Σειρές (Κύπρος)', 'cy_shows', 'https://www.alphacyprus.com.cy/shows/ellinikes-seires', icon=get_local_icon('series.png'))
    add_dir('Ψυχαγωγία (Κύπρος)', 'cy_shows', 'https://www.alphacyprus.com.cy/shows/entertainment', icon=get_local_icon('shows.png'))
    add_dir('Ενημέρωση (Κύπρος)', 'cy_shows', 'https://www.alphacyprus.com.cy/shows/informative', icon=get_local_icon('news.png'))
    
    xbmcplugin.endOfDirectory(ADDON_HANDLE)

# -------------------------------------------------------------------
# SCRAPERS ΕΛΛΑΔΑΣ (On-Demand)
# -------------------------------------------------------------------
def gr_shows(url):
    xbmcplugin.setContent(ADDON_HANDLE, 'tvshows')
    html_data = fetch(url)
    
    pattern = r'<figure class="card__image">.*?data-src="([^"]+)".*?<h[23] class="card__title">\s*<a href="([^"]+)"[^>]*>([^<]+)</a>'
    matches = re.findall(pattern, html_data, re.S)
    
    seen = set()
    for img, show_url, title in matches:
        title = html.unescape(title.strip())
        if show_url not in seen:
            seen.add(show_url)
            
            if not show_url.endswith('/'):
                show_url += '/'
            episodes_url = show_url + 'episodes/'
            
            add_dir(title, 'gr_episodes', episodes_url, icon=img)

    xbmcplugin.endOfDirectory(ADDON_HANDLE)

def gr_episodes(url):
    xbmcplugin.setContent(ADDON_HANDLE, 'episodes')
    html_data = fetch(url)
    
    pattern_card = r'<figure class="card__image">.*?data-src="([^"]+)".*?<h[23] class="card__title">\s*<a href="([^"]+)"[^>]*>([^<]+)</a>'
    matches = re.findall(pattern_card, html_data, re.S)
    
    seen = set()
    base_url = url.replace('episodes/', '').replace('broadcasts/', '')
    
    if matches:
        for img, ep_url, title in matches:
            if ep_url not in seen and ep_url != url and ep_url != base_url:
                seen.add(ep_url)
                title = html.unescape(title.strip())
                add_dir(title, 'play_gr_vod', ep_url, icon=img, is_playable=True)
                
        # Επόμενη Σελίδα
        next_match = re.search(r'<a class="next page-numbers" href="([^"]+)"', html_data)
        if next_match:
            next_url = html.unescape(next_match.group(1))
            add_dir('➡️ Επόμενη Σελίδα...', 'gr_episodes', next_url, icon=get_local_icon('next.png'))
            
    else:
        # Εναλλακτική μέθοδος για απλές λίστες
        pattern_simple = r'<a href="([^"]+)"[^>]*>([^<]+)</a>'
        matches_simple = re.findall(pattern_simple, html_data)
        for ep_url, title in matches_simple:
            title = html.unescape(title.strip())
            if ep_url not in seen and '<' not in title and ep_url.startswith('http'):
                if ep_url != url and ep_url != base_url:
                    seen.add(ep_url)
                    add_dir(title, 'play_gr_vod', ep_url, is_playable=True)
                    
        # Επόμενη Σελίδα
        next_match = re.search(r'<a class="next page-numbers" href="([^"]+)"', html_data)
        if next_match:
            next_url = html.unescape(next_match.group(1))
            add_dir('➡️ Επόμενη Σελίδα...', 'gr_episodes', next_url, icon=get_local_icon('next.png'))

    xbmcplugin.endOfDirectory(ADDON_HANDLE)

def play_gr_vod(url):
    html_data = fetch(url)
    stream_url = ''
    
    # 1. Ψάχνει για το .mp4 link
    mp4_match = re.search(r'(https?://alphavod\.[^\s"\'\?]+\.mp4)', html_data)
    if mp4_match:
        stream_url = mp4_match.group(1)
    
    # 2. Ψάχνει για m3u8 αν δεν βρει mp4
    if not stream_url:
        m3u8_match = re.search(r'(https?://[^\s"\'\?]+\.m3u8)', html_data)
        if m3u8_match:
            stream_url = m3u8_match.group(1)
            
    # 3. Αν είναι YouTube
    if not stream_url:
        yt_match = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]+)', html_data)
        if yt_match:
            stream_url = f"plugin://plugin.video.youtube/play/?video_id={yt_match.group(1)}"

    if stream_url:
        # Η "Ασπίδα"
        if 'm3u8' in stream_url and '|' not in stream_url:
            stream_url += '|Referer=https://www.alphatv.gr/&Origin=https://www.alphatv.gr&User-Agent=' + urllib.parse.quote(UA)

        play_item = xbmcgui.ListItem(path=stream_url)
        play_item.setInfo('video', {'title': 'ALPHA VOD'})
        
        if '.m3u8' in stream_url:
            play_item.setMimeType('application/vnd.apple.mpegurl')
            play_item.setProperty('inputstream', 'inputstream.adaptive')
            play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
            
        xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, listitem=play_item)
    else:
        xbmcgui.Dialog().notification('ALPHA Player', 'Δεν βρέθηκε το αρχείο βίντεο', xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.setResolvedUrl(ADDON_HANDLE, False, xbmcgui.ListItem())

# -------------------------------------------------------------------
# SCRAPERS ΚΥΠΡΟΥ (On-Demand)
# -------------------------------------------------------------------
def cy_shows(url):
    xbmcplugin.setContent(ADDON_HANDLE, 'tvshows')
    html_data = fetch(url)
    blocks = re.split(r'class="box"', html_data)[1:]
    
    for block in blocks:
        link_match = re.search(r'<a[^>]+href="(/shows/[^"]+)"[^>]*>([^<]+)</a>', block)
        img_match = re.search(r'<img[^>]+src="([^"]+)"', block)
        
        if link_match:
            show_url = "https://www.alphacyprus.com.cy" + link_match.group(1) + "/webtv"
            title = html.unescape(link_match.group(2).strip())
            img = "https://www.alphacyprus.com.cy" + img_match.group(1) if img_match and not img_match.group(1).startswith('http') else (img_match.group(1) if img_match else 'DefaultVideo.png')
            
            add_dir(title, 'cy_episodes', show_url, icon=img)

    xbmcplugin.endOfDirectory(ADDON_HANDLE)

def cy_episodes(url):
    xbmcplugin.setContent(ADDON_HANDLE, 'episodes')
    html_data = fetch(url)
    blocks = re.split(r'class="box"', html_data)[1:]
    
    for block in blocks:
        if 'webtv' not in block: continue
        link_match = re.search(r'<a[^>]+href="([^"]+webtv/[^"]+)"[^>]*>([^<]+)</a>', block)
        img_match = re.search(r'<img[^>]+src="([^"]+)"', block)
        
        if link_match:
            ep_url = "https://www.alphacyprus.com.cy" + link_match.group(1)
            title = html.unescape(link_match.group(2).strip())
            img = "https://www.alphacyprus.com.cy" + img_match.group(1) if img_match and not img_match.group(1).startswith('http') else (img_match.group(1) if img_match else 'DefaultVideo.png')
            
            add_dir(title, 'play_cy_vod', ep_url, icon=img, is_playable=True)

    xbmcplugin.endOfDirectory(ADDON_HANDLE)

def play_cy_vod(url):
    html_data = fetch(url)
    stream_url = ""
    
    if 'cloudskep' in html_data:
        url_match = re.search(r'class="player-play-inline[^>]*href="([^"]+)"', html_data)
        sig_match = re.search(r'player-signature="([^"]+)"', html_data)
        if url_match:
            stream_url = url_match.group(1)
            if sig_match:
                stream_url += f"?wmsAuthSign={sig_match.group(1)}"
    else:
        hls_match = re.search(r'hls:\s*[\'"]([^\'"]+)[\'"]', html_data)
        if hls_match:
            stream_url = hls_match.group(1)

    if stream_url:
        if 'm3u8' in stream_url and '|' not in stream_url:
            stream_url += '|Referer=https://www.alphacyprus.com.cy/&Origin=https://www.alphacyprus.com.cy&User-Agent=' + urllib.parse.quote(UA)

        play_item = xbmcgui.ListItem(path=stream_url)
        play_item.setInfo('video', {'title': 'ALPHA CY VOD'})
        if '.m3u8' in stream_url:
            play_item.setMimeType('application/vnd.apple.mpegurl')
            play_item.setProperty('inputstream', 'inputstream.adaptive')
            play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
        xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, listitem=play_item)
    else:
        xbmcgui.Dialog().notification('ALPHA Player', 'Το βίντεο δε βρέθηκε', xbmcgui.NOTIFICATION_ERROR, 3000)

# -------------------------------------------------------------------
# ΑΝΑΠΑΡΑΓΩΓΗ LIVE
# -------------------------------------------------------------------
def play_live(channel_id):
    if xbmc.Player().isPlaying():
        xbmc.Player().stop()
        xbmc.sleep(500)

    stream_url = DIRECT_LIVE_LINKS.get(channel_id, '')
    title = 'ALPHA TV (Ελλάδα)' if channel_id == 'alpha_gr' else 'ALPHA Κύπρου'
    icon_file = get_local_icon('live.png')
            
    if not stream_url:
        xbmcgui.Dialog().notification('ALPHA Player', 'Αποτυχία φόρτωσης Live', xbmcgui.NOTIFICATION_ERROR, 3000)
        xbmcplugin.setResolvedUrl(ADDON_HANDLE, False, xbmcgui.ListItem())
        return

    if 'm3u8' in stream_url and '|' not in stream_url:
        if channel_id == 'alpha_gr':
            stream_url += '|Referer=https://www.alphatv.gr/&Origin=https://www.alphatv.gr&User-Agent=' + urllib.parse.quote(UA)
        else:
            stream_url += '|Referer=https://www.alphacyprus.com.cy/&Origin=https://www.alphacyprus.com.cy&User-Agent=' + urllib.parse.quote(UA)

    play_item = xbmcgui.ListItem(path=stream_url)
    play_item.setInfo('video', {'title': title})
    play_item.setArt({'icon': icon_file, 'thumb': icon_file, 'poster': icon_file})
    
    if '.m3u8' in stream_url:
        play_item.setMimeType('application/vnd.apple.mpegurl')
        play_item.setProperty('inputstream', 'inputstream.adaptive')
        play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')

    xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, listitem=play_item)

# -------------------------------------------------------------------
# ROUTER
# -------------------------------------------------------------------
def router():
    param_string = sys.argv[2][1:]
    params = dict(urllib.parse.parse_qsl(param_string))
    
    action = params.get('action')
    url = params.get('url', '')
    
    if action == 'play_live':
        play_live(url)
    elif action == 'gr_shows':
        gr_shows(url)
    elif action == 'gr_episodes':
        gr_episodes(url)
    elif action == 'play_gr_vod':
        play_gr_vod(url)
    elif action == 'cy_shows':
        cy_shows(url)
    elif action == 'cy_episodes':
        cy_episodes(url)
    elif action == 'play_cy_vod':
        play_cy_vod(url)
    else:
        root()

if __name__ == '__main__':
    router()