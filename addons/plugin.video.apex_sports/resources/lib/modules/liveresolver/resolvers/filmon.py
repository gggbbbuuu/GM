import re
import json
from resources.lib.modules.log_utils import log
from resources.lib.modules.constants import USER_AGENT
import requests
try:
	from urllib.parse import urlparse
except:
	from urlparse import urlparse  # Python 2


class Resolver():

	def __init__(self):
		self.hosts = {}
		self.headers = {'User-Agent': USER_AGENT, 'Cache-control': 'no-cache'}

	def isSupported(self, url, html):
		return bool(re.search('filmon.com', url))

	def resolve(self, url, html = '', referer=None):
		try:
			s = requests.session()
			if '/vod/' in url:
				url = re.compile('/(\d+)').findall(url)[-1]
				url = 'http://www.filmon.com/vod/info/%s' % url
			elif '/tv/' in url:
				url = url.replace('/tv/', '/channel/')
			elif not '/channel/' in url:
				raise Exception()
	 
			headers = {'X-Requested-With': 'XMLHttpRequest'}

			

			cid = s.get(url, headers=headers).text
			cid = json.loads(cid)['id']

			headers = {'X-Requested-With': 'XMLHttpRequest', 'Referer': url}

			url = 'http://www.filmon.com/ajax/getChannelInfo?channel_id=%s' % cid

			s.headers.update(headers)
			result = s.get(url).text

			result = json.loads(result)
			try:
				result = result['streams']
			except:
				result = result['data']['streams']
				result = [i[1] for i in result.items()]

			url = [(i['url'], int(i['watch-timeout'])) for i in result]
			url = [i for i in url if '.m3u8' in i[0]]
			
			url.sort()
			url = url[-1][0]
			return {'url': url, 'headers':{}}
		except Exception as e:
			log("Filmon error: " + str(e))
			return ' '
			