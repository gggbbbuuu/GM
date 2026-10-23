# -*- coding: utf-8 -*-
"""
ResolveURL Test Suite Harness
Mocks the Kodi environment and loads ResolveURL modules for standalone testing.
"""

import os
import sys
import types

# Ensure temp resources exist for ResolveURL settings initialization
os.makedirs('/tmp/resources', exist_ok=True)
for path in ['/tmp/settings.xml', '/tmp/resources/settings.xml']:
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write('<settings></settings>')


class MockWindowXMLDialog:
    pass


class MockWindowDialog:
    pass


def make_mod(name, **attrs):
    m = types.ModuleType(name)
    m.__all__ = list(attrs.keys())
    for k, v in attrs.items():
        setattr(m, k, v)
    return m


class MockAddon:
    def __init__(self, id=None):
        self.id = id or 'script.module.resolveurl'

    def getAddonInfo(self, attr):
        if attr == 'version':
            return '21.0.0'
        return '/tmp'

    def getSetting(self, key):
        return ''

    def setSetting(self, key, value):
        pass

    def getLocalizedString(self, id):
        return ''

    def openSettings(self):
        pass


class MockDialog:
    def __init__(self, *a, **k):
        pass

    def notification(self, *a, **k):
        pass

    def select(self, *a, **k):
        return 0


class MockListItem:
    def __init__(self, *a, **k):
        self.label = k.get('label', '')
        self.art = {}

    def setArt(self, art):
        self.art.update(art)


# Set up mock Kodi native C/Python modules
xbmc = make_mod(
    'xbmc',
    LOGINFO=1,
    LOGERROR=2,
    LOGWARNING=3,
    LOGNOTICE=4,
    LOGDEBUG=5,
    log=lambda *a, **k: None,
    translatePath=lambda p: p,
    getInfoLabel=lambda l: '',
    sleep=lambda ms: None,
    getSupportedMedia=lambda m: '.mp4|.mkv|.avi|.m3u8',
    executeJSONRPC=lambda cmd: '{"result":{"Debug.showloginfo":false}}',
    getCondVisibility=lambda s: True,
    executebuiltin=lambda *a, **k: None,
    getSkinDir=lambda: '',
    getCleanMovieTitle=lambda t, b=True: (t, ''),
    getRegion=lambda x: '',
    VideoStreamDetail=type('VideoStreamDetail', (), {'__init__': lambda self, *a, **k: None}),
    Keyboard=type('Keyboard', (), {'__init__': lambda self, *a, **k: None}),
    Player=type('Player', (), {'__init__': lambda self, *a, **k: None}),
    Monitor=type('Monitor', (), {'__init__': lambda self, *a, **k: None, 'waitForAbort': lambda self, *a, **k: False, 'abortRequested': lambda self: False}),
)

xbmcgui = make_mod(
    'xbmcgui',
    Dialog=MockDialog,
    ListItem=MockListItem,
    WindowXMLDialog=MockWindowXMLDialog,
    WindowDialog=MockWindowDialog,
    Window=type('Window', (), {'__init__': lambda self, *a, **k: None}),
    DialogProgress=type('DialogProgress', (), {'__init__': lambda self, *a, **k: None}),
    DialogProgressBG=type('DialogProgressBG', (), {'__init__': lambda self, *a, **k: None}),
    ControlButton=type('ControlButton', (), {'__init__': lambda self, *a, **k: None}),
    ControlImage=type('ControlImage', (), {'__init__': lambda self, *a, **k: None}),
    INPUT_ALPHANUM=0,
    INPUT_DATE=2,
    INPUT_TIME=3,
    INPUT_PASSWORD=1,
    PASSWORD_VERIFY=1,
    ALPHANUM_HIDE_INPUT=1,
)

xbmcplugin = make_mod(
    'xbmcplugin',
    setResolvedUrl=lambda *a, **k: None,
    addDirectoryItem=lambda *a, **k: True,
    addDirectoryItems=lambda *a, **k: True,
    endOfDirectory=lambda *a, **k: None,
    setContent=lambda *a, **k: None,
    addSortMethod=lambda *a, **k: None,
    setPluginCategory=lambda *a, **k: None,
    setPluginFanart=lambda *a, **k: None,
    setProperty=lambda *a, **k: None,
    SORT_METHOD_NONE=0,
    SORT_METHOD_LABEL=1,
    SORT_METHOD_TITLE=10,
    SORT_METHOD_LABEL_IGNORE_THE=100,
    SORT_METHOD_LABEL_IGNORE_FOLDERS=101,
    SORT_METHOD_TITLE_IGNORE_THE=102,
    SORT_METHOD_DATE=103,
    SORT_METHOD_SIZE=104,
    SORT_METHOD_FILE=105,
    SORT_METHOD_DRIVE_TYPE=106,
    SORT_METHOD_TRACKNUM=107,
    SORT_METHOD_DURATION=108,
    SORT_METHOD_EPISODE=109,
    SORT_METHOD_VIDEO_RATING=110,
    SORT_METHOD_PROGRAM_COUNT=111,
    SORT_METHOD_PLAYLIST_ORDER=112,
    SORT_METHOD_VIDEO_TITLE=113,
    SORT_METHOD_VIDEO_SORT_TITLE=114,
    SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE=115,
    SORT_METHOD_PRODUCTIONCODE=116,
    SORT_METHOD_SONG_RATING=117,
    SORT_METHOD_SONG_USER_RATING=118,
    SORT_METHOD_MPAA_RATING=119,
    SORT_METHOD_VIDEO_RUNTIME=120,
    SORT_METHOD_STUDIO=121,
    SORT_METHOD_STUDIO_IGNORE_THE=122,
    SORT_METHOD_UNSORTED=123,
    SORT_METHOD_BITRATE=124,
    SORT_METHOD_LISTENERS=125,
    SORT_METHOD_COUNTRY=126,
    SORT_METHOD_DATEADDED=127,
    SORT_METHOD_FULLPATH=128,
    SORT_METHOD_LASTPLAYED=129,
    SORT_METHOD_PLAYCOUNT=130,
    SORT_METHOD_CHANNEL=131,
    SORT_METHOD_ARTIST=132,
    SORT_METHOD_ARTIST_IGNORE_THE=133,
    SORT_METHOD_ALBUM=134,
    SORT_METHOD_ALBUM_IGNORE_THE=135,
    SORT_METHOD_GENRE=136,
    SORT_METHOD_VIDEO_USER_RATING=137,
    SORT_METHOD_VIDEO_YEAR=138,
    SORT_METHOD_YEAR=139,
    SORT_METHOD_DATE_TAKEN=140,
)

xbmcvfs = make_mod(
    'xbmcvfs',
    exists=lambda p: True,
    mkdir=lambda p: None,
    mkdirs=lambda p: None,
    File=lambda *a, **k: None,
    translatePath=lambda p: p,
    delete=lambda p: None,
    copy=lambda a, b: True,
    makeLegalFilename=lambda s, *a: s,
    rmdir=lambda p, *a: None,
    rename=lambda a, b: None,
    listdir=lambda p: ([], []),
    Stat=type('Stat', (), {'__init__': lambda self, *a, **k: None}),
)

xbmcaddon = make_mod(
    'xbmcaddon',
    Addon=MockAddon,
)

sys.modules['xbmc'] = xbmc
sys.modules['xbmcgui'] = xbmcgui
sys.modules['xbmcplugin'] = xbmcplugin
sys.modules['xbmcvfs'] = xbmcvfs
sys.modules['xbmcaddon'] = xbmcaddon

# Configure sys.path for local Kodi libraries and plugins
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_DIR = os.path.join(REPO_ROOT, 'resources', 'plugins')
LIB_DIR = os.path.join(REPO_ROOT, 'resources', 'lib')

resolveurl_search_paths = [
    '/home/twilight/Development/Kodi_libs/script.module.kodi-six/libs',
    '/home/twilight/Development/Kodi_libs/ResolveURL/script.module.resolveurl/lib',
    PLUGINS_DIR,
    LIB_DIR,
]

for p in resolveurl_search_paths:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

# kodi_six.xbmcvfs is what the vendored ytresolver engine actually uses
# (kodion.compatibility imports kodi_six directly, bypassing the sys.modules
# mock above). Give it a temp-backed filesystem so engine file writes
# (generated MPD manifests) really land somewhere in tests.
try:
    import tempfile as _tempfile

    _YT_VFS_TMP = os.path.join(_tempfile.gettempdir(), 'pluginsgr_ytvfs')
    os.makedirs(_YT_VFS_TMP, exist_ok=True)

    def _yt_translate(path):
        if isinstance(path, str):
            if path.startswith('special://temp'):
                return path.replace('special://temp', _YT_VFS_TMP, 1)
            if path.startswith('special://profile'):
                return path.replace('special://profile', _YT_VFS_TMP, 1)
        return path

    class _YT_VFS_File:
        def __init__(self, path, mode='r'):
            real = _yt_translate(path)
            if 'w' in mode:
                parent = os.path.dirname(real)
                if parent:
                    os.makedirs(parent, exist_ok=True)
            self._fh = open(real, mode.replace('b', '') if isinstance(mode, str) else mode)

        def write(self, data):
            if isinstance(data, (bytes, bytearray)):
                data = bytes(data).decode('utf-8', errors='ignore')
            result = self._fh.write(data)
            return True if isinstance(result, int) else bool(result)

        def read(self, *args):
            return self._fh.read(*args)

        def close(self):
            try:
                self._fh.close()
            except Exception:
                pass

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            self.close()
            return False

    import kodi_six.xbmcvfs as _kodi_vfs

    _kodi_vfs.translatePath = _yt_translate
    _kodi_vfs.File = _YT_VFS_File
    _kodi_vfs.exists = lambda p: os.path.exists(_yt_translate(p))
    _kodi_vfs.mkdirs = lambda p: (os.makedirs(_yt_translate(p), exist_ok=True), True)[1]
    _kodi_vfs.listdir = lambda p: ([], os.listdir(_yt_translate(p)) if os.path.isdir(_yt_translate(p)) else [])
except Exception:
    pass
