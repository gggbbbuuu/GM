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

	def priority(self):
		return -2

	def isSupported(self, url, html):
		return bool(re.search('http(s)?://(www\.)?livestream.com/', url))

	def resolve(self, url, html = '', referer=None):
		try:
			r = html
			fid = re.findall('secure_m3u8_url[\"\']\s*\:\s*[\"\']([^\"\']+)', r)[0]
			return {'url': fid, 'headers': {'referer':url, 'user-agent': USER_AGENT}}
		except Exception as e:
			log(e)
			return None