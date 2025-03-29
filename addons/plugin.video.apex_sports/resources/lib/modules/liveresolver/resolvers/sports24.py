import re
import requests
import json
try:
  from urllib.parse import urlparse
except:
  from urlparse import urlparse  # Python 2

from resources.lib.modules.constants import USER_AGENT

class Resolver():

  def __init__(self):
    self.hosts = {}
    self.headers = {'User-Agent': USER_AGENT, 'Cache-control': 'no-cache'}

  def isSupported(self, url, html):
    return bool(re.search('sport24hd.+?\/channel\/',url)) or bool(re.search('whd365.+?\/channel\/',url)) 

  def resolve(self, url, html='', referer=None):
    try:
      s = requests.session()

      s.headers.update(self.headers)

      host = s.get('https://api.livesports24.online:8443/gethost',  timeout=3).text
      channel = urlparse(url).path.split('/')[-1]
      play_url = 'https://' + host + '/' + channel + '.m3u8'
      return {'url': play_url, 'headers': {'referer': url} }
    except:
      return None
