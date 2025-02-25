from resources.lib.modules import cache
from resources.lib.modules.log_utils import log
from resources.lib.modules import control
from resources.lib.modules.constants import USER_AGENT
import requests
import re
try:
	from urllib.parse import urlencode
except:
	from urllib import urlencode

class info():
	def __init__(self):
		self.mode = 'cricfree'
		self.name = 'cricfree.com'
		self.icon = 'cricfree.png'
		self.enabled = False
		self.paginated = False
		self.categorized = False
		self.multilink = True


class main():
	
	def __init__(self, url = 'http://cricfree.unblckd.pw'):
		self.base = 'http://cricfree.unblckd.pw'
		self.url = url
		self.s = requests.session()
		self.s.headers.update({'user-agent': USER_AGENT})

	def events(self):
		events = []
		html = self.s.get(self.url).text
		chs = re.findall('<span>([^<]+).+?href\s*=\s*[\"\']([^\"\']+)', html, flags=re.DOTALL)
		for c in chs:
			events.append((c[1], c[0].strip()))
		return events

	def links(self, url):
		ls = []
		html = self.s.get(url).text
		links = re.findall('window.open.+?href\s*=\s*[\"\']([^\"\']+)', html)
		for i in range(len(links)):
			ls.append((links[i], 'Link #{}'.format(i+1)))

		return ls


	def resolve(self,url):
		from resources.lib.modules import liveresolver
		d = liveresolver.Liveresolver().resolve(url)
		if not d or d is None:
			return ' '
		if d['url'].startswith('plugin://'):
			return d['url']

		if d:
			return '{}|{}'.format(d['url'], urlencode(d['headers']))
		return ' '
