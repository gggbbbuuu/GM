# Tulip — Kodi helper library (`script.module.tulip`)

> Lightweight framework for building Kodi video / audio / executable plugins on Kodi 20+.
> Provides directory building, stream resolving (incl. InputStream Adaptive + DRM),
> Kodi API shortcuts, title cleaning / Greek transliteration, SQLite bookmarks,
> file helpers, downloaders and threading primitives.

- **Addon id:** `script.module.tulip`
- **Current version:** `4.1.3` (see `addon.xml` / `changelog.txt`)
- **Python:** 3 only (2.x support was dropped in 4.0.x)
- **Kodi:** 20+ (Nexus, Omega, Piers and later)
- **Extension point:** `xbmc.python.module`, library `resources/lib`
- **License:** GPL-3.0-only (see `LICENCES/`)
- **Author:** Twilight0

This library is the “sidekick” behind [plugin.video.alivegr](https://github.com/Twilight0/plugin.video.alivegr) —
AliveGR’s navigators, player, bookmarks, history and settings screens are all built on top of it.
Examples below are distilled from real AliveGR code (`router.py`,
`resources/lib/indexers/navigator.py`, `bookmarks.py`, `resources/lib/modules/player.py`).

---

## Table of contents

1. [What this addon does / does not do](#1-what-this-addon-does--does-not-do)
2. [Requirements & installation](#2-requirements--installation)
3. [Project layout](#3-project-layout)
4. [Quick start – minimal video plugin in ~30 lines](#4-quick-start--minimal-video-plugin-in-30-lines)
5. [Module reference](#5-module-reference)
   - [5.1 `tulip.init` – argv parsing](#51-tulipinit--argv-parsing)
   - [5.2 `tulip.log` – logging](#52-tuliplog--logging)
   - [5.3 `tulip.kodi` – Kodi API shortcuts](#53-tulipkodi--kodi-api-shortcuts)
   - [5.4 `tulip.directory` – listings & playback](#54-tulipdirectory--listings--playback)
   - [5.5 `tulip.cleantitle` – title cleaning & Greek transliteration](#55-tulipcleantitle--title-cleaning--greek-transliteration)
   - [5.6 `tulip.bookmarks` – SQLite favourites](#56-tulipbookmarks--sqlite-favourites)
   - [5.7 `tulip.utils` – files, strings, urls, misc](#57-tuliputils--files-strings-urls-misc)
   - [5.8 `tulip.getter` – downloads & HLS helpers ⚠️](#58-tulipgetter--downloads--hls-helpers-️)
   - [5.9 `tulip.workers` – threads](#59-tulipworkers--threads)
6. [End-to-end patterns (as used by AliveGR)](#6-end-to-end-patterns-as-used-by-alivegr)
7. [Kodi-version notes](#7-kodi-version-notes)
8. [Untested / known limitations](#8-untested--known-limitations)
9. [Changelog, credits, licence](#9-changelog-credits-licence)

---

## 1. What this addon does / does not do

**Does:**

- Parse `sys.argv` into `syshandle / sysaddon / params` (`tulip.init`).
- Wrap `xbmc / xbmcaddon / xbmcgui / xbmcplugin / xbmcvfs` into short, memorable
  functions and constants (`tulip.kodi`).
- Build virtual-folder listings from plain Python dicts, handling quoting,
  artwork, `VideoInfoTag / MusicInfoTag`, context menus, stream details,
  sorting, categories, playlists (`tulip.directory.builder`).
- Resolve a final stream URL into a `ListItem`, wiring `inputstream.adaptive`
  (`mpd / hls / ism`), custom headers, mime-type, ClearKey / Widevine licence
  and live-TV manifest flags (`tulip.directory.resolve`).
- Emit M3U playlists of internal `plugin://` URLs (`playlist_maker`).
- Navigate containers programmatically (`run_builtin` → `ActivateWindow` /
  `Container.Update` / `PlayMedia`).
- Clean / compare titles, strip HTML, normalize accents, transliterate Greek →
  Greeklish (`tulip.cleantitle`).
- Store user favourites in a SQLite `bookmarks.db` (`tulip.bookmarks`).
- Read / trim / append line-based history files, split lists into pages,
  quote URL paths, convert durations, parse headers, test connectivity
  (`tulip.utils`).
- Download files with progress and concatenate unencrypted HLS `.ts` segments
  (`tulip.getter`).
- Fire-and-forget threads (`tulip.workers.Thread`).

**Does not:**

- Fetch HTTP itself (no `client.request` any more — use `script.module.netclient`,
  `requests`, `urllib`, or ResolveURL + PluginsGR as AliveGR does).
- Cache HTTP (caching was removed in 2.9.x — use `script.module.unicache` /
  `pickled.FunctionCache` as AliveGR does).
- Parse DOM / resolve hosts (use `script.module.parsers` + `script.module.resolveurl`).
- Provide any UI on its own — it is a *dependency only*, there is no runnable
  plugin entry point.

---

## 2. Requirements & installation

`addon.xml` declares only:

```xml
<requires>
    <import addon="xbmc.python" version="3.0.0"/>
</requires>
<extension point="xbmc.python.module" library="resources/lib" />
```

That means in your own addon add:

```xml
<requires>
    <import addon="xbmc.python" version="3.0.0"/>
    <import addon="script.module.tulip" version="4.1.3"/>
</requires>
```

And install from the Twilight0 repository zip:

- Repo zip: `https://twilight0.github.io/repository.twilight0/` (file
  `repository.twilight0.zip`), or
- Clone / zip this folder and install via *Add-ons → Install from zip*.

In code, import like any Kodi module (Kodi adds `resources/lib` to `sys.path`
automatically once the dependency is declared):

```python
from tulip import kodi, directory, cleantitle, bookmarks
from tulip.log import log
from tulip.utils import list_divider, iteritems, convert_to_bool
from tulip.init import syshandle, sysaddon, params
from tulip.workers import Thread
```

> ⚠️ `tulip.getter` additionally needs `script.module.m3u8` (import `m3u8`)
> and a `useragents` module (import `get_ua`). Neither is declared in
> `addon.xml` nor vendored here, so `import tulip.getter` raises
> `ModuleNotFoundError: No module named 'useragents'` on a clean install.
> See [§5.8](#58-tulipgetter--downloads--hls-helpers-️).

---

## 3. Project layout

```text
addon.xml
changelog.txt
icon.png / fanart.jpg (optional in this repo snapshot)
LICENCES/GPL-3.0-only
resources/lib/__init__.py
resources/lib/tulip/
    __init__.py      # author marker only
    init.py          # sys.argv → syshandle / sysaddon / params
    kodi.py          # ~770 lines: xbmc* shortcuts, dialogs, settings, json-rpc, filesystem
    directory.py     # builder / resolve / playlist_maker / run_builtin
    cleantitle.py    # get / query / normalize / strip_accents / transliterate / stripTags / replaceHTMLCodes
    bookmarks.py     # add / delete / get / clear (sqlite3)
    utils.py         # file helpers, pickers, converters, url helpers
    getter.py        # retriever / download_media / M3U8 picker+downloader (needs extra deps)
    workers.py       # Thread wrapper
    log.py           # log()
```

Dev-only (not shipped): `.venv/` with `Kodistubs` (xbmc API stubs for
static checking), `m3u8`, `iso8601`.

---

## 4. Quick start – minimal video plugin in ~30 lines

`addon.xml`:

```xml
<extension point="xbmc.python.pluginsource" library="main.py">
    <provides>video</provides>
</extension>
```

`main.py`:

```python
# -*- coding: utf-8 -*-
from urllib.parse import parse_qsl
import sys
from tulip import directory, kodi

params = dict(parse_qsl(sys.argv[2][1:]))
action = params.get('action')
url = params.get('url')

def root():
    items = [
        {'title': 'Live TV', 'action': 'live', 'icon': kodi.addonmedia('live.png'),
         'isFolder': 'True', 'isPlayable': 'False'},
        {'title': 'Play on demand', 'action': 'play', 'url': 'https://example.com/video.mp4',
         'image': 'https://example.com/thumb.jpg', 'plot': 'Demo stream',
         'isFolder': 'False', 'isPlayable': 'True'},
    ]
    directory.builder(items, content='videos', category='Demo')

def play(url):
    # direct mp4, no InputStream needed:
    directory.resolve(url, meta={'title': params.get('title', 'Demo')})

if action is None:
    root()
elif action == 'live':
    root()  # expand further
elif action == 'play':
    play(url)
```

Install, open the plugin — you get a two-row folder with artwork, and the
second row plays. Everything else below is a richer version of this skeleton.

---

## 5. Module reference

### 5.1 `tulip.init` – argv parsing

File: `resources/lib/tulip/init.py:11`

```python
from tulip.init import syshandle, sysaddon, params
```

- `sys.argv[0]` → `sysaddon` (e.g. `plugin://plugin.video.alivegr/`)
- `sys.argv[1]` → `syshandle` (int, `-1` when run outside Kodi / service)
- `sys.argv[2]` → `params` dict via `parse_qsl` (defaults to `{'action': None}`)

Exported as `__all__ = ["syshandle", "sysaddon", "params"]`.

`directory.builder()` / `resolve()` use these implicitly, or accept an explicit
`argv` list (useful for Leia+ Python caching tests, services, or unit tests):

```python
directory.builder(items, argv=sys.argv)           # explicit, same as default
directory.builder(items, argv=['plugin://x/', '1', '?action=x'])
```

### 5.2 `tulip.log` – logging

File: `resources/lib/tulip/log.py:15`

```python
from tulip.log import log
import xbmc

log('Opening live TV')                      # LOGDEBUG by default
log('Stream failed: ' + url, level=xbmc.LOGINFO)
```

Format: `{addon name}, {version}:: {message}`. Never raises — falls back to
bare `xbmc.log(msg)` on failure.

### 5.3 `tulip.kodi` – Kodi API shortcuts

File: `resources/lib/tulip/kodi.py:1`. Thin aliases + convenience wrappers.
Import granularity is up to you:

```python
from tulip import kodi
kodi.infoDialog('Hello')
kodi.sleep(500)
```

#### 5.3.1 Aliases (constants)

| Tulip name | Kodi equivalent | Notes |
|---|---|---|
| `addon`, `i18n`, `setting`, `setSetting`, `addonInfo` | `xbmcaddon.Addon`, `getLocalizedString`, `getSetting`, `setSetting`, `getAddonInfo` | `setting('id')`, `i18n(30001)` |
| `addItem`, `addItems`, `directory`, `content`, `setproperty`, `setcategory`, `resolve`, `addsortmethod` | `xbmcplugin.*` | rarely called directly — use `directory.builder` |
| `infoLabel`, `condVisibility`, `jsonrpc`, `keyboard`, `sleep`, `execute`, `skin`, `player`, `monitor`, `wait`, `aborted` | `xbmc.*` | `wait`/`aborted` are bound `Monitor` methods |
| `cleanmovietitle`, `getregion`, `videostreamdetail` | `xbmc.*` | |
| `window`, `dialog`, `progressDialog`, `progressDialogGB`, `windowDialog`, `button`, `image`, `item` | `xbmcgui.*` | `item` = `ListItem` |
| `alphanum_input`, `password_input`, … | `xbmcgui.INPUT_*` constants | for `inputDialog` |
| `openFile`, `makeFile`, `makeFiles`, `deleteFile`, `deleteDir`, `listDir`, `exists`, `copy`, `rename`, `legalfilename`, `transPath` | `xbmcvfs.*` | |
| `skinPath`, `addonPath`, `dataPath`, `join`, `settingsFile`, `bookmarksFile`, `cacheFile`, `cacheDirectory` | derived paths | `bookmarks.db`, `cache.db`, `cache/` under profile; `cache/` is created on import |
| `integer = 1000` | — | legacy placeholder |

#### 5.3.2 Addon meta

```python
kodi.name()       # addonInfo('name')
kodi.version()    # addonInfo('version')
kodi.fanart()     # addonInfo('fanart')
kodi.icon()       # addonInfo('icon')
kodi.kodi_version()  # float(infoLabel('System.BuildVersion')[:4]), e.g. 21.0
```

#### 5.3.3 Dialogs

```python
kodi.infoDialog('Stream added', heading='AliveGR', time=3000)
kodi.okDialog('AliveGR', 'Nothing found')
if kodi.yesnoDialog('Clear history?', heading='AliveGR'):
    ...
choice = kodi.selectDialog(['720p', '1080p'], heading='Quality')  # -1 = cancel
text = kodi.inputDialog(heading='Search', default='')
kodi.text_viewer('Changelog', long_text, use_mono=False)
```

#### 5.3.4 Progress / busy helpers (context managers)

```python
with kodi.WorkingDialog():          # busydialognocancel on enter, idle on exit
    do_heavy_indexing()

with kodi.ProgressDialog('Downloading', line1='Starting…') as pd:
    for i, total in loop():
        pd.update(percent, line1='…')
        if pd.is_canceled():
            break

# delayed + background variants:
with kodi.ProgressDialog('Indexing', background=True) as pd:
    ...
with kodi.ProgressDialog('Loading', timer=2) as pd:  # only pops up after 2 s
    ...

# polling countdown (e.g. retry until stream appears):
with kodi.CountdownDialog('Waiting', line1='Retrying…', countdown=60, interval=5) as cd:
    stream = cd.start(check_function, args=[url])
```

#### 5.3.5 Settings / windows

```python
kodi.openSettings()                          # current addon
kodi.openSettings(query='1.2')               # focus category 1, control 2
kodi.openSettings(addon_id='inputstream.adaptive', explicit=True)

kodi.playlist(mode=1).clear()                # 1 = video, 0 = music
kodi.openPlaylist(1)                         # ActivateWindow(videoplaylist)
kodi.refresh()                               # Container.Refresh
kodi.update_container('plugin://…?action=x')
kodi.idle()                                  # close busydialognocancel
kodi.busynocancel() / kodi.busy()
kodi.close_all()                             # Dialog.Close(all)
kodi.set_view_mode(500)
kodi.addonmedia('live.png')                  # resources/media/live.png in caller addon
kodi.addonmedia('live.png', addonid='plugin.video.alivegr', theme='gemini')
kodi.setsortmethod('label')                  # see table below
```

`setsortmethod()` accepts (file `kodi.py:445`): `none, label, label_ignore_the,
date, size, file, drive_type, tracknum, duration, title, title_ignore_the,
artist, artist_ignore_the, album, album_ignore_the, genre, video_rating,
program_count, playlist_order, episode, video_title, video_sort_title,
video_sort_title_ignore_the, production_code, song_rating, mpaa_rating,
video_runtime, studio, studio_ignore_the, unsorted, bitrate, listeners,
country, date_added, full_path, label_ignore_folders, last_played, play_count,
channel, date_taken, video_user_rating, song_user_rating, year` (`year` maps to
`SORT_METHOD_YEAR` or legacy `SORT_METHOD_VIDEO_YEAR`).

#### 5.3.6 JSON-RPC

```python
kodi.json_rpc({"jsonrpc": "2.0", "method": "Addons.GetAddonDetails",
               "id": 1, "params": {"addonid": "inputstream.adaptive",
                                   "properties": ["enabled"]}})
kodi.addon_details('inputstream.adaptive')              # {'enabled': True}
kodi.addon_details('inputstream.adaptive', fields=['enabled', 'version'])
kodi.enable_addon('inputstream.adaptive', enable=True)
kodi.set_gui_setting('locale.language', 'resource.language.el_gr')
kodi.get_a_setting('locale.language')
kodi.get_skin_bool_setting('show_fanart')
kodi.set_skin_bool_setting('show_fanart', state='true')
kodi.set_skin_string_setting('homepage', 'movies')
kodi.set_default_addon('xbmc.gui.skin')
```

#### 5.3.7 System / navigation shortcuts

```python
kodi.conditional_visibility('System.HasAddon(inputstream.adaptive)')  # bool
kodi.get_info_label('Container.CurrentItem')
kodi.active_mode()            # 'videos' | 'music' | 'pictures' | 'programs' | 'other'
kodi.quit_kodi()
kodi.reload_skin()
kodi.android_activity('https://…', package='org.mozilla.firefox')
kodi.open_web_browser('https://alivegr.net/')
kodi.update_repositories()    # UpdateAddonRepos
kodi.update_addons()          # UpdateLocalAddons
kodi.add_to_playlist()        # Action(Queue)
kodi.clear_playlist()         # Playlist.Clear
kodi.toggle_watched() / kodi.toggle_debug() / kodi.skin_debug() / kodi.skin_choice()
kodi.global_settings() / kodi.pvr_settings() / kodi.system_info()
kodi.activate_screensaver()
kodi.install_addon('inputstream.adaptive')  # auto-confirms yes/no dialog
```

### 5.4 `tulip.directory` – listings & playback

File: `resources/lib/tulip/directory.py:18`. The heart of the library.

#### 5.4.1 `builder(items, …)` – turn dicts into a Kodi folder

Signature (verified):

```python
directory.builder(
    items, content=None, mediatype=None, infotype='video', argv=None,
    as_playlist=False, autoplay=False, clear_first=True, category=None,
    updateListing=False, cacheToDisc=True, end_directory=True,
    add_all_at_once=False
)
```

Each entry is a plain dict. Recognized keys (AliveGR-style):

```python
{
    'title': 'ERT1',                 # or int language id, e.g. 30001 → i18n
    'label': 'ERT1 [Live]',          # overrides title for display if present
    'action': 'play',                # → plugin://id/?action=play&…
    'url': 'https://…/index.m3u8',   # quote_plus-encoded into plugin url
    'image': 'https://…/logo.png',   # thumb/poster/banner/icon
    'icon': '…', 'fanart': '…',      # fall back to addon icon/fanart
    'artwork': {'thumb': …, 'poster': …, 'fanart': …},  # bypass auto art
    'name': 'ERT1', 'year': 2024, 'plot': '…', 'genre': ['News'] | 'News',
    'dash': 'true', 'query': json.dumps({...}),  # extra passthrough params
    'isFolder': 'True' | 'False',    # strings or bools (convert_to_bool)
    'isPlayable': 'True' | 'False',  # auto-sets IsPlayable + h264 stream detail
    'streaminfo': {'codec': 'h264', 'width': 1280, 'height': 720},
    'infotype': 'video',             # per-item override of infotype
    'cm': [                          # context menu
        {'title': 30054, 'query': {'action': 'refresh'}},          # int → i18n
        {'title': 'Clear cache', 'query': {'action': 'cache_clear'}},
    ],
    # any of ~50 Kodi info labels below are forwarded to InfoTag:
    'mediatype': 'movie', 'duration': 5400, 'rating': 7.5, 'director': […],
    'cast': […], 'studio': […], 'country': […], 'premiered': '2024-01-01', …
}
```

Meta keys forwarded (`directory.py:45`): `count, size, date, genre, country,
year, episode, season, sortepisode, sortseason, episodeguide, showlink, top250,
setid, tracknumber, rating, userrating, watched, playcount, overlay, cast,
castandrole, director, mpaa, plot, plotoutline, title, originaltitle,
sorttitle, duration, studio, tagline, writer, tvshowtitle, premiered, status,
set, setoverview, tag, imdbnumber, code, aired, credits, lastplayed, album,
artist, votes, path, trailer, dateadded, mediatype, dbid, discnumber, lyrics,
listeners, musicbrainztrackid, comment, picturepath, platform, genres,
publisher, developer, overview, gameclient`.

Behaviour notes:

- Empty `items` → logs and calls `endOfDirectory` (empty folder, no crash).
- `action/url/title/image/name/year/plot/genre/dash/query` are serialized as
  `plugin://id/?action=…&url=…&title=…` with `quote_plus`. The receiving side
  reads them back with `parse_qsl` (see router pattern in §6).
- `title`/`label`/`cm title` accept either `str` or `int` language id.
- `genre` accepts `str` or `list` (lists are JSON-encoded for the plugin URL
  but passed as real lists to `VideoInfoTag.setGenres`).
- Modern path: uses `getVideoInfoTag()` / `getMusicInfoTag()` when available,
  with graceful fallback to legacy `setInfo()`.
- `isPlayable=True` sets `IsPlayable=true`; without explicit `streaminfo` a
  default `h264` video stream detail is added.
- `content='videos'|'movies'|'episodes'|'music'|…` → `setContent`; `category`
  → `setPluginCategory` (skin header).
- `as_playlist=True` queues playables into the video (or music) playlist
  instead of a folder; `autoplay=True` starts playback immediately, otherwise
  opens the playlist window.
- `add_all_at_once=True` uses a single `addDirectoryItems()` call (faster for
  hundreds of rows, added in 4.0.x).
- `end_directory=False` lets you append multiple `builder()` calls before a
  final `kodi.directory(handle)`.

Minimal → rich example:

```python
from tulip import directory, kodi

items = [
    {
        'title': kodi.i18n(30001), 'action': 'live_tv',
        'icon': 'https://example.com/monitor.png',
        'isFolder': 'True', 'isPlayable': 'False',
        'cm': [{'title': 30054, 'query': {'action': 'refresh'}}],
    },
    {
        'label': 'Movie night', 'title': 'Taкса', 'action': 'play',
        'url': 'https://example.com/movie.mp4',
        'image': 'https://example.com/poster.jpg',
        'plot': 'A drama', 'year': 2023, 'genre': ['Drama'],
        'mediatype': 'movie', 'duration': 5400, 'rating': 7.2,
        'isFolder': 'False', 'isPlayable': 'True',
    },
]
directory.builder(items, content='movies', category='On demand', add_all_at_once=True)
kodi.setsortmethod('label')
```

AliveGR `navigator.root()` pattern (filter by setting, attach global CM):

```python
self.list = [i for i in self.list if convert_to_bool(i['show_item'])]
for item in self.list:
    item.update({'cm': [refresh, cache_clear, settings, tools]})
directory.builder(self.list)
```

#### 5.4.2 `resolve(url, …)` – play a stream

Signature (verified):

```python
directory.resolve(
    url, meta=None, icon=None, dash=False, manifest_type=None,
    inputstream_type='adaptive', headers=None, mimetype=None,
    resolved_mode=True, live=False, verify=True,
    licence_type=None, licence_key=None
)
```

Examples:

```python
# 1. Plain progressive file, headers appended with pipe:
directory.resolve(
    'https://cdn.example.com/v.mp4|User-Agent=Mozilla%2F5.0&Referer=https%3A%2F%2Fexample.com%2F',
    meta={'title': 'Demo'}, icon='https://example.com/thumb.jpg'
)

# 2. HLS with InputStream Adaptive + custom headers dict:
directory.resolve(
    'https://example.com/live.m3u8', dash=True, manifest_type='hls',
    mimetype='application/x-mpegURL',
    headers={'User-Agent': 'Kodi', 'Referer': 'https://example.com/'},
    meta={'title': 'Live channel'}, live=True
)

# 3. DASH Widevine:
directory.resolve(
    mpd_url, dash=True, manifest_type='mpd',
    licence_type='com.widevine.alpha',
    licence_key='https://license.example.com/|R{SSM}|',
    meta={'title': title}, icon=image
)

# 4. DASH ClearKey (dict or JSON string accepted):
directory.resolve(
    mpd_url, dash=True,
    licence_type='org.w3.clearkey',
    licence_key={'abcdef0123456789': '0011223344556677'},
)

# 5. Push into player instead of setResolvedUrl (strm-style / background):
directory.resolve(url, resolved_mode=False)
```

Rules:

- Empty `url` → logs and returns (no Kodi error popup).
- `url|headers` pipe syntax is understood; explicit `headers` dict/str wins.
- `verify=False` appends `verifypeer=false` (for self-signed hosts).
- `dash=True` requires `inputstream.adaptive` enabled; otherwise falls back to
  plain playback. Auto-detects `mpd` vs `hls` from extension when
  `manifest_type` is omitted; sets `inputstream.adaptive.manifest_type` on
  Kodi < 21, `stream_headers / manifest_headers / stream_params /
  common_headers` depending on Kodi version (19/20/21+ matrix in
  `directory.py:494`).
- `live=True` sets `manifest_update_parameter=&start_seq=$START_NUMBER$`.
- AliveGR wraps this with pre-flight checks + DRM unpacking (see §6.3).

#### 5.4.3 `playlist_maker(items, argv)` – M3U of internal URLs

```python
m3u = directory.playlist_maker(items, argv=sys.argv)
# #EXTM3U
# #EXTINF:0 tvg-logo="&image=…",ERT1
# plugin://plugin.video.alivegr/?action=play&url=…&title=…
```

Each item needs at least `action` + `title`; `url/image/name/year/plot` are
optional. Used by AliveGR’s `live_m3u` to export live TV.

#### 5.4.4 `run_builtin(…)` – drive the container

```python
from tulip.directory import run_builtin

run_builtin(content_type='video')                       # ActivateWindow(videos, plugin://id/?content_type=video)
run_builtin(action='directory', url=url, title=title)   # Container.Update(plugin://…?action=directory&url=…)
run_builtin(action='play', url=url, command='PlayMedia')
url_only = run_builtin(action='x', get_url=True)        # return string, don't execute
```

`query={…}` dict overrides individual kwargs; `path_history=',return' |
',replace'` controls back-stack; `command` defaults to
`('ActivateWindow', 'Container.Update')`. Raises `TypeError` with no args,
`AttributeError` on unknown `content_type`.

AliveGR use: `activate_other_addon()` → `run_builtin(addon_id=…, action=…,
url=…, content_type=…)` to jump between video/audio/executable sections.

### 5.5 `tulip.cleantitle` – title cleaning & Greek transliteration

File: `resources/lib/tulip/cleantitle.py:16`. Pure Python, no Kodi needed.

```python
from tulip import cleantitle

cleantitle.get('Hello: World (2020) [HD] vs. Test')
# 'helloworldvstest'  — lowercased, brackets/parens/punctuation/whitespace stripped
# (note: strips numeric HTML entities first)

cleantitle.get('ΤΑΙΝΙΑ (2023)', lower=False)
# 'ΤΑΙΝΙΑ'

cleantitle.query("Stathis: Psomi: test's")
# "Stathis: Psomi"  — drops suffix after last colon, removes apostrophes

cleantitle.normalize('Café naïve')
# 'Cafe naive'  — NFKD → ASCII

cleantitle.strip_accents('Καλημέρα café')
# 'Καλημερα cafe'  — removes combining marks only, keeps base Greek

cleantitle.transliterate('Καλημέρα κόσμε')
# 'Kalimera kosme'
cleantitle.transliterate('αυγό ευχαριστώ Μπράβο ντομάτα')
# 'avgo efxaristo Bravo domata'
# handles αυ/ευ/ηυ → av/af etc. by voicing context, μπ/ντ/γκ initial vs medial
# (b/mp, d/nt, g/gk), ου/γγ/τσ/τζ/αι/ει/οι/υι digraphs, χ→x, ξ→ks, ψ→ps …

cleantitle.stripTags("<b>hi</b> <a href='x'>there</a>")
# 'hi there'

cleantitle.replaceHTMLCodes('Tom &amp; Jerry &#8211; test')
# 'Tom & Jerry – test'
```

Use it for search keys (`get`), display queries (`query`), sorting
(`strip_accents(...).lower()` as AliveGR’s bookmarks do), and URL-safe
Greeklish (`transliterate` + `normalize`, added in 4.1.x).

> Known quirk: `get()`’s regex emits `FutureWarning: Possible nested set`
> (character-class brackets inside alternation). Harmless, but don’t copy the
> pattern verbatim into strict-warning projects.

### 5.6 `tulip.bookmarks` – SQLite favourites

File: `resources/lib/tulip/bookmarks.py:19`. Path defaults to
`kodi.bookmarksFile` (`…/addon_data/<your-id>/bookmarks.db`).

AliveGR router wiring:

```python
# router.py
elif action == 'addBookmark':
    bm.add(url)          # url is a JSON string (see below)
elif action == 'deleteBookmark':
    bm.delete(url)
elif action == 'bookmarks':
    Indexer().bookmarks()
```

Adding (sender side — e.g. playback-history or directory item):

```python
import json
from tulip import bookmarks as bm

bookmark = dict((k, v) for k, v in item.items() if k != 'next')
bookmark['bookmark'] = item['url']          # dedupe key part 1
payload = json.dumps(bookmark)              # must contain 'bookmark' + 'action'
bm.add(payload)
```

The `md5(bookmark + action)` becomes the row id; re-adding overwrites.
`delete` expects `delbookmark` + `action` keys instead:

```python
item = dict((k, v) for k, v in row.items() if k != 'next')
item['delbookmark'] = row['url']
cm = {'title': 30081, 'query': {'action': 'deleteBookmark', 'url': json.dumps(item)}}
```

Reading / listing (AliveGR `bookmarks.Indexer().bookmarks()`):

```python
rows = bm.get() or []
if not rows:
    directory.builder([{'title': 30033, 'action': None}])
else:
    for r in rows:
        r.update({'cm': [{'title': 30081,
                           'query': {'action': 'deleteBookmark',
                                     'url': json.dumps(del_item)}}]})
    rows = sorted(rows, key=lambda k: strip_accents(k['title'].lower()))
    directory.builder(rows)
```

Clearing:

```python
bm.clear(table=['bookmark'])   # drops listed tables + VACUUM
```

> ⚠️ `clear(table=None)` iterates `None` → silently swallowed `TypeError`
> (all tulip bookmark functions swallow exceptions and return `None`).
> **Always pass an explicit list** like `['bookmark']`, or delete the file as
> AliveGR’s `purge_bookmarks()` does (`kodi.deleteFile(kodi.bookmarksFile)`).

### 5.7 `tulip.utils` – files, strings, urls, misc

File: `resources/lib/tulip/utils.py:19`. Mixed Kodi + pure helpers.

```python
from tulip.utils import (
    read_file, trim_content, add_to_file, process_file, single_picker,
    duration_converter, percent, py3_dec, enum, list_divider, merge_dicts,
    quote_paths, form_data_conversion, url2name, iteritems,
    check_connection, parse_headers, convert_to_bool,
)
```

File-backed history (AliveGR stores search + playback history as JSON-lines):

```python
text = read_file(path)                              # whole file
lines = read_file(path, line_by_line=True, reverse=True)  # newest first

add_to_file(path, json.dumps(params))               # append if missing, auto-trim to 10 lines
trim_content(path, trim_size=10)

# remove or interactively rename a line, then Container.Refresh:
process_file(path, text, mode='remove', refresh_container=True)
process_file(path, text, mode='change', heading='Edit term')
```

Pickers / converters:

```python
choice = single_picker(['a', 'b'], heading='Choose')       # select dialog, None on cancel
choice = single_picker([('Label', value), …])              # tuple list supported
seconds = duration_converter('02:30')                      # 150
p = percent(1, 3)                                          # 33 (capped at 100)
s = py3_dec(b'bytes')                                      # decode utf-8 if bytes
Color = enum(RED='red', GREEN='green')
pages = list_divider(range(100), 20)                       # paginate listings
merged = merge_dicts({'a': 1}, {'b': 2})
```

URL / HTTP helpers:

```python
quote_paths('https://example.com/αβ γ/file name.mp4')
# 'https://example.com/%CE%B1%CE%B2%20%CE%B3/file%20name.mp4'

form_data_conversion({'a': '1'})   # 'a=1'
form_data_conversion('a=1&b=2')    # {'a': '1', 'b': '2'}
url2name('https://example.com/v.mp4|User-Agent=x')  # 'v.mp4'
parse_headers('Content-Type: video/mp4\nX-A: b')    # {'Content-Type': 'video/mp4', …}
check_connection('1.1.1.1', timeout=3)              # HEAD /, True/False (logs on fail)
iteritems({'a': 1})                                 # iter(d.items()) — py2/3 shim
convert_to_bool('True')   # True  ('y/yes/t/true/on/1')
convert_to_bool('False')  # False ('n/no/f/false/off/0'/None)
```

### 5.8 `tulip.getter` – downloads & HLS helpers ⚠️

File: `resources/lib/tulip/getter.py:22`.

> **Status: partially untested, extra dependencies required.**
> `getter.py` does `import m3u8` and `from useragents import get_ua` at module
> top. Neither package is vendored nor declared in `addon.xml`, so on a stock
> Kodi install `from tulip import getter` / `import tulip.getter` fails with
> `ModuleNotFoundError: No module named 'useragents'`. AliveGR 3.x itself no
> longer depends on this module (M3U8 handling moved to adaptive / best-stream
> logic + `script.module.m3u8` as an optional separate dependency).
> Only use it if you also ship `script.module.m3u8` + a `useragents` module,
> or vendor those imports.

When the deps *are* present:

```python
from tulip.getter import retriever, download_media, M3U8

# low-level copy with optional progress callback:
retriever(source, destination, user_agent=None, referer=None,
          reporthook=lambda blocks, size, total: …, Referer='https://…')

# file download with Kodi progress dialog + ETA + cancel:
download_media('https://example.com/movie.mp4', 'special://home/videos/',
               filename='movie.mp4')

# HLS: pick variant then download:
m = M3U8('https://example.com/master.m3u8|User-Agent=Kodi', heading='Quality')
url = m.m3u8_picker()                       # select dialog of WxH, or direct url
m.downloader('/tmp/hls', filename='episode.ts')
```

`M3U8.downloader` only supports **unencrypted** TS segments (concatenates to
one `.ts`), appends `|headers` through variant selection, and shows per-segment
progress. Encrypted (`AES-128`, SAMPLE-AES, Widevine) playlists are out of scope.

### 5.9 `tulip.workers` – threads

File: `resources/lib/tulip/workers.py:14`.

```python
from tulip.workers import Thread

t = Thread(target=fetch, arg1, arg2)   # args passed positionally
t.start()
t.join()
```

Thin `threading.Thread` wrapper that swallows `TypeError` from wrong arity
inside `run()`. Good for parallel metadata lookups; for anything needing a
result, prefer `concurrent.futures` in your own addon.

---

## 6. End-to-end patterns (as used by AliveGR)

### 6.1 Router (`router.py` pattern)

```python
from sys import argv
from urllib.parse import parse_qsl
from tulip import kodi, bookmarks as bm
from tulip.directory import run_builtin

params = dict(parse_qsl(argv[2][1:]))
action, url = params.get('action'), params.get('url')

def route():
    if action is None:
        Indexer().root()
    elif action == 'root':
        run_builtin(content_type='video')
    elif action == 'live_tv':
        live.Indexer().live_tv()
    elif action == 'play':
        player.player(url, params)
    elif action == 'addBookmark':
        bm.add(url)
    elif action == 'deleteBookmark':
        bm.delete(url)
    elif action == 'refresh':
        kodi.refresh()

route()
```

### 6.2 Indexer with history + favourites CM

```python
bookmark = dict((k, v) for k, v in i.items() if k != 'next')
bookmark['bookmark'] = i['url']
bookmark_cm = {'title': 30080,
               'query': {'action': 'addBookmark', 'url': json.dumps(bookmark)}}
remove_cm = {'title': 30485,
             'query': {'action': 'delete_from_history', 'query': json.dumps(i)}}
i.update({'isPlayable': 'true', 'cm': [bookmark_cm, remove_cm]})
directory.builder(self.list)
```

### 6.3 Player (`player.player` pattern, simplified)

```python
from tulip import directory, kodi

stream = resolveurl.HostedMediaFile(url).resolve() if is_hosted else url

# split Kodi pipe headers, unpack DRM if your indexer embeds it:
if '|' in stream:
    stream, _, h = stream.rpartition('|')
    headers = dict(parse_qsl(h))
    if 'DRM' in headers:
        drm = json.loads(headers.pop('DRM'))
        licence_type, licence_key = drm[0], drm[1]
    stream = '|'.join([stream, urlencode(headers)])

dash = any(x in stream for x in ('.mpd', '.m3u8', '.ism', 'dash'))
directory.resolve(
    stream, meta={'title': title, 'plot': plot}, icon=image,
    dash=dash, manifest_type='hls' if '.m3u8' in stream else 'mpd',
    mimetype='application/x-mpegURL' if '.m3u8' in stream else None,
    licence_type=licence_type, licence_key=licence_key,
)
```

AliveGR adds reliability layers around this: stream-availability pre-flight
(status + content-type + `#EXTM3U`/`<MPD>` sniffing), secondary-stream
fallback sorted by reliability (clear HLS > YouTube/Twitch > clear DASH > DRM),
and auto-jump to the next live channel (capped at 5 fails).

### 6.4 Cross-section jump + settings

```python
from tulip.directory import run_builtin
run_builtin(addon_id='plugin.video.alivegr', action=None, content_type='audio')
kodi.openSettings()
kodi.open_web_browser('https://alivegr.net/')
```

---

## 7. Kodi-version notes

- **InfoTags:** `builder` prefers `getVideoInfoTag()` / `getMusicInfoTag()`
  (Omega/Piers API) and falls back to `setInfo()` on older builds.
- **InputStream Adaptive:** property names changed across 19/20/21.
  `resolve()` handles the matrix: `inputstream.adaptive.manifest_type` (< 21),
  `manifest_headers` / `stream_params` (> 19), `common_headers` (> 21.8),
  plus `manifest_update_parameter` for live. Do **not** set these yourself —
  pass `dash/manifest_type/headers/live` and let `resolve()` map them.
- **Mime types:** HLS defaults to `application/x-mpegURL`, DASH to
  `application/xml+dash` when omitted.
- `kodi.kodi_version()` parses `System.BuildVersion[:4]` as float — guard
  alphas/betas that don’t parse cleanly.
- Python 2-isms (`iteritems`, `py3_dec`, `xbmc.python` version tricks) are kept
  as harmless shims; new code should use native Python 3.

---

## 8. Untested / known limitations

- **`tulip.getter` untested without extra deps** — see §5.8. `retriever`,
  `download_media`, `M3U8.stream_picker / m3u8_picker / downloader` require
  manual testing with `m3u8` + `useragents` installed. Encrypted HLS and
  cancellation mid-segment are also untested.
- **`bookmarks.clear()` requires explicit table list** — `clear()` with
  default `table=None` raises internally (swallowed). Call
  `clear(table=['bookmark'])`.
- **`directory.playlist_maker` early-returns `None`** if any item lacks
  `action`; `icon/title` with non-ASCII need `str`, not pre-encoded bytes.
- **`run_builtin(image=…)`** appends `query` instead of `image` (copy-paste in
  `directory.py:587`) — pass `query=` dict to be safe.
- **`cleantitle.get` FutureWarning** (nested set) — see §5.5.
- **Swallowed exceptions:** `bookmarks.*` and parts of `builder` catch broad
  `Exception` and `pass` / return `None`. Check Kodi logs (`tulip.log`) when a
  listing silently comes up empty.
- No test suite ships with the addon; the examples in §5 were verified against
  `Kodistubs 21` + stdlib only (`cleantitle`, `utils`, `workers`, `init`,
  signatures of `kodi/directory/bookmarks`). Kodi-runtime behaviour (dialogs,
  playback, InfoTags) follows AliveGR’s production usage but should be
  re-verified on your target Kodi version.

---

## 9. Changelog, credits, licence

- Full history: `changelog.txt` (1.0.0 → 4.1.x). Highlights:
  - **4.1.x** — modernization, Greek transliteration.
  - **4.0.x** — Python-3-only strip-down, licence support in `resolve`,
    batched `addDirectoryItems`, genre-as-list.
  - **3.x** — `certifi`, HLS-TS saver, auth/limit in net module.
  - **2.x** — ResolveURL-derived net/cache, YouTube/scrapetube helpers,
    parsers, fuzzy matching, Kodi 19 fixes (since removed/outsourced again).
- Credits: tknorris (shared `kodi`/`log`/`parsedom` origins), globocom (m3u8
  modules), Kodi team (InputStream Adaptive), Flaticon artwork in downstream
  addons, and the AliveGR / PluginsGR / ResolveURL ecosystem for production
  battle-testing.
- Licence: **GPL-3.0-only**. See `LICENCES/GPL-3.0-only`.
  Artwork in downstream addons may carry separate attribution (cf. AliveGR
  README).

**Have fun building.**
