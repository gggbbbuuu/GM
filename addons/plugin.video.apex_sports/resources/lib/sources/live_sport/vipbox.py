from resources.lib.modules import webutils, control, linkSearch, cache, constants
from resources.lib.modules.log_utils import log
import re, requests, sys
try:
	from urllib.parse import quote, urlencode
except:
	from urllib import quote, urlencode

if sys.version_info[0] < 3 or sys.version_info[1] < 4:
    # python version < 3.3
    import time
    def timestamp(date):
        return time.mktime(date.timetuple())
else:
    def timestamp(date):
        return date.timestamp()

class info():
	def __init__(self):
		self.mode = 'vipbox'
		self.name = 'Viprow'
		self.icon = 'viprow.png'
		self.enabled = control.setting(self.mode) == 'true'
		self.categorized = True
		self.paginated = False
		self.multilink = True
		self.searchable = True

class main():
	def __init__(self, url=''):
		self.base = 'https://www.viprow.net'
		self.search_url = 'https://www.viprow.me/find-{}-stream'
		self.s = requests.session()
		self.s.headers.update({'user-agent': constants.USER_AGENT})

	def categories(self):

		html = self.s.get(self.base).text

		cats = re.findall("href=[\"\']([^\"\']+)[\"\'] title=[\"\'](.+?) Online[\"\']", html)
		cs = []
		for c in cats:
			cs.append((self.base + c[0], c[1], 'icons/{}.png'.format(c[1].lower())))
		
		return cs

	def events(self,url):
		out = []
		self.s.headers.update({'referer': self.base})
		html = self.s.get(url).text
		
		soup = webutils.bs(html)
		table = soup.find('div', {'class':'col-12 col-md-9'})
		events = table.findAll('a')
		for event in events:
			title = event['title']
			url  = self.base + event['href']
			try:
				time = event.findAll('span')[1]['content']
			except:
				time = None
			if time:
				t1, t2 = time.split('T')
				time = t2
				year, month, day = t1.split('-')
				time, stamp = self.convert_time(time, year, month, day)
				title = u"({}) [B]{}[/B]".format(time, title)

			out.append((url, title))
		return out

	def links(self, url, timeout=int(control.setting('cache_timeout'))):
		#return self._links(url)
		return cache.get(self._links, timeout, url)

	def _links(self,url):
		self.s.headers.update({'referer': self.base})
		html = self.s.get(url).text
		links = re.findall('text\-warning.+?ur(?:i|l)\s*=\s*[\"\']([^\"\']+).+?>([^<]+)', html)
		titles = {}
		inp = []
		for l in links:
			url = self.base + l[0]
			inp.append(url)
			titles[url] = l[1].strip()

		ret = linkSearch.getLinks(inp)

		out2 = []
		for u in ret:
			out2.append((u, titles[u]))

		return out2

	@staticmethod
	def convert_time(time,year, month, day):
		def month_converter(month):
			months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
			return months.index(month) + 1
		li = time.split(':')
		hour,minute=li[0],li[1]
		#month = month_converter(month)
		import datetime
		import pytz
		d = pytz.timezone(str(pytz.timezone('Europe/London'))).localize(datetime.datetime(int(year), int(month), int(day), hour=int(hour), minute=int(minute)))
		timezona = control.setting('timezone_new')
		my_location = pytz.timezone(constants.get_zone(int(timezona)))
		convertido=d.astimezone(my_location)
		fmt = "%m/%d %H:%M"
		time=convertido.strftime(fmt)
		return time, timestamp(convertido)

	def resolve(self,url):
		from resources.lib.modules import liveresolver
		d = liveresolver.Liveresolver().resolve(url)
		if not d:
			return None
		if d['url'].startswith('plugin://'):
			return d['url']

		if d:
			return '{}|{}'.format(d['url'], urlencode(d['headers'])), False
		return ' '


	def search(self, query):
		query = quote(query)
		search_url = self.search_url.format(query)
		return self.events(search_url)