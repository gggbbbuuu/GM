from ..models import *
import requests, re
from bs4 import BeautifulSoup

class NizarStream(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["nizarstream.com", "smartermuver.com"]
        self.name = "NizarStream"


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        r = requests.get(f"https://{self.domains[0]}").text
        soup = BeautifulSoup(r, "html.parser")
        for section in soup.select("div.jumbotron"):
            header = section.select_one("button").text.strip()
            for item in section.select("div.col-lg-3 > a"):
                href = f"https://{self.domains[0]}/" + item.get("href")
                p = item.select("p")
                league = p[0].text
                home = p[1].text
                away = p[3].text
                extra = p[4].text or "LIVE"
                title = f"{header}: {home} vs. {away} - {extra}"
                items.append(JetItem(title, links=[JetLink(href)], league=league))
        return items
    

    def get_link(self, url: JetLink) -> JetLink:
        r = requests.get(url.address).text
        iframe = re.findall(r'iframe.+?src="(.+?)"', r)[0].strip()
        ch = iframe.split("/")[-1][2:]
        embed = f"https://{self.domains[1]}/embedred.php?player=desktop&live=do{ch}"
        r = requests.get(embed, headers={"Referer": iframe}).text
        address = "".join(eval(re.findall(r'return\((\["h","t".+?\])', r)[0])).replace("\\", "").replace("////", "//")
        return JetLink(address, headers={"Referer": f"https://{self.domains[1]}/"})
    