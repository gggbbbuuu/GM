# -*- coding: utf-8 -*-

'''
    Blacklodge Add-on

    Trakt device authorisation with a QR code.

    authTrakt() keeps its own flow (device code, polling at the interval Trakt
    gives, settings written on success). Only the dialog the user looks at
    changes: open_dialog() returns an object with the same calls the flow
    makes on control.progressDialog (update / iscanceled / close).

    The window works like ResolveURL's QRCodeProgressDialog (debrid device
    authorisation, script.module.resolveurl): a WindowXMLDialog opened with
    show() from the thread that polls, no second thread. Kodi runs the
    window's onAction (BACK, ENTER) on that thread while it waits in Kodi, so
    authTrakt() waits with control.sleep() (xbmc.sleep), not time.sleep().

    - The QR code holds https://trakt.tv/activate/<code>, so the phone opens
      the activation page with the code already filled in and the user does
      not type it. The address and the code are also on screen, for anyone
      without a phone camera.
    - The QR code is made on the device (segno 1.6.6, pure Python, BSD,
      unmodified copy in resources/lib/qrlib/segno). No online QR service:
      the code never leaves Kodi.
    - Anything that fails (segno not loading, e.g. Python 2 / Kodi 18, the
      window not opening) gives the original DialogProgress with the original
      text, so authorisation always works as before.
'''

import os
import sys
import time

from resources.lib.modules import control
from resources.lib.modules import log_utils

_QRLIB = os.path.join(control.addonPath, 'resources', 'lib', 'qrlib')
_XML = 'script-blacklodge-traktauth.xml'
_KEEP_FILES = 3
# Not moved by clock changes (NTP setting the time on a box without a clock
# battery while the user authorises). Python 2 never gets this window.
_now = getattr(time, 'monotonic', time.time)

CTRL_QR, CTRL_HEADING, CTRL_TEXT, CTRL_CODE, CTRL_URL = 200, 2000, 2001, 2002, 2003
CTRL_REMAIN, CTRL_HINT, CTRL_PROGRESS = 2005, 2006, 5000

# BACK, ESC, PREVIOUS_MENU, NAV_BACK, SELECT / ENTER and right click (the
# usual "back" with a mouse): the only thing to do in this window is cancel.
# Left click (100) is left out: on touch screens any tap is a left click.
_CLOSE_ACTIONS = (9, 10, 13, 92, 7, 101)

# Fixed address: Trakt now returns https://auth.trakt.tv/activate in
# verification_url, but trakt.tv/activate/<code> is the address that fills the
# code in by itself (used this way in the ManaLAB build's script.trakt) and the
# short one is easier to type.
ACTIVATE_URL = 'https://trakt.tv/activate'
SHORT_URL = 'trakt.tv/activate'


def activate_url(code):
    return '%s/%s' % (ACTIVATE_URL, code)


def make_qr(url, scale=20):
    # PNG in the add-on profile, or '' on failure. The time comes first in
    # the name: Kodi caches textures by path (same name = old QR), and
    # cleanup() keeps the newest by sorting the names.
    try:
        if _QRLIB not in sys.path: sys.path.append(_QRLIB)
        import segno
    except Exception:
        log_utils.log('traktqr: segno not available', 1)
        return ''
    try:
        import hashlib
        profile = control.dataPath
        if not os.path.isdir(profile): os.makedirs(profile)
        name = 'trakt_qr_%013d_%s.png' % (int(time.time() * 1000), hashlib.sha1(url.encode('utf-8')).hexdigest()[:10])
        path = os.path.join(profile, name)
        segno.make(url, error='m', micro=False).save(path, scale=scale, dark='#000000', light='#ffffff')
        cleanup(protect=name)
        return path if os.path.exists(path) else ''
    except Exception:
        log_utils.log('traktqr: make', 1)
        return ''


def cleanup(keep=_KEEP_FILES, protect=None):
    # protect: the file just written is never removed, even if the clock was
    # set back and older files sort after it.
    try:
        profile = control.dataPath
        names = sorted(n for n in os.listdir(profile) if n.startswith('trakt_qr_') and n.endswith('.png') and n != protect)
        if protect: keep = max(0, keep - 1)
        for n in (names[:-keep] if keep else names):
            try: os.remove(os.path.join(profile, n))
            except Exception: pass
    except Exception:
        pass


def _window_class():
    from kodi_six import xbmcgui

    class _AuthWindow(xbmcgui.WindowXMLDialog):

        def __init__(self, *args, **kwargs):
            self.canceled = False

        def onInit(self):
            pass

        def onAction(self, action):
            try: action_id = action.getId()
            except Exception: action_id = action
            if action_id in _CLOSE_ACTIONS:
                self.canceled = True
                self.close()

        def onClick(self, control_id):
            self.canceled = True
            self.close()

        def percent(self, value):
            try: self.getControl(CTRL_PROGRESS).setPercent(max(0, min(100, int(value))))
            except Exception: pass

        def label(self, cid, value):
            try: self.getControl(cid).setLabel(value or '')
            except Exception: pass

        def text(self, cid, value):
            try: self.getControl(cid).setText(value or '')
            except Exception: pass

        def image(self, cid, value):
            # useCache=False: the PNG is used once, so it is not copied into
            # Kodi's texture cache (Thumbnails); old PNGs are removed by
            # cleanup().
            try: self.getControl(cid).setImage(value or '', False)
            except TypeError:
                try: self.getControl(cid).setImage(value or '')
                except Exception: pass
            except Exception: pass

    return _AuthWindow


class _QRDialog(object):
    # Same calls authTrakt makes on control.progressDialog.

    def __init__(self, win, expires_in, started=None):
        self.win = win
        self.started = started or _now()
        self.expires_in = max(1, int(expires_in))
        self.closed = False

    def update(self, percent, *args):
        # Never raises (e.g. a translation of 32659 without %s): authTrakt's
        # loop would skip the cancel check and the poll for that second. The
        # bar is the caller's percent, as with the original dialog; the time
        # left is read from the clock.
        if self.closed: return
        try:
            self.win.percent(percent)
            elapsed = _now() - self.started
            left = max(0, int(self.expires_in - elapsed + 0.999))
            self.win.label(CTRL_REMAIN, control.lang(32659) % ('%d:%02d' % (left // 60, left % 60)))
        except Exception:
            pass

    def iscanceled(self):
        return self.closed or self.win.canceled

    def close(self):
        if self.closed: return
        self.closed = True
        try: self.win.close()
        except Exception: pass
        cleanup()


def _plain_dialog():
    # The original dialog, exactly as authTrakt opened it before.
    dialog = control.progressDialog
    dialog.create('Trakt')
    return dialog


def open_dialog(verification_url, code, expires_in, started=None):
    win = None
    try:
        image = make_qr(activate_url(code))
        if not image: return _plain_dialog()
        win = _window_class()(_XML, control.addonPath, 'Default', '1080i')
        win.show()
        dialog = _QRDialog(win, expires_in, started)
        win.label(CTRL_HEADING, control.lang(32657))
        win.text(CTRL_TEXT, control.lang(32658))
        win.label(CTRL_URL, SHORT_URL)
        win.label(CTRL_CODE, code)
        win.label(CTRL_HINT, control.lang(32660))
        win.image(CTRL_QR, image)
        dialog.update(0)
        return dialog
    except Exception:
        log_utils.log('traktqr: open_dialog', 1)
        if win is not None:
            try: win.close()
            except Exception: pass
    cleanup(0)
    return _plain_dialog()
