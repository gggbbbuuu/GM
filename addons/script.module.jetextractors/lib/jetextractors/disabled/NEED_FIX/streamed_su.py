import re
import json
import requests
from ..models import *
from xbmc import sleep

#######  NEED FIXING  ########
categories = ["basketball","american-football","baseball","motor-sports","rugby","cricket","afl","football",
              "hockey","fight","tennis","golf","darts","other"]

user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'
headers = {"User-Agent":user_agent, "referrer": 'daddylive.me', "Connection":'keep-alive', 'Accept':'audio/webm,audio/ogg,udio/wav,audio/*;q=0.9,application/ogg;q=0.7,video/*;q=0.6,*/*;q=0.5'}

class Streamedsu(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["streamed.su", "embedme.top"]
        self.categories = categories
        self.name = "Streamedsu"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        api_url = f"https://{self.domains[0]}/api/matches/all-today"
        r = requests.get(api_url, timeout=self.timeout)
        matches = r.json()
        for match in matches:
            title = match['title']
            if self.progress_update(progress, title):
                return items
            #sleep(50)
            league = match['category']
            sources = match.get('sources', [])
            if sources:
                items.append(JetItem(league=league.upper(), title=title, links=[JetLink(f'https://{self.domains[0]}/api/stream/', links=True, params={'sources': sources} )], starttime=None))
        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        params = url.params
        if params:
            sources = params.get('sources')
        else:
            r = requests.get(url.address, timeout=self.timeout).text
            sources = re.findall('sources:(\[.+?\])', r)
            if not sources:
                return
            sources = sources[0].replace('source:', '"source":').replace('id:', '"id":')
            sources = json.loads(sources)
        
        links = []
        for source in sources:
            source_id = source['id']
            source_name = source['source']
            api_url = f'https://{self.domains[0]}/api/stream/'
            stream_api_url = f"{api_url}{source_name}/{source_id}"
            r = requests.get(stream_api_url, timeout=self.timeout).json()
            if r:
                for stream in r:
                    stream_source = stream.get('source')
                    stream_num = stream.get('streamNo')
                    title = f'{stream_source} {stream_num}'
                    title += ' HD' if stream.get('hd') is True else ''
                    link = stream.get('embedUrl')
                    links.append(JetLink(link, name=title))
        return links
    
    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url, timeout=self.timeout).text
        info = re.findall(r'k="(.+?)",i="(.+?)",s="(.+?)",l=\["(.+?)"\],h="(.+?)"', r)[0]
        my_referer = "https://embedme.top/"
        my_starter = "https://info-fetch.vercel.app/api/stream?url=" 
        # my_link = f"{my_starter}https://{info[3]}.{info[4]}/{info[0]}/js/{info[1]}/{info[2]}/playlist.m3u8"
        # return JetLink(f"https://{info[3]}.{info[4]}/{info[0]}/js/{info[1]}/{info[2]}/playlist.m3u8", headers={"Referer": url})
        return JetLink(f"{my_starter}https://{info[3]}.{info[4]}/{info[0]}/js/{info[1]}/{info[2]}/playlist.m3u8", headers={"Referer": url})
        # return JetLink(my_link, headers={"Referer": url})
