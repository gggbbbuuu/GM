import requests, re
from bs4 import BeautifulSoup
from dateutil.parser import parse
from urllib.parse import urlparse
from datetime import timedelta
from ..models import *
from ..util import m3u8_src
from .daddylive import Daddylive
from .vecdn import VeCDN

class Cricfree(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["cricfree.live", "hd.cricfree.io"]
        self.name = "Cricfree"
#######  NEED FIXING  ########
    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[1]}", timeout=self.timeout)
        soup = BeautifulSoup(r.text, "html.parser")
        for table in soup.select("table"):
            date = table.select_one("th").text
            for row, link_row in zip(table.select("tr.info-open"), table.select("tr.info")):
                time = row.select_one("td.time").text.strip()
                utc_time = parse(date + time) - timedelta(hours=1)
                title = row.select_one("td.event").text.strip()
                league = row.select_one("td.competition").text.strip()
                links = [JetLink(a.get("href"), links=True) for a in link_row.select("a")]
                items.append(JetItem(title, links, starttime=utc_time, league=league))

        if self.progress_update(progress):
            return items

        r_channels = requests.get(f"https://{self.domains[0]}/live/sky-sports-main-event", timeout=self.timeout)
        soup_channels = BeautifulSoup(r_channels.text, "html.parser")
        channel = soup_channels.find('ul', class_='nav-sidebar')
        if channel:
            channels_links = channel.find_all('a')
            for link in channels_links:
                title = link['title']
                href = link['href']
                items.append(JetItem(league="Channel", title=title ,links=[JetLink(href, links=True)]))

        return items
    
    def get_links(self, url: JetLink) -> List[JetLink]:
        r = requests.get(url.address).text
        iframe = re.findall(r'iframe src="(.+?)"', r)[0]
        soup = BeautifulSoup(r, "html.parser")
        buttons = soup.select("div.channel_names > button")
        links = [JetLink(iframe.replace("/live/embed", f"/live/embed/{link}") if (link := re.findall(r'changeLink\(\'(.+?)\'\)', b.get('onclick'))[0]) != "link1" else iframe, name=b.text) for b in buttons]
        return links

    def get_link(self, url: JetLink) -> JetLink:
        if "/live/embed" in url.address:
            iframe = url.address.replace(f"https://{self.domains[0]}/live/embed", "https://cricplay2.xyz")
            r_iframe = requests.get(iframe).text
        else:
            r = requests.get(url.address).text
            iframe = re.findall(r'iframe src="(.+?)"', r)[0].replace(f"https://{self.domains[0]}/live/embed", "https://cricplay2.xyz")
            r_iframe = requests.get(iframe).text
        
        v = VeCDN()
        d = Daddylive()
        if "fid=" in r_iframe:
            return v.get_link(JetLink(iframe))
        else:
            re_link = re.findall(r'iframe src="(.+?)"', r_iframe)[0].strip()
            if re_link.startswith("//"):
                re_link = "https:" + re_link
            if "popcdn" in re_link:
                r_popcdn = requests.get(re_link).text
                iframe = re.findall(r'iframe.+?src="(.+?)"', r_popcdn)[0]
                popcdn = urlparse(iframe)
                stream = popcdn.path.split("/")[1]
                token = popcdn.query.split("&")[0].split("=")[1]
                netloc = popcdn.netloc
                link = f"https://{netloc}/{stream}/index.fmp4.m3u8?token={token}"
                referer = f"https://{netloc}/{stream}/embed.html?token={token}&remote=no_check_ip"
                return JetLink(link, headers={"Referer": referer})
            if "topembed" in re_link:
                return m3u8_src.scan_page(re_link)
            if d.is_available(JetLink(re_link)):
                return d.get_link(JetLink(re_link.replace("/embed/", "/stream/")))
            else:
                return v.get_link(JetLink(re_link))