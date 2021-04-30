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
		return 'vaughn.live' in url

	def resolve(self, url, html = '', referer=None):
		try:
			r = html
			fid = re.findall('mp4StreamName\s*=\s*[\"\']([^\"\']+)', r)[0]
			play_url = 'https://stream2-cdn.vaughnsoft.net/play/{}.flv'.format(fid)
			return {'url': play_url, 'headers': {'user-agent': USER_AGENT, 'referer': url}}
		except:
			return None