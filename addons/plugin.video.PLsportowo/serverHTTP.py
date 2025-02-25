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
    
from binascii import unhexlify
try:  # The crypto package depends on the library installed (see Wiki)
    from Cryptodome.Cipher import AES
    from Cryptodome.Util import Padding
except ImportError:
    from Crypto.Cipher import AES
    from Crypto.Util import Padding


import struct
import base64
import re
import socket
from contextlib import closing

import xbmcaddon, xbmc

addon = xbmcaddon.Addon('plugin.video.PLsportowo')
proxyport = addon.getSetting('proxyport')
import requests
import sys
PY3 = sys.version_info >= (3,0,0)
if PY3:
    LOGNOTICE = xbmc.LOGINFO

else:
    LOGNOTICE = xbmc.LOGNOTICE
__BLOCK_SIZE__ = 16




from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context
import ssl
# from urllib3.util.ssl_ import DEFAULT_CIPHERS
DEFAULT_CIPHERS = ":".join(
    [
        "ECDHE+AESGCM",
        "ECDHE+CHACHA20",
        "DHE+AESGCM",
        "DHE+CHACHA20",
        "ECDH+AESGCM",
        "DH+AESGCM",
        "ECDH+AES",
        "DH+AES",
        "RSA+AESGCM",
        "RSA+AES",
        "!aNULL",
        "!eNULL",
        "!MD5",
        "!DSS",
    ]
)

UA='Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:83.0) Gecko/20100101 Firefox/83.0'

#CIPHERS = ":".join(["DEFAULT","!DHE","!SHA1","!SHA256","!SHA384",])

DEFAULT_CIPHERS += ":!ECDHE+SHA:!AES128-SHA:!AESCCM:!DHE:!ARIA"

CIPHERS = DEFAULT_CIPHERS

class ZoomTVAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=CIPHERS)
        context.set_ecdh_curve("prime256v1")
        context.options |= (ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1)
        kwargs["ssl_context"] = context
        return super(ZoomTVAdapter, self).init_poolmanager(*args, **kwargs)

headers = {
    "Referer": "https://www.tvply.me/sdembed?v=soc22sd",
    "Origin": "https://www.tvply.me",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.0.0 Safari/537.36",
    "Accept-Language": "en",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}
session = Session()
session.mount("https://key.seckeyserv.me", ZoomTVAdapter())
session.headers.update(headers)

def unpad(data):
    if PY3:
        cc = data[:-ord(data[len(data)-1:])]

    else:
        cc= data[:-ord(data[-1])]
    return cc


def num_to_iv(n):
    return struct.pack(">8xq", n)

def pkcs7_decode(paddedData, keySize=16):
    '''
    Remove the PKCS#7 padding
    '''
    # Use ord + [-1:] to support both python 2 and 3
    val = ord(paddedData[-1:])
    if val > keySize:
        raise StreamError("Input is not padded or padding is corrupt, got padding size of {0}".format(val))

    return paddedData[:-val]


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_HEAD(self):

        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        """Handle http get requests, used for manifest"""
        orig = addon.getSetting('viporig')
        urlk = addon.getSetting('vipurlk')
        
        path = self.path  # Path with parameters received from request e.g. "/manifest?id=234324"
       # print('HTTP GET Request received to {}'.format(path))
       # xbmc.log('pathpathpathpath: %s' % str(path), level=LOGNOTICE)
        #if 'seckeyserv' in (self.path):
 
        #    a=''    
        if (self.path).startswith('https://mf.svc.nhl.com'):# in path: for NHL

            try:
            
                licurl=(addon.getSetting('streamNHL'))
                ab=eval(addon.getSetting('heaNHL'))
                result = requests.get(url=licurl, headers=ab, verify=False, timeout = 30).content
        

                replace = "https://mf.svc.nhl.com"
                keyurl = "https://e10.julinewr.xyz/ingest4s"
                manifest_data = result.replace(replace,keyurl)

                self.send_response(200)
                self.send_header('Content-type', 'application/x-mpegURL')
                self.end_headers()
                self.wfile.write(manifest_data)
            except Exception:
                self.send_response(500)
                self.end_headers()
        elif 'plyvivo' in (self.path) and '.m3u8' in (self.path):

            a=''
            try:

                licurl=(self.path).split('dd=')[-1]
                #print('licurl')
                #print(licurl)
 
                ab=eval(addon.getSetting('heaNHL2'))
                #print('hea')
                #print(ab)
                
                hea= '&'.join(['%s=%s' % (name, value) for (name, value) in ab.items()])
                result = session.get(url=licurl, headers=ab, verify=False, timeout = 30).content
                if PY3:
                    result = result.decode(encoding='utf-8', errors='strict')
                if 'https://key.seckeyserv' in result:
                    addon.setSetting('cbc','ok')

                    result = result.replace('KEYFORMAT="identity"', 'KEYFORMAT=""')
                    uri,sequence = re.findall('\,URI="(.+?)",IV\=0x(.+?),',result,re.DOTALL)[0]
                    
                    addon.setSetting('vipkuri',str(uri))
                    addon.setSetting('vipksequence',str(sequence))

                    reg = '(#EXT-X-KEY.*?KEYFORMATVERSIONS="1")'#,'',
                    result = re.sub(reg, '', result)
                    #print(result)
                    a=''

                    self.send_response(200)
                    self.send_header('Content-type', 'application/vnd.apple.mpegurl')
                    self.end_headers()

                    if PY3:
                        result = result.encode(encoding='utf-8', errors='strict')
                    self.wfile.write(result)

                else:

                    addon.setSetting('cbc','none')
                    self.send_response(200)
                    self.send_header('Content-type', 'application/vnd.apple.mpegurl')
                    if PY3:
                        result = result.encode(encoding='utf-8', errors='strict')
                    self.end_headers()
                    self.wfile.write(result)
            except Exception as exc:
              #  xbmc.log('ExceptionExceptionExceptionException: %s' % str(exc), level=LOGNOTICE)
                self.send_response(500)
                self.end_headers()

        elif (self.path).endswith('.m3u8'):
            result=''
            if '/NHL=' in (self.path):#NHL .m3u8
                print('proxyURL-NHL')
                newurl = self.path.split('/NHL=')[1]

                result1 = requests.get(url= newurl, timeout = 30).content
                #print(result1)
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
                
                result=result.encode('utf-8')
            
            if 'WIKISPORT' in (self.path):#WIKISPORT .m3u8
                print('proxyURL-WIKISP')
                newurl = self.path.split('WIKISPORT=')[1]
                hdr={'Referer':'http://wikisport.click','Origin':'http://wikisport.click'}
                result = requests.get('https://javal1.herokuapp.com/'+newurl, headers=hdr, timeout = 30).content
                if PY3:
                    result = result.decode(encoding='utf-8', errors='strict')
                try:
                    result=result.replace('https:','https://javal1.herokuapp.com/https:')
                except:
                    result=''
                    
                result=result.encode('utf-8')
                
            #print('RESULT_MANIFEST')
            #print(result)
            self.send_response(200)
            self.send_header('Content-type', 'application/vnd.apple.mpegurl')
            self.end_headers()

            self.wfile.write(result)
        
        elif (self.path).endswith('.ts') and '/NHL=' in (self.path):#NHL .ts
            print('proxy_NHL_ts')
            newurl=''
            if 'NHL='in (self.path):
                newurl=(self.path).split('NHL=')[-1]
                
            result=requests.get(newurl, verify=False, timeout = 30).content
            
            self.send_response(200)
            self.send_header('Content-type', 'application/vnd.apple.mpegurl')
            self.end_headers()

            self.wfile.write(result)
        
        
        elif (self.path).endswith('.ts') and 'nhl.com' not in (self.path) and '/WIKISPORT=' not in (self.path):

            xbmc.log('tutajtutajtutajtutaj: ', level=LOGNOTICE)
            newurl=''
            if 'dd=' in (self.path):
                newurl=(self.path).split('dd=')[-1]

            host =urlparse(newurl).netloc
            #print('host')
            #print(host)

            hd5 = {
                'User-Agent': UA,
                'Accept': '*/*',
                'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
                'Referer': urlk,
                'Origin': orig,
                'Host': host,
                'Connection': 'keep-alive',
            }
            
            #print('hd5')
            #print(hd5)
            
            hd5=eval(addon.getSetting('heaNHL2'))
            
            resultx = requests.get(url= newurl,headers=hd5, verify=False, timeout = 30)
            #print('resultx')
            #print(resultx)

            if resultx.status_code == 200:

                vipkuri=addon.getSetting('vipkuri')
              #  xbmc.log('vipkurivipkurivipkurivipkuri: %s'%str(vipkuri), level=LOGNOTICE)
                
                sequence=addon.getSetting('vipksequence')
                
                
                
                hd5 = eval(addon.getSetting('viphdrs'))

                result = session.get(url=vipkuri, headers=hd5, verify=False, timeout = 30)#.content
                
                result.encoding = "binary/octet-stream"
                result = result.content

                iv = sequence

                if PY3:
                    iv = iv.encode(encoding='utf-8', errors='strict')
                iv = b"\x00" * (16 - len(iv)) + iv

                iv = unhexlify(iv)
                
                if addon.getSetting('cbc')=='ok':
                    decryptor = AES.new(result, AES.MODE_CBC, iv)
                
                    decrypted_chunkx = decryptor.decrypt(resultx.content)
                 #   decrypted_chunkx = Padding.unpad(padded_data=decryptor.decrypt(resultx.content[AES.block_size:]),block_size=__BLOCK_SIZE__)

                else:
                    decrypted_chunkx = resultx.content
                #print('resultx.content')
                #print(resultx.content)
                
                self.send_response(resultx.status_code, 'OK')
                self.send_header('Content-Type', 'video/mp2t')
                self.send_header('Connection', 'keep-alive')
                self.send_header('Content-Length', len(decrypted_chunkx))
                self.end_headers()
                self.wfile.write(decrypted_chunkx)
            else:
                self.send_response(resultx.status_code)


        else:

            return

    def do_POST(self):
        """Handle http post requests, used for license"""
        path = self.path  # Path with parameters received from request e.g. "/license?id=234324"
        #xbmc.log('pathpathpathpath222: %s' % str(path), level=LOGNOTICE)
      #  print('HTTP POST Request received to {}'.format(path))
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