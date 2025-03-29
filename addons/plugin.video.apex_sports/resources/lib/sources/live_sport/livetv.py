# -*- coding: utf-8 -*-
from resources.lib.modules import webutils, control, cache, linkSearch, constants
import re, sys
from resources.lib.modules.log_utils import log
try:
	from urllib.parse import urlparse, quote_plus, urlencode
except:
	from urlparse import urlparse
	from urllib import quote_plus, urlencode
# python 2 doesn't support date.datetime.timestamp()
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
		self.mode = 'livetv'
		self.name = 'Livetv.sx'
		self.icon = 'livetv.png'
		self.enabled = control.setting(self.mode) == 'true'
		self.categorized = True
		self.paginated = False
		self.multilink = True
		self.searchable = True

class main():
	def __init__(self, url = ''):
		self.base = control.setting('livetv_base')
		self.search_url = self.base+'/enx/megasearch/?msq={}'

	def categories(self):
		import requests
		self.html = requests.get(self.base + '/en/allupcoming').text
		
		cats = re.findall('<tr>\s*<[^<]*<a class="main" href="([^"]*allupcomingsports/(\d+)/)"><img[^>]*src="([^"]+)"></a></td>\s*<td align="left">[^<]*<a[^<]*<b>([^<]*)</b></a>\s*</td>\s*<td width=\d+ align="center">\s*<a [^<]*<b>\+(\d+)</b></a>\s*</td>\s*</tr>', self.html)
		cats = self.__prepare_cats(cats)
		return cats

	def events(self,url):
		import requests
		html = requests.get(url).text
		soup = webutils.bs(html)
		soup = soup.find('table',{'class':'main'})

		events = soup.findAll('td',{'colspan':'2', 'height':'38'})
		events = self.__prepare_events(events)
		return events

	def links(self, url, timeout=int(control.setting('cache_timeout'))):
		#return self._links(url)
		return cache.get(self._links, timeout, url)

	def _links(self,url):
		import requests
		html = requests.get(url).text
		links = re.findall('title\s*=\s*[\"\']([^\"\']*)[^$]+linkflag.+?Kbps.+?>([^<]*).+?\&nbsp;(\d*).+?href\s*=\s*[\"\']([^\"\']+).+?(?:&nbsp.+?>([^<]+))?', html, re.DOTALL)
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


	@staticmethod
	def convert_time(time,month, day):
		def month_converter(month):
			months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
			return months.index(month) + 1
		li = time.split(':')
		hour,minute=li[0],li[1]
		month = month_converter(month)
		import datetime
		import pytz
		d = pytz.timezone('Europe/London').localize(datetime.datetime(2021 , int(month), int(day), hour=int(hour), minute=int(minute)))
		timezona = control.setting('timezone_new')
		my_location = pytz.timezone(constants.get_zone(int(timezona)))
		convertido=d.astimezone(my_location)
		fmt = "%m/%d %H:%M"
		time=convertido.strftime(fmt)
		return time, timestamp(convertido)
		

	def __prepare_links(self,links):
		new = []
		for link in links:
			streamer_tmp = 'Web'
			url = 'http:' + link[3]
			if 'acestream' in url:
				continue
			health = link[2]
			lang = link[0]
			if u'ð' in lang:
				lang = 'unknown'
			if 'aliez' in url:
				streamer_tmp = 'Aliez'
			if lang == '':
				lang = 'unknown'
			
			bitrate = link[1]
			title = "%s | %s | %s"%(streamer_tmp,lang, bitrate)
			new.append((url,title.replace('ifr','flash')))
			
		return new




	def __prepare_cats(self,cats):
		new = []
		for cat in cats:
			url = self.base + cat[0]
			title = cat[3] + ' (%s)'%cat[4]
			id = self.get_id(cat[3])
			img = 'icons/%s.png'%id
			new.append((url,title,img))

		return new

	def get_id(self,id):
		id = id.lower().replace(' ','_')
		id = id.replace('ice_hockey','hockey').replace('football','soccer').replace('american_soccer','football').replace('rugby_union','rugby').replace('combat_sport','fighting').replace('winter_sport','skiing').replace('water_sports','waterpolo').replace('billiard','snooker')
		return id

	def __prepare_events(self,events):
		new=[]
		for ev in events:
			url = self.base + ev.find('a')['href']
			event = ev.find('a').getText()
			info = ev.find('span', {'class':'evdesc'}).getText()
			try:
				league = re.findall('\((.+?)\)', info)[0]
			except:
				league = ''

			time = re.findall('(\d+:\d+)',info)[0]
			day,month = re.findall('(\d+) (\w+) at',info)[0]
			time, timestamp = self.convert_time(time,month, day)
			color = 'orange'
			if 'live.gif' in str(ev):
				time = '[COLOR red]LIVE[/COLOR]'
			title = u'(%s) [B]%s[/B] - (%s)'%(time, event, league)        
			new.append(((url,title), timestamp))

		new = list(set(new))
		new.sort(key=lambda x: x[1])	
		new = [x[0] for x in new]
		return new

	def resolve(self,url):
		from resources.lib.modules import liveresolver
		d = liveresolver.Liveresolver().resolve(url)
		if d:
			if d['url'].startswith('plugin://'):
				return d['url']

			return '{}|{}'.format(d['url'], urlencode(d['headers'])), False
		return ' '
	
	def search(self, query):
		query = quote_plus(query)
		search_url = self.search_url.format(query)
		import requests
		html = requests.get(search_url).text
		tables = webutils.bs(html).findAll('table')
		table = None
		for i in range(len(tables)):
			if tables[i].getText().strip() == 'Broadcast Schedules':
				table = tables[i+1]
				break
		tds = table.findAll('td')
		league = ''
		out = []
		for i in range(len(tds)):
			if (i%2 == 0):
				league = tds[i].find('img')['title']
			else:
				a = tds[i].find('a')
				url = self.base + a['href']
				ev = a.getText().strip()
				ev_time = tds[i].find('span', {'class': 'date'}).getText()
				t1, t2 = ev_time.split('at')
				day = t1.split(' ')[0].strip()
				month = t1.split(' ')[1].strip()
				t = t2.strip()
				tm, stamp = self.convert_time(t, month, day)
				title = u'(%s) [B]%s[/B] - (%s)'%(tm, ev, league)        
				out.append((url, title))

		return out


