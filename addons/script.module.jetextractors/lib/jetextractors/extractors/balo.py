import requests
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, quote
from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress, JetInputstreamFFmpegDirect
from typing import Optional, List


class Balo(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["bingsport3.com", "cdn-rum.n2olabs.pro"]
        self.name = "Balo"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        r = requests.get(f"https://{self.domains[0]}", timeout=self.timeout).text
        soup = BeautifulSoup(r, 'html.parser')

        for game in soup.select("a.item-match"):
            href = game.get("href")
            league_name = game.select_one("div.league-name").text.strip()
            if teams := game.select("div.txt-team-name"):
                title = " vs. ".join([team.text.strip() for team in teams])
            else:
                title = game.select_one("div.txt-name").text.strip()
            items.append(JetItem(title, links=[JetLink(href, links=True)], league=league_name))
        return items
    

    def get_links(self, url: JetLink) -> List[JetLink]:
        r = requests.get(url.address).text
        match_info = json.loads(re.findall(r'var matchInfo = (.+?);', r)[0])
        me = requests.post(f"https://{self.domains[0]}/me").json()
        token = me["token_livestream"].split(".")
        link_format = f"https://{self.domains[1]}/stream.m3u8?url={{}}&token={token[0]}&is_vip={token[1]}&verify={quote(token[2])}"
        links = []
        for link in match_info["links"]:
            links.append(JetLink(link_format.format(quote(link["stream_link"], safe="")), unquote=False, inputstream=JetInputstreamFFmpegDirect.default(), headers={"Referer": f"https://{urlparse(link['iframe_link']).netloc}/", "User-Agent": self.user_agent}, name=link["display_name"], direct=True))
        return links
    

    def get_link(self, url: JetLink) -> JetLink:
        if "/live-sport/" in url.address:
            return self.get_links(url)[0]
        else:
            tv_id = parse_qs(urlparse(url.address).query)["tv"][0]
            r = requests.get(url.address).text
            soup = BeautifulSoup(r, 'html.parser')
            tv = soup.select_one(f'div[data-slug="{tv_id}"]')
            href = tv.get("data-link")
            link = JetLink(parse_qs(urlparse(href).query)["m3u8"][0], headers={"Referer": f"https://{urlparse(href).netloc}/"}) if "m3u8" in href else JetLink(href)
            return link

