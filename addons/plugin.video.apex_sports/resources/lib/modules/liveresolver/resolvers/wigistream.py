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
		return (bool('wigistream' in url) and bool('embed' in url) ) or ('docast' in url and 'embed' in url) or bool(re.search('p\s*,\s*a\s*,\s*c\s*,\s*k\s*,\s*e\s*,\s*d', html))
	def resolve(self, url, html = '', referer=None, referer_map={}):
		if referer:

			a = url
			ref = referer
			while ref != '':
				a = ref
				ref = referer_map[a]

			self.s.get(a)

				

			self.s.headers.update({'Referer': referer})

			html = self.s.get(url).text
			
			ts = re.findall('(eval\(function\(p,a,c,k,e,(?:r|d).*)', html)
			for t in ts:
				u = jsunpack.Unpacker()
				if u.detect(t):
					html = u.unpack(t)
					#log(html)
				try:
					play_url = re.findall('[\"\']((?:http)?[^\"\']+\.m3u8[^\"\']*)[\"\']', html)[0]
					return {'url': play_url, 'headers':{'referer':url, 'user-agent':USER_AGENT}}
				except:
					pass

			return None

			
		#except:
	#		return None
		