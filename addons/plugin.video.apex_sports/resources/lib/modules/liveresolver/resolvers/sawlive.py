import re
import requests
import json
from resources.lib.modules.log_utils import log
from resources.lib.modules.constants import USER_AGENT

try:
	from urllib.parse import urlparse
except:
	from urlparse import urlparse  # Python 2


class Resolver():

	def __init__(self):
		self.hosts = {}
		self.headers = {'User-Agent': USER_AGENT, 'Cache-control': 'no-cache'}
		self.s = requests.session()
		self.s.headers.update(self.headers)

	def isSupported(self, url, html):
		return 'sawlive.tv/embed/' in html

	def resolve(self, url, html = '', referer=None):
		try:
			u = re.findall('src\s*=\s*[\"\'](https?.+?sawlive.+?embed[^\"\']+)', html)[0]
			self.s.headers.update({'referer': url})
			html = self.s.get(u).text
			var1 = re.findall('([a-zA-Z]+)\.split', html)[0]
			var2 = re.findall('var\s+{}\s*=\s*[\"\']([^\"\']+)'.format(var1), html)[0]
			v1, v2 = var2.split(';')
			u2 = 'http://www.sawlive.tv/embedm/stream/{}/{}'.format(v2, v1)
			self.s.headers.update({'referer': u})
			html = self.s.get(u2).text

			lst = eval(re.findall('var.+?=\s*(\[[\d\,]+\])', html)[0])
			stream_url = ""
			for c in lst:
				stream_url += chr(c)
			return {'url': stream_url, 'headers': {'User-Agent': USER_AGENT, 'referer': u2}}


		except:
			return None
		