"""
StreamLinkProxy
based on XBMCLocalProxy by
Copyright 2011 Torben Gerkensmeyer

Modified for Livestreamer by your mom 2k15

Modified for StreamLink by jairoxyz 2k18/19

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
MA 02110-1301, USA.
"""

import xbmc
import xbmcgui
import xbmcvfs
import sys
import traceback  # noQA
import os
import errno
import re
import time
import json
import base64
import threading
import socket
import struct
import requests
import six

if six.PY3:
    from urllib.parse import urlparse
    from urllib.parse import urljoin
    from urllib.parse import unquote
    from urllib.parse import quote
    from urllib.parse import quote_plus
    from urllib.parse import parse_qsl
    from urllib.parse import urlencode

    # from typing import List, NamedTuple, Optional, Union

elif six.PY2:
    # Python 2.7
    from urlparse import urlparse
    from urlparse import urljoin
    from urlparse import parse_qsl
    from urlparse import urlencode
    from urllib import quote
    from urllib import quote_plus
    # from .typing2 import List, NamedTuple, Optional, Union

if six.PY3:
    from http.server import BaseHTTPRequestHandler
    from http.server import HTTPServer
elif six.PY2:
    # Python 2.7
    from BaseHTTPServer import BaseHTTPRequestHandler
    from BaseHTTPServer import HTTPServer

if six.PY3:
    from socketserver import ThreadingMixIn
elif six.PY2:
    # Python 2.7
    from SocketServer import ThreadingMixIn

import ssl
from urllib3.poolmanager import PoolManager
from requests.adapters import HTTPAdapter


# HTTPServer errors
ACCEPTABLE_ERRNO = (
    errno.ECONNABORTED,
    errno.ECONNRESET,
    errno.EINVAL,
    errno.EPIPE,
)
try:
    ACCEPTABLE_ERRNO += (errno.WSAECONNABORTED,)
except AttributeError:
    pass  # Not windows


# aes stuff - custom crypto implementation
_dec = False
_crypto = 'None'

try:
    import Cryptodome
    sys.modules['Crypto'] = Cryptodome
    from Cryptodome.Cipher import AES
    _dec = True
    _crypto = 'pyCryptodome'
except ImportError:
    try:
        from Crypto.Cipher import AES
        _dec = True
        _crypto = 'pyCrypto'
    except ImportError:
        xbmc.log('[StreamLink_Proxy] no Crypto lib found. Encrypted streams won\'t play')
        _dec = False


# streamlink imports
from streamlink import Streamlink
from streamlink.stream import hls, HLSStream, HTTPStream
from streamlink.exceptions import StreamError, PluginError, NoPluginError
from streamlink.plugin.api import useragents
from streamlink.utils import LazyFormatter
# from streamlink.stream.hls_playlist import Key, M3U8, Map, Segment


# TLS 1.2 adapter for older nginx behind CF
class TLS12HttpAdapter(HTTPAdapter):
    """"Transport adapter that forces the use of TLS v1.2."""
    def init_poolmanager(self, connections, maxsize, block=False):
        tls = ssl.PROTOCOL_TLSv1_2 if six.PY3 else ssl.PROTOCOL_TLSv1
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize,
            block=block, ssl_version=tls)


# SLProxy SL method implementations #
#####################################

# Sequence class used in type declarations, throws error in Py2
# class Sequence(NamedTuple):
#     num = None  # type: int
#     segment = None  # type: Segment

# !!! TODO: https://mypy.readthedocs.io/en/stable/cheat_sheet.html !!! #
########################################################################

# num to IV
def num_to_iv(n):
    return struct.pack(">8xq", n)


# override SL decryptor function
def create_decryptor(self, key, sequence):
    # ##### type: (hls.HLSStreamWriter, Key, int) -> AES
    if key.method != "AES-128":
        raise StreamError("Unable to decrypt cipher {0}", key.method)

    if not self.key_uri_override and not key.uri:
        raise StreamError("Missing URI to decryption key")

    if self.key_uri_override:
        p = urlparse(key.uri)
        key_uri = LazyFormatter.format(
            self.key_uri_override,
            url=key.uri,
            scheme=p.scheme,
            netloc=p.netloc,
            path=p.path,
            query=p.query,
        )
    else:
        key_uri = key.uri

    if self.key_uri != key_uri:
        # zoom_key = self.reader.stream.session.options.get("zoom-key")
        # zuom_key = self.reader.stream.session.options.get("zuom-key")
        ply_key = self.reader.stream.session.options.get("ply-key")
        livecam_key = self.reader.stream.session.options.get("livecam-key")
        saw_key = self.reader.stream.session.options.get("saw-key")
        your_key = self.reader.stream.session.options.get("your-key")
        mama_key = self.reader.stream.session.options.get("mama-key")
        tele_key = self.reader.stream.session.options.get("tele-key")
        tinyurl_key = self.reader.stream.session.options.get("tinyurl-key")
        sports24_key = self.reader.stream.session.options.get("sports24-key")
        flowcable_key = self.reader.stream.session.options.get("flowcable-key")
        # custom_uri = self.reader.stream.session.options.get("custom-uri")

        # if zoom_key:
        #     zoom_key = zoom_key.encode() if six.PY3 else zoom_key
        #     _tmp = (base64.urlsafe_b64encode(zoom_key + base64.urlsafe_b64encode(key_uri.encode() if six.PY3 else key_uri)))
        #     _tmp = _tmp.decode() if six.PY3 else _tmp
        #     uri = 'http://www.zoomtv.me/k.php?q=' + _tmp
        # elif zuom_key:
        #     zuom_key = zuom_key.encode() if six.PY3 else zuom_key
        #     _tmp = (base64.urlsafe_b64encode(zuom_key + base64.urlsafe_b64encode(key_uri.encode() if six.PY3 else key_uri)))
        #     _tmp = _tmp.decode() if six.PY3 else _tmp
        #     uri = 'http://www.zuom.xyz/k.php?q=' + _tmp
        if ply_key:
            uri = base64.urlsafe_b64decode(ply_key.encode() if six.PY3 else ply_key) + base64.urlsafe_b64encode(key_uri.encode() if six.PY3 else key_uri)
            uri = "https://www.plylive.me" + (uri.decode() if six.PY3 else uri)
        elif livecam_key:
            h = urlparse(unquote(livecam_key)).netloc
            h = h.encode() if six.PY3 else h
            q = urlparse(unquote(livecam_key)).query
            q = q.encode() if six.PY3 else q
            uri = 'https://%s/kaesv2?sqa=' % (h + base64.urlsafe_b64encode(q + base64.b64encode(key_uri.encode() if six.PY3 else key_uri)))
            uri = uri.decode() if six.PY3 else uri
        elif saw_key:
            if 'foxsportsgo' in key_uri:
                _tmp = key_uri.split('/')
                uri = urljoin(saw_key, '/m/fream?p=' + _tmp[-4] + '&k=' + _tmp[-1])
            elif 'nlsk.neulion' in key_uri:
                _tmp = key_uri.split('?')
                uri = urljoin(saw_key, '/m/stream?' + _tmp[-1])
            elif 'nlsk' in key_uri:
                _tmp = key_uri.split('?')
                uri = 'http://bile.level303.club/m/stream?' + _tmp[-1]
            elif 'nhl.com' in key_uri:
                _tmp = key_uri.split('/')
                uri = urljoin(saw_key, '/m/streams?vaa=' + _tmp[-3] + '&va=' + _tmp[-1])
            else:
                uri = key_uri
        elif mama_key:
            if 'nlsk' in key_uri:
                _tmp = key_uri.split('&url=')
                uri = 'http://mamahd.in/nba?url=' + _tmp[-1]
        elif your_key:
            if re.search(r'playback\.svcs\.mlb\.com|mlb-ws-mf\.media\.mlb\.com|mf\.svc\.nhl\.com', key_uri, re.IGNORECASE) is not None:
                try:
                    _ip = your_key.split('?')[1]
                    uri = re.sub(r'playback\.svcs\.mlb\.com|mlb-ws-mf\.media\.mlb\.com|mf\.svc\.nhl\.com', _ip, key_uri, re.IGNORECASE)
                except:
                    pass
            elif 'mlb.com' in key_uri:
                _tmp = key_uri.split('?')
                uri = urljoin(your_key, '/mlb/get_key/' + _tmp[-1])
            elif 'espn3/auth' in key_uri:
                _tmp = key_uri.split('?')
                uri = urljoin(your_key, '/ncaa/get_key/' + _tmp[-1])
            elif 'nhl.com' in key_uri:
                _tmp = key_uri.split('nhl.com/')
                uri = urljoin(your_key, '/nhl/get_key/' + _tmp[-1])
            else:
                uri = key_uri
        elif tele_key:
            if 'nhl.com' in key_uri:
                _tmp = key_uri.split('nhl.com/')
                uri = '%s/%s' % (tele_key, _tmp[-1])
        elif tinyurl_key:
            tiny = requests.get(key_uri, headers=self.session.get_option("http-headers"))
            uri = tiny.url
        elif sports24_key:
            if "cbsi.live.ott.irdeto.com" in key_uri:
                _tmp = base64.b64encode(key_uri.encode() if six.PY3 else key_uri)
                _tmp = _tmp.decode() if six.PY3 else _tmp
                uri = urljoin(sports24_key, 'pp/key.php?id=' + _tmp)
            elif "playback.svcs.plus.espn" in key_uri:
                _tmp = urljoin(sports24_key, "/espn/espnpkey.php?url=")
                uri = key_uri.replace("https://playback.svcs.plus.espn.com/events/", _tmp)
        elif flowcable_key:
            try:
                res = requests.get(key_uri, headers=self.session.get_option("http-headers"), verify=False)
                auth = res.headers["xauth"]
                hdrs = self.session.get_option("http-headers")
                hdrs["Xauth"] = auth
                self.session.set_option("http-headers", hdrs)
            except:
                pass
            uri = key_uri
        else:
            uri = key_uri

        xbmc.log('[StreamLink_Proxy] using key uri %s' % str(uri))

        # get key from key data from key uri
        try:
            res = self.session.http.get(uri, exception=StreamError,
                                        retries=self.retries,
                                        **self.reader.request_params)
        except Exception as rerr:
            # check if nginx behind cloudflare doesn't accept TLS1.3
            if isinstance(rerr.err, requests.exceptions.HTTPError):
                status_code = rerr.err.response.status_code
                try:
                    srv = rerr.err.response.headers.get('Server').lower()
                except:
                    srv = ""
                if status_code > 400 and "cloudflare" in srv:
                    # rtxt = rerr.err.response.text
                    # if "This website is using a security service to protect itself from online attacks" in rtxt:
                    self.session.http.mount("https://", TLS12HttpAdapter())  # force TLS1.2

            res = self.session.http.get(
                uri,
                exception=StreamError,
                retries=self.retries,
                **self.reader.request_params
            )

        res.encoding = "binary/octet-stream"
        self.key_data = res.content[:16]  # strip any potential LF or other extra chars from key data
        self.key_uri = uri

    iv = key.iv or num_to_iv(sequence)

    # Pad IV to 16 bytes if needed
    iv = b"\x00" * (16 - len(iv)) + iv

    return AES.new(self.key_data, AES.MODE_CBC, iv)


# override sequence processing
def process_sequences(self, playlist, sequences):
    # ##### playlist: M3U8, sequences: List[Sequence]) -> None
    first_sequence, last_sequence = sequences[0], sequences[-1]
    # xbmc.log("[StreamLink_Proxy] process_sequences: %s"%len(sequences))
    # xbmc.log("[StreamLink_Proxy] process_sequences: %s"%str(first_sequence))

    if first_sequence.segment.key and first_sequence.segment.key.method != "NONE":
        xbmc.log('[StreamLink_Proxy] Segments in this playlist are encrypted.')

    self.playlist_changed = ([s.num for s in self.playlist_sequences] != [s.num for s in sequences])
    self.playlist_sequences = sequences

    if not self.playlist_changed:
        self.playlist_reload_time = max(self.playlist_reload_time / 2, 1)

    if playlist.is_endlist:
        self.playlist_end = last_sequence.num

    if self.playlist_sequence < 0:
        if self.playlist_end is None and not self.hls_live_restart:
            edge_index = -(min(len(sequences), max(int(self.live_edge), 1)))
            edge_sequence = sequences[edge_index]
            self.playlist_sequence = edge_sequence.num
        else:
            self.playlist_sequence = first_sequence.num


# override fetch for segment uri rewrite
# fetch2 for py2 and SL <= 1.7.2
def fetch2(self, sequence, retries=None):
    if self.closed or not retries:
        return

    try:
        request_params = self.create_request_params(sequence)

        # skip ignored segment names - until 1.7.0
        if six.PY2 and self.ignore_names and self.ignore_names_re.search(sequence.segment.uri):
            xbmc.log("[StreamLink_Proxy] Skipping segment {0}".format(sequence.num))
            return

        urimod = ''
        uri = sequence.segment.uri
        # print('segment-uri ' + uri)
        if self.session.options.get('hls-segment-uri-mod') is not None:
            xbmc.log('[StreamLink_Proxy] Rewriting segment uri ...')
            urimod = self.session.options.get('hls-segment-uri-mod')
            try:
                urimod = base64.b64decode(urimod).decode('utf-8')
                urimod = json.loads(urimod)
            except:
                # traceback.print_exc()
                pass

            if not isinstance(urimod, dict):
                uri = uri + urimod
            elif 'regex' in urimod:
                repl = urimod['repl']
                uri = re.sub(urimod['regex'], repl, uri, 1)

        return self.session.http.get(
            uri,
            stream=(self.stream_data and not sequence.segment.key),
            timeout=self.timeout,
            exception=StreamError,
            retries=self.retries,
            **request_params
        )

    except StreamError as err:
        print("Failed to open segment {0}: {1}", sequence.num, err)
        return


# fetch3 for py3 and SL >= 2.0
def fetch3(self, segment, stream):
    if self.closed or not self.retries:  # pragma: no cover
        return

    request_params = self.create_request_params(segment)

    urimod = ''
    uri = segment.uri
    # print('segment-uri ' + uri)
    if self.session.options.get('hls-segment-uri-mod') is not None:
        xbmc.log('[StreamLink_Proxy] Rewriting segment uri ...')
        urimod = self.session.options.get('hls-segment-uri-mod')
        try:
            urimod = base64.b64decode(urimod).decode('utf-8')
            urimod = json.loads(urimod)
        except:
            # traceback.print_exc()
            pass

        if not isinstance(urimod, dict):
            uri = uri + urimod
        elif 'regex' in urimod:
            repl = urimod['repl']
            uri = re.sub(urimod['regex'], repl, uri, 1)

    return self.session.http.get(
        segment.uri,
        stream=stream,
        timeout=self.timeout,
        exception=StreamError,
        retries=self.retries,
        **request_params
    )


def load_custom_plugins(session):
    # get SL custom plugins dir

    try:
        streamlink_plugins = os.path.join('script.module.streamlink.plugins', 'plugins')
        path_streamlink_service = os.path.join('script.module.slproxy', 'lib', 'dsp')
        kodi_folder = os.path.dirname(os.path.realpath(__file__))
        custom_plugins = kodi_folder.replace(path_streamlink_service, streamlink_plugins)
        custom_plugins_new = xbmc.translatePath('special://home/addons/script.module.streamlink-plugins/lib/data/').encode('utf-8') \
            if six.PY2 else xbmcvfs.translatePath('special://home/addons/script.module.streamlink-plugins/lib/data/')
    except:
        # traceback.print_exc()
        pass

    try:
        session.load_plugins(custom_plugins)
        session.load_plugins(custom_plugins_new)
    except:
        # traceback.print_exc()
        pass


class MyHandler(BaseHTTPRequestHandler):
    handlerStop = threading.Event()
    handlerStop.clear()

    def log_message(self, format, *args):
        pass

    """
    Serves a HEAD request
    """
    def do_HEAD(self):
        self.answer_request(0)

    """
    Serves a GET request.
    """
    def do_GET(self):
        self.answer_request(1)

    def answer_request(self, sendData):
        try:
            request_path = self.path[1:]
            parsed_path = urlparse(self.path)
            path = parsed_path.path[1:]

            try:
                params = dict(parse_qsl(parsed_path.query))
            except:
                self.send_response(404)
                self.end_headers()
                self.wfile.write('URL malformed or stream not found!')
                return

            if request_path == "version":
                self.send_response(200)
                self.end_headers()
                self.wfile.write("StreamLink Proxy: Running\r\n")
                self.wfile.write("Version: 0.1.1\r\n")

            elif path == "streamlink/":
                fURL = params.get('url')
                # fURL = unquote(fURL)
                q = params.get('q', None)
                p = params.get('p', None)
                if not q:
                    q = 'best'
                # print('fURL, q, p ', fURL,q,p)
                self.serveFile(fURL, q, p, sendData)

            elif path == "vodrewrite/":
                pUrl = params.get('url')
                pUrl = unquote(pUrl)
                try:
                    pUrl = re.findall(r'(http.*$)', pUrl)[0]
                except:
                    pass
                m3u8mod = params.get('m3u8mod', None)
                m3u8mod = unquote(m3u8mod)
                self.rewriteVOD(pUrl, m3u8mod)

            elif path == "wtvrestream/":
                fURL = params.get('url')
                q = params.get('q', '720')
                q = re.search(r'(\d+)', q).group(1)
                hdrs = params.get('hdrs', None)
                try:
                    hdrs = base64.b64decode(hdrs.encode("Utf-8")).decode("Utf-8")
                except:
                    pass
                # print('fURL  ', fURL)
                # print('Quality  ', repr(q))
                self.restreamWTV(fURL, q, hdrs)

            else:
                self.send_response(404)
                self.end_headers()
        except:
            # traceback.print_exc()
            self.send_response(500)
            self.end_headers()
        finally:
            return

    """
    Sends the requested file and add additional headers.
    """
    def serveFile(self, fURL, quality, proxy, sendData):

        session = Streamlink()
        load_custom_plugins(session)

        if _dec:
            xbmc.log('[StreamLink_Proxy] using %s encryption library' % _crypto)
            hls.HLSStreamWriter.create_decryptor = create_decryptor
            hls.HLSStreamWorker.process_sequences = process_sequences

        if '|' in fURL:
            sp = fURL.split('|')
            fURL = sp[0]
            headers = quote_plus(sp[1]).replace('%3D', '=').replace('%26', '&') if ' ' in sp[1] else sp[1]
            headers = dict(parse_qsl(headers))

            # session.set_option("http-ssl-verify", False)
            # session.set_option("hls-segment-threads", 1)
            # session.set_option("hls-segment-timeout", 10)

            try:
                if 'Referer' in headers:
                    # if 'zoomtv' in headers['Referer']:
                    #     session.set_option("zoom-key", headers['Referer'].split('?')[1])
                    # elif 'zuom' in headers['Referer']:
                    #     session.set_option("zuom-key", headers['Referer'].split('?')[1])
                    if (
                        ('livecamtv' in headers['Referer']
                         or 'realtimetv' in headers['Referer']
                         or 'seelive.me' in headers['Referer'])
                        and ('vw%253D' in headers['Referer']
                             or 'vw=' in headers['Referer'])
                    ):
                        session.set_option("livecam-key", headers['Referer'])
                        headers.pop('Referer')
                    elif 'sawlive' in headers['Referer']:
                        session.set_option("saw-key", headers['Referer'])
                    elif 'yoursportsinhd' in headers['Referer']:
                        session.set_option("your-key", headers['Referer'])
                        headers.pop('Referer')
                    elif 'mamahd' in headers['Referer']:
                        session.set_option("mama-key", headers['Referer'].split('&')[1])
                    elif '@@@zoomtv' in headers['Referer']:
                        _r, _k, _s, _a, _z = headers['Referer'].split('@@@')
                        session.set_option("zoomtv-ksrv", _k)
                        session.set_option("zoomtv-stream", _s)
                        session.set_option("zoomtv-auth", _a)
                        headers['Referer'] = _r
                    elif 'tvply.me' in headers['Referer'] or 'plylive.me' in headers['Referer'] and '@@@' in headers['Referer']:
                        session.set_option("ply-key", headers['Referer'].split('@@@')[1])
                        headers['Referer'] = headers['Referer'].split('@@@')[0]
                        headers['Cookie'] = '_pshflg=~; tamedy=2'
                        headers['Origin'] = 'https://www.plylive.me'
                    elif 'julinewr.xyz' in headers['Referer'] or 'lowend.xyz' in headers['Referer']:
                        session.set_option("tele-key", headers['Referer'].split('@@@')[1])
                        headers['Referer'] = headers['Referer'].split('@@@')[0]
                    elif 'wmsxx.com' in headers['Referer'] or 'eplayer.to' in headers['Referer']:
                        session.set_option("tinyurl-key", True)
                        session.set_option("http-ssl-verify", False)
                    elif 'sports24' in headers['Referer']:
                        session.set_option("sports24-key", headers['Referer'])
                    elif 'flowcablevision' in headers['Referer']:
                        session.set_option("http-ssl-verify", False)
                        session.set_option("flowcable-key", True)

                if 'CustomKeyUri' in headers:
                    session.set_option("hls-segment-key-uri", unquote(headers['CustomKeyUri']))
                    headers.pop('CustomKeyUri')
                if 'CustomSegmentUri' in headers:
                    if six.PY2:
                        hls.HLSStreamWriter.fetch = fetch2  # for rewriting segment uris
                    elif six.PY3:
                        hls.HLSStreamWriter._fetch = fetch3

                    session.set_option("hls-segment-uri-mod", unquote(headers['CustomSegmentUri']))
                    headers.pop('CustomSegmentUri')

            except:
                # traceback.print_exc()
                pass

            session.set_option("http-headers", headers)
        else:
            # session.set_option('http-headers', {"User-Agent": useragents.CHROME})
            session.set_option('http-headers', {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"})

        if proxy and len(proxy) > 0 and 'http' in proxy:
            if 'https' in proxy:
                session.set_option('https-proxy', proxy)
            else:
                session.set_option('http-proxy', proxy)
            xbmc.log('[StreamLink_Proxy] using http-proxy: {0}'.format(proxy))

        xbmc.log('[StreamLink_Proxy] http-headers added: %s' % str(session.get_option("http-headers")))

        try:
            # handle zoomtv redirects
            if session.options.get("zoomtv-auth") is not None:
                res_ = session.http.get(fURL.replace("hls://", ""), allow_redirects=False)
                if res_.status_code in (302, 303):
                    fURL = "hls://" + urljoin(res_.url, res_.headers["Location"])

            # xbmc.log('[StreamLink_Proxy] %s'%fURL)
            plugin = session.resolve_url(fURL)
            xbmc.log('[StreamLink_Proxy] Found matching plugin %s for URL %s' % (plugin.module, fURL))
            # streams = session.streams(fURL)
            streams = plugin.streams()

        except NoPluginError:
            xbmc.log('[StreamLink_Proxy] Error: no plugin found to handle this stream.')
            self.send_response(404)
            self.end_headers()
            return

        except PluginError as err:
            xbmc.log('[StreamLink_Proxy] a plugin error occured: %s' % str(err))
            self.send_response(500)
            self.end_headers()
            return

        except Exception as err:
            # traceback.print_exc(file=sys.stdout)
            xbmc.log('[StreamLink_Proxy] an error occured: %s' % str(err))
            self.send_response(500)
            self.end_headers()
            return

        if not streams:
            xbmc.log('[StreamLink_Proxy] Error: no playable streams found on this URL: %s' % fURL)
            self.send_response(404)
            self.end_headers()
            return

        if (sendData):

            if not streams.get(quality, None):
                quality = "best"

            try:
                with streams[quality].open() as stream:
                    # xbmc.log('[StreamLink_Proxy] Playing stream %s with quality \'%s\''%(streams[quality],quality))
                    isHLS = (isinstance(streams[quality], HLSStream))
                    isHTTP = (isinstance(streams[quality], HTTPStream))
                    cache = 100 * 1024
                    self.send_response(200)
                    self.send_header('Content-Type', 'video/mp2t' if isHLS or isHTTP else 'video/unknown')
                    # self.send_header('Content-Range', 'bytes 0-%s/*'%str(cache))
                    self.end_headers()

                    # init zoomtv auth refresh
                    zoomtv_auth = None
                    tdelta = None
                    try:
                        zoomtv_ksrv = stream.session.options.get("zoomtv-ksrv").replace("ksrv=", "")
                        zoomtv_stream = stream.session.options.get("zoomtv-stream").replace("stream=", "")
                        zoomtv_auth = stream.session.options.get("zoomtv-auth").replace("auth=", "")
                        zoomtv_auth = six.ensure_str(base64.b64decode(zoomtv_auth))
                        zoomtv_auth = json.loads(zoomtv_auth)
                        tdelta = (int(zoomtv_auth["ts"]) - int(time.time())) / 2
                    except:
                        pass

                    # t0 = time.time()
                    buf = 'INIT'
                    while buf and (len(buf) > 0 and not self.handlerStop.isSet()):
                        # print('buf ' + repr(buf[:200]))
                        buf = stream.read(cache)

                        # delete fake PNG header and img in hls
                        if isHLS and buf[:8] == b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A':
                            off = re.search(b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A.*?\x47', buf)  # 0x47 (G) is ts header sync byte
                            if off:
                                off = off.end() - 1
                            else:
                                off = 8
                            buf = buf[off:]

                        # call zoomtv auth page before expire ts
                        if zoomtv_auth is not None and tdelta is not None:
                            if time.time() >= int(zoomtv_auth["ts"]) - tdelta:
                                try:
                                    zoomtv_securl = "{}/?stream={}&scode={}&expires={}".format(zoomtv_ksrv, zoomtv_stream, zoomtv_auth['scode'], zoomtv_auth['ts'])
                                    xbmc.log('[StreamLink_Proxy] calling ZoomTV auth page: %s' % str(zoomtv_securl))
                                    # session is closed after with block
                                    with requests.Session() as ses:
                                        ses.mount("https://", TLS12HttpAdapter())
                                        ses.headers = stream.session.get_option("http-headers")
                                        # ses.verify = False
                                        zoomtv_auth = ses.get(zoomtv_securl).json()

                                except:
                                    traceback.print_exc(file=sys.stdout)
                                    pass

                        # print(repr(buf[:13]))
                        if not buf:
                            xbmc.log("[StreamLink_Proxy] Error: no data returned from stream!")
                            break

                        self.wfile.write(buf)

                    # self.wfile.close()
                    # self.handlerStop.set()

            except socket.error as e:
                if isinstance(e.args, tuple):
                    if e.errno == errno.EPIPE:
                        # remote peer disconnected
                        xbmc.log('[StreamLink_Proxy] detected remote disconnect!')
                    else:
                        xbmc.log('[StreamLink_Proxy] socket error %s' % str(e))
                else:
                    xbmc.log('[StreamLink_Proxy] socket error %s' % str(e))

            except Exception as err:
                # traceback.print_exc(file=sys.stdout)
                xbmc.log('[StreamLink_Proxy] could not open stream: {0}'.format(err))
                self.handlerStop.set()

            try:
                stream.close()
            except:
                pass
            stream = None

    def rewriteVOD(self, pUrl, m3u8mod):
        try:
            if '|' in pUrl:
                sp = pUrl.split('|')
                pUrl = sp[0]
                headers = quote_plus(sp[1]).replace('%3D', '=').replace('%26', '&') if ' ' in sp[1] else sp[1]
                headers = dict(parse_qsl(headers))
            else:
                headers = {"User-Agent": useragents.CHROME}

            r = requests.get(pUrl, headers=headers, verify=False)

            try:
                cl = r.headers['content-length']
            except:
                cl = str(len(r.content))

            try:
                ct = r.headers['content-type']
            except:
                ct = 'application/vnd.apple.mpegurl'
            m3u8 = r.text

            try:
                m3u8mod = base64.b64decode(m3u8mod).decode('utf-8')
                m3u8mod = json.loads(m3u8mod)
            except:
                # traceback.print_exc()
                m3u8mod = None

            if 'regex' in m3u8mod:
                repl = m3u8mod['repl']
                regex = m3u8mod['regex']
                m3u8 = re.sub(regex, repl, m3u8, 0)
                m3u8 = m3u8.encode('utf-8') if six.PY2 else m3u8

            self.send_response(200)
            self.send_header('Content-type', ct)  # m3u8
            self.send_header("Content-Length", cl)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(m3u8)
            # self.wfile.close()

        except socket.error as err:
            xbmc.log('[StreamLink_Proxy] Socket Error: {0}'.format(err))
            pass

        except Exception as err:
            # traceback.print_exc()
            self.handlerStop.set()
            xbmc.log('[StreamLink_Proxy] could not rewrite or open playlist: {0}'.format(err))

    def restreamWTV(self, link, quality, headers):
        try:
            prx = 'http://%s:%s/wtvrestream/?url=' % (SLProxy.HOST_NAME, SLProxy.PORT_NUMBER)
            scode = 0
            s = requests.Session()
            # s = Streamlink().http

            if headers is None:
                headers = {"User-Agent": useragents.CHROME}
            else:
                try:
                    headers__ = {}
                    headers_ = headers.split("&")
                    for header_ in headers_:
                        headers__.update({header_.split("=")[0].strip(): header_.split("=")[1].strip()})
                    headers = headers__
                except:
                    pass

            isTS = False
            isTS = re.search(r'^.*\.ts.*$', link) or re.search(r'^.*\.mp4a.*$', link) or re.search(r'^.*\.aac.*$', link)

            r = s.get(
                link,
                stream=isTS,
                headers=headers,
                allow_redirects=True
            )
            scode = r.status_code

            # print("[VODPROXY]    " + repr(headers))
            if scode >= 400:
                self.send_response(scode)
                self.end_headers()
                self.wfile.flush()
            else:
                base = re.findall(r'(^.*\/)', r.url)[0]
                # if ('content-type' in headers and headers['content-type'] == 'application/vnd.apple.mpegurl') or b"#EXT" in r.content:
                if not isTS and '.m3u8' or '/m3u8/' in link:
                    hls7 = r.text

                    # filter resolution and language in master pl
                    if "#EXT-X-STREAM-INF" in hls7:
                        try:
                            hls7 = re.sub(r'#EXT-X-STREAM-INF:.*RESOLUTION=\d+x(?!{0}).*\s+.*'.format(quality), r"", hls7)
                            bw = re.findall(r'BANDWIDTH=(\d+)', hls7)
                            bw.sort(reverse=True, key=lambda x: int(x))
                            bw = bw[0]
                            hls7 = re.sub(r'#EXT-X-STREAM-INF:.*BANDWIDTH=(?!{0}).*\s+.*'.format(bw), r"", hls7)
                            hls7 = re.sub(r'#EXT-X-MEDIA:TYPE=AUDIO.*DEFAULT=NO.*', r"", hls7)
                        except:
                            # traceback.print_exc()
                            pass

                    data = hls7.splitlines()

                    ct = "application/vnd.apple.mpegurl"
                    self.send_response(200)
                    self.send_header("Content-Type", ct)
                    # self.send_header("Content-Length", cl)
                    # self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()

                    hdrs_ = base64.b64encode(urlencode(headers).encode("Utf-8")).decode("Utf-8")
                    lines = ""

                    for line in data:
                        if re.search(r'^#EXT-X-MEDIA.*?URI="(.*?)"', line):
                            uri = re.search(r'^#EXT-X-MEDIA.*?URI="(.*?)"', line).group(1)
                            line = re.sub(r'URI=".*?(".*$)', r'URI="{0}{1}\1'.format(prx, quote(urljoin(base, uri))), line)
                            pass
                        elif re.search(r'(?:#EXTM3U|#EXT-X-|EXTINF)', line):
                            # print(line)
                            pass
                        elif re.search(r'^\w+.*(?:\.m3u8|\.ts|\.aac|\.mp4a)*$', line):
                            line = '{0}{1}'.format(prx, quote(urljoin(base, line)))
                            line += "&hdrs=%s" % hdrs_ if "#EXTINF:" in hls7 else ""
                            pass
                        elif line == '':
                            continue
                        else:
                            pass

                        line += "\n"
                        lines += line

                    self.wfile.write(lines.encode() if six.PY3 else lines)
                    self.wfile.flush()

                elif isTS:
                    if re.search(r'^https?://.*\.ts', link):
                        ct = 'video/mp2t'
                    elif re.search(r'^https?://.*\.aac', link):
                        ct = 'audio/aac'
                    elif re.search(r'^https?://.*\.mp4a', link):
                        ct = 'audio/mp4'
                    headers = {header.lower(): r.headers[header] for header in r.headers}
                    self.send_response(200)
                    self.send_header('Content-Type', ct)
                    try:
                        self.send_header("Content-Length", headers['content-length'])
                    except:
                        pass

                    self.end_headers()
                    # print("[SLPROXY TS]    " + repr(link))
                    # rmhead = 1

                    # for chunk in r.iter_content(chunk_size=1000000):
                    #    print("[SLPROXY]    " + repr(chunk[:50]))
                    #     if rmhead == 1:
                    #    self.wfile.write(chunk.lstrip(b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'))
                    #         rmhead = 0
                    #     else:
                    for line in r.iter_lines():
                        self.wfile.write(line)
                        self.wfile.flush()

        except socket.error:
            pass

        except Exception as err:
            # traceback.print_exc()
            self.handlerStop.set()
            xbmc.log('[SLProxy] could not open playlist: {0}'.format(err))

        pass


class Server(HTTPServer):
    """HTTPServer class with timeout."""
    timeout = 5

    def finish_request(self, request, client_address):
        """Finish one request by instantiating RequestHandlerClass."""
        try:
            self.RequestHandlerClass(request, client_address, self)
        except socket.error as err:
            if err.errno not in ACCEPTABLE_ERRNO:
                raise


class ThreadedHTTPServer(ThreadingMixIn, Server):
    """Handle requests in a separate thread."""
    allow_reuse_address = True
    daemon_threads = True


class SLProxy():
    HOST_NAME = '127.0.0.1'
    PORT_NUMBER = 45678
    ready = threading.Event()

    def start(self, stopEvent):
        self.ready.clear()
        sys.stderr = sys.stdout
        server_class = ThreadedHTTPServer
        MyHandler.handlerStop = stopEvent
        httpd = server_class((self.HOST_NAME, self.PORT_NUMBER), MyHandler)
        xbmc.log("[StreamLink_Proxy] Service started - %s:%s." % (self.HOST_NAME, self.PORT_NUMBER))

        while(True and not stopEvent.isSet()):  # and not xbmc.abortRequested
            httpd.handle_request()
            self.ready.set()

        httpd.server_close()
        self.ready.clear()
        xbmc.log('[StreamLink_Proxy] Service stopped.')

    def stop(self):
        pass

    def status(self):
        pass


class SLProxy_Helper():

    def getKodiVersion(self):
        return xbmc.getInfoLabel("System.BuildVersion").split(".")[0]

    def startProxy(self):
        pass

    def playSLink(self, url, listitem):
        # print('SLurl {0}'.format(url))
        stopPlaying = threading.Event()
        stopPlaying.clear()
        progress = xbmcgui.DialogProgress()
        progress.create('Starting StreamLink Proxy')
        progress.update(10, 'Loading StreamLink Proxy')

        sl_Proxy = SLProxy()
        url = url.replace('slplugin://', '')  # plugin flag from SD
        if 'm3u8mod=' in url:
            action = 'vodrewrite'
        # elif 'streams.wilmaa.com' in url: # todo: update for yallo
        #     action = 'wtvrestream'
        else:
            action = 'streamlink'
        # action = 'vodrewrite' if 'm3u8mod=' in url else 'streamlink'
        url_to_play = 'http://%s:%s/%s/?url=%s' % (sl_Proxy.HOST_NAME, sl_Proxy.PORT_NUMBER, action, url)
        threading.Thread(target=sl_Proxy.start, args=(stopPlaying,)).start()
        proxyReady = sl_Proxy.ready

        progress.update(20)
        xbmc.sleep(200)
        p = 30
        while True and p < 100:
            if proxyReady.isSet():
                progress.update(90)
                break
            progress.update(p)
            xbmc.sleep(200)
            p += 10

        mplayer = MyPlayer()
        mplayer.stopPlaying = stopPlaying
        mplayer.play(url_to_play, listitem)
        progress.update(100)
        progress.close()
        played = False

        while True:
            if stopPlaying.isSet():
                break
            if xbmc.Player().isPlaying():
                played = True
            xbmc.log('[StreamLink_Proxy] idle running ...')
            xbmc.sleep(5000)

        return played

    def resolve_url(self, url):
        xbmc.log('[StreamLink_Proxy] trying to resolve url ...')
        session = Streamlink()
        # get custom plugins
        load_custom_plugins(session)

        try:
            params = dict(parse_qsl('url=%s' % url))
            fURL = params.get('url')
            fURL = unquote(fURL)
            q = params.get('q', False) or 'pick'
            proxy = params.get('p', None)

            if '|' in fURL:
                sp = fURL.split('|')
                fURL = sp[0]
                headers = dict(parse_qsl(sp[1]))
                session.set_option("http-headers", headers)

            if proxy and len(proxy) > 0 and 'http' in proxy:
                if 'https' in proxy:
                    session.set_option('https-proxy', proxy)
                else:
                    session.set_option('http-proxy', proxy)
                xbmc.log('[StreamLink_Proxy] using http-proxy: {0}'.format(proxy))

            plugin = session.resolve_url(fURL)
            session.set_plugin_option("rtve", "mux-subtitles", True)
            streams = plugin.streams()
            # print streams
            if "streams.wilmaa.com" in fURL:
                ql = [q for q in streams.keys() if re.search(r'^[\d]{3}p$', q)]
                q = xbmcgui.Dialog().select('Choose the stream quality', ql)
                if q == -1:
                    return None
                else:
                    q = ql[q]

                uri = quote(fURL) + '&q={0}'.format(q)
                return uri
            else:
                if len(streams) > 2 and q == 'pick':
                    q = xbmcgui.Dialog().select('Choose the stream quality', [q for q in streams.keys()])
                    if q == -1:
                        return None
                    else:
                        q = list(streams.keys())[q]
                elif q == 'pick':
                    q = 'best'

                stream = streams.get(q, False) or streams.get('best')
                return stream.url

        except Exception as err:
            # traceback.print_exc(file=sys.stdout)
            xbmc.log('[StreamLink_Proxy] resolve error: {0}'.format(err))
            return None


class MyPlayer (xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)

    def play(self, url, listitem):
        # print 'Now im playing... %s' % url
        self.stopPlaying.clear()
        xbmc.Player().play(url, listitem)

    def onPlayBackEnded(self):
        # Will be called when xbmc stops playing a file
        # print "seting event in onPlayBackEnded "
        self.stopPlaying.set()
        # print "stop Event is SET"

    def onPlayBackStopped(self):
        # Will be called when user stops xbmc playing a file
        # print "seting event in onPlayBackStopped "
        self.stopPlaying.set()
        # print "stop Event is SET"

    def onPlayBackError(self):
        self.stopPlaying.set()

    def onPlayBackStarted(self):
        # xbmc.executebuiltin("Dialog.Close(busydialog)")
        pass
