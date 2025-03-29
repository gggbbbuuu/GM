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
		return bool(re.search('wmsxx.+?\.js', self.s.get(url).text))

	def resolve(self, url, html = '', referer=None):
		try:
			#r = self.s.get(url).text
			r = html
			fid = re.findall('id\s*=\s*[\"\']([^\"\']+).+?wms.+?\.js', r)[0]
			u = 'https://www.wmsxx.com/embx.php?live=' + fid

			import genericm3u8
			return genericm3u8.Resolver().resolve(u, referer=url)
		except:
			return None
		
		
# l = Wmsxx()
# url = 'http://www.sports-stream.org/chtv/sps.php?ch=2'
# a = l.isSupported(url)
# a = l.resolve(url)
# print(a)
# print('{}|referer={}&user-agent={}'.format(a['url'], a['headers']['referer']), USER_AGENT)