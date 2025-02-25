from resources.lib.modules import cache
from resources.lib.modules.log_utils import log
from resources.lib.modules import control, constants, webutils
import requests
import re
try:
	from urllib.parse import urlencode
except:
	from urllib import urlencode

class info():
	def __init__(self):
		self.mode = 'lmshows'
		self.name = 'LMShows 24/7'
		self.icon = 'lm.png'
		self.enabled = control.setting(self.mode) == 'true'
		self.paginated = False
		self.categorized = False
		self.multilink = False


class main():
	
	def __init__(self, url = 'https://lmshows.se'):
		self.base = 'https://lmshows.se/'
		self.url = url

	def events(self):
		html = requests.get(self.base, headers={'user-agent': constants.USER_AGENT}).text
		channels = re.findall('href=[\"\']([^\"\']+)[\"\']><img src=[\"\']([^\"\']+)[\"\'] alt=[\"\']([^\"\']+)[\"\'].+?class=[\"\']ch-cover',html)
		events = []
		for c in channels:
		   
			url = self.base + c[0]
			img = self.base + c[1]
			title = c[2]
			if c[0] == 'tr.php':
				continue
			events.append((url,title,img))
		return events


	def resolve(self,url):
		html = requests.get(url, headers={'user-agent': constants.USER_AGENT, 'referer':self.base}).text
		fid = re.findall('vaughn.live.+?video/?([^\?]+)', html)
		if len(fid)==0:
			return ' '
		else:
			url = 'https://vaughn.live/' + fid[0]

		from resources.lib.modules import liveresolver
		d = liveresolver.Liveresolver().resolve(url)
		if not d or d is None:
			return ' '
		if d['url'].startswith('plugin://'):
			return d['url']

		if d:
			return '{}|{}'.format(d['url'], urlencode(d['headers'])), False
		return ''
