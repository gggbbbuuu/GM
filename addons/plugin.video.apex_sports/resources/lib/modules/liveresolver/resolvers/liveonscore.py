import re
import requests
import json
from resources.lib.modules.constants import USER_AGENT

try:
	from urllib.parse import urlparse
except:
	from urlparse import urlparse  # Python 2


class Resolver():

	def __init__(self):
		self.headers = {'User-Agent': USER_AGENT, 'Cache-control': 'no-cache'}

	def isSupported(self, url, html):
		
		return bool(re.search('liveonscore\.tv\/.+?\/\d+', url))

	def resolve(self, url, html='', referer=None):
		s = requests.session()
		s.headers.update(self.headers)
		html = s.get(url, timeout=3).text
		var = re.findall('gethlsUrl\(([^\,]+)\s*,\s*\)', html)
		if len(var) > 0:
			value = re.findall('var\s+{}\s*=\s*[\"\']([^\"\']+)'.format(var[0]), html)
			if len(value) > 0:
				value = value[0]
				r = s.get('http://liveonscore.tv/gethls.php?idgstream={}&serverid='.format(value), headers = {'Referer': url, 'Content-Type': 'application/json', 
				'X-Requested-With': 'XMLHttpRequest', 'User-Agent': USER_AGENT})
				print(r.text)
				play_url = json.loads(r.text)['rawUrl']

				ret = {'url' : play_url, 'headers' : {'referer': url}}

				return ret

		else:
			value = re.findall('var\s+vidgstream \s*=\s*[\"\']([^\"\']+)', html)
			if len(value) > 0:
				value = value[0]
				r = s.get('http://liveonscore.tv/gethls.php?idgstream={}'.format(value), headers = {'Referer': url, 'Content-Type': 'application/json', 
					'X-Requested-With': 'XMLHttpRequest', 'User-Agent': USER_AGENT})

				play_url = json.loads(r.text)['rawUrl']

				ret = {'url' : play_url, 'headers' : {'referer': url}}

				return ret
		return None
