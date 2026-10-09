# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    Optional TLS-impersonating transport (curl_cffi).

    Some hosts sit behind Cloudflare plus Anubis. Cloudflare rejects plain
    python-urllib TLS fingerprints outright, while Anubis only challenges
    User-Agents that look JavaScript-capable. Combining a browser TLS
    fingerprint with a random non-browser User-Agent satisfies both without
    solving any challenge.

    The User-Agent trick follows socram8888/anubypass (WTFPL).

    Degrades to None-aware no-ops when script.module.curlcffi is absent, so
    callers must check AVAILABLE.

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

import ctypes
import os
import random
import string
import sys

from tulip import kodi as control
from tulip.log import log as log_debug


def _addon_lib_base():

    '''
    Locates the curlcffi addon's native library directory, if installed.

    Kodi only adds an optional dependency to sys.path unreliably, so this is
    resolved explicitly instead of hoping the import finds it.
    '''

    try:
        base = control.transPath('special://home/addons/script.module.curlcffi/lib')

        if base and os.path.isdir(base):
            return base
    except Exception:
        pass

    override = os.environ.get('CURLCFFI_LIB')

    if override and os.path.isdir(override):
        return override

    return None


def _platform_dirs():

    '''Mirrors the platform layout of the curlcffi addon lib directory.'''

    try:
        machine = __import__('platform').machine().lower()
    except Exception:
        machine = ''

    dirs = []

    if sys.platform.startswith('linux'):
        if 'aarch64' in machine or 'arm64' in machine or 'armv8' in machine:
            dirs.append('linux_aarch64')
        elif 'arm' in machine:
            dirs.append('linux_armv7l')
        else:
            dirs.append('linux_x86_64')
    elif sys.platform == 'darwin':
        dirs.append('macos_arm64')
    elif sys.platform.startswith('win'):
        dirs.append('windows_x64')

    # Every other known layout, so a mismatched detection still finds a copy
    # rather than silently falling through to the system one.
    for name in ('linux_x86_64', 'linux_aarch64', 'linux_armv7l', 'macos_arm64',
                 'windows_x64', 'android_x86_64', 'android_arm64-v8a',
                 'android_armeabi-v7a', 'ios_arm64'):
        if name not in dirs:
            dirs.append(name)

    return dirs


def _find_wrappers():

    '''
    Returns paths of curl_cffi native wrappers on disk, addon copy first.

    This locates files without importing anything, so the caller can preload
    the chosen binary before Python binds the module.
    '''

    found = []
    tag = 'cp{0}{1}'.format(sys.version_info.major, sys.version_info.minor)

    base = _addon_lib_base()

    if base:
        for plat in _platform_dirs():
            directory = os.path.join(base, plat)

            try:
                names = sorted(os.listdir(directory))
            except OSError:
                continue

            for name in names:
                if name.startswith(tag):
                    wrapper = os.path.join(directory, name, 'curl_cffi', '_wrapper.abi3.so')

                    if os.path.isfile(wrapper):
                        found.append(wrapper)

            wrapper = os.path.join(directory, 'curl_cffi', '_wrapper.abi3.so')

            if os.path.isfile(wrapper):
                found.append(wrapper)

    try:
        import site as _site

        extra = list(sys.path) + _site.getsitepackages()
    except Exception:
        extra = list(sys.path)

    for path in extra:
        wrapper = os.path.join(path, 'curl_cffi', '_wrapper.abi3.so')

        if os.path.isfile(wrapper) and wrapper not in found:
            found.append(wrapper)

    return found


def _deepbind_preload():

    '''
    Preloads the curl_cffi native library with RTLD_DEEPBIND on Linux.

    Kodi links stock libcurl.so.4 globally at startup for its own HTTP. When
    the impersonate build is loaded afterwards, its curl_easy_setopt calls
    resolve to the stock library instead of its own, and every impersonation
    target fails with return code 48 ("is not supported"). DEEPBIND puts the
    wrapper's own symbols first in its lookup scope, restoring rc=0.

    Must run before the first `import curl_cffi` of the process. If another
    invocation already loaded the wrapper without it, only a Kodi restart
    picks this up; the probe diagnostics will show it.
    '''

    deepbind = getattr(os, 'RTLD_DEEPBIND', 0)

    if not deepbind:
        return None

    mode = os.RTLD_NOW | deepbind

    try:
        import ctypes.util

        lib = ctypes.util.find_library('curl-impersonate')

        if lib:
            try:
                _PRELOADED_HANDLES.append(ctypes.CDLL(lib, mode=mode))
            except Exception:
                pass
    except Exception:
        pass

    for wrapper in _find_wrappers():
        try:
            # The handle is kept in _PRELOADED_HANDLES for the life of the
            # process. Without a live reference the loader could reclaim and
            # unload the library, and the later plain import would rebind it
            # without DEEPBIND, silently reintroducing the interposition.
            _PRELOADED_HANDLES.append(ctypes.CDLL(wrapper, mode=mode))
            return wrapper
        except Exception:
            continue

    return None


# Live references to every preloaded native library. See above.
_PRELOADED_HANDLES = []


_PRELOADED = _deepbind_preload()

# If the addon ships its own copy, make sure the Python code comes from the
# same build that was preloaded, not from a system site-packages copy.
if _PRELOADED:
    package_dir = os.path.dirname(os.path.dirname(_PRELOADED))

    if package_dir not in sys.path:
        sys.path.insert(0, package_dir)

try:
    from curl_cffi import requests as _cr
except Exception:
    _cr = None

AVAILABLE = _cr is not None

# Pinned, explicit versions newest first - never the bare 'chrome' alias.
#
# The alias is re-pointed at the newest Chrome by each curl_cffi release, so
# requesting it couples us to whatever the installed Python package happens
# to mean today. Pinning exact versions removes that moving target; combined
# with the probe below, an outdated entry is simply skipped at runtime.
_PROFILES = ['chrome150', 'chrome146', 'chrome145', 'chrome142', 'chrome136',
             'chrome124', 'safari17_0']

# Used when no profile could be proven to work. Deliberately NOT _PROFILES[0]:
# if the whole list was rejected the newest entry is the most suspicious, so
# falling back to it would re-run the likeliest failure instead of the
# broadest-supported candidate.
_SAFE_PROFILE = 'chrome124'

# A tiny, cheap and stable endpoint used only to confirm a profile really
# performs requests. Never cached, never retried.
_PROBE_URL = 'https://www.cloudflare.com/cdn-cgi/trace'
_PROBE_TIMEOUT = 10

_profile = None

_LETTERS = string.ascii_lowercase


def _fake_name():

    name = random.choice(_LETTERS).upper() + ''.join(
        random.choice(_LETTERS) for _ in range(random.randint(8, 14))
    )

    # keep 'bot' out of the string just in case
    name = name.replace('Bot', 'Bxt')

    return '{0}/{1}{2}'.format(
        name,
        random.randint(0, 99),
        '.{0}'.format(random.randint(0, 99)) if random.random() < 0.5 else '',
    )


def fake_user_agent():

    """Random non-JS-looking UA, as per anubypass."""

    parts = [_fake_name() for _ in range(random.randint(3, 6))]

    return '{0} ({1})'.format(_fake_name(), '; '.join(parts))


def _unsupported(error):

    """True only when curl_cffi rejected the impersonation target itself."""

    return 'is not supported' in str(error)


def _pick_profile():

    """
    Returns the first TLS profile this build actually supports.

    The probe has to perform a real request: constructing a Session does not
    validate the profile, so Session(impersonate='chrome') succeeds even when
    the bundled libcurl has never heard of the version the alias resolves to.
    Only issuing the request raises "Impersonating <target> is not supported",
    which is why probing with Session() alone silently accepted the first
    profile and never reached the fallback list.
    """

    global _profile

    if _profile:
        return _profile

    try:
        origin = getattr(_cr, '__file__', 'unknown')
    except Exception:
        origin = 'unknown'

    log_debug(
        'Impersonate: probing with curl_cffi from {0} (preloaded={1})'.format(
            origin, _PRELOADED or 'none'
        )
    )

    for name in _PROFILES:

        probe = None

        try:
            probe = _cr.Session(impersonate=name)
            probe.get(_PROBE_URL, timeout=_PROBE_TIMEOUT)
        except Exception as e:
            # Only an explicit rejection proves the profile is unsupported.
            # A timeout, DNS failure or refused connection says nothing about
            # the profile, so it must not disqualify it, or a flaky network
            # would discard every candidate and leave us guessing.
            if _unsupported(e):
                log_debug('Impersonate: {0} rejected ({1})'.format(name, e))
                continue

            log_debug('Impersonate: {0} probe failed but usable ({1})'.format(name, e))
            _profile = name
            return name
        finally:
            close(probe)

        log_debug('Impersonate: {0} verified'.format(name))
        _profile = name
        return name

    log_debug('Impersonate: no profile verified, falling back to {0}'.format(_SAFE_PROFILE))

    # Nothing verified. Use a broadly supported profile rather than the newest
    # alias, and leave _profile unset so the next call probes again instead of
    # trusting a guess.
    return _SAFE_PROFILE


def session(cookie=None, user_agent=None, timeout=25):

    """Returns a curl_cffi session or None when unavailable."""

    if not AVAILABLE:
        return None

    try:
        profile = _pick_profile()
    except Exception:
        profile = _SAFE_PROFILE

    s = _cr.Session(impersonate=profile)

    if cookie:
        _seed(s, cookie)

    s.headers.update({'User-Agent': user_agent or fake_user_agent()})

    return s


def close(sess):

    '''
    Releases a session's native handle.

    curl_cffi sessions hold a libcurl easy handle plus pooled connections.
    Callers must close what session() returns instead of leaving it for the
    garbage collector, so no native state outlives the search.
    '''

    if sess is None:
        return

    try:
        sess.close()
    except Exception:
        pass


def _seed(s, cookie):

    """Applies a raw 'name=value; name=value' cookie string."""

    log_debug('Impersonate: session built (profile={0})'.format(_profile or _SAFE_PROFILE))

    for part in cookie.split(';'):
        part = part.strip()

        if '=' not in part:
            continue

        name, value = part.split('=', 1)

        try:
            s.cookies.set(name.strip(), value.strip())
        except Exception:
            pass