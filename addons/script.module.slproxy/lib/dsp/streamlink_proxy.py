"""
StreamLinkProxy
based on XBMCLocalPorxy by
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

import xbmc, xbmcgui

import sys, traceback, os, errno, re, time, json
import base64
import threading
import socket
import struct
import requests
import six

if six.PY3:
    import urllib.parse as urlparse
    import urllib.parse as urllib
    from urllib.parse import urljoin
elif six.PY2:
    # Python 2.7
    import urlparse, urllib
    from urlparse import urljoin

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






#HTTPServer errors
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


##aes stuff - custom crypto implementation
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



def num_to_iv(n):
    return struct.pack(">8xq", n)

## streamlink imports
from streamlink import Streamlink
from streamlink.stream import hls, HLSStream
from streamlink.exceptions import StreamError, PluginError, NoPluginError
from streamlink.plugin.api import useragents
from streamlink.utils import LazyFormatter


## override SL decryptor functions
def create_decryptor(self, key, sequence):
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
        zoom_key = self.reader.stream.session.options.get("zoom-key")
        zuom_key = self.reader.stream.session.options.get("zuom-key")
        livecam_key = self.reader.stream.session.options.get("livecam-key")
        saw_key = self.reader.stream.session.options.get("saw-key")
        your_key = self.reader.stream.session.options.get("your-key")
        mama_key = self.reader.stream.session.options.get("mama-key")
        tele_key = self.reader.stream.session.options.get("tele-key")
        #custom_uri = self.reader.stream.session.options.get("custom-uri")

        if zoom_key:
            uri = 'http://www.zoomtv.me/k.php?q=' + (base64.urlsafe_b64encode(zoom_key.encode()+base64.urlsafe_b64encode(key_uri.encode()))).decode()
        elif zuom_key:
            uri = 'http://www.zuom.xyz/k.php?q=' + (base64.urlsafe_b64encode(zoom_key.encode()+base64.urlsafe_b64encode(key_uri.encode()))).decode()
        elif livecam_key:           
            h = urlparse.urlparse(urllib.unquote(livecam_key)).netloc
            q = urlparse.urlparse(urllib.unquote(livecam_key)).query          
            uri = 'https://%s/kaesv2?sqa='%(h.encode()+base64.urlsafe_b64encode(q.encode()+base64.b64encode(key_uri.encode()))).decode()
        elif saw_key:
            if 'foxsportsgo' in key_uri:
                _tmp = key_uri.split('/')
                uri = urljoin(saw_key,'/m/fream?p='+_tmp[-4]+'&k='+_tmp[-1])
            elif 'nlsk.neulion' in key_uri:
                _tmp = key_uri.split('?')
                uri = urljoin(saw_key,'/m/stream?'+_tmp[-1])
            elif 'nlsk' in key_uri:
                _tmp = key_uri.split('?')
                uri = 'http://bile.level303.club/m/stream?'+_tmp[-1]
            elif 'nhl.com' in key_uri:
                _tmp = key_uri.split('/')
                uri = urljoin(saw_key,'/m/streams?vaa='+_tmp[-3]+'&va='+_tmp[-1])
            else:
                uri = key_uri
        elif mama_key:
           if 'nlsk' in key_uri:
                _tmp = key_uri.split('&url=')
                uri = 'http://mamahd.in/nba?url=' + _tmp[-1]
        elif your_key:
            if re.search(r'playback\.svcs\.mlb\.com|mlb-ws-mf\.media\.mlb\.com|mf\.svc\.nhl\.com', key_uri, re.IGNORECASE) != None:
                try:
                    _ip = your_key.split('?')[1]
                    uri = re.sub(r'playback\.svcs\.mlb\.com|mlb-ws-mf\.media\.mlb\.com|mf\.svc\.nhl\.com', _ip, key_uri, re.IGNORECASE)
                except:
                    pass
            elif 'mlb.com' in key_uri:
                _tmp = key_uri.split('?')
                uri = urljoin(your_key,'/mlb/get_key/'+_tmp[-1])
            elif 'espn3/auth' in key_uri:
                _tmp = key_uri.split('?')
                uri = urljoin(your_key,'/ncaa/get_key/'+_tmp[-1])
            elif 'nhl.com' in key_uri:
                _tmp = key_uri.split('nhl.com/')
                uri = urljoin(your_key, '/nhl/get_key/'+_tmp[-1])            
            else:
                uri = key_uri
        elif tele_key:
             if 'nhl.com' in key_uri:
                _tmp = key_uri.split('nhl.com/')
                uri = '%s/%s'%(tele_key,_tmp[-1])

        #elif custom_uri:            
            #uri = custom_uri

        else:
            uri = key_uri

        #xbmc.log('[StreamLink_Proxy] using key uri %s'%str(uri))

        res = self.session.http.get(uri, exception=StreamError,
                                        retries=self.retries,
                                        **self.reader.request_params)

        res.encoding = "binary/octet-stream"
        self.key_data = res.content
        self.key_uri = key_uri

    iv = key.iv or num_to_iv(sequence)

    # Pad IV if needed
    iv = b"\x00" * (16 - len(iv)) + iv

    return AES.new(self.key_data, AES.MODE_CBC, iv)


def process_sequences(self, playlist, sequences):    
    first_sequence, last_sequence = sequences[0], sequences[-1]
    #xbmc.log("[StreamLink_Proxy] process_sequences: %s"%len(sequences))
    #xbmc.log("[StreamLink_Proxy] process_sequences: %s"%str(first_sequence))

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


#override fetch for segment uri rewrite
def fetch(self, sequence, retries=None):
    if self.closed or not retries:
        return

    try:
        request_params = self.create_request_params(sequence)
        # skip ignored segment names
        if self.ignore_names and self.ignore_names_re.search(sequence.segment.uri):
            print("Skipping segment {0}".format(sequence.num))
            return

        urimod = ''
        uri = sequence.segment.uri
        if self.session.options.get('hls-segment-uri-mod') is not None:
            xbmc.log('[StreamLink_Proxy] Rewriting segment uri ...')
            urimod = self.session.options.get('hls-segment-uri-mod')                        
            try:
                urimod = base64.b64decode(urimod)
                if six.PY3: urimod = urimod.decode()
                urimod = json.loads(urimod)
            except:
                #traceback.print_exc()
                pass

            if not isinstance(urimod, dict):
                uri = uri + urimod
            elif 'regex' in urimod:
                repl = urimod['repl']
                uri = re.sub(urimod['regex'], repl, uri, 1)
                
                
        return self.session.http.get(uri,
                                    stream=(self.stream_data
                                                and not sequence.segment.key),
                                    timeout=self.timeout,
                                    exception=StreamError,
                                    retries=self.retries,
                                    **request_params)

    except StreamError as err:
        print("Failed to open segment {0}: {1}", sequence.num, err)
        return


def load_custom_plugins(session):
    # get SL custom plugins dir
    
    try:
        streamlink_plugins = os.path.join('script.module.streamlink.plugins', 'plugins')
        path_streamlink_service = os.path.join('script.module.slproxy', 'lib', 'dsp')
        kodi_folder = os.path.dirname(os.path.realpath(__file__))
        custom_plugins = kodi_folder.replace(path_streamlink_service, streamlink_plugins)
        custom_plugins_new = xbmc.translatePath('special://home/addons/script.module.streamlink-plugins/lib/data/').encode('utf-8')
    except:
        #traceback.print_exc()
        pass
    
    try:
        session.load_plugins(custom_plugins)
        session.load_plugins(custom_plugins_new)
    except:
        #traceback.print_exc()
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
            request_path =  self.path[1:]
            parsed_path = urlparse.urlparse(self.path)
            path =  parsed_path.path[1:]
            try:
                params = dict(urlparse.parse_qsl(parsed_path.query))
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
                fURL = urllib.unquote(fURL)
                q = params.get('q', None)
                p = params.get('p', None)
                if not q:
                    q = 'best'
                #print('fURL, q, p ', fURL,q,p)  
                self.serveFile(fURL, q, p, sendData)     

            elif path == "vodrewrite/":
                pUrl = params.get('url')                   
                pUrl = urllib.unquote(pUrl)
                try:
                    pUrl = re.findall(r'(http.*$)', pUrl)[0]
                except:
                    pass
                m3u8mod = params.get('m3u8mod', None)
                m3u8mod = urllib.unquote(m3u8mod)
                self.rewriteVOD(pUrl, m3u8mod)

            else:
                self.send_response(404)
                self.end_headers()
        finally:
                return

    """
    Sends the requested file and add additional headers.
    """
    def serveFile(self, fURL, quality, proxy, sendData):
        
        session = Streamlink()
        #session.set_loglevel("debug")
        #session.set_logoutput(sys.stdout)

        load_custom_plugins(session)
        
        if _dec:
            xbmc.log('[StreamLink_Proxy] using %s encryption library'%_crypto) 
            hls.HLSStreamWriter.create_decryptor = create_decryptor
            hls.HLSStreamWorker.process_sequences = process_sequences        
                 

        if '|' in fURL:
            sp = fURL.split('|')
            fURL = sp[0]
            headers = urllib.quote_plus(sp[1]).replace('%3D', '=').replace('%26','&') if ' ' in sp[1] else sp[1]
            headers = dict(urlparse.parse_qsl(headers))
            session.set_option("http-ssl-verify", False)
            session.set_option("hls-segment-threads", 1)
            session.set_option("hls-segment-timeout", 10)

            try:
                if 'Referer' in headers:
                    if 'zoomtv' in headers['Referer']:
                        session.set_option("zoom-key", headers['Referer'].split('?')[1])                    
                    elif 'zuom' in headers['Referer']:
                        session.set_option("zuom-key", headers['Referer'].split('?')[1])
                    elif ('livecamtv' in headers['Referer'] or 'realtimetv' in headers['Referer'] or \
                            'seelive.me' in headers['Referer']) and ('vw%253D' in headers['Referer'] or \
                            'vw=' in headers['Referer']): 
                        session.set_option("livecam-key", headers['Referer'])
                        headers.pop('Referer')               
                    elif 'sawlive' in headers['Referer']:
                        session.set_option("saw-key", headers['Referer'])
                    elif 'yoursportsinhd' in headers['Referer']:
                        session.set_option("your-key", headers['Referer'])
                        headers.pop('Referer')
                    elif 'mamahd' in headers['Referer']:
                        session.set_option("mama-key", headers['Referer'].split('&')[1])
                    elif ('kuntv.pw' in headers['Referer'] or 'plytv.me' in headers['Referer']) and '@@@' in headers['Referer']:
                        session.set_option("kuntv-stream", headers['Referer'].split('@@@')[1])
                        session.set_option("kuntv-auth", headers['Referer'].split('@@@')[2])
                        headers['Referer'] =  headers['Referer'].split('@@@')[0]
                    elif 'julinewr.xyz' in headers['Referer'] or 'lowend.xyz' in headers['Referer']:
                        session.set_option("tele-key", headers['Referer'].split('@@@')[1])
                        headers['Referer'] =  headers['Referer'].split('@@@')[0]

                if 'CustomKeyUri' in headers:
                    session.set_option("hls-segment-key-uri", headers['CustomKeyUri'])
                    headers.pop('CustomKeyUri')
                if 'CustomSegmentUri' in headers:                    
                    hls.HLSStreamWriter.fetch = fetch #for rewriting segment uris
                    session.set_option("hls-segment-uri-mod", headers['CustomSegmentUri'])
                    headers.pop('CustomSegmentUri')
                    
            except:
                #traceback.print_exc()
                pass

            
            session.set_option("http-headers", headers)
            #session.set_option('http-headers', {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36"})
        else:
            session.set_option('http-headers', {"User-Agent": useragents.CHROME})
        
        if proxy and len(proxy)>0 and 'http' in proxy:
            if 'https' in proxy:
                session.set_option('https-proxy', proxy)
            else: session.set_option('http-proxy', proxy)
            xbmc.log('[StreamLink_Proxy] using http-proxy: {0}'.format(proxy))

        xbmc.log('[StreamLink_Proxy] http-headers added: %s'%str(session.get_option("http-headers"))) 

        try:
            #xbmc.log('[StreamLink_Proxy] %s'%fURL)
            plugin = session.resolve_url(fURL)
            xbmc.log('[StreamLink_Proxy] Found matching plugin %s for URL %s'%(plugin.module, fURL))
            #streams = session.streams(fURL)
            streams = plugin.streams()           

        except NoPluginError:
            xbmc.log('[StreamLink_Proxy] no plugin found to handle this stream.')
            self.send_response(404)
            self.end_headers()
            return

        except PluginError as err:
            xbmc.log('[StreamLink_Proxy] a plugin error occured: %s'%str(err))
            self.send_response(500)
            self.end_headers()
            return
            
        except Exception as err:
            #traceback.print_exc(file=sys.stdout)
            xbmc.log('[StreamLink_Proxy] an error occured: %s'%str(err))
            self.send_response(500)
            self.end_headers()
            return

        if not streams:
            xbmc.log('[StreamLink_Proxy] no playable streams found on this URL: %s'%fURL)
            self.send_response(404)
            self.end_headers()
            return
                

        if (sendData):
               
            if not streams.get(quality, None):
                quality = 'best'                
                
            try:
                with streams[quality].open() as stream:
                    #xbmc.log('[StreamLink_Proxy] Playing stream %s with quality \'%s\''%(streams[quality],quality))
                    cache = 8 * 1024
                    self.send_response(200)
                    self.send_header('Content-type', 'video/unknown') #Content-Type: video/mp2t
                    self.end_headers()                     

                    #init zoom/kun tv auth refresh
                    kuntv_auth = None
                    try:
                        kuntv_stream = stream.session.options.get("kuntv-stream")
                        kuntv_auth = stream.session.options.get("kuntv-auth")
                        kuntv_auth = re.findall(r'(\{.*\})', base64.b64decode(kuntv_auth))[0]
                        kuntv_auth = json.loads(kuntv_auth)        
                    except:
                        pass        
                        #traceback.print_exc(file=sys.stdout)

                    t0 = time.time()
                    buf = 'INIT'
                    isHLS = (isinstance(streams[quality], HLSStream))
                    while buf and (len(buf) > 0 and not self.handlerStop.isSet()):
                        #print('buf ' + repr(buf[:20]))
                        buf = stream.read(cache)
                        #cut off fake PNG headers in hls
                        if isHLS and buf[:8] == b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A':
                            buf = buf[8:]
                        elapsed = time.time() - t0
                        #call zoom/kun tv auth page every 2 min
                        if kuntv_auth and elapsed > 120:
                            t0 = time.time()                            
                            try:
                                kuntv_securl = "https://authme.seckeyserv.me/?%s&scode=%s&exts=%s"%(kuntv_stream, kuntv_auth['scode'], kuntv_auth['ts'])
                                kuntv_auth = requests.get(kuntv_securl, headers=stream.session.get_option("http-headers")).content
                                kuntv_auth = re.findall(r'(\{.*\})', kuntv_auth)[0]
                                kuntv_auth = json.loads(kuntv_auth)
                            except:
                                pass
                                #traceback.print_exc(file=sys.stdout)
                            
                            xbmc.log('[StreamLink_Proxy] calling ZoomTV auth page: %s'%str(kuntv_securl))
                        #print(repr(buf[:13]))
                        if not buf:
                            xbmc.log('No Data for buff!')
                            break

                        self.wfile.write(buf)                    
            
                    #self.wfile.close()
                    #self.handlerStop.set()

            
            except socket.error as e:                
                if isinstance(e.args, tuple):
                    if e.errno == errno.EPIPE:
                        # remote peer disconnected
                        xbmc.log('[StreamLink_Proxy] detected remote disconnect!')
                    else:
                        xbmc.log('[StreamLink_Proxy] socket error %s'%str(e))
                else:
                    xbmc.log('[StreamLink_Proxy] socket error %s'%str(e))            
            
            except Exception as err:
                #traceback.print_exc(file=sys.stdout)
                xbmc.log('[StreamLink_Proxy] could not open stream: {0}'.format(err))
                self.handlerStop.set()
            

            try: stream.close()
            except: pass
            stream = None
            

    def rewriteVOD(self, pUrl, m3u8mod):
        try:
            if '|' in pUrl:
                sp = pUrl.split('|')
                pUrl = sp[0]
                headers = urllib.quote_plus(sp[1]).replace('%3D', '=').replace('%26','&') if ' ' in sp[1] else sp[1]
                headers = dict(urlparse.parse_qsl(headers))

            else: headers = {"User-Agent": useragents.CHROME}

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
                m3u8mod = base64.b64decode(m3u8mod)
                if six.PY3: m3u8mod = m3u8mod.decode()
                m3u8mod = json.loads(m3u8mod)
            except:
                #traceback.print_exc()
                m3u8mod = None
            
            if 'regex' in m3u8mod:
                repl = m3u8mod['repl']
                regex = m3u8mod['regex']
                m3u8 = re.sub(regex, repl, m3u8, 0) 
                m3u8 = m3u8.encode('utf-8') if six.PY2 else m3u8

            self.send_response(200)
            self.send_header('Content-type', ct) #m3u8
            self.send_header("Content-Length", cl)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(m3u8)           
            #self.wfile.close()
            
        except socket.error as err:
            pass
            
        except Exception as err:
            # traceback.print_exc()
            self.handlerStop.set()
            xbmc.log('[StreamLink_Proxy] could not rewrite or open playlist: {0}'.format(err))


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
        
        while(True and not stopEvent.isSet()): #and not xbmc.abortRequested            
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
        #print 'SLurl ',url
        stopPlaying=threading.Event()
        stopPlaying.clear()
        progress = xbmcgui.DialogProgress()
        progress.create('Starting StreamLink Proxy')
        progress.update(10, 'Loading StreamLink Proxy')

        sl_Proxy = SLProxy()
        url = url.replace('slplugin://','') #plugin flag from SD
        action = 'vodrewrite' if 'm3u8mod=' in url else 'streamlink'
        url_to_play = 'http://%s:%s/%s/?url=%s'%(sl_Proxy.HOST_NAME, sl_Proxy.PORT_NUMBER, action, url)
        threading.Thread(target=sl_Proxy.start, args=(stopPlaying,)).start()
        proxyReady = sl_Proxy.ready
        
        progress.update(20)
        xbmc.sleep(200)
        p = 30        
        while True and p<100:
            if proxyReady.isSet():
                progress.update(90)
                break
            progress.update(p)
            xbmc.sleep(200)
            p+=10

        mplayer = MyPlayer()  
        mplayer.stopPlaying = stopPlaying        
        mplayer.play(url_to_play, listitem)
        progress.update(100)
        progress.close()
        played=False

        while True:
            if stopPlaying.isSet():
                break
            if xbmc.Player().isPlaying():
                played=True
            xbmc.log('[StreamLink_Proxy] idle sleeping ...')
            xbmc.sleep(1000)
            
        return played

    def resolve_url(self, url):
        xbmc.log('[StreamLink_Proxy] trying to resolve url ...')
        session = Streamlink()
        ## get custom plugins
        load_custom_plugins(session)

        try:
            params = dict(urlparse.parse_qsl('url=%s'%url))
            fURL = params.get('url')                   
            fURL = urllib.unquote(fURL)
            q = params.get('q', False) or 'pick'
            proxy = params.get('p', None)

            if '|' in fURL:
                sp = fURL.split('|')
                fURL = sp[0]        
                headers = dict(urlparse.parse_qsl(sp[1]))        
                session.set_option("http-headers", headers)

            if proxy and len(proxy)>0 and 'http' in proxy:
                if 'https' in proxy:
                    session.set_option('https-proxy', proxy)
                else: session.set_option('http-proxy', proxy)
                xbmc.log('[StreamLink_Proxy] using http-proxy: {0}'.format(proxy))


            plugin = session.resolve_url(fURL)
            streams = plugin.streams()
            #print streams
            if len(streams) > 2 and q == 'pick':
                q = xbmcgui.Dialog().select('Choose the stream quality', [q for q in streams.keys()])
                if q == -1:                    
                    return None
                else: q = list(streams.keys())[q]
            elif q == 'pick': q = 'best'
            stream = streams.get(q, False) or streams.get('best')
            return stream.to_url()

        except Exception as err:
            #traceback.print_exc(file=sys.stdout)
            xbmc.log('[StreamLink_Proxy] resolve error: {0}'.format(err))
            return None

        


class MyPlayer (xbmc.Player):
    def __init__ (self):
        xbmc.Player.__init__(self)

    def play(self, url, listitem):
        #print 'Now im playing... %s' % url
        self.stopPlaying.clear()
        xbmc.Player().play(url, listitem)
        
    def onPlayBackEnded( self ):
        # Will be called when xbmc stops playing a file
        #print "seting event in onPlayBackEnded " 
        self.stopPlaying.set()
        #print "stop Event is SET" 

    def onPlayBackStopped( self ):
        # Will be called when user stops xbmc playing a file
        #print "seting event in onPlayBackStopped " 
        self.stopPlaying.set()
        #print "stop Event is SET" 
    
    def onPlayBackError( self ):
        self.stopPlaying.set()

    def onPlayBackStarted( self ):
        #xbmc.executebuiltin("Dialog.Close(busydialog)")
        pass



