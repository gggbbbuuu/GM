import re
import requests
import json
import sys
from resources.lib.modules.constants import USER_AGENT
from resources.lib.modules.log_utils import log
try:
	from urllib.parse import urlparse
except:
	from urlparse import urlparse  # Python 2

# python 2 doesn't support date.datetime.timestamp()
if sys.version_info[0] < 3 or sys.version_info[1] < 4:
    # python version < 3.3
    import time
    def timestamp(date):
        return time.mktime(date.timetuple())
else:
    def timestamp(date):
        return date.timestamp()

class Resolver():

	def __init__(self):
		self.hosts = {}
		self.headers = {'User-Agent': USER_AGENT, 'Cache-control': 'no-cache'}

	def isSupported(self, url, html):
		return bool(re.search('telerium.+?embed\/\d+', url))

	def resolve(self, url, html, referer = None):
		#try:
			s = requests.session()

			s.headers.update(self.headers)
			if referer:
				s.headers.update({'Referer': referer})
			# html = s.get(url).text
			
			host, id = re.findall('(telerium\.[^/]+).+?embed\/(\d+)', url)[0]
			from datetime import datetime, timedelta
			now = datetime.now()
			now = now.replace(second=0, microsecond=0) +timedelta(hours=24)
			now = int(round(timestamp(now))*1000)
			s.headers.update({'referer':url})
			uri = 'https://{}/streams/{}/{}.json'.format(host, id, now)
			a = json.loads(s.get(uri).text)
			token = 'http://' + urlparse(url).netloc + a['tokenurl']
			token = json.loads(s.get(token).text)
			for t in token:
				t=t[::-1]
				uu = 'http:' + a['url'] + t
				if s.get(uu).status_code == 200:
					play_url = uu

			return {'url':play_url, 'headers':{'referer':url, 'User-Agent':USER_AGENT, 'Host': urlparse(play_url).netloc}}
		#except:
		#	return None

