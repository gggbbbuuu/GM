# -*- coding: utf-8 -*-
"""Xbox/Windows UWP *test* fallback: requests, not native Go/TLS impersonation.

Kodi 21.x on Xbox can fail merely importing ctypes because kernel32 cannot be
resolved in the sandbox. Avoid ctypes and Go DLL loading entirely on UWP.
This fallback cannot reproduce Go's TLS fingerprint/anti-bot profiles.
"""
import threading

_LOCK = threading.RLock()
_SESSIONS = {}
_LOGGED = False


def _log(message):
    try:
        import xbmc
        xbmc.log('[script.module.go][UWP-TEST] ' + message, xbmc.LOGINFO)
    except (ImportError, AttributeError):
        pass


def target_name(*args, **kwargs):
    """UWP uses Python fallback rather than a native Go ABI."""
    return 'windows-uwp-python-fallback'


def installed_targets():
    """No Go native target is loaded on UWP in this test build."""
    return []


def using_generic_native():
    return False


def _session(profile, name):
    # Explicit named cookie jars mirror the Go module's Session behavior.
    # Profiles only influence the HTTP User-Agent, *not* the TLS fingerprint.
    key = (str(profile), str(name))
    with _LOCK:
        session = _SESSIONS.get(key)
        if session is None:
            import requests
            session = requests.Session()
            # Default headers can be overwritten by user-provided headers.
            if str(profile).lower().startswith('android'):
                session.headers['User-Agent'] = (
                    'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/133.0.0.0 Mobile Safari/537.36'
                )
            elif str(profile).lower().startswith('chrome'):
                version = {'chrome150': '150', 'chrome133': '133'}.get(str(profile), '133')
                session.headers['User-Agent'] = (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/' + version +
                    '.0.0.0 Safari/537.36'
                )
            _SESSIONS[key] = session
        return session


def perform(method, url, headers, body, profile, session, timeout):
    """Same result dictionary as native.perform, via ordinary Python HTTPS.

    No Go DLL or ctypes is used. Site-specific TLS/Cloudflare behavior can differ.
    """
    global _LOGGED
    with _LOCK:
        if not _LOGGED:
            _log('Using requests-based fallback on UWP; Go native engine disabled')
            _LOGGED = True
    if not str(url).lower().startswith(('https://', 'http://')):
        return dict(status_code=0, content=b'', url=str(url), headers={},
                    protocol='Python UWP fallback',
                    error='UWP fallback only supports HTTP(S) URLs', mitigated='')
    try:
        import requests
        sess = _session(profile, session)
        # Sessions with distinct names are isolated. Keep their cookie jars.
        # A lock also guards shared-session requests against concurrent mutation.
        with _LOCK:
            reply = sess.request(
                method=str(method).upper(), url=str(url),
                headers=dict(headers or {}), data=(body or None),
                timeout=max(1.0, min(120.0, float(timeout))),
                allow_redirects=True,
            )
        raw_version = getattr(getattr(reply, 'raw', None), 'version', None)
        protocol = {10: 'HTTP/1.0', 11: 'HTTP/1.1', 20: 'HTTP/2'}.get(raw_version, 'HTTP (Python)')
        return dict(status_code=reply.status_code, content=reply.content,
                    url=reply.url, headers=dict(reply.headers),
                    protocol=protocol + ' [UWP Python fallback]',
                    error='', mitigated=reply.headers.get('cf-mitigated', ''))
    except Exception as exc:
        # Do not log sensitive URLs, headers, query strings, or cookies.
        _log('Python fallback request failed: ' + type(exc).__name__)
        return dict(status_code=0, content=b'', url=str(url), headers={},
                    protocol='Python UWP fallback',
                    error='Xbox UWP Python fallback: ' + type(exc).__name__,
                    mitigated='')
