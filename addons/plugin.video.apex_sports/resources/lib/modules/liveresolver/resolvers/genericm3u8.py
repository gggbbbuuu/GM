import re
import requests
import json

try:
	from urllib.parse import urlparse
except:
	from urlparse import urlparse  # Python 2

from resources.lib.modules.log_utils import log
from resources.lib.modules import jsunpack
from resources.lib.modules.constants import USER_AGENT





class Resolver():

	def __init__(self):
		self.hosts = {}
		self.headers = {'User-Agent': USER_AGENT, 'Cache-control': 'no-cache'}

	def priority(self):
		return 0

	def isSupported(self, url, html):
		return bool(re.search('[\"\']((?:http)?[^\"\']+\.m3u8[^\"\']*)[\"\']', html))

	def resolve(self, url, html='', referer = None):

		s = requests.session()
		s.headers.update(self.headers)
		if referer:
			s.headers.update({'Referer': referer})
		try:
			resp = s.get(url, timeout=3)
			try:
				url = resp.history[-1].url
			except:
				pass
			html = resp.text
		except Exception as e:
			log(e)
			return None

		
		#try:
		play_url = re.findall('[\"\']((?:http)?[^\"\']+\.m3u8[^\"\']*)[\"\']', html)

		if len(play_url) == 0:
			return None
		play_url = play_url[0]
		if play_url.startswith('%3C'):
			return None
		if urlparse(play_url).scheme == '':
			play_url = play_url.replace('://', '')
			play_url = 'http://' + play_url
			play_url = play_url.replace('////','//')

		headers = {'Referer': url, 'User-Agent':USER_AGENT, 'Host': urlparse(play_url).netloc, 'Origin': 'https://'+urlparse(url).netloc, 'Connection':'keep-alive'}
		return {'url': play_url, 'headers': headers}
		#except:
		#return None
