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
    executeJSONRPC=lambda cmd: '{"result":{"Debug.showloginfo":false}}',
    getInfoLabel=lambda l: '',
    sleep=lambda ms: None,
    getSupportedMedia=lambda m: '.mp4|.mkv|.avi|.m3u8',
    getCondVisibility=lambda s: True,
)

xbmcgui = make_mod(
    'xbmcgui',
    Dialog=MockDialog,
    ListItem=lambda *a, **k: None,
    WindowXMLDialog=MockWindowXMLDialog,
    WindowDialog=MockWindowDialog,
)

xbmcplugin = make_mod(
    'xbmcplugin',
    setResolvedUrl=lambda *a, **k: None,
)

xbmcvfs = make_mod(
    'xbmcvfs',
    exists=lambda p: True,
    mkdir=lambda p: None,
    mkdirs=lambda p: None,
    File=lambda *a, **k: None,
    translatePath=lambda p: p,
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
except Exception:
    pass
