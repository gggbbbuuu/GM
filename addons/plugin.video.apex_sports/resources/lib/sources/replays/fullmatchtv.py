import re, json
import requests
from resources.lib.modules.log_utils import log
from resources.lib.modules.constants import USER_AGENT
from resources.lib.modules import control
try:
	from urllib.parse import urlencode
except:
	from urllib import urlencode

class info():
	def __init__(self):
		self.mode = 'fullmatchtv'
		self.name = 'fullmatchtv.com'
		self.icon = 'fullmatchtv.png'
		self.enabled = control.setting(self.mode) == 'true'
		self.paginated = True
		self.categorized = True
		self.multilink = True


class main():
	
	def __init__(self,url = 'https://fullmatchtv.com/nhl'):
		self.base = 'https://fullmatchtv.com'
		self.url = url
		self.post_url = 'https://fullmatchtv.com/wp-admin/admin-ajax.php?td_theme_name=Newspaper&v=10.3.7'
		self.postData = self.get_post()
		

	def get_post(self):
		content = requests.get(self.url, headers={'referer': self.base}).text		
		
		action = 'td_ajax_block'
		block_type = re.compile('block_type\s*=\s*[\"\']([^\"\']+)').findall(content)[0]
		td_atts = re.compile('\.atts\s*=\s*\'([^\']+)').findall(content)[1]
		td_block_id = re.findall('td\-block\-uid\s*=\s*[\"\']([^\"\']+)', content)[0]
		td_column_number = re.compile('column_number\s*=\s*[\"\']([^\"\']+)').findall(content)[0]
		nonce = re.findall('tdblocknonce\s*=\s*[\"\']([^\"\']+)', content, re.I)[0]
		data = {
			'action':action,
			'block_type':block_type,
			'td_atts':td_atts,
			'td_block_id':td_block_id,
			'td_column_number':td_column_number,
			'td_magic_token':nonce
		}
		try:
			data['td_current_page'] = self.url.split('##')[1]
		except:
			data['td_current_page'] = '1'
		return data

	def clean(self,text):
		def fixup(m):
			text = m.group(0)
			c = None
			if text[:3] == "&#x":
				try:
					c = unichr(int(text[3:-1], 16)).encode('utf-8')
				except:
					c = chr(int(text[3:-1], 16))#.encode('utf-8')
				return c
			else:
				try:
					c = unichr(int(text[2:-1])).encode('utf-8')
				except:
					c = chr(int(text[2:-1]))#.encode('utf-8')
				return c
		try :return re.sub("(?i)&#\w+;", fixup, text)#.encode('ISO-8859-1').decode('utf-8'))
		except:return re.sub("(?i)&#\w+;", fixup, text)#.encode("ascii", "ignore").decode('utf-8'))


	def categories(self):
		out = []
		html = requests.get(self.base).text
		cs = re.findall('menu-item.+?href=[\"\']([^\"\']+).+?>([^<]+)', html)
		for c in cs:
			if c[1] == 'Home':
				continue
			if c not in out:
				out.append((c[0], c[1], '{}.png'.format(c[1].lower())))
			if c[1] == 'Other sports':
				break
			
		return out

	def events(self, url):
		out = []
		import requests
		s = requests.session()
		
		self.url = url
		self.postData = self.get_post()

		if 'other' in url:
			data = s.get(url).text
		else:
			html = s.post(self.post_url,data=self.postData, headers={'user-agent': USER_AGENT, 'Sec-Fetch-Mode': 'cors','content-type': 'application/x-www-form-urlencoded; charset=UTF-8' , 'referer':url, 'x-requested-with':'XMLHttpRequest'}).text
			j = json.loads(html)
			data = j['td_data']
		items = re.findall('href=[\"\']([^\"\']+)[\"\'].+?title=[\"\']([^\"\']+)[\"\'].+?img.+?src=[\"\']([^\"\']+)[\"\']',data)
		for item in items:
			try:
				import HTMLParser
				parser = HTMLParser.HTMLParser()
				unescape = parser.unescape
			except:
				import html
				unescape = html.unescape
				
			title = unescape(item[1])
			out.append((item[0], title, item[2]))
		

		return out

	def links(self, url):
		out=[]
		html = requests.get(url).text
		try:
			img = re.findall('og\:image.+?content\s*=\s*[\"\']([^\"\']+)', html)[0]
		except:
			img = control.icon_path(info().icon)

		try:
			import resolveurl
		except:
			return []

		iframe = re.findall('iframe.+?src\s*=\s*[\"\']([^\"\']+)', html)
		i = 1
		for l in iframe:
			if l.startswith('//'):
					l = 'http:' + l
			hmf = resolveurl.HostedMediaFile(url=l)
			if hmf.valid_url():
				title = 'Link %s'%i
				i += 1
				out.append((l, title, img))

		return out
	
	def resolve(self,url):
		import resolveurl
		res = resolveurl.resolve(url)
		if res:
			return res
		return ' '

	def next_page(self):
		try:
			page = int(self.url.split('##')[1])
		except:
			page=1
		next = self.url.split('##')[0] + '##%s'%(page+1)
		return next