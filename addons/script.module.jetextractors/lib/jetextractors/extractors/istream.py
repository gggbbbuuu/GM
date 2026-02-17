import requests, re
from bs4 import BeautifulSoup
from ..models import *
from ..util import find_iframes, m3u8_src
from ..icons import icons

class IStreamEast(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["istreameast.app","gooz.aapmains.net"]
        self.name = "IStreamEast"
        self.short_name = "SE"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        base_url = f"https://{self.domains[0]}"
        
        try:
            r = requests.get(base_url, timeout=self.timeout, headers={"User-Agent": self.user_agent})
            soup = BeautifulSoup(r.text, "html.parser")
        except requests.exceptions.RequestException:
            return items
        
        event_items = soup.find_all("li", class_="f1-podium--item")
        
        for item in event_items:
            link_tag = item.find("a", class_="f1-podium--link")
            if not link_tag:
                continue
            
            href = link_tag.get("href", "")
            if not href:
                continue
            
            if href.startswith("/"):
                href = base_url + href
            
            rank_tag = item.find("span", class_="f1-podium--rank")
            league = rank_tag.text.strip() if rank_tag else ""
            
            title_tag = item.find("span", class_="f1-podium--driver")
            title = title_tag.text.strip() if title_tag else ""
            
            time_tag = item.find("span", class_="f1-podium--time")
            status = ""
            if time_tag:
                live_tag = time_tag.find("span", style=lambda x: x and "color: #930f0d" in x if x else False)
                if live_tag:
                    status = "LIVE"
                else:
                    time_text = time_tag.text.strip()
                    if time_text:
                        status = time_text
            
            full_title = f"[{status}] {title}" if status else title
            
            if full_title and href:
                links = self.get_links(href)
                
                if links:
                    jet_links = links
                else:
                    jet_links = [JetLink(href)]
                
                items.append(JetItem(
                    icon=icons[league.lower()] if league.lower() in icons else None,
                    league=league.upper(),
                    title=full_title,
                    links=jet_links
                ))
        
        return items
    
    def get_links(self, event_url: str) -> List[JetLink]:
        links = []
        try:
            r = requests.get(event_url, timeout=self.timeout, headers={"User-Agent": self.user_agent})
            
            stream_buttons = re.findall(r'<div[^>]+id="stream-btn-(\d+)"[^>]+onclick="window\.changeStream\((\d+)\)"[^>]*>\s*([^<]+)', r.text)
            
            if stream_buttons:
                for stream_id, _, channel_name in stream_buttons:
                    channel_name = channel_name.strip()
                    stream_url = f"https://gooz.aapmains.net/new-stream-embed/{stream_id}"
                    links.append(JetLink(stream_url, name=channel_name))
            else:
                iframe_match = re.search(r'<iframe[^>]+id="wp_player"[^>]+src="([^"]+)"', r.text, re.IGNORECASE)
                if not iframe_match:
                    iframe_match = re.search(r"document\.getElementById\('wp_player'\)\.src\s*=\s*'([^']+)'", r.text)
                
                if iframe_match:
                    iframe_url = iframe_match.group(1)
                    if not iframe_url.startswith("http"):
                        iframe_url = "https://" + iframe_url.lstrip("/")
                    links.append(JetLink(iframe_url))
                    
        except Exception:
            pass
        
        return links

    def get_link(self, url: JetLink) -> JetLink:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        base_headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        original_url = url.address
        
        if "gooz.aapmains.net" in original_url or "new-stream-embed" in original_url:
            stream_headers = base_headers.copy()
            stream_headers["Referer"] = f"https://{self.domains[0]}/"
            try:
                resolved = find_iframes.find_iframes(original_url, "", [], [], stream_headers)
                if resolved:
                    first = resolved[0]
                    if isinstance(first, str):
                        return JetLink(first, headers=stream_headers, inputstream=JetInputstreamFFmpegDirect.default())
                    return first
            except Exception:
                pass
            return url
        
        stream_headers = base_headers.copy()
        stream_headers["Referer"] = f"https://{self.domains[0]}/"
        
        try:
            r = requests.get(original_url, timeout=self.timeout, headers=base_headers)
            
            iframe_match = re.search(r'<iframe[^>]+id="wp_player"[^>]+src="([^"]+)"', r.text, re.IGNORECASE)
            if not iframe_match:
                iframe_match = re.search(r"document\.getElementById\('wp_player'\)\.src\s*=\s*'([^']+)'", r.text)
            
            if iframe_match:
                iframe_url = iframe_match.group(1)
                if not iframe_url.startswith("http"):
                    iframe_url = "https://" + iframe_url.lstrip("/")
                
                resolved = find_iframes.find_iframes(iframe_url, "", [], [], stream_headers)
                if resolved:
                    first = resolved[0]
                    if isinstance(first, str):
                        return JetLink(first, headers=stream_headers, inputstream=JetInputstreamFFmpegDirect.default())
                    return first
            
            m3u8_link = m3u8_src.scan_page(original_url, html=r.text)
            if m3u8_link:
                return m3u8_link
                
        except Exception:
            pass
        
        return url
