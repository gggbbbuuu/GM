"""Cross-platform ctypes wrapper for Go shared libraries built by script.module.go.

One Python API for Android ARMv7/ARM64, Linux, Windows and macOS. The
native .so/.dll/.dylib MUST match the Kodi Python process architecture.
Each native platform downloads just its own pinned, verified Go library.
An existing legacy solid-XZ archive is also supported. No changes needed in any Python extractor.
"""
import base64
import ctypes
import json
import os
import platform
import sys
import sysconfig
import threading
from urllib.parse import urlsplit

_LOCK = threading.RLock()
_LIB = None
_FD = None
_GENERIC = None
_PY_SESSIONS = {}


def _log(message):
    try:
        import xbmc
        xbmc.log('[script.module.go] ' + message, xbmc.LOGINFO)
    except (ImportError, AttributeError):
        pass


def _is_ios(system=None, machine=None):
    if system is None: system = platform.system()
    if machine is None: machine = platform.machine()
    system=str(system).lower()
    machine=str(machine).lower()
    if system=='ios' or (system=='darwin' and machine.startswith(('iphone','ipad','ipod'))):
        return True
    if system=='darwin':
        try:
            import xbmc
            return bool(xbmc.getCondVisibility('System.Platform.IOS'))
        except (ImportError, AttributeError):
            return False
    return False


def _is_android():
    # Kodi Python on Android generally reports sys.platform == 'linux'.
    try:
        import xbmc
        if xbmc.getCondVisibility('System.Platform.Android'):
            return True
    except (ImportError, AttributeError):
        pass
    return (hasattr(sys, 'getandroidapilevel') or
            bool(os.environ.get('ANDROID_ROOT') and os.environ.get('ANDROID_DATA')))


def target_name(system=None, machine=None, pointer_bits=None, android=None):
    """Return the ABI required by the *running Python process*, not host CPU."""
    if system is None:
        system = platform.system()
    if machine is None:
        machine = platform.machine()
        # On Windows ARM devices x86-64 Kodi may be running under emulation.
        # sysconfig describes the Python ABI rather than the physical CPU.
        if str(system).lower() == 'windows':
            win_platform = sysconfig.get_platform().lower()
            if 'arm64' in win_platform:
                machine = 'arm64'
            elif 'amd64' in win_platform:
                machine = 'amd64'
            elif win_platform == 'win32':
                machine = 'x86'
    if pointer_bits is None:
        pointer_bits = 8 * ctypes.sizeof(ctypes.c_void_p)
    if android is None:
        android = _is_android()
    system = str(system).lower()
    machine = str(machine).lower().replace('-', '_')
    if _is_ios(system, machine):
        return 'ios-arm64' if pointer_bits == 64 else 'ios-armv7'
    if android:
        if machine in ('aarch64', 'arm64', 'armv8l', 'armv7l', 'armv7', 'arm'):
            return 'android-arm64' if pointer_bits == 64 else 'android-armv7'
        if machine in ('x86_64', 'amd64', 'i686', 'i386'):
            return 'android-x86_64' if pointer_bits == 64 else 'android-x86'
    if system == 'linux':
        if machine in ('aarch64', 'arm64', 'armv8l', 'armv7l', 'armv7', 'arm'):
            return 'linux-arm64' if pointer_bits == 64 else 'linux-armv7'
        if machine in ('x86_64', 'amd64', 'x64', 'i686', 'i386'):
            return 'linux-x86_64' if pointer_bits == 64 else 'linux-x86'
    if system == 'darwin':
        if machine in ('arm64', 'aarch64'):
            return 'macos-arm64'
        if machine in ('x86_64', 'amd64'):
            return 'macos-x86_64'
    if system == 'windows':
        if machine in ('arm64', 'aarch64'):
            return 'windows-arm64'
        if machine in ('amd64', 'x86_64', 'x64', 'i386', 'i686', 'x86'):
            return 'windows-x86_64' if pointer_bits == 64 else 'windows-x86'
    raise RuntimeError('Unsupported Go native platform: {} / {} / {}-bit'.format(
        system, machine, pointer_bits))


_DIRECTORY = {
    'android-armv7': ('armeabi-v7a', 'libgotls.so'),
    'android-arm64': ('arm64-v8a', 'libgotls.so'),
    'android-x86_64': ('android-x86_64', 'libgotls.so'),
    'android-x86': ('android-x86', 'libgotls.so'),
    'linux-x86_64': ('linux-x86_64', 'libgotls.so'),
    'linux-arm64': ('linux-arm64', 'libgotls.so'),
    'linux-armv7': ('linux-armv7', 'libgotls.so'),
    'linux-x86': ('linux-x86', 'libgotls.so'),
    'macos-x86_64': ('macos-x86_64', 'libgotls.dylib'),
    'macos-arm64': ('macos-arm64', 'libgotls.dylib'),
    'windows-x86_64': ('windows-x86_64', 'gotls.dll'),
    'windows-arm64': ('windows-arm64', 'gotls.dll'),
    'windows-x86': ('windows-x86', 'gotls.dll'),
}


def _native_root():
    return os.path.join(os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')),
                        'resources', 'native')



# Storage: a universal ZIP retains every platform's Go library in XZ form.
# The library matching Kodi Python's architecture is decompressed ONLY when
# first needed. This keeps a SINGLE Kodi module installable on all platforms.
_TEMP_HANDLE = None



# Universal solid-XZ archive with member index.  No other Kodi add-on required.
# A 64 MiB XZ dictionary enables cross-OS compression of matching Go code.
_PACKED_META = None

def _solid_archive():
    return os.path.join(_native_root(), 'libraries.tar.xz')


def _packed_index():
    global _PACKED_META
    if _PACKED_META is None:
        index_path = os.path.join(_native_root(), 'libraries.json')
        if os.path.isfile(index_path) and os.path.isfile(_solid_archive()):
            with open(index_path, 'r', encoding='utf-8') as file:
                _PACKED_META = json.load(file)
        else:
            _PACKED_META = {}
    return _PACKED_META


def _packed_relative(location):
    return os.path.relpath(location, _native_root()).replace(os.sep, '/')


def _packed_library_available(location):
    return _packed_relative(location) in _packed_index()


def _read_solid_library(reference):
    # Each member is checked against the package manifest before being loaded.
    import hashlib
    import tarfile
    member = reference[len('solid://'):]
    expected = _packed_index().get(member)
    if not expected:
        raise RuntimeError('Missing native library in universal module: ' + member)
    try:
        # Streaming tar is essential: do not extract all platforms into RAM.
        with tarfile.open(_solid_archive(), mode='r|xz') as archive:
            for info in archive:
                if info.name != member:
                    continue
                if not info.isfile() or info.size != expected['size']:
                    raise RuntimeError('Invalid native library archive entry: ' + member)
                entry = archive.extractfile(info)
                if entry is None:
                    raise RuntimeError('Could not read native library: ' + member)
                data = entry.read()
                if hashlib.sha256(data).hexdigest() != expected['sha256']:
                    raise RuntimeError('Native library failed SHA256 check: ' + member)
                return data
    except (OSError, tarfile.TarError) as exc:
        raise RuntimeError('Could not unpack universal Go module: ' + str(exc)) from exc
    raise RuntimeError('Native library not present in archive: ' + member)



# On Android the bundled library lives inside a solid XZ archive using a
# 64 MiB dictionary. Kodi launches separate Python interpreters for plug-in
# requests, so repeating that decompression can exhaust 32-bit address space.
# Extract exactly the selected member once, verify it against libraries.json,
# then reuse a verified persistent cache without touching the XZ decoder.
_ANDROID_IO_CHUNK = 256 * 1024


def _android_cache_directory():
    # Kodi's master profile is writable on Android, unlike the APK resources.
    try:
        import xbmcvfs
        root = xbmcvfs.translatePath('special://masterprofile/')
    except (ImportError, AttributeError):
        root = os.path.join(os.path.expanduser('~'), '.kodi', 'userdata')
    return os.path.join(root, 'addon_data', 'script.module.go', 'native-cache')


def _verified_cached_file(location, expected):
    """Check the file's content, not just its name or length (user-writable)."""
    import hashlib
    try:
        if os.stat(location).st_size != int(expected['size']):
            return False
        digest = hashlib.sha256()
        with open(location, 'rb') as source:
            for chunk in iter(lambda: source.read(_ANDROID_IO_CHUNK), b''):
                digest.update(chunk)
        return digest.hexdigest() == expected['sha256'].lower()
    except (OSError, ValueError, TypeError, KeyError):
        return False


def _android_cached_solid_library(reference, target):
    """One-time streaming extraction, integrity-checked and atomically cached.

    The large XZ dictionary is released BEFORE the native loader starts.
    Subsequent Kodi Python invocations read the verified raw ELF instead.
    """
    import hashlib
    import tarfile
    import tempfile

    member = reference[len('solid://'):]
    expected = _packed_index().get(member)
    if not expected:
        raise RuntimeError('Missing native library in universal module: ' + member)
    expected_size = int(expected['size'])
    expected_hash = expected['sha256'].lower()
    if expected_size <= 0 or expected_size > 256 * 1024 * 1024 or len(expected_hash) != 64:
        raise RuntimeError('Invalid library size/hash in universal module index')
    cache_dir = _android_cache_directory()
    cache_name = '{}-{}.so'.format(target, expected_hash)
    cached = os.path.join(cache_dir, cache_name)
    if _verified_cached_file(cached, expected):
        return cached

    os.makedirs(cache_dir, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', prefix=target + '-', suffix='.tmp',
                                         dir=cache_dir, delete=False) as dst:
            temporary = dst.name
            found = False
            # Stream the universal archive; never allocate the whole ELF in Python.
            with tarfile.open(_solid_archive(), mode='r|xz') as archive:
                for info in archive:
                    if info.name != member:
                        continue
                    if not info.isfile() or info.size != expected_size:
                        raise RuntimeError('Invalid native library archive entry: ' + member)
                    source = archive.extractfile(info)
                    if source is None:
                        raise RuntimeError('Could not read native library: ' + member)
                    digest = hashlib.sha256()
                    remaining = expected_size
                    while remaining:
                        chunk = source.read(min(_ANDROID_IO_CHUNK, remaining))
                        if not chunk:
                            raise RuntimeError('Truncated native library: ' + member)
                        dst.write(chunk)
                        digest.update(chunk)
                        remaining -= len(chunk)
                    if digest.hexdigest() != expected_hash:
                        raise RuntimeError('Native library failed SHA256 check: ' + member)
                    found = True
                    break
            if not found:
                raise RuntimeError('Native library not present in archive: ' + member)
        os.replace(temporary, cached)
        temporary = None
        _log('Cached {} Go native library for later low-memory loads'.format(target))
        return cached
    except MemoryError as exc:
        raise MemoryError(
            'Not enough Android memory for first-time 64 MiB solid-XZ extraction. '
            'Install the verified uncompressed {} library in resources/native/{} '
            'or populate the native-cache on a device with more free memory.'.format(
                target, _DIRECTORY[target][0])) from exc
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def _android_unpacked_stream(reference, target):
    """Return a readable ELF stream without retaining the native file in RAM."""
    if reference.startswith('solid://'):
        return open(_android_cached_solid_library(reference, target), 'rb')
    if reference.endswith('.xz'):
        import lzma
        return lzma.open(reference, 'rb')
    return open(reference, 'rb')


def _native_basename(reference):
    if reference.startswith('solid://'):
        return os.path.basename(reference[len('solid://'):])
    if reference.endswith('.xz'):
        return os.path.basename(reference[:-3])
    return os.path.basename(reference)



def _native_present(location):
    return os.path.isfile(location) or os.path.isfile(location + '.xz') or _packed_library_available(location)


def _read_native(path):
    if path.startswith('solid://'):
        return _read_solid_library(path)
    with open(path, 'rb') as file:
        data = file.read()
    if path.endswith('.xz'):
        try:
            import lzma
        except ImportError as exc:
            raise RuntimeError('script.module.go: This Kodi Python build lacks the '
                               'standard _lzma module required for the compact '
                               'universal package') from exc
        try:
            data = lzma.decompress(data, format=lzma.FORMAT_XZ)
        except lzma.LZMAError as exc:
            raise RuntimeError('script.module.go: Compressed native library is corrupt: '
                               + path) from exc
    return data


def _desktop_load_compressed(path, target):
    global _TEMP_HANDLE
    data = _read_native(path)
    # Linux can run directly from memory without writing any native binary
    # into addon files or userdata. The same memfd remains live with _LIB.
    if target.startswith('linux-') and hasattr(os, 'memfd_create'):
        fd = os.memfd_create('kodi_go_tls', 0)
        try:
            with os.fdopen(os.dup(fd), 'wb') as out:
                out.write(data)
            lib = ctypes.CDLL('/proc/self/fd/{}'.format(fd))
            return lib, fd
        except (OSError, RuntimeError):
            os.close(fd)
            # Fall through for Linux without a suitable /proc filesystem.
    import tempfile
    # Windows requires a real pathname for LoadLibrary; macOS also loads from
    # a temporary file. The temp directory is held for the module's lifetime.
    # No persistent files are written in Kodi userdata.
    temp = tempfile.TemporaryDirectory(prefix='kodi_go_')
    basename = _native_basename(path)
    path_to_load = os.path.join(temp.name, basename)
    try:
        with open(path_to_load, 'wb') as out:
            out.write(data)
        lib = ctypes.CDLL(path_to_load)
    except Exception:
        temp.cleanup()
        raise
    _TEMP_HANDLE = temp
    return lib, None


_REMOTE_INDEX = None
_REMOTE_CHUNK = 256 * 1024
_REMOTE_MAX_COMPRESSED = 16 * 1024 * 1024
_REMOTE_MAX_RAW = 32 * 1024 * 1024


def _remote_index():
    global _REMOTE_INDEX
    if _REMOTE_INDEX is None:
        index_file = os.path.join(_native_root(), 'remote.json')
        if os.path.isfile(index_file):
            with open(index_file, 'r', encoding='utf-8') as file:
                _REMOTE_INDEX = json.load(file).get('files', {})
        else:
            _REMOTE_INDEX = {}
    return _REMOTE_INDEX


def _remote_base_url():
    base = ''
    try:
        import xbmcaddon
        base = xbmcaddon.Addon('script.module.go').getSetting('server_base_url').strip()
    except (ImportError, AttributeError, RuntimeError):
        pass
    # Existing installations may have saved an older default in addon_data.
    # Migrate only the two known outdated 1.0.5 URLs; preserve custom URLs.
    if base.rstrip('/') in (
            'https://loopaddon.uk/golib/1.0.5',
            'https://www.jetxtractors.com/Go/1.0.5'):
        base = ''
    if not base:
        setting_file = os.path.join(_native_root(), 'server.json')
        try:
            with open(setting_file, 'r', encoding='utf-8') as config:
                base = str(json.load(config).get('base_url', '')).strip()
        except (OSError, ValueError, TypeError):
            pass
    base = base.rstrip('/')
    info = urlsplit(base)
    if (info.scheme.lower() != 'https' or not info.hostname or
            info.username is not None or info.password is not None or
            info.query or info.fragment or '\\' in base):
        raise RuntimeError('Go library server URL is not configured. Set a valid '
                           'HTTPS base URL in script.module.go addon settings, '
                           'e.g. https://cdn.example.com/go/1.0.5')
    return base


def _remote_expected(target):
    entry = _remote_index().get(target)
    if entry is None:
        raise RuntimeError('No remote Go library configured for ' + target)
    directory, name = _DIRECTORY[target]
    if entry.get('path') != directory + '/' + name + '.xz':
        raise RuntimeError('Invalid server index path for ' + target)
    expected = dict(sha256=entry.get('sha256', ''), size=entry.get('size', 0))
    xz_sha = str(entry.get('xz_sha256', '')).lower()
    raw_sha = str(expected['sha256']).lower()
    raw_size, xz_size = int(expected['size']), int(entry.get('xz_size', 0))
    import re
    if (not re.fullmatch('[a-f0-9]{64}', raw_sha) or
            not re.fullmatch('[a-f0-9]{64}', xz_sha) or
            not 0 < raw_size <= _REMOTE_MAX_RAW or
            not 0 < xz_size <= _REMOTE_MAX_COMPRESSED):
        raise RuntimeError('Invalid pinned Go library metadata for ' + target)
    return entry, dict(sha256=raw_sha, size=raw_size), xz_sha, xz_size


def _remote_cache_root():
    return _android_cache_directory()  # Same userdata location on every Kodi OS.


def _remote_cached_native(target):
    """Return verified cached native library, downloading only when missing.

    Two independent SHA-256 checks: compressed response and resulting library.
    A failed/interrupted download cannot replace an earlier valid cache file.
    """
    import hashlib
    import lzma
    import tempfile
    from urllib.request import Request, urlopen

    entry, expected, xz_hash, xz_size = _remote_expected(target)
    directory, name = _DIRECTORY[target]
    ext = os.path.splitext(name)[1]
    cache_dir = _remote_cache_root()
    cached = os.path.join(cache_dir, target + '-' + expected['sha256'] + ext)
    if _verified_cached_file(cached, expected):
        return cached

    base = _remote_base_url()
    from urllib.parse import urlsplit as _split
    url = base + '/' + entry['path']
    cache_zip = None
    cache_raw = None
    os.makedirs(cache_dir, exist_ok=True)
    try:
        # Do not keep the downloaded compressed payload in Python heap memory.
        with tempfile.NamedTemporaryFile('wb', dir=cache_dir, prefix='.go-download-',
                                         suffix='.xz', delete=False) as compressed:
            cache_zip = compressed.name
            request = Request(url, headers={'User-Agent': 'Kodi-script.module.go/1.0.5'})
            with urlopen(request, timeout=35) as response:
                if response.getcode() != 200:
                    raise RuntimeError('Go native download returned HTTP {}'.format(response.getcode()))
                if (response.headers.get('Content-Encoding') or 'identity').lower() != 'identity':
                    raise RuntimeError('Go library server must not apply HTTP content encoding')
                final = _split(response.geturl())
                start = _split(base)
                if (final.scheme.lower() != 'https' or
                        (final.hostname, final.port) != (start.hostname, start.port)):
                    raise RuntimeError('Go library download redirected outside trusted HTTPS host')
                size_header = response.headers.get('Content-Length')
                if size_header is not None and int(size_header) != xz_size:
                    raise RuntimeError('Go download has unexpected Content-Length')
                downloaded = 0
                digest = hashlib.sha256()
                for chunk in iter(lambda: response.read(_REMOTE_CHUNK), b''):
                    downloaded += len(chunk)
                    if downloaded > xz_size:
                        raise RuntimeError('Go download exceeds pinned length')
                    compressed.write(chunk)
                    digest.update(chunk)
                if downloaded != xz_size or digest.hexdigest() != xz_hash:
                    raise RuntimeError('Go library compressed download failed SHA256/size check')
        with tempfile.NamedTemporaryFile('wb', dir=cache_dir, prefix='.go-extract-',
                                         suffix=ext, delete=False) as output:
            cache_raw = output.name
            total = 0
            digest = hashlib.sha256()
            with lzma.open(cache_zip, 'rb') as source:
                for chunk in iter(lambda: source.read(_REMOTE_CHUNK), b''):
                    total += len(chunk)
                    if total > expected['size']:
                        raise RuntimeError('Go native library exceeds pinned size')
                    output.write(chunk)
                    digest.update(chunk)
            if total != expected['size'] or digest.hexdigest() != expected['sha256']:
                raise RuntimeError('Go native library failed SHA256/size check')
        # The original Android loader also checks ELF class/machine before dlopen.
        os.replace(cache_raw, cached)
        cache_raw = None
        _log('Downloaded and verified Go native: {} ({} compressed bytes)'.format(
            target, xz_size))
        return cached
    except (OSError, EOFError, lzma.LZMAError, ValueError) as exc:
        raise RuntimeError('Go native download/cache failed for {}: {}'.format(target, exc)) from exc
    finally:
        for temporary in (cache_zip, cache_raw):
            if temporary:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass


def prepare_native():
    """Pre-fetch only the matching library, without loading the Go runtime."""
    target = target_name()
    if _remote_index():
        return _remote_cached_native(target)
    return _select_library()[0]


def _select_library():
    target = target_name()
    # Prefer the signed-in-addon remote index, even if a previous installation
    # left a legacy universal XZ archive in the addon directory.
    if _remote_index():
        return _remote_cached_native(target), target, False
    directory, name = _DIRECTORY[target]
    location = os.path.join(_native_root(), directory, name)
    if os.path.isfile(location):
        return location, target, False
    if os.path.isfile(location + '.xz'):
        return location + '.xz', target, False
    if _packed_library_available(location):
        return 'solid://' + _packed_relative(location), target, False
    if target == 'android-armv7':
        legacy = os.path.join(_native_root(), 'armeabi-v7a', 'librugby24tls.so')
        if os.path.isfile(legacy):
            return legacy, target, True
    raise RuntimeError('script.module.go: No native Go library for {}. '
                       'Build it using source/build_target.sh {} and reinstall the ZIP '
                       '(looked in {}).'.format(target, target, location))


def installed_targets():
    """List ABIs bundled in the installed module (not necessarily runnable here)."""
    if _remote_index():
        return sorted(_remote_index())  # Available for remote download; not all cached.
    root = _native_root()
    installed = []
    for name, (subdir, filename) in sorted(_DIRECTORY.items()):
        if _native_present(os.path.join(root, subdir, filename)):
            installed.append(name)
    if os.path.isfile(os.path.join(root, 'armeabi-v7a', 'librugby24tls.so')):
        if 'android-armv7' not in installed:
            installed.append('android-armv7 [Rugby24-only compatibility]')
    return installed


def _select_library():
    target = target_name()
    if _remote_index():
        return _remote_cached_native(target), target, False
    directory, name = _DIRECTORY[target]
    location = os.path.join(_native_root(), directory, name)
    if os.path.isfile(location):
        return location, target, False
    if os.path.isfile(location + '.xz'):
        return location + '.xz', target, False
    if _packed_library_available(location):
        return 'solid://' + _packed_relative(location), target, False
    if target == 'android-armv7':
        legacy = os.path.join(_native_root(), 'armeabi-v7a', 'librugby24tls.so')
        if os.path.isfile(legacy):
            return legacy, target, True
    raise RuntimeError('script.module.go: No native Go library for {}. '
                       'Build it using source/build_target.sh {} and reinstall the ZIP '
                       '(looked in {}).'.format(target, target, location))


def installed_targets():
    """List ABIs bundled in the installed module (not necessarily runnable here)."""
    if _remote_index():
        return sorted(_remote_index())  # Available remotely, not all downloaded.
    root = _native_root()
    installed = []
    for name, (subdir, filename) in sorted(_DIRECTORY.items()):
        if _native_present(os.path.join(root, subdir, filename)):
            installed.append(name)
    if os.path.isfile(os.path.join(root, 'armeabi-v7a', 'librugby24tls.so')):
        if 'android-armv7' not in installed:
            installed.append('android-armv7 [Rugby24-only compatibility]')
    return installed


def _android_create_memfd(target):
    """Create an anonymous in-memory ELF file on Android API 28 and newer.

    Android's libc wrapper for memfd_create only appeared in API 30. Older
    devices with a supporting Linux kernel can use the same system call via
    libc.syscall. Limit syscall numbers to known Android ABIs; never guess.
    """
    if hasattr(os, 'memfd_create'):
        return os.memfd_create('kodi_go_tls', 1)  # MFD_CLOEXEC

    libc = ctypes.CDLL(None, use_errno=True)
    try:
        creator = libc.memfd_create
    except AttributeError:
        syscall_numbers = {
            'android-armv7': 385,    # ARM EABI __NR_memfd_create
            'android-arm64': 279,    # AArch64
            'android-x86': 356,     # i386
            'android-x86_64': 319,  # x86_64
        }
        number = syscall_numbers.get(target)
        if number is None:
            raise RuntimeError('No known memfd_create syscall for {}'.format(target))
        try:
            syscall = libc.syscall
        except AttributeError as exc:
            raise RuntimeError('Android libc does not provide syscall()') from exc
        syscall.restype = ctypes.c_long
        fd = syscall(ctypes.c_long(number), ctypes.c_char_p(b'kodi_go_tls'),
                     ctypes.c_uint(1))
        _log('Android legacy memfd_create syscall used: {}'.format(target))
    else:
        creator.argtypes = (ctypes.c_char_p, ctypes.c_uint)
        creator.restype = ctypes.c_int
        fd = creator(b'kodi_go_tls', 1)

    if fd < 0:
        err = ctypes.get_errno() or 1
        raise OSError(err, os.strerror(err))
    return fd


def _android_load_bytes(path, target):
    """Android: copy the selected ABI into memfd in bounded chunks.

    Do not hold a full decompressed Go library in Python memory. The XZ
    decompressor (if needed) exits before dlopen starts the Go runtime.
    """
    expected_class, expected_machine = {
        'android-armv7': (1, 40),
        'android-arm64': (2, 183),
        'android-x86': (1, 3),
        'android-x86_64': (2, 62),
    }[target]
    if expected_class * 32 != 8 * ctypes.sizeof(ctypes.c_void_p):
        raise RuntimeError('Android native library ABI mismatch: ' + target)
    fd = _android_create_memfd(target)
    try:
        # Opening and closing the stream here ensures any decompressor memory
        # has been freed before the Android dynamic loader maps the Go runtime.
        with _android_unpacked_stream(path, target) as source:
            header = source.read(20)
            if (len(header) < 20 or header[:4] != b'\x7fELF'
                    or header[4] != expected_class or header[5] != 1
                    or int.from_bytes(header[18:20], 'little') != expected_machine):
                raise RuntimeError('Android native library ABI mismatch: {} (expected {})'.format(path, target))
            with os.fdopen(os.dup(fd), 'wb') as dst:
                dst.write(header)
                for chunk in iter(lambda: source.read(_ANDROID_IO_CHUNK), b''):
                    dst.write(chunk)
        class AndroidDlExtInfo(ctypes.Structure):
            _fields_ = [('flags', ctypes.c_uint64), ('reserved_addr', ctypes.c_void_p),
                        ('reserved_size', ctypes.c_size_t), ('relro_fd', ctypes.c_int),
                        ('library_fd', ctypes.c_int), ('library_fd_offset', ctypes.c_int64),
                        ('library_namespace', ctypes.c_void_p)]
        lib = None
        errors = []
        try:
            dl = ctypes.CDLL('libdl.so')
            ext = dl.android_dlopen_ext
            ext.argtypes = (ctypes.c_char_p, ctypes.c_int,
                            ctypes.POINTER(AndroidDlExtInfo))
            ext.restype = ctypes.c_void_p
            info = AndroidDlExtInfo()
            info.flags = 0x10  # ANDROID_DLEXT_USE_LIBRARY_FD
            info.library_fd = fd
            handle = ext(os.path.basename(path).encode('utf-8'),
                         getattr(os, 'RTLD_NOW', 2), ctypes.byref(info))
            if not handle:
                dl.dlerror.restype = ctypes.c_char_p
                raise OSError((dl.dlerror() or b'android_dlopen_ext failed').decode('utf-8', 'replace'))
            lib = ctypes.CDLL(None, handle=handle)
        except (OSError, AttributeError, ValueError) as exc:
            errors.append(str(exc))
        if lib is None:
            try:
                lib = ctypes.CDLL('/proc/self/fd/{}'.format(fd))
            except (OSError, AttributeError, ValueError) as exc:
                errors.append(str(exc))
                raise RuntimeError('Android Go library could not load: ' + '; '.join(errors))
    except Exception:
        os.close(fd)
        raise
    return lib, fd


def _load():
    global _LIB, _FD, _GENERIC
    with _LOCK:
        if _LIB is not None:
            return _LIB
        path, target, legacy = _select_library()
        if target.startswith('android-'):
            lib, fd = _android_load_bytes(path, target)
        else:
            # Decompress into a memory FD on Linux; temporary path on Windows
            # or macOS. Original uncompressed .dll/.dylib/.so still supported.
            try:
                if path.endswith('.xz') or path.startswith('solid://'):
                    lib, fd = _desktop_load_compressed(path, target)
                else:
                    lib, fd = ctypes.CDLL(path), None
            except OSError as exc:
                raise RuntimeError('Unable to load {}: {}'.format(path, exc)) from exc
        try:
            generic = hasattr(lib, 'GoRequest') and hasattr(lib, 'GoFree')
            if generic:
                lib.GoRequest.argtypes = (ctypes.c_char_p,)
                lib.GoRequest.restype = ctypes.c_void_p
                lib.GoFree.argtypes = (ctypes.c_void_p,)
                lib.GoFree.restype = None
            elif legacy:
                lib.Rugby24Fetch.argtypes = (ctypes.c_char_p, ctypes.c_char_p)
                lib.Rugby24Fetch.restype = ctypes.c_void_p
                lib.Rugby24Free.argtypes = (ctypes.c_void_p,)
                lib.Rugby24Free.restype = None
            else:
                raise RuntimeError('GoRequest and GoFree missing from ' + path)
        except Exception:
            if fd is not None:
                os.close(fd)
            raise
        _FD, _LIB, _GENERIC = fd, lib, generic
        _log('Native Go loaded: {} {}'.format(target, 'generic' if generic else 'Rugby24-only'))
        return lib




# Built-in Android-only persistent Go service inside script.module.go.
# Kodi plug-in invocations have separate Python interpreters, so a native Go
# dlopen on each one maps a fresh 44 MiB Go runtime into the same 32-bit Kodi
# address space. The xbmc.service extension in *this* addon owns one library.
# Other interpreters call it over authenticated localhost without dlopen.
_BRIDGE_SERVER = False  # This flag is set only inside script.module.go/service.py.
_BRIDGE_ADDON_ID = 'script.module.go'
_BRIDGE_EXTENSION_READY = None
_BRIDGE_MAX_REPLY = 20 * 1024 * 1024
_BRIDGE_MAX_REQUEST = 4 * 1024 * 1024


def _go_bridge_installed():
    """Use bridge only when script.module.go declares its service extension.

    script.module.go always exists, so merely checking the addon ID would
    incorrectly enable the bridge before the service is registered.
    """
    global _BRIDGE_EXTENSION_READY
    # Use the persistent bridge ONLY in 32-bit Android Kodi.  A 64-bit
    # Android process uses the existing direct Go path, just like desktop.
    # Check process pointer size, not hardware or Android OS bitness.
    if (_BRIDGE_SERVER or not _is_android() or
            ctypes.sizeof(ctypes.c_void_p) != 4):
        return False
    if _BRIDGE_EXTENSION_READY is not None:
        return _BRIDGE_EXTENSION_READY
    try:
        import xbmcaddon
        import xml.etree.ElementTree as ET
        root = xbmcaddon.Addon(_BRIDGE_ADDON_ID).getAddonInfo('path')
        manifest = os.path.join(root, 'addon.xml')
        document = ET.parse(manifest)
        for extension in document.getroot().findall('extension'):
            if (extension.get('point') == 'xbmc.service' and
                    extension.get('library') == 'service.py' and
                    os.path.isfile(os.path.join(root, 'service.py'))):
                _BRIDGE_EXTENSION_READY = True
                return True
    except (OSError, ValueError, ImportError, AttributeError, ET.ParseError):
        pass
    _BRIDGE_EXTENSION_READY = False
    return False


def _go_bridge_info_path():
    import xbmcvfs
    return os.path.join(xbmcvfs.translatePath('special://masterprofile/'),
                        'addon_data', _BRIDGE_ADDON_ID, 'bridge.json')


def _go_bridge_discovery():
    # A just-started Kodi service may need a moment to initialize. Never fall
    # back to a new dlopen while a bridge installation is present.
    import time
    location = _go_bridge_info_path()
    last_exc = None
    for _ in range(120):
        try:
            with open(location, 'r', encoding='utf-8') as discovery:
                detail = json.load(discovery)
            port = int(detail['port'])
            token = detail['token']
            if not 1 <= port <= 65535 or not isinstance(token, str) or len(token) < 32:
                raise ValueError('invalid service address')
            return port, token
        except (OSError, ValueError, TypeError, KeyError) as exc:
            last_exc = exc
            time.sleep(.5)
    raise RuntimeError('Built-in Go bridge not ready (check [GoBridge] in Kodi log)') from last_exc


def _go_bridge_perform(method, url, headers, body, profile, session, timeout):
    import http.client
    if not isinstance(body, bytes):
        body = bytes(body or b'')
    request = {'method': method, 'url': url, 'headers': headers,
               'body_base64': base64.b64encode(body).decode('ascii'),
               'profile': profile, 'session': session,
               'timeout': max(1, min(120, float(timeout)))}
    payload = json.dumps(request, separators=(',', ':')).encode('utf-8')
    if len(payload) > _BRIDGE_MAX_REQUEST:
        raise ValueError('Go bridge request is too large')
    port, token = _go_bridge_discovery()
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=max(5, float(timeout) + 10))
    try:
        conn.request('POST', '/v1/perform', body=payload, headers={
            'Content-Type': 'application/json',
            'X-Go-Bridge-Token': token,
            'Content-Length': str(len(payload)),
            'Connection': 'close',
        })
        response = conn.getresponse()
        reply = response.read(_BRIDGE_MAX_REPLY + 1)
        if len(reply) > _BRIDGE_MAX_REPLY:
            raise RuntimeError('Go bridge response exceeded safety limit')
        result = json.loads(reply.decode('utf-8'))
        if response.status != 200 or not isinstance(result, dict):
            raise RuntimeError('Go bridge error HTTP {}: {}'.format(
                response.status, str(result.get('error', 'unknown'))[:250] if isinstance(result, dict) else 'invalid response'))
        data = base64.b64decode(result.pop('body_base64'), validate=True)
        return dict(status_code=result.get('status_code', 0), content=data,
                    url=result.get('url') or url, headers=result.get('headers') or {},
                    protocol=result.get('protocol') or '', error=result.get('error') or '',
                    mitigated=result.get('mitigated') or '')
    except (OSError, ValueError, KeyError) as exc:
        raise RuntimeError('Go bridge request failed: {}'.format(exc)) from exc
    finally:
        conn.close()


def using_generic_native():
    """True if current platform has a loaded generic Go engine."""
    if _go_bridge_installed():
        # The long-lived service owns the generic Go engine.
        return True
    _load()
    return bool(_GENERIC)


def _call_native(payload, free_fn, method):
    ptr = method(*payload)
    if not ptr:
        raise RuntimeError('Go shared library returned NULL')
    try:
        return json.loads(ctypes.string_at(ptr).decode('utf-8'))
    finally:
        free_fn(ptr)


def perform(method, url, headers, body, profile, session, timeout):
    """One normalized request/response API across platforms."""
    split = urlsplit(url)
    if split.scheme.lower() not in ('http', 'https') or not split.hostname:
        raise ValueError('An absolute HTTP(S) URL is required')
    if target_name().startswith('ios-'):
        from .ios_wasm import perform as _ios_perform
        return _ios_perform(method, url, headers, body, profile, session, timeout)
    if _go_bridge_installed():
        return _go_bridge_perform(method, url, headers, body, profile, session, timeout)
    lib = _load()
    if _GENERIC:
        req = {'method': method, 'url': url, 'headers': headers,
               'body_base64': base64.b64encode(body).decode('ascii'),
               'profile': profile, 'session': session,
               'timeout_seconds': int(max(1, min(120, float(timeout))))}
        raw = _call_native([json.dumps(req, separators=(',', ':')).encode('utf-8')],
                           lib.GoFree, lib.GoRequest)
        data = base64.b64decode(raw.get('body_base64') or '', validate=True)
        return dict(status_code=raw.get('status', 0), content=data,
                    url=raw.get('url') or url, headers=raw.get('headers') or {},
                    protocol=raw.get('protocol', ''), error=raw.get('error', ''),
                    mitigated=raw.get('cf_mitigated', ''))
    # Prebuilt compatibility library is intentionally LIMITED TO Rugby24 GET.
    if (method == 'GET' and not body and split.scheme.lower() == 'https'
            and split.hostname.lower() == 'rugby24.net'):
        raw = _call_native([url.encode('utf-8'), profile.encode('utf-8')],
                           lib.Rugby24Free, lib.Rugby24Fetch)
        return dict(status_code=raw.get('status', 0),
                    content=(raw.get('body') or '').encode('utf-8'),
                    url=raw.get('url') or url,
                    headers={'content-type': raw.get('content_type', '')},
                    protocol=raw.get('protocol', ''), error=raw.get('error', ''),
                    mitigated=raw.get('cf_mitigated', ''))
    # Preserve previous behavior for other hosts on Android ARM32 until rebuilt.
    import requests
    key = (profile, session)
    with _LOCK:
        py_session = _PY_SESSIONS.get(key)
        if py_session is None:
            py_session = requests.Session()
            _PY_SESSIONS[key] = py_session
    r = py_session.request(method, url, headers=headers, data=body if body else None,
                           timeout=timeout)
    return dict(status_code=r.status_code, content=r.content, url=r.url,
                headers=dict(r.headers), protocol='python-requests', error='',
                mitigated=r.headers.get('cf-mitigated', ''))
