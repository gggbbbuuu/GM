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
		return bool(re.search('up.live\/(?:nba|soccer|nfl)(.+?)202\d', url))

	def resolve(self, url, html = '', referer=None):
		try:

			id = re.findall('up.live\/(?:nba|soccer|nfl)(.+?)202\d', url)[0]
			play_url = 'http://nflup.live/gu/{}.m3u8'.format(id)
			return {'url': play_url, 'headers':{'referer':url, 'user-agent':USER_AGENT}}
		except:
			return None
		
