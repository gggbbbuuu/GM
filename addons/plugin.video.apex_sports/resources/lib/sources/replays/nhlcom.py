import re, json
import requests
from resources.lib.modules.log_utils import log
from resources.lib.modules import control

class info():
	def __init__(self):
		self.mode = 'nhlcom'
		self.name = 'nhl.com'
		self.icon = 'nhl.png'
		self.enabled = control.setting(self.mode) == 'true'
		self.paginated = True
		self.categorized = True
		self.multilink = False


class main():
	def __init__(self, url = ''):
		self.url = url
		self.base = 'https://www.nhl.com'
		self.event_url = 'https://search-api.svc.nhl.com/svc/search/v2/nhl_global_en/topic/{}?page={}&sort=new&type=video&hl=false&expand=image.cuts.640x360%2Cimage.cuts.1136x640&listed=true'

	def categories(self):
		html = requests.get(self.base + '/video/').text
		cs = re.findall('/video/t-(\d+).+?>([^<]+)', html, flags=re.DOTALL)
		out = []
		for c in cs:
			out.append((self.event_url.format(c[0], '1'), c[1]))
		return out

	def events(self, url):
		self.url = url
		
		out = []
		html = requests.get(url).text
		query = json.loads(html)
		events = query['docs']
		for e in events:
			link = e['asset_id']

			title=e['blurb']
			imgs = list(e['image']['cuts'].keys())
			imgs.sort(reverse=True, key=lambda x: eval(x.replace('x','*')))
			thumb = e['image']['cuts'][imgs[0]]['src']
			
			out.append((link, title, thumb))
		return out

	def resolve(self, link):

		url = 'https://cms.nhl.bamgrid.com/nhl/id/v1/{}/details/web-v1.json'.format(link)
		js = requests.get(url)
		js = json.loads(js.text)
		return js['playbacks'][-1]['url']	    

	def next_page(self):
		
		current = re.findall("page=(\d+)",self.url)[0]
		next = str(int(current) + 1)
		next_page = re.sub('page\=\d+', 'page='+next, self.url)
		
		return next_page


