from resources.lib.modules import webutils, control, cache, linkSearch, constants
from resources.lib.modules.log_utils import log
import re, os, requests
try:
	from urllib.parse import urlencode
except:
	from urllib import urlencode


AddonPath = control.addonPath
IconPath = AddonPath + "/resources/media/"
def icon_path(filename):
	return os.path.join(IconPath, filename)

class info():
	def __init__(self):
		self.mode = 'rojadirecta'
		self.name = 'Rojadirecta.eu'
		self.icon = 'roja.jpg'
		self.enabled = control.setting(self.mode) == 'true'
		self.categorized = False
		self.paginated = False
		self.multilink = True
		self.searchable = True

class main():
	def __init__(self, url = ''):
		self.base = "http://www.rojadirecta.eu"

	def links(self, url, timeout=int(control.setting('cache_timeout'))):
		return cache.get(self._links, timeout, url)


	def _links(self, url):
		result = requests.get(self.base, headers={'user-agent': constants.USER_AGENT}).text
		soup = webutils.bs(result)
		table = soup.find('span',{'class': url})
		links = table.findAll('tr')
		links.pop(0)
		links = self.__prepare_links(links)

		if len(links) == 0:
			return []
		titles = {}
		for l in links:
			titles[l[0]] = l[1]

		links = [u[0] for u in links]

		ret = linkSearch.getLinks(links)

		
		out2 = []
		for u in ret:
			out2.append((u, titles[u]))

		return out2
		return links

	def events(self):
		import requests
		headers = {'User-Agent': constants.USER_AGENT, 'referer': self.base}
		result = requests.get(self.base, headers=headers).text
		reg = re.compile('<span class=[\"\'](.+?)[\"\'].+\s*.+<div class=[\"\']menutitle[\"\'].+?content\s*=\s*[\"\']([^\"\']+).+?<span class=[\"\']t[\"\']>.+?</span>(.+?)</div>')
		events = re.findall(reg,result)
		events = self.__prepare_events(events)
		return events
	

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
		d = pytz.timezone(str(pytz.timezone('Europe/Ljubljana'))).localize(datetime.datetime(int(year), int(month), int(day), hour=int(hour), minute=int(minute)))
		timezona = control.setting('timezone_new')
		my_location = pytz.timezone(constants.get_zone(int(timezona)))
		convertido=d.astimezone(my_location)
		fmt = "%m/%d %H:%M"
		time=convertido.strftime(fmt)
		return time

	

	def __prepare_events(self,events):
		new = []
		for event in events:
			try:
				url = event[0]
				title = event[2]
				title = re.sub('<span class="es">.*?</span>','',title).replace('<span class="en">','').replace('</span>','').replace('()','').replace('</time>','').replace('<span itemprop="name">','')
				sport,title = re.findall('(.*)<b>\s*(.*?)\s*</b>',title)[0]
				sport = sport.replace(':','')
				time = event[1]
				t1, t2 = time.split('T')
				time = t2
				year, month, day = t1.split('-')
				time = self.convert_time(time, year, month, day)
				#title = u'[COLOR orange](%s)[/COLOR] (%s) [B]%s[/B]'%(time,sport,title)
				title = u'(%s) [B]%s[/B] - %s'%(time, title, sport)
				title = title.encode('utf-8')
				new.append((url,title, info().icon))
			except:
				pass
		
		return new

	def __prepare_links(self,links):
		new=[]        
		i=1
		items = len(links)
		for link in links:
			info = link.findAll('td')
			name = info[1].getText()
			lang = info[2].getText()
			service = info[3].getText()
			kbps = info[4].getText()
			url = info[5].find('a')['href']
			title = u"%s (%s, %skbps) - %s"%(name, lang, kbps, service)
			new.append((url,title))
		return new

	def resolve(self,url):
		if 'it.rojadirecta' in url:
			html = requests.get(url, headers={'referer':self.base, 'user-agent': constants.USER_AGENT}).text
			url = re.findall('href\s*=\s*[\"\']([^\"\']+)', html)[0]
		from resources.lib.modules import liveresolver
		d = liveresolver.Liveresolver().resolve(url)
		if not d or d is None:
			return ''
		if d['url'].startswith('plugin://'):
			return d['url']

		if d:
			return '{}|{}'.format(d['url'], urlencode(d['headers'])), False
		return ' '

	def search(self, query):
		query = query.lower()
		evs = self.events()
		out = []
		for ev in evs:
			try: 
				v = ev[1].lower()
				if query in v:
					out.append(ev)
			except: 
				v = ev[1].lower()
				if query.encode('utf-8') in v:
					out.append(ev)
			
		return out