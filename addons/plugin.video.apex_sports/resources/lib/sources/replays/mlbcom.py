import re, json
import requests
from resources.lib.modules.log_utils import log
from resources.lib.modules import constants
from resources.lib.modules import control
class info():
	def __init__(self):
		self.mode = 'mlbcom'
		self.name = 'mlb.com'
		self.icon = 'mlb.png'
		self.enabled = control.setting(self.mode) == 'true'
		self.paginated = True
		self.categorized = True
		self.multilink = False


class main():
	def __init__(self, url = ''):
		self.url = url
		self.base = 'https://www.mlb.com/'
		self.category_url = 'https://fastball-gateway.mlb.com/graphql?query=query%20getTopic(%24topicId%3A%20String!%2C%20%24languagePreference%3A%20LanguagePreference%2C%20%24limit%3A%20Int%2C%20%24page%3A%20Int%2C%20%24videoSlug%3A%20String%2C%20%24contentGroup%3A%20ContentGroup%2C%20%24videoTranslationId%3A%20String%2C%20%24sessionId%3A%20String)%20%7B%0A%20%20topicPlayList(topicId%3A%20%24topicId%2C%20languagePreference%3A%20%24languagePreference%2C%20limit%3A%20%24limit%2C%20page%3A%20%24page%2C%20videoSlug%3A%20%24videoSlug%2C%20contentGroup%3A%20%24contentGroup%2C%20videoTranslationId%3A%20%24videoTranslationId%2C%20sessionId%3A%20%24sessionId)%20%7B%0A%20%20%20%20hasMore%0A%20%20%20%20title%0A%20%20%20%20puid%0A%20%20%20%20modelType%0A%20%20%20%20modelVersion%0A%20%20%20%20mediaPlayback%20%7B%0A%20%20%20%20%20%20...MediaPlaybackFields%0A%20%20%20%20%20%20__typename%0A%20%20%20%20%7D%0A%20%20%20%20__typename%0A%20%20%7D%0A%7D%0A%0Afragment%20MediaPlaybackFields%20on%20MediaPlayback%20%7B%0A%20%20id%0A%20%20slug%0A%20%20title%0A%20%20blurb%0A%20%20description%0A%20%20date%0A%20%20canAddToReel%0A%20%20feeds%20%7B%0A%20%20%20%20type%0A%20%20%20%20duration%0A%20%20%20%20closedCaptions%0A%20%20%20%20playbacks%20%7B%0A%20%20%20%20%20%20name%0A%20%20%20%20%20%20url%0A%20%20%20%20%20%20segments%0A%20%20%20%20%20%20__typename%0A%20%20%20%20%7D%0A%20%20%20%20image%20%7B%0A%20%20%20%20%20%20altText%0A%20%20%20%20%20%20templateUrl%0A%20%20%20%20%20%20cuts%20%7B%0A%20%20%20%20%20%20%20%20aspectRatio%0A%20%20%20%20%20%20%20%20width%0A%20%20%20%20%20%20%20%20height%0A%20%20%20%20%20%20%20%20src%0A%20%20%20%20%20%20%20%20__typename%0A%20%20%20%20%20%20%7D%0A%20%20%20%20%20%20__typename%0A%20%20%20%20%7D%0A%20%20%20%20__typename%0A%20%20%7D%0A%20%20keywordsDisplay%20%7B%0A%20%20%20%20slug%0A%20%20%20%20displayName%0A%20%20%20%20__typename%0A%20%20%7D%0A%20%20translationId%0A%20%20playInfo%20%7B%0A%20%20%20%20balls%0A%20%20%20%20strikes%0A%20%20%20%20outs%0A%20%20%20%20inning%0A%20%20%20%20inningHalf%0A%20%20%20%20pitchSpeed%0A%20%20%20%20pitchType%0A%20%20%20%20exitVelocity%0A%20%20%20%20hitDistance%0A%20%20%20%20launchAngle%0A%20%20%20%20spinRate%0A%20%20%20%20scoreDifferential%0A%20%20%20%20gamePk%0A%20%20%20%20runners%20%7B%0A%20%20%20%20%20%20first%0A%20%20%20%20%20%20second%0A%20%20%20%20%20%20third%0A%20%20%20%20%20%20__typename%0A%20%20%20%20%7D%0A%20%20%20%20teams%20%7B%0A%20%20%20%20%20%20away%20%7B%0A%20%20%20%20%20%20%20%20name%0A%20%20%20%20%20%20%20%20shortName%0A%20%20%20%20%20%20%20%20triCode%0A%20%20%20%20%20%20%20%20__typename%0A%20%20%20%20%20%20%7D%0A%20%20%20%20%20%20home%20%7B%0A%20%20%20%20%20%20%20%20name%0A%20%20%20%20%20%20%20%20shortName%0A%20%20%20%20%20%20%20%20triCode%0A%20%20%20%20%20%20%20%20__typename%0A%20%20%20%20%20%20%7D%0A%20%20%20%20%20%20batting%20%7B%0A%20%20%20%20%20%20%20%20name%0A%20%20%20%20%20%20%20%20shortName%0A%20%20%20%20%20%20%20%20triCode%0A%20%20%20%20%20%20%20%20__typename%0A%20%20%20%20%20%20%7D%0A%20%20%20%20%20%20pitching%20%7B%0A%20%20%20%20%20%20%20%20name%0A%20%20%20%20%20%20%20%20shortName%0A%20%20%20%20%20%20%20%20triCode%0A%20%20%20%20%20%20%20%20__typename%0A%20%20%20%20%20%20%7D%0A%20%20%20%20%20%20__typename%0A%20%20%20%20%7D%0A%20%20%20%20players%20%7B%0A%20%20%20%20%20%20pitcher%20%7B%0A%20%20%20%20%20%20%20%20id%0A%20%20%20%20%20%20%20%20name%0A%20%20%20%20%20%20%20%20lastName%0A%20%20%20%20%20%20%20%20playerHand%0A%20%20%20%20%20%20%20%20__typename%0A%20%20%20%20%20%20%7D%0A%20%20%20%20%20%20batter%20%7B%0A%20%20%20%20%20%20%20%20id%0A%20%20%20%20%20%20%20%20name%0A%20%20%20%20%20%20%20%20lastName%0A%20%20%20%20%20%20%20%20playerHand%0A%20%20%20%20%20%20%20%20__typename%0A%20%20%20%20%20%20%7D%0A%20%20%20%20%20%20__typename%0A%20%20%20%20%7D%0A%20%20%20%20__typename%0A%20%20%7D%0A%20%20__typename%0A%7D%0A&operationName=getTopic&variables=%7B%22topicId%22%3A%22{}%22%2C%22languagePreference%22%3A%22EN%22%2C%22limit%22%3A20%2C%22page%22%3A{}%7D'

	def categories(self):
		html = requests.get(self.base + 'video').text
		cs = re.findall('"text.\":.\"([^\\\\"]+).+?link.\":.\"/topic/([^\\\\"]+)', html)
		out = []
		for c in cs:
			out.append((self.category_url.format(c[1], '0'), c[0]))
		return out

	def events(self, url):
		self.url = url
		
		out = []
		html = requests.get(url, headers={'user-agent':constants.USER_AGENT}).text
		query = json.loads(html)
		events = query['data']['topicPlayList']['mediaPlayback']
		
		for e in events:
			link = e['feeds'][0]['playbacks'][-1]['url']

			title = e['title']
			
			thumb = e['feeds'][0]['image']['cuts'][0]['src']
			
			out.append((link, title, thumb))
		return out

	def resolve(self, link):

		return link 

	def next_page(self):
		
		current = re.findall("page\%22%3A(\d+)",self.url)[0]
		next = str(int(current) + 1)
		next_page = self.url.replace('page%22%3A{}'.format(current), 'page%22%3A{}'.format(next))
		return next_page


