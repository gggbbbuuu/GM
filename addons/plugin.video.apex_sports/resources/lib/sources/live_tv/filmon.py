import re, requests
from resources.lib.modules.log_utils import log
from resources.lib.modules import control
try:
	from urllib.parse import urlencode
except:
	from urllib import urlencode
class info():
	def __init__(self):
		self.mode = 'filmon'
		self.name = 'filmon.com'
		self.icon = 'filmon.png'
		self.enabled = control.setting(self.mode) == 'true'
		self.paginated = False
		self.categorized = True
		self.multilink = False


class main():
	def __init__(self,url = 'http://www.filmon.com/group'):
		self.base = 'http://www.filmon.com'
		self.url = url

	def categories(self):
		html = requests.get(self.url).text
		cats = re.findall('<li class="group-item">\s*<a href="([^"]+)">\s*<img class="logo" src="([^"]+)" title="[^"]+" style="[^"]+" />\s*<span class="group-title">([^<]+)</span>',html)
		out = []
		for cat in cats:
			url = self.base + cat[0]
			img = cat[1]
			ch = cat[2].encode('utf-8')
			out.append((url,ch,img))
		return out

	def events(self,url):
		self.url = url
		html = requests.get(url, headers={'referer': self.base}).text
		regex='<a href="([^"]+)" class="clearfix" onclick="return false;">\s*<img class="channel_logo" src="([^"]+)" title="([^"]+)'
		channels=re.compile(regex).findall(html)
		events = self.__prepare_channels(channels)
		events.sort(key=lambda x: x[1])
		return events

	def __prepare_channels(self,channels):
		new=[]
		for channel in channels:
			url = self.base + channel[0]
			img = channel[1]
			title = channel[2]
			new.append((url,title,img))

		return new


	

	def resolve(self,url):
		from resources.lib.modules import liveresolver
		d = liveresolver.Liveresolver().resolve(url)
		if not d or d is None:
			return ' '
		if d['url'].startswith('plugin://'):
			return d['url']

		if d:
			return '{}|{}'.format(d['url'], urlencode(d['headers'])), False
		return ''