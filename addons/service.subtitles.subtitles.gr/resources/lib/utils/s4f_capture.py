# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    One-shot LAN listener that collects the Subs4Series session cookie.

    Started from Settings, it binds a port - a fixed one if 's4f_capture_port'
    is set, otherwise any free one - puts the address on the TV and serves a
    small setup page. That page hands out a bookmarklet which, run while the
    user is on subs4series.com, forwards document.cookie back here. The site's
    PHPSESSID is not HttpOnly, so a page on that origin is allowed to read it;
    nothing is solved or bypassed, the user's own logged-in session is simply
    handed over.

    The same page and the same bookmarklet also carry a gated download. When a
    download stops at the Subs4Series captcha, the provider raises Gated and
    this listener is started with the subtitle page as its target: the page
    links straight to it, the bookmarklet posts that page's own form with the
    token the user just ticked, and what comes back is the address the browser
    lands on - a plain, session-free /smp/tmp/....zip. Kodi fetches that archive
    itself. Nothing is solved here either, but there is no other way: the token
    answers one page, once, and no cookie can stand in for it.

    The wait is shown as a WindowXML dialog: the address, the instructions, and
    a QR code a phone can scan. That is not decoration. The browser is often on
    another device entirely, and on a set-top box there is no browser to open at
    all, so the code is what carries the address across. Nothing native can draw
    the captcha itself: Kodi has no browser control, and the site's reCAPTCHA key
    only works on the site's own origin, so a page served from this machine could
    never mint a token however it were drawn. Kodi can only show the code that
    takes the phone to the page that can. Where a browser does exist locally, the
    dialog opens the address in it.

    A fixed port gives a permanent address, so the bookmarklet can be saved
    once and reused. It carries a token that is minted on first use and kept
    in the 's4f.capture_token' setting, which is what makes the import link
    both permanent and unguessable: a per-run secret would have to change, and
    a bookmarklet that changes is not a bookmarklet. Clearing that setting
    renews the token and locks out every bookmarklet handed out before.

    The listener accepts one import and then stops, so the port is only
    occupied, and the address only answers, while the dialog is on screen.

    Stops on the first successful import, on cancel, or after TIMEOUT seconds.
    Every thread is a daemon and the socket is always closed, because a server
    left listening would keep Kodi from exiting.

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

import hashlib
import hmac
import html
import ipaddress
import json
import os
import re
import socket
import string
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

# extract_cookies sits next to this file and both scripts are launched the same
# way (a bare RunScript path), so the sibling import is made explicit rather
# than relying on Kodi having put the addon on sys.path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from s4f_qr import matrix as qr_matrix, png as qr_png
from s4f_session import extract_cookies

ADDON_ID = 'service.subtitles.subtitles.gr'
SETTING = 's4f.session'
SETTING_PORT = 's4f.capture_port'
SETTING_TOKEN = 's4f.capture_token'

# The waiting dialog, as it sits in this add-on's own skin folder. Kodi cannot
# be told to draw the captcha; it can only be told what to put in front of the
# user instead.
DIALOG_XML = 'handoff.xml'
DIALOG_SKIN = 'Default'
DIALOG_RES = '720p'

# The dialog lays the code out at 340 pixels of its 720p coordinate space, and
# Kodi scales the window to the screen, so the picture is asked for the pixels
# it will really occupy.
QR_BOX = 340

# 16 random bytes; the token is compared as hex text.
TOKEN_BYTES = 16

# How long the listener stays up: three minutes, time to install the
# bookmarklet, work out the browser path, and use it. A forgotten dialog costs
# a held port, but cutting a user off mid-captcha costs the download.
TIMEOUT = 240
TICK = 0.25

PAGE = string.Template('''<!doctype html>
<html lang="$lang"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<style>
 body{font-family:system-ui,Segoe UI,Roboto,sans-serif;margin:0;background:#14161a;color:#e8eaed}
 main{max-width:640px;margin:0 auto;padding:28px 20px 60px}
 h1{font-size:1.35rem;margin:0 0 6px}
 p{line-height:1.5;color:#c3c7cd}
 .drag{display:inline-block;margin:6px 0 14px;padding:11px 18px;border-radius:8px;
       background:#8ab4f8;color:#14161a;font-weight:600;text-decoration:none;cursor:grab}
 textarea{width:100%;box-sizing:border-box;background:#1e2127;color:#e8eaed;border:1px solid #333941;
          border-radius:8px;padding:10px;font-family:monospace;font-size:.82rem;resize:vertical}
 button{margin-top:8px;padding:10px 18px;border:0;border-radius:8px;background:#3d5afe;color:#fff;
        font-weight:600;cursor:pointer}
 .status{margin-top:18px;padding:12px 14px;border-radius:8px;background:#1e2127;border:1px solid #333941}
 .status.ok{border-color:#3c8c5a;color:#9ae6b4} .status.err{border-color:#8c3c3c;color:#f2a0a0}
 .hint{display:none;background:#1e2127;border:1px solid #333941;border-radius:8px;
       padding:10px 12px;margin:10px 0;font-size:.92rem;color:#c3c7cd}
 .hint.show{display:block}
 #copied{margin-left:10px;color:#9ae6b4;font-size:.9rem}
 details{margin-top:18px;color:#c3c7cd} summary{cursor:pointer;color:#e8eaed}
</style></head>
<body><main>
<h1>$title</h1>
<p>$subtitle</p>
$target_block
<details open><summary>$userscript_title</summary>
<p>$userscript_intro</p>
<p><b>$userscript_step1</b><br>$userscript_stores
<br><a href="https://chromewebstore.google.com/detail/violentmonkey/jinjaccalgkegednnccohejagnlnfdag" target="_blank" rel="noreferrer">$userscript_store_link</a></p>
<p><b>$userscript_step2</b><br>$userscript_install_note
<br><a href="/kodi.user.js">$userscript_link</a></p>
</details>
<div class="status" id="s">$status</div>
<details><summary>$bookmarklet_title</summary>
<p><a class="drag" href="$marklet_href" onclick="return false">$drag</a></p>
<textarea id="marklet" rows="5" readonly onclick="this.select()">$marklet</textarea>
<button type="button" id="copy">$copy_label</button><span id="copied"></span>
<noscript><p>$how_generic</p></noscript>
<p class="hint" data-when="android-firefox">$how_firefox</p>
<p class="hint" data-when="android-other">$how_android</p>
<p class="hint" data-when="ios">$how_ios</p>
<p class="hint" data-when="desktop">$how_desktop</p>
</details>
<details><summary>$paste_label</summary>
<form method="post" action="/set">
 <input type="hidden" name="t" value="$token">
 <textarea name="c" rows="4" placeholder="PHPSESSID=..."></textarea>
 <button type="submit">$send</button>
</form></details>
<script>
 var seen = false;
 var said = function () {
   if (!seen) { seen = true; document.getElementById('s').textContent = $received_js; }
 };
 // The Kodi dialog closes the moment the hand-over lands, and the listener
 // goes with it, so a second page of this same address is told by the tab that
 // did the hand-over instead - they share an origin, so they can share the
 // memory of it, and nothing has to keep waiting on the server.
 try {
   window.addEventListener('storage', function (e) { if (e.key === 's4f.received') { said(); } });
 } catch (e) {}
 if ($autoclose) {
   try { localStorage.setItem('s4f.received', String(Date.now())); } catch (e) {}
   setTimeout(function () { window.close(); }, 2000);
 }
 setInterval(function () {
   fetch('/status').then(function (r) { return r.json(); }).then(function (d) {
     if (d.received) { said(); }
   }).catch(function () {});
 }, 1500);

 // A phone cannot drag a bookmarklet to a bookmarks bar, and typing it as an
 // address gets a search instead, so it can at least be copied from here.
 // navigator.clipboard needs a secure context and this page is plain http on a
 // LAN address, so in practice it is the selected-textarea way that runs.
 var box = document.getElementById('marklet');
 var cbutton = document.getElementById('copy');
 if (box && cbutton) {
   cbutton.addEventListener('click', function () {
     var said = function () { document.getElementById('copied').textContent = $copied_js; };
     var selectit = function () {
       box.focus(); box.select();
       try { box.setSelectionRange(0, box.value.length); } catch (e) {}
       try { if (document.execCommand('copy')) { said(); } } catch (e) {}
     };
     if (navigator.clipboard && navigator.clipboard.writeText) {
       navigator.clipboard.writeText(box.value).then(said)['catch'](selectit);
     } else { selectit(); }
   });
 }

 // Which browser is reading this decides which steps are worth showing: on a
 // phone only some browsers can run a bookmarklet at all, and the rest are the
 // ones that turn the tap into a search.
 var ua = navigator.userAgent || '';
 var which = 'desktop';
 if (ua.indexOf('Android') >= 0) { which = /Firefox|FxiOS/.test(ua) ? 'android-firefox' : 'android-other'; }
 else if (/iPhone|iPad|iPod/.test(ua)) { which = 'ios'; }
 var hints = document.querySelectorAll('.hint');
 for (var h = 0; h < hints.length; h++) {
   if (hints[h].getAttribute('data-when') === which) { hints[h].className = 'hint show'; }
 }
</script>
</main></body></html>
''')

# What /done?m=... may say, and whether it is a success page. Anything else
# falls back to the refusal text.
DONE_STATES = {
    'ok': ('received', True),
    'nocookie': ('no_cookie', False),
    'token': ('bad_token', False),
    'nocaptcha': ('no_captcha', False)
}

# The userscript the page offers, with the address and the token baked in at
# serve time. It is the bookmarklet promoted to a resident: the same form the
# bookmarklet posts, fired automatically once the ticked token exists, handed
# over the same way - a navigation, so no cross-origin grants are needed. $u
# is the listener's /set address with the token; $t is the profile token, sent
# only there. It runs on Subs4Series pages and nowhere else (@match), starts
# nothing on its own, and phones home to nothing but the listener.
USERSCRIPT = string.Template('''// ==UserScript==
// @name        Subtitles.gr hand-off
// @namespace   subtitles.gr
// @match       *://www.subs4series.com/*
// @match       *://subs4series.com/*
// @grant       none
// @run-at      document-idle
// ==/UserScript==
(function () {
  'use strict';
  var u = '$u';
  function handOver(extra) {
    location.href = u + '&c=' + encodeURIComponent(document.cookie) + (extra || '');
  }
  function tick() {
    var t = '';
    try { t = grecaptcha.getResponse(); } catch (e) {}
    return t;
  }
  // After the tick the token sits in the page; poll gently until it does,
  // then do exactly what the bookmarklet does: post the captcha form with
  // the session it is holding, and report where the browser landed.
  var tries = 0;
  var timer = setInterval(function () {
    tries += 1;
    if (tick()) {
      clearInterval(timer);
      var f = null, s = document.forms, i;
      for (i = 0; i < s.length; i++) {
        if (s[i].querySelector('[name="my_recaptcha_challenge_field"]')) { f = s[i]; break; }
      }
      if (!f) { handOver(); return; }
      var b = new URLSearchParams(new FormData(f));
      b.set('g-recaptcha-response', tick());
      fetch(new URL(f.getAttribute('action') || '', location.href).href,
        {method: 'POST', body: b, credentials: 'include'}).then(function (r) {
          handOver('&z=' + encodeURIComponent(r.url || ''));
        })['catch'](function () { handOver(); });
    } else if (tries > 120) {
      clearInterval(timer);
    }
  }, 500);
})();''')


class _State(object):

    def __init__(self, token, target='', archive_mode=False):

        self.token = token
        self.target = target
        self.archive_mode = archive_mode
        self.value = ''
        self.archive = ''
        self.received = False
        self.timed_out = False

    @property
    def done(self):

        '''
        Whether the wait is over.

        A download hand-off is not finished by a cookie: only an archive
        answers it, or every cookie-bearing click would end the wait early and
        fail the download.
        '''

        return bool(self.archive) if self.archive_mode else self.received


def _archive_ok(url):

    '''
    True for the address the browser lands on after solving the captcha.

    The file comes back as /smp/tmp/<id>_<slug>_<n>.zip and is served with no
    session at all. Anything else means the captcha was not accepted, and
    treating that as a download would only produce a confusing failure later.
    '''

    return url.startswith('http') and '/smp/' in url


def addon():

    # RunScript(path) carries no addon id, so it must be passed explicitly
    return xbmcaddon.Addon(ADDON_ID)


def lang(string_id):

    return addon().getLocalizedString(string_id)


def countdown(strings, seconds):

    '''
    The wait, in the words the dialog and the fallback already use.

    Three minutes counts as minutes and seconds (240 reads "4 min 0 s" only in
    the first second, then "3 min 59 s"); under a minute it is seconds alone.
    One helper for all three call sites, so they can never drift apart.
    '''

    seconds = max(0, int(seconds))

    if seconds >= 60:
        text = strings['line3_min'] % (seconds // 60, seconds % 60)
    else:
        text = strings['line3'] % seconds

    return text


def page_lang():

    '''
    The two-letter language of the served page, for <html lang>.

    Kodi's own UI language decides: Greek Kodi gets the Greek page, anything
    else gets English, because those are the two languages this add-on ships.
    getLocalizedString() already resolves the wording the same way, so this
    only declares what the page is - for screen readers, spellchecking, and
    the browser's offer to translate something it should not need to.
    '''

    try:
        code = xbmc.getLanguage(xbmc.ISO_639_1, False)
    except Exception:
        return 'en'

    return 'el' if str(code).lower().startswith('el') else 'en'


def log_debug(message):

    '''
    Logs through the plain API, never through tulip.

    tulip.log resolves an addon id with xbmcaddon.Addon() as it is imported,
    and this script is launched as a bare RunScript(path) where Kodi cannot
    supply one, so importing it raises before any of this file runs. That is
    also why addon() passes ADDON_ID explicitly.
    '''

    try:
        xbmc.log('service.subtitles.subtitles.gr: ' + message, xbmc.LOGDEBUG)
    except Exception:
        pass


def message_lines(*parts):

    # Kodi 19 dropped the extra line arguments of the progress dialog; [CR] is
    # the replacement (the same trick resolveurl uses for its Python 3 branch).
    return '[CR]'.join([part for part in parts if part])


def _usable(candidate):

    '''
    True for something a human can actually type into a browser.

    Kodi's own network labels are not trusted on their own: while its network
    information is not ready, Kodi answers them with a placeholder of its own
    and that placeholder used to be printed straight to the user. On a real
    box both Network.IPAddress and Network.MacAddress came back as the literal
    string "Busy", so the dialog offered 'http://Busy:46805/'. Anything that
    is not a routable IPv4 address is dropped here.
    '''

    try:
        address = ipaddress.IPv4Address(candidate)
    except ValueError:
        return False

    return not (address.is_loopback or address.is_unspecified
                or address.is_multicast or address.is_reserved)


def lan_addresses():

    '''
    Every plausible LAN address, most likely first.

    The route probe leads: it reports the address the kernel itself would use
    to reach the internet, which is the one a browser elsewhere on the network
    can reach. Kodi's infolabel follows, then the hostname lookup as a last
    resort. Loopback is never useful here, since the browser is on another
    device, and every candidate is validated before being offered.
    '''

    found = []

    def add(candidate):

        candidate = (candidate or '').strip()

        if candidate and candidate not in found and _usable(candidate):
            found.append(candidate)

    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            # No packet is sent; connect() only selects the outbound interface.
            probe.connect(('8.8.8.8', 80))
            add(probe.getsockname()[0])
        finally:
            probe.close()
    except Exception:
        pass

    try:
        label = (xbmc.getInfoLabel('Network.IPAddress') or '').strip()

        if label and not _usable(label):
            log_debug('Capture: Kodi network label {0!r} is not an address, ignored'.format(label))

        add(label)
    except Exception:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            add(info[4][0])
    except Exception:
        pass

    return found


def _dialog_path():

    base = (addon().getAddonInfo('path') or '').rstrip('/\\')

    return '/'.join([base, 'resources', 'skins', DIALOG_SKIN, DIALOG_RES, DIALOG_XML])


def _dialog_available():

    # A skin file could be missing on an install that predates it, and Kodi
    # answers a missing window file with a blank dialog rather than an error, so
    # it is checked here instead. The caller falls back to the progress dialog.
    try:
        return bool(xbmcvfs.exists(_dialog_path()))
    except Exception:
        return False


def _screen_factor():

    # The window is laid out for 720p and Kodi scales it to whatever the screen
    # is, so the code is drawn at the size it will actually be shown at.
    try:
        height = xbmcgui.getScreenHeight()
    except Exception:
        height = 0

    return (float(height) / 720.0) if height else 1.0


def _discard_image(path):

    if not path:
        return

    try:
        os.remove(path)
    except OSError:
        pass


def qr_image(address):

    '''
    Draws the address as a QR code in the temp folder, and returns the path.

    Kodi has neither a QR module nor a QR control, so s4f_qr writes both the
    code and the PNG. The file name follows the address, which keeps Kodi's
    texture cache from ever handing back a code for an address shown in an
    earlier run, and the scale is worked out from the screen so the modules land
    on whole pixels and a phone camera gets clean edges.
    '''

    if not address.startswith('http'):
        return ''

    try:
        folder = xbmcvfs.translatePath('special://temp/')
    except Exception:
        return ''

    if not folder:
        return ''

    grid = qr_matrix(address)

    if grid is None:
        log_debug('Capture: {0!r} does not fit a QR code'.format(address))
        return ''

    # Four modules of quiet zone on each side, as the format requires.
    scale = max(2, int(round(QR_BOX * _screen_factor() / float(len(grid) + 8))))

    # The name carries both the address and the moment it was drawn. The
    # address keeps a code from being handed back for an address shown earlier,
    # and the moment keeps Kodi's texture cache from serving a copy of this
    # file's first load over a later one - a path whose contents have changed is
    # not a path Kodi is obliged to look at again.
    name = 's4f_handoff_{0}_{1:x}.png'.format(
        hashlib.md5(address.encode('utf-8')).hexdigest()[:8],
        int(time.time() * 1000) & 0xffffff
    )
    path = folder.rstrip('/\\') + '/' + name

    if not qr_png(path, address, scale=scale):
        log_debug('Capture: could not write the QR image to {0!r}'.format(path))
        return ''

    return path


def open_in_browser(url):

    '''
    Hands the address to whatever browser this machine has, and says whether one
    was found. Silently does nothing where there is none, which is the normal
    case on a set-top box - and the reason the dialog also shows a code.

    The browser is started detached and never waited for: some webbrowser
    backends block until the browser exits, which would hold this listener - and
    the port - for the whole browser session.
    '''

    if not url.startswith('http'):
        return False

    if sys.platform.startswith('win'):
        commands = [['cmd', '/c', 'start', '', url]]
    elif sys.platform == 'darwin':
        commands = [['open', url]]
    else:
        commands = [['xdg-open', url], ['gio', 'open', url]]

    for command in commands:

        try:
            subprocess.Popen(
                command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return True
        except Exception:
            continue

    try:
        import webbrowser

        return bool(webbrowser.open(url))
    except Exception:
        return False


class _WaitDialog(xbmcgui.WindowXMLDialog):

    '''
    The wait: a QR code, the address, the instructions, and a way out.    A WindowXML dialog rather than a progress dialog, because the address has to
    be scannable from a phone lying on a sofa. The window itself is deliberately
    plain - no skin fonts and no skin includes, so it renders on any skin - and
    every label is filled in from here, which keeps the wording in strings.po
    with the rest of the add-on.

    Note what this is not: it is not a captcha solver, and it cannot be one.
    Kodi has no browser control, and Subs4Series' reCAPTCHA key is bound to its
    own domain, so no window of ours could ever mint a token. It shows the code
    that takes the phone to the page that can.

    It is opened with doModal(), which matters more than it sounds: Kodi sends
    input to the topmost *modal* window and ignores every other one, so a window
    shown with show() cannot be clicked at all when Kodi's own modal dialog is
    up - which it is, both when this is started from the add-on's settings
    dialog and when the subtitle module is waiting on a download.

    Control ids are shared with resources/skins/Default/720p/handoff.xml.
    '''

    CANCEL = 1
    HEADING = 2
    INSTRUCTIONS = 3
    ADDRESS = 4
    STEPS = 5
    STATUS = 6
    QR = 10
    OPEN = 11

    def __init__(self, *args, **kwargs):

        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

        self.closed = False
        self.open_requested = False
        self.qr_path = ''
        self.payload = None
        self.wanted_status = None

    def onInit(self):

        # Kodi builds the window's controls as it is opened, so this is where
        # the contents are drawn; _serve() draws again from its own thread, in
        # case a skin or a Kodi build never calls this.
        self.draw()

    def onAction(self, action):

        # Back, Escape and the menu key close it. The window is the add-on's
        # own, so nothing else will: a hand-off the user has changed their mind
        # about must not keep holding a port.
        try:
            action_id = action.getId()
        except Exception:
            return

        if action_id in (9, 10, 13, 92):
            self._end()

    def _end(self):

        '''Ends the wait, from wherever it is called.'''

        self.closed = True

        try:
            self.close()
        except Exception:
            pass

    def onControl(self, control):

        try:
            self._pressed(control.getId())
        except Exception:
            pass

    def onClick(self, control_id):

        self._pressed(control_id)

    def _pressed(self, control_id):

        if control_id == self.OPEN:
            # Not a way out: it only puts the address back in front of a
            # browser, and the wait carries on.
            self.open_requested = True
        elif control_id == self.CANCEL:
            self._end()

    def _label(self, control_id, text):

        try:
            self.getControl(control_id).setLabel(text)
        except Exception as error:
            log_debug('Capture: dialog control {0} refused text: {1!r}'.format(control_id, error))

    def status(self, text):

        self.wanted_status = text
        self._label(self.STATUS, text)

    def prepare(self, strings, address, qr_path='', target='', status=''):

        '''
        Records what the dialog is to show, without touching its controls.

        Called before the window is opened, when the controls do not exist yet:
        Kodi builds them as it opens the window and refuses everything else.
        '''

        self.payload = (strings, address, qr_path, target)

        if status:
            self.wanted_status = status

    def fill(self, strings, address, qr_path='', target='', status=''):

        '''prepare(), and draw it now.'''

        self.prepare(strings, address, qr_path, target, status)
        self.draw()

    def draw(self):

        '''
        Draws what prepare() was given. Safe to call as often as you like.

        Returns False while the window has no controls yet - which is what a
        caller that draws from another thread needs to know, rather than a
        dozen refused-control lines in the log.
        '''

        if self.payload is None:
            return False

        try:
            self.getControl(self.HEADING)
        except Exception:
            return False

        strings, address, qr_path, target = self.payload

        self.qr_path = qr_path

        self._label(self.HEADING, strings['heading'])
        self._label(self.INSTRUCTIONS, strings['subtitle'])
        self._label(self.ADDRESS, '[CR]'.join([strings['scan'], address]))
        self._label(self.STATUS, self.wanted_status or strings['waiting'])
        self._label(self.OPEN, strings['open_button'])
        self._label(self.CANCEL, strings['cancel_button'])

        steps = []

        if target:
            steps.append(strings['target_label'])
            steps.append(target)

        steps.append(strings['step2'])

        self._label(self.STEPS, '[CR]'.join(steps))

        if qr_path:

            try:
                self.getControl(self.QR).setImage(qr_path)
            except Exception as error:
                log_debug('Capture: QR image refused {0!r}: {1!r}'.format(qr_path, error))

        return True


def _wait_window(strings, address, target=''):

    '''
    Builds the waiting dialog, or returns None for the caller to fall back on.

    None means the progress dialog: no address to serve, no skin file, or no
    window. Each of those is survivable, and a hand-off that cannot show a code
    is still worth showing as text.

    The window comes back ready to be opened with doModal(), not already open:
    the wait and the dialog are on different threads, because doModal blocks
    the one that opens it.

    The status opens on the first countdown, so the wording on screen is never
    the one line the page already carries.
    '''

    if not address.startswith('http') or not _dialog_available():
        return None

    picture = qr_image(address)

    try:
        window = _WaitDialog(
            DIALOG_XML, addon().getAddonInfo('path'), DIALOG_SKIN, DIALOG_RES
        )
        window.prepare(strings, address, picture, target, countdown(strings, TIMEOUT))
    except Exception as error:
        log_debug('Capture: no window dialog ({0!r}), using the progress dialog'.format(error))

        _discard_image(picture)

        return None

    return window


def _window_loop(window, state, monitor, deadline, strings, shown):

    '''
    The wait, beside a dialog that is modal on the thread that opened it.

    doModal() blocks, so everything that has to happen while the dialog is up
    happens here: the countdown, the address for a browser on this machine when
    its button says so, and the close at the end - whichever way it ends.
    '''

    try:

        # draw() says when the controls exist; Kodi builds them as the window
        # opens, and onInit() has normally drawn them by now.
        for _ in range(40):

            if window.draw() or monitor.abortRequested():
                break

            time.sleep(0.05)

        # The browser opens only when asked, from the dialog's own button: an
        # unasked window steals the focus Kodi is running in, and on a box with
        # no browser at all there is nothing to open.
        while not state.done:

            if monitor.abortRequested() or window.closed:
                break

            if time.time() >= deadline:
                state.timed_out = True
                break

            if window.open_requested:
                window.open_requested = False
                open_in_browser(shown)

            window.status(countdown(strings, deadline - time.time()))

            time.sleep(TICK)

        if state.done and not monitor.abortRequested():

            # Set, then close at once: this dialog is modal, so every second it
            # stays up after the hand-over is a second Kodi ignores input,
            # while the download it is waiting for cannot start. Anything that
            # still has to say "received" says it outside this window.
            window.status(strings['received_note'])

    except Exception as error:
        log_debug('Capture: the hand-off dialog stopped early: {0!r}'.format(error))

    finally:

        # However this thread ended, the dialog has to end with it: it is modal
        # and doModal() in _serve() is waiting for exactly this.
        try:
            window.close()
        except Exception:
            pass


class _Handler(BaseHTTPRequestHandler):

    server_version = 'SubtitlesGr'

    # A stalled client must not pin a request thread forever.
    timeout = 30

    def log_message(self, fmt, *args):

        # BaseHTTPRequestHandler writes to stderr, which on Kodi means a noisy
        # log for every poll of /status. Silence it.
        pass

    def _params(self):

        params = parse_qs(urlparse(self.path).query, keep_blank_values=True)

        if self.command == 'POST':
            try:
                length = int(self.headers.get('Content-Length') or 0)
            except ValueError:
                length = 0

            body = self.rfile.read(length).decode('utf-8', 'replace')

            for key, values in parse_qs(body, keep_blank_values=True).items():
                params.setdefault(key, []).extend(values)

        return {key: values[0] for key, values in params.items()}

    def _send(self, body, status=200, content_type='text/html; charset=utf-8'):

        payload = body.encode('utf-8')

        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(payload)

    def _page(self, message='', ok=False, autoclose=False):

        state = self.server.state
        strings = self.server.strings

        # The bookmarklet is built from the Host the user actually reached us
        # on, so a box with several interfaces works whichever address they
        # picked. The token is the one minted for this profile: it does not
        # change between runs, which is what lets a saved bookmarklet keep
        # working while still being refused to anyone who does not have it.
        host = self.headers.get('Host') or '127.0.0.1'

        # One bookmarklet, two jobs. On an ordinary Subs4Series page it just
        # carries the cookie over, as before. On a page that holds the download
        # form it posts that form first - the same fields, the same session, the
        # token the user ticked - so the address the browser ends up on is the
        # archive, and that address travels back with the cookie.
        marklet = (
            "javascript:(function(){var u='http://" + host + "/set?t=" + state.token
            + "&c='+encodeURIComponent(document.cookie);"
            "var i,f=null,s=document.forms;"
            "for(i=0;i<s.length;i++){"
            "if(s[i].querySelector('[name=\"my_recaptcha_challenge_field\"]')){f=s[i];break;}}"
            "if(!f){window.open(u,'_blank');return;}"
            "var t='';try{t=grecaptcha.getResponse();}catch(e){}"
            "var b=new URLSearchParams(new FormData(f));b.set('g-recaptcha-response',t);"
            "fetch(new URL(f.getAttribute('action')||'',location.href).href,"
            "{method:'POST',body:b,credentials:'include'}).then(function(r){"
            "location.href=u+'&z='+encodeURIComponent(r.url||'');"
            "})['catch'](function(){location.href=u;});})()"
        )

        target_block = ''

        if state.target:

            target_block = (
                '<p>' + html.escape(strings['target_label'])
                + '<br><a href="' + html.escape(state.target, quote=True)
                + '" target="_blank" rel="noreferrer">' + html.escape(state.target) + '</a></p>'
            )

        status = message or strings['waiting']

        return PAGE.safe_substitute(
            lang=page_lang(),
            title=html.escape(strings['title']),
            subtitle=html.escape(strings['subtitle']),
            target_block=target_block,
            drag=html.escape(strings['drag']),
            copy_label=html.escape(strings['copy_label']),
            userscript_title=html.escape(strings['userscript_title']),
            userscript_intro=html.escape(strings['userscript_intro']),
            userscript_step1=html.escape(strings['userscript_step1']),
            userscript_stores=html.escape(strings['userscript_stores']),
            userscript_store_link=html.escape(strings['userscript_store_link']),
            userscript_step2=html.escape(strings['userscript_step2']),
            userscript_install_note=html.escape(strings['userscript_install_note']),
            userscript_link=html.escape(strings['userscript_link']),
            bookmarklet_title=html.escape(strings['bookmarklet_title']),
            how_firefox=html.escape(strings['how_firefox']),
            how_android=html.escape(strings['how_android']),
            how_ios=html.escape(strings['how_ios']),
            how_desktop=html.escape(strings['how_desktop']),
            how_generic=html.escape(strings['how_generic']),
            paste_label=html.escape(strings['paste_label']),
            send=html.escape(strings['send']),
            status=html.escape(status),
            received_js=json.dumps(strings['received']),
            copied_js=json.dumps(strings['copied']),
            autoclose='true' if autoclose else 'false',
            marklet=html.escape(marklet, quote=True),
            marklet_href=html.escape(marklet, quote=True),
            token=html.escape(state.token, quote=True),
        )

    def _redirect(self, code):

        # The cookie travels in the query of /set, so never answer the request
        # where it was asked: send the browser to a cookie-free page instead,
        # and the secret is gone from the address bar and from history before
        # anything is drawn.
        self.send_response(302)
        self.send_header('Location', '/done?m=' + code)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def _import(self, params):

        state = self.server.state

        supplied = params.get('t', '')

        # compare_digest wants ASCII on both sides, and a malformed token has
        # to look exactly like a wrong one.
        if not supplied.isascii() or not hmac.compare_digest(supplied, state.token):
            self._redirect('token')
            return

        sent = params.get('z', '').strip()
        refused = bool(sent) and not _archive_ok(sent)

        if sent and not refused:
            state.archive = sent
            state.received = True

        blob = params.get('c', '')

        cookies = extract_cookies(blob)

        if not cookies:

            # A bare session id pasted by hand is still a valid answer.
            candidate = blob.strip()

            if re.match(r'^[A-Za-z0-9_\-]{16,}$', candidate):
                cookies = 'PHPSESSID=' + candidate

        if cookies:
            state.value = cookies
            state.received = True

        if state.archive or (cookies and not state.archive_mode):
            self._redirect('ok')
        elif cookies or refused:
            # A gated download is answered by an archive and nothing else, so
            # say the captcha did not take rather than claim a success.
            self._redirect('nocaptcha')
        else:
            self._redirect('nocookie')

    def _userscript(self):

        # Served with the listener's own address and the profile token baked
        # in, so there is nothing to configure: the manager that picks up the
        # .user.js link offers it for install as-is.
        state = self.server.state
        host = self.headers.get('Host') or '127.0.0.1'
        script = USERSCRIPT.safe_substitute(
            u='http://' + host + '/set?t=' + state.token,
        )

        self._send(script, content_type='text/javascript; charset=utf-8')

    def _done(self, params):

        key, ok = DONE_STATES.get(params.get('m', ''), DONE_STATES['token'])

        self._send(self._page(self.server.strings[key], ok=ok, autoclose=ok))

    def do_GET(self):

        path = urlparse(self.path).path

        if path == '/status':

            # The page confirms on 'done', not on raw arrival: in a download
            # hand-off a cookie is not the answer it is waiting for.
            self._send(
                json.dumps({'received': self.server.state.done}),
                content_type='application/json'
            )
        elif path == '/set':
            self._import(self._params())
        elif path == '/done':
            self._done(self._params())
        elif path in ('/', '/index.html'):
            self._send(self._page())
        elif path == '/kodi.user.js':
            self._userscript()
        elif path == '/favicon.ico':
            self._send('', status=204)
        else:
            self.send_error(404)

    def do_POST(self):

        if urlparse(self.path).path == '/set':
            self._import(self._params())
        else:
            self.send_error(404)


class _Server(ThreadingHTTPServer):

    # Daemon request threads: a half-open connection must never keep the
    # interpreter alive at shutdown. block_on_close stays off for the same
    # reason - joining the request threads could stall on a browser that is
    # still holding a socket open.
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = True

    def __init__(self, address, handler_class, state):

        ThreadingHTTPServer.__init__(self, address, handler_class)

        self.state = state
        self.strings = {}


def _strings(archive_mode=False):

    '''
    Every string the page and the waiting dialog need, per job.

    The cookie import and the download hand-off share the page, the bookmarklet
    and the address line; they differ in what they promise the user and in what
    they wait for, so only the wording changes here.
    '''

    strings = {
        'drag': lang(30339),
        'paste_label': lang(30341),
        'send': lang(30342),
        'received': lang(30344),
        'no_cookie': lang(30345),
        'bad_token': lang(30346),
        'no_captcha': lang(30355),
        'line1': lang(30331),
        # The dialog's own wording, the same whichever job it is doing.
        'scan': lang(30363),
        'open_button': lang(30361),
        'cancel_button': lang(30362),
        'received_note': lang(30364),
        # Saving the bookmarklet, and how to do it in the browser that is
        # reading the page - the page picks one of these by user agent.
        'copy_label': lang(30365),
        'copied': lang(30366),
        'userscript_title': lang(30374),
        'userscript_intro': lang(30375),
        'userscript_step1': lang(30376),
        'userscript_stores': lang(30377),
        'userscript_store_link': lang(30381),
        'userscript_step2': lang(30378),
        'userscript_install_note': lang(30379),
        'userscript_link': lang(30380),
        'bookmarklet_title': lang(30382),
        'how_firefox': lang(30367),
        'how_android': lang(30368),
        'how_ios': lang(30369),
        'how_desktop': lang(30370),
        'how_generic': lang(30371),
    }

    if archive_mode:

        strings.update({
            'heading': lang(30356),
            'title': lang(30356),
            'subtitle': lang(30360),
            'target_label': lang(30354),
            'step2': lang(30357),
            'waiting': lang(30357),
            'line2': lang(30357),
            'line3': lang(30358),
            'line3_min': lang(30373),
        })

    else:

        strings.update({
            'heading': lang(30330),
            'title': lang(30335),
            'subtitle': lang(30336),
            'target_label': '',
            'step2': lang(30338),
            'waiting': lang(30343),
            'line2': lang(30332),
            'line3': lang(30333),
            'line3_min': lang(30372),
        })

    return strings


def pinned_port():

    '''The port the user fixed in settings, or 0 for an automatic one.

    Ships fixed at 50190: a fresh install gets a permanent address, and only a
    deliberately cleared field falls back to a free port.
    '''

    value = addon().getSetting(SETTING_PORT).strip()

    if value.isdigit() and 0 < int(value) < 65536:
        return int(value)

    return 0


def capture_token():

    '''
    The bookmarklet's secret, minted once and then reused.

    It has to outlive a single run: a bookmarklet saved under a fixed port
    would otherwise carry a stale secret and be refused on its next use. Kept
    in a setting, it makes the import link permanent *and* unguessable, so a
    fixed address does not have to be an open one. Clearing the setting mints
    a new token and invalidates every bookmarklet handed out so far.
    '''

    current = addon().getSetting(SETTING_TOKEN).strip().lower()

    if re.match(r'^[0-9a-f]{16,64}$', current):
        return current

    token = os.urandom(TOKEN_BYTES).hex()

    addon().setSetting(SETTING_TOKEN, token)

    return token


def _serve(target='', archive_mode=False):

    '''
    Binds the listener, puts the address on screen, waits for one hand-over.

    Returns the state it ended with, or None when no address could be served at
    all. Every exit path releases the port, because a socket left listening
    would keep Kodi from closing.
    '''

    addresses = lan_addresses()

    state = _State(capture_token(), target, archive_mode)
    strings = _strings(archive_mode)
    wanted = pinned_port()
    pinned = False
    server = None

    if wanted:
        try:
            server = _Server(('0.0.0.0', wanted), _Handler, state)
            pinned = True
        except OSError:
            # Taken by something else: fall through to a free port and say so,
            # because the saved bookmarklet will not be the right one.
            server = None

    if server is None:
        try:
            server = _Server(('0.0.0.0', 0), _Handler, state)
        except Exception as error:
            xbmcgui.Dialog().ok(strings['heading'], lang(30348) + '[CR]' + str(error))
            return None

    server.strings = strings

    port = server.server_address[1]

    if addresses:
        shown = 'http://{0}:{1}/'.format(addresses[0], port)
    else:
        shown = lang(30347)

    if wanted and not pinned:
        xbmcgui.Dialog().notification(
            strings['heading'], lang(30351) % (wanted, port), time=5000, sound=False
        )

    worker = threading.Thread(
        target=server.serve_forever, kwargs={'poll_interval': TICK},
        daemon=True, name='SubtitlesGr-capture'
    )
    worker.start()

    monitor = xbmc.Monitor()
    window = _wait_window(strings, shown, state.target)
    progress = None
    deadline = time.time() + TIMEOUT
    beside = None

    try:

        if window is None:

            progress = xbmcgui.DialogProgress()
            progress.create(
                strings['heading'], message_lines(strings['line1'], shown, strings['line2'])
            )

            while not state.done:

                if monitor.abortRequested():
                    break

                if progress.iscanceled():
                    break

                if time.time() >= deadline:
                    state.timed_out = True
                    break

                left = int(deadline - time.time())

                progress.update(
                    int((TIMEOUT - left) * 100 / TIMEOUT),
                    message_lines(strings['line1'], shown, countdown(strings, left))
                )

                xbmc.sleep(int(TICK * 1000))

        else:

            # Modal, and the wait runs beside it. Kodi sends input to the
            # topmost modal window and to nothing else, which is the whole
            # reason this cannot simply be shown and then polled: started from
            # the settings dialog, or during a download, Kodi's own modal
            # dialog is still up, and the buttons here would be dead.
            beside = threading.Thread(
                target=_window_loop,
                args=(window, state, monitor, deadline, strings, shown),
                daemon=True, name='SubtitlesGr-handoff'
            )
            beside.start()

            window.doModal()

        if state.done and not monitor.abortRequested():

            if window is None:
                # Give the page that is already open one polling interval to
                # show the confirmation before the listener goes away.
                xbmc.sleep(2000)

    finally:

        if beside is not None and beside.is_alive():
            beside.join(timeout=10)

        # The window, the port and the worker thread are released whatever
        # happened above: a listener still holding a socket would stop Kodi from
        # exiting, and the code on screen has served its purpose.
        picture = getattr(window, 'qr_path', '')

        if window is not None:

            try:
                window.close()
            except Exception:
                pass

        _discard_image(picture)

        if progress is not None:
            progress.close()

        server.shutdown()
        server.server_close()

    return state


def run():

    '''Settings action: takes the session cookie a browser is holding.'''

    state = _serve()

    if state is None:
        return

    if state.received:

        if state.value:
            addon().setSetting(SETTING, state.value)

        xbmcgui.Dialog().notification(lang(30330), lang(30262), time=4000, sound=False)

    elif state.timed_out:

        xbmcgui.Dialog().notification(lang(30330), lang(30334), time=4000, sound=False)


def capture(target):

    '''
    Download hand-off: returns the archive address the browser produced, or ''.

    Nothing here talks to Subs4Series and nothing is solved on the user's
    behalf. Their browser posts the form it is already holding, with the token
    they ticked, and lands on the archive; this only carries that address back
    so the download can be completed locally.
    '''

    state = _serve(target, True)

    if state is None:
        return ''

    if state.value:
        addon().setSetting(SETTING, state.value)

    if state.archive:
        return state.archive

    if state.timed_out:
        xbmcgui.Dialog().notification(lang(30356), lang(30359), time=4000, sound=False)

    return ''


if __name__ == '__main__':

    run()
