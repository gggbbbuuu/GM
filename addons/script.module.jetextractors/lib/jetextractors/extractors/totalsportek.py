from ..models import *
from ..util.resolver import UniversalResolver
import requests
import re
import xbmc
from ..tools import debug_log
from bs4 import BeautifulSoup


class TotalSportek(JetExtractor):
    def __init__(self) -> None:
        self.domains = [
            "total-sportek.st",
            "live2.totalsporteks.st",
            "live3.totalsporteks.st",
            "live4.totalsporteks.st",
            "live5.totalsporteks.st",
            "totalsportekx.is",
            "streameast100.is",
            "totalsportek.nexus",
            "totalsportekz.app"
        ]
        self.name = "TotalSportek"
        self.resolver = UniversalResolver(self.user_agent, "[TotalSportek]")

    def get_items(self, params=None, progress=None):
        items = []
        if self.progress_init(progress, items):
            return items

        debug_log(f"[TotalSportek] Fetching homepage", xbmc.LOGINFO)
        try:
            r = requests.get(f"https://{self.domains[0]}", timeout=10)
            debug_log(f"[TotalSportek] Homepage status: {r.status_code}", xbmc.LOGINFO)
            soup = BeautifulSoup(r.text, "html.parser")

            for game in soup.select("a.text-decoration-none.nav-link2"):
                href = game.get("href")
                if not href:
                    continue
                teams = game.select("div.row.my-auto")
                title = " vs ".join([team.text.strip() for team in teams])
                status_elem = game.select_one("div.col-3.fs-8, div.col-2.fs-8")
                status = status_elem.text.strip() if status_elem else ""
                # debug_log(f"[TotalSportek] Game: {title} ({status}) -> {href}", xbmc.LOGINFO)
                items.append(JetItem(title, links=[JetLink(href, links=True)], status=status))
        except Exception as e:
            debug_log(f"[TotalSportek] Error fetching homepage: {e}", xbmc.LOGERROR)

        # debug_log(f"[TotalSportek] Total items: {len(items)}", xbmc.LOGINFO)
        return items

    def get_links(self, url):
        links = []
        debug_log(f"[TotalSportek] get_links: {url.address}", xbmc.LOGINFO)

        try:
            r = requests.get(url.address, timeout=10)
            debug_log(f"[TotalSportek] Game page status: {r.status_code}", xbmc.LOGINFO)
            soup = BeautifulSoup(r.text, "html.parser")

            for data_row in soup.select("div.col-md-12.data-row"):
                a_tag = data_row.select_one("a")
                if not a_tag:
                    continue

                href = a_tag.get("href")
                cols = data_row.select("div.col-md-3.col-5")
                streamer = cols[0].text.strip() if len(cols) > 0 else ""
                channel = cols[1].text.strip() if len(cols) > 1 else ""
                display_cols = data_row.select("div.col-md-1.display-small")
                quality = display_cols[1].text.strip() if len(display_cols) > 1 else ""
                language = display_cols[3].text.strip() if len(display_cols) > 3 else ""

                name = f"{streamer} - {channel}"
                if quality:
                    name += f" [{quality}]"
                if language:
                    name += f" ({language})"
                name = name.replace("(", "").replace(")", "").strip()
                if "english" in name.lower():
                    name = name.replace("english", "[COLOR=white]english[/COLOR]")
                debug_log(f"[TotalSportek] Link: {name} -> {href}", xbmc.LOGINFO)
                links.append(JetLink(href, name=name))
        except Exception as e:
            debug_log(f"[TotalSportek] Error getting links: {e}", xbmc.LOGERROR)

        debug_log(f"[TotalSportek] Total links: {len(links)}", xbmc.LOGINFO)
        return links

    def get_link(self, url):
        debug_log(f"[TotalSportek] get_link: {url.address}", xbmc.LOGINFO)

        try:
            stream_url = self.resolver.resolve_url(url.address)
            if stream_url:
                
                debug_log(f"[TotalSportek] Resolved stream: {stream_url}", xbmc.LOGINFO)
                
                return JetLink(
                    stream_url,
                    headers={
                        "Referer": url.address,
                        "User-Agent": self.user_agent
                    }
                )

            r = requests.get(url.address, timeout=10, headers={"User-Agent": self.user_agent})
            html = r.text

            config = self.resolver.extract_worker_config(html)
            if config:
                wd, wk, wri = config
                worker_url = self.resolver.decrypt_worker_url(wd, wk, wri)
                if worker_url:
                    debug_log(f"[TotalSportek] Decrypted worker: {worker_url}", xbmc.LOGINFO)
                    stream_url = self.resolver.resolve_worker(worker_url, url.address)
                    if stream_url:
                        debug_log(f"[TotalSportek] Worker stream: {stream_url}", xbmc.LOGINFO)
                        return JetLink(
                            stream_url,
                            headers={
                                "Referer": worker_url,
                                "User-Agent": self.user_agent
                            }
                        )

            iframes = self.resolver.resolve_iframes(html, url.address)
            debug_log(f"[TotalSportek] Found {len(iframes)} iframes", xbmc.LOGINFO)

            for iframe_url in iframes:
                if "youtube.com" in iframe_url:
                    continue
                debug_log(f"[TotalSportek] Following iframe: {iframe_url}", xbmc.LOGINFO)

                try:
                    stream_url = self.resolver.resolve_url(iframe_url, url.address, depth=1)
                    if stream_url:
                        debug_log(f"[TotalSportek] Stream from iframe: {stream_url}", xbmc.LOGINFO)
                        return JetLink(
                            stream_url,
                            headers={
                                "Referer": iframe_url,
                                "User-Agent": self.user_agent
                            }
                        )
                except Exception as e:
                    debug_log(f"[TotalSportek] Iframe error: {e}", xbmc.LOGWARNING)

            debug_log(f"[TotalSportek] No stream found", xbmc.LOGWARNING)
        except Exception as e:
            debug_log(f"[TotalSportek] Error in get_link: {e}", xbmc.LOGERROR)

        return None
