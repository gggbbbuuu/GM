import re
import requests
import json
from resources.lib.modules.log_utils import log
from resources.lib.modules import hunter
from resources.lib.modules.constants import USER_AGENT
import base64

try:
	from urllib.parse import urlparse
except:
	from urlparse import urlparse  # Python 2
import urllib


class Resolver():

	def __init__(self):
		self.hosts = {}
		self.headers = {'User-Agent': USER_AGENT, 'Cache-control': 'no-cache'}
		self.s = requests.session()
		self.s.headers.update(self.headers)

	def isSupported(self, url, html):
		return bool(re.search('plytv.+?\.js', html))

	def resolve(self, url, html = '', referer=None):
		try:
			#r = self.s.get(url).text
			r = html
			pdettxt, zmid, pid, edm = re.findall('pdettxt\s*=\s*[\"\']([^\"\']+).+?zmid\s*=\s*[\"\']([^\"\']+).+?pid\s*=\s*(\d+).+?edm\s*=\s*[\"\']([^\"\']+)', r)[0]
			headers = {
				'authority': 'www.plytv.me',
				'cache-control': 'max-age=0',
				'upgrade-insecure-requests': '1',
				'content-type': 'application/x-www-form-urlencoded',
				'user-agent': USER_AGENT,
				'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
				'sec-gpc': '1',
				'sec-fetch-site': 'cross-site',
				'sec-fetch-mode': 'navigate',
				'sec-fetch-dest': 'iframe',
				'referer': url,
				'accept-language': 'en-US,en;q=0.9',
				'origin' : "https://"+urlparse(url).netloc
			}
			post_data = {'pid': str(pid), 'ptxt':pdettxt}
			u = 'https://www.plytv.me/sdembed?v={}'.format(zmid)

			html = self.s.post(u, headers=headers, data=post_data).text
			h,uu,n,t,e,r = re.findall('function\(h,u,n,t,e,r\).*?}\((".+?)\)\)', html)[0].split(',')

			ret = hunter.dehunt(h.replace('"', ''),int(uu),n.replace('"', ''),int(t),int(e),int(r))
			bs = re.findall('[\"\'](aHR[^\"\']+)', ret)
			for b in bs:
				play_url = base64.b64decode(b).decode('utf-8')
				if 'm3u8' in play_url:
					orig = "https://"+urlparse(u).netloc
					return {'url': play_url, 'headers':{'referer':u, 'user-agent':USER_AGENT, 'origin':orig}}
		except Exception as e:
			log("Plytv Exception: " + str(e))
			return None
		
