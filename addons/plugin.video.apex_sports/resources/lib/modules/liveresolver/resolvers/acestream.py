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
		c1 = 'acestream.org' in html and bool(re.search('atob\s*\([\"\']?(aHR0[^\"\'\)]+)', html))
		
		b = c1
		return b

	def resolve(self, url, html = '', referer=None):
		atob = re.findall('atob\s*\([\"\']?(aHR0[^\"\'\)]+)', html)
		if atob != []:
			atob = atob[0]
			import base64
			play_url = base64.b64decode(atob).decode('utf-8')
			if '127.0.0.1' and 'ace' in play_url:
				ace_id = re.findall('id=([^$]+)', play_url)
				if ace_id != []:
					return {'url': 'plugin://program.plexus/?mode=1&url={}&name=Acestream'.format(ace_id[0]), 'headers': {}}

		return None