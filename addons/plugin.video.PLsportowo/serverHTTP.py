try:  # Python 3
    from http.server import BaseHTTPRequestHandler
except ImportError:  # Python 2
    from BaseHTTPServer import BaseHTTPRequestHandler

try:  # Python 3
    from socketserver import TCPServer
except ImportError:  # Python 2
    from SocketServer import TCPServer

try:  # Python 3
    from urllib.parse import parse_qs, urlparse, urlencode,quote,unquote
except ImportError:  # Python 2
    from urlparse import urlparse, parse_qs
    from urllib import urlencode,quote,unquote
import base64
import re
import socket
from contextlib import closing

import xbmcaddon

addon = xbmcaddon.Addon(id='plugin.video.PLsportowo')
import requests
import sys
PY3 = sys.version_info >= (3,0,0)
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        """Handle http get requests, used for manifest"""

        path = self.path  # Path with parameters received from request e.g. "/manifest?id=234324"
        print('HTTP GET Request received to {}'.format(path))
        
        if (self.path).startswith('https://mf.svc.nhl.com'):# in path: for NHL

            try:
            
                licurl=(addon.getSetting('streamNHL'))
                ab=eval(addon.getSetting('heaNHL'))
                result = requests.get(url=licurl, headers=ab, verify=False).content
        

                replace = "https://mf.svc.nhl.com"
                keyurl = "https://e10.julinewr.xyz/ingest4s"
                manifest_data = result.replace(replace,keyurl)
                # Call your method to do the magic to generate DASH manifest data
                #manifest_data = b'my manifest data'
                self.send_response(200)
                self.send_header('Content-type', 'application/x-mpegURL')
                self.end_headers()
                self.wfile.write(manifest_data)
            except Exception:
                self.send_response(500)
                self.end_headers()
        elif 'media.mlb' in (self.path):# for MLB
            try:
            
                licurl=(addon.getSetting('streamMLB'))
                ab=eval(addon.getSetting('heaMLB'))
                keyurl=addon.getSetting('keyurl')
                replkey=addon.getSetting('replkey')
                newurl = self.path.split('/manifest=')[1]
                result = requests.get(url=newurl, headers=ab, verify=False).content
                if PY3:
                    result = result.decode(encoding='utf-8', errors='strict')
                manifest_data = result
                if 'playback.svcs' in manifest_data:

                    cc=re.findall('METHOD=AES-128,URI="(.+?)"',result)[0]

                    replkey+=base64.b64encode(cc)

                    manifest_data = result.replace(cc,replkey)
                # Call your method to do the magic to generate DASH manifest data
                #manifest_data = b'my manifest data'
                self.send_response(200)
                self.send_header('Content-type', 'application/x-mpegURL')
                self.end_headers()
                self.wfile.write(manifest_data)
            except Exception:
                self.send_response(500)
                self.end_headers()
        elif (self.path).endswith('.m3u8'):
            newurl = self.path.split('/manifest=')[1]
           # licurl=(addon.getSetting('streamNHL'))
          #  ab=eval(addon.getSetting('heaNHL'))
            result1 = requests.get(url= newurl).content
            if PY3:
                result1 = result1.decode(encoding='utf-8', errors='strict')
            try:
                replacekey=(addon.getSetting('replkey'))
                keyurl=(addon.getSetting('keyurl'))
                if not replacekey and not keyurl:
                    replacekey = "https://mf.svc.nhl.com"
                    keyurl = "https://e10.julinewr.xyz/ingest4s"

                result = result1.replace(replacekey,  keyurl)

            except:
                result=result1
            
            
            
            self.send_response(200)
            self.send_header('Content-type', 'application/vnd.apple.mpegurl')
            self.end_headers()

            self.wfile.write(result)
        elif (self.path).endswith('.ts'):
            newurl = self.path.split('/manifest=')[1]
            result = requests.get(url= newurl)
            
            if result.status_code == 200:
                result_content = result.content
                if PY3:
                    result_content = result_content.decode(encoding='utf-8', errors='strict')
                self.send_response(result.status_code, 'OK')
                self.send_header('Content-Type', 'video/mp2t')
                self.send_header('Connection', 'keep-alive')
                self.send_header('Content-Length', len(result_content))
                self.end_headers()
                self.wfile.write(result_content)
            else:
                self.send_response(result.status_code)

        else:

            return

    def do_POST(self):
        """Handle http post requests, used for license"""
        path = self.path  # Path with parameters received from request e.g. "/license?id=234324"

        print('HTTP POST Request received to {}'.format(path))
        if '/license' not in path:
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get('content-length', 0))
        isa_data = self.rfile.read(length).decode('utf-8').split('!')
        
        challenge = isa_data[0]
        path2 = path.split('cense=')[-1]
        
        licurl=(addon.getSetting('licurl'))
        ab=eval(addon.getSetting('hea'))
        result = requests.post(url=licurl, headers=ab, data=challenge).content
        if PY3:
            result = result.decode(encoding='utf-8', errors='strict')
        
        licens=re.findall('ontentid=".+?">(.+?)<',result)[0]
        
        if PY3:
            licens= licens.encode(encoding='utf-8', errors='strict')
        
        self.send_response(200)
        self.end_headers()
        
        self.wfile.write(licens)

            
            
def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        addon.setSetting('proxyport',str(s.getsockname()[1]))
        return s.getsockname()[1]           


address = '127.0.0.1'  # Localhost

port = find_free_port()
server_inst = TCPServer((address, port), SimpleHTTPRequestHandler)
# The follow line is only for test purpose, you have to implement a way to stop the http service!
server_inst.serve_forever()