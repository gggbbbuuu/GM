import re
import requests
import json
from resources.lib.modules.log_utils import log
from resources.lib.modules import jsunpack
from resources.lib.modules.constants import USER_AGENT

try:
	from urllib.parse import urlparse
except:
	from urlparse import urlparse  # Python 2


class Resolver():

	def __init__(self):
		self.hosts = {}
		self.headers = {'User-Agent': USER_AGENT}
		self.s = requests.session()
		self.s.headers.update(self.headers)

	def isSupported(self, url, html):
		return bool(re.search('https?://cdn.livestreamapi.ru', html))

	def resolve(self, url, html = '', referer=None, referer_map={}):
		try:
			self.s.headers.update({'Referer':referer})
			html = self.s.get(url).text
			try:
				u = re.findall('](https?://cdn.livestreamapi.ru.+?getvideo[^\"\'\,\s]+)', html)[0]
			except:
				return None

			self.s.headers.update({'Referer':url, 'User-Agent':USER_AGENT})
			#play_url = self.s.get(u, allow_redirects=False, timeout=5).headers['Location']
			return {'url': u, 'headers':{'Referer': url, 'User-Agent': USER_AGENT}}
		except Exception as e:
			log(e)
			return None