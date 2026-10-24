from ..models import *
from ..util.resolver import UniversalResolver
from ..util.stream_proxy import build_proxy_url
from .._core import fetch_page
import xbmc
import os
import json
from ..tools import debug_log
from bs4 import BeautifulSoup

DEFAULT_EXCLUDED_HOSTS = (
    "topstreamer.site",
    "pitchstream.xyz",
    "streamsify.xyz",
    "hadcrak.cyou",
    "mackwatch.lol",
    "shd247.world",
    "goomdstea.click",
    "opturspapa.xyz",
)


class TotalSportek(JetExtractor):
    def __init__(self) -> None:
        self.domains = [
            "total-sportek.st",
            "live2.totalsporteks.st",
            "live3.totalsporteks.st",
            "live4.totalsporteks.st",
            "live5.totalsporteks.st",
            "totalsporteke.st",
            "live.totalsporteke.st",
            "live2.totalsporteke.st",
            "live3.totalsporteke.st",
            "live4.totalsporteke.st",
            "live5.totalsporteke.st",
            "live6.totalsporteke.st",
            "live7.totalsporteke.st",
            "live8.totalsporteke.st",
            "totalsportekx.is",
            "streameast100.is",
            "totalsportek.nexus",
            "totalsportekz.app",
            "totalsportek24.is",
            "www.totalsportek24.is",
            "totalsportekl.is",
            "www.totalsportekl.is",
            "links.totalsportekl.is",
            "hoofoot.is"
        ]
        self.name = "TotalSportek"
        self.resolver = UniversalResolver(self.user_agent, "[TotalSportek]")

    def get_items(self, params=None, progress=None):
        items = []
        if self.progress_init(progress, items):
            return items

        debug_log(f"[TotalSportek] Fetching homepage", xbmc.LOGINFO)
        try:
            r = fetch_page(f"https://{self.domains[0]}")
            debug_log(f"[TotalSportek] Homepage fetched", xbmc.LOGINFO)
            soup = BeautifulSoup(r, "html.parser")

            for game in soup.select("a.text-decoration-none.nav-link2"):
                href = game.get("href")
                if not href:
                    continue
                if href.startswith("/"):
                    href = f"https://{self.domains[0]}{href}"
                teams = game.select("div.row.my-auto")
                title = " vs ".join([team.text.strip() for team in teams])
                status_elem = game.select_one("div.col-3.fs-8, div.col-2.fs-8")
                status = status_elem.text.strip() if status_elem else ""
                items.append(JetItem(title, links=[JetLink(href, links=True)], status=status))
        except Exception as e:
            debug_log(f"[TotalSportek] Error fetching homepage: {e}", xbmc.LOGERROR)

        # debug_log(f"[TotalSportek] Total items: {len(items)}", xbmc.LOGINFO)
        return items

    def get_links(self, url):
        links = []
        debug_log(f"[TotalSportek] get_links: {url.address}", xbmc.LOGINFO)

        try:
            r = fetch_page(url.address)
            debug_log(f"[TotalSportek] Game page fetched", xbmc.LOGINFO)
            soup = BeautifulSoup(r, "html.parser")
            excluded_hosts = self._excluded_hosts()
            seen_hrefs = set()

            for data_row in soup.select("div.col-md-12.premium-stream-row, div.col-md-12.data-row"):
                a_tag = data_row.select_one("a")
                if not a_tag:
                    continue

                href = a_tag.get("href")
                if not href:
                    continue
                if href.startswith("/"):
                    href = f"https://{self.domains[0]}{href}"
                if href in seen_hrefs:
                    continue
                if self._is_excluded(href, excluded_hosts):
                    debug_log(f"[TotalSportek] Excluded host: {href}", xbmc.LOGINFO)
                    continue
                seen_hrefs.add(href)
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
                name = " ".join(name.replace("(", "").replace(")", "").split())
                if "english" in name.lower():
                    name = name.replace("english", "[COLOR=white]english[/COLOR]")
                debug_log(f"[TotalSportek] Link: {name} -> {href}", xbmc.LOGINFO)
                links.append(JetLink(href, name=name, resolveurl=True, extractor=self.name))

            if not links:
                for iframe in soup.find_all("iframe"):
                    src = iframe.get("src") or ""
                    if "youtube.com/embed/" in src or "youtube-nocookie.com/embed/" in src:
                        video_id = src.split("/embed/")[1].split("?")[0]
                        links.append(JetLink(f"plugin://plugin.video.youtube/play/?video_id={video_id}", name="YouTube"))
        except Exception as e:
            debug_log(f"[TotalSportek] Error getting links: {e}", xbmc.LOGERROR)

        debug_log(f"[TotalSportek] Total links: {len(links)}", xbmc.LOGINFO)
        return links

    def _excluded_file(self) -> str:
        try:
            import xbmcaddon
            import xbmcvfs
            profile = xbmcvfs.translatePath(
                xbmcaddon.Addon(id="script.module.jetextractors").getAddonInfo("profile")
            )
            if isinstance(profile, str) and profile:
                return os.path.join(profile, "totalsportek_excluded.json")
        except Exception:
            pass
        return ""

    def _excluded_hosts(self):
        hosts = {h.lower() for h in DEFAULT_EXCLUDED_HOSTS}
        path = self._excluded_file()
        if not path:
            return hosts
        try:
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    entries = data
                elif isinstance(data, dict):
                    entries = data.get("hosts", [])
                else:
                    entries = []
                hosts.update(str(x).strip().lower() for x in entries if str(x).strip())
            else:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"hosts": sorted(DEFAULT_EXCLUDED_HOSTS)}, f, indent=2)
                debug_log(f"[TotalSportek] Created exclusion file: {path}", xbmc.LOGINFO)
        except Exception as e:
            debug_log(f"[TotalSportek] Exclusion file error: {e}", xbmc.LOGWARNING)
        return hosts

    def _is_excluded(self, address: str, hosts=None) -> bool:
        try:
            host = urlparse(address).netloc.lower().split(":")[0]
        except Exception:
            return False
        if host.startswith("www."):
            host = host[4:]
        if hosts is None:
            hosts = self._excluded_hosts()
        for blocked in hosts:
            if host == blocked or host.endswith("." + blocked):
                return True
        return False

    def _build_play_headers(self, referer_fallback: str) -> dict:
        referer = getattr(self.resolver, "stream_referer", None) or referer_fallback
        headers = {
            "User-Agent": self.user_agent,
            "Referer": referer,
        }
        origin = getattr(self.resolver, "stream_origin", None)
        if origin:
            headers["Origin"] = origin
        return headers

    def _resolve_stream(self, address: str):
        """Full resolution chain -> (stream_url, headers) or (None, None)."""
        self.resolver.stream_referer = None
        self.resolver.stream_origin = None
        try:
            stream_url = self.resolver.resolve_url(address)
            if stream_url:
                debug_log(f"[TotalSportek] Resolved stream: {stream_url}", xbmc.LOGINFO)
                return stream_url, self._build_play_headers(address)

            html = fetch_page(address)

            config = self.resolver.extract_worker_config(html)
            if config:
                wd, wk, wri = config
                worker_url = self.resolver.decrypt_worker_url(wd, wk, wri)
                if worker_url:
                    debug_log(f"[TotalSportek] Decrypted worker: {worker_url}", xbmc.LOGINFO)
                    stream_url = self.resolver.resolve_worker(worker_url, address)
                    if stream_url:
                        debug_log(f"[TotalSportek] Worker stream: {stream_url}", xbmc.LOGINFO)
                        return stream_url, self._build_play_headers(worker_url)

            iframes = self.resolver.resolve_iframes(html, address)
            debug_log(f"[TotalSportek] Found {len(iframes)} iframes", xbmc.LOGINFO)

            for iframe_url in iframes:
                if "youtube.com" in iframe_url:
                    continue
                debug_log(f"[TotalSportek] Following iframe: {iframe_url}", xbmc.LOGINFO)
                try:
                    stream_url = self.resolver.resolve_url(iframe_url, address, depth=1)
                    if stream_url:
                        debug_log(f"[TotalSportek] Stream from iframe: {stream_url}", xbmc.LOGINFO)
                        return stream_url, self._build_play_headers(iframe_url)
                except Exception as e:
                    debug_log(f"[TotalSportek] Iframe error: {e}", xbmc.LOGWARNING)

            debug_log(f"[TotalSportek] No stream found", xbmc.LOGWARNING)
        except Exception as e:
            debug_log(f"[TotalSportek] Error in resolve: {e}", xbmc.LOGERROR)

        return None, None

    def _proxy_stream(self, stream_url: str, headers: dict, original_address: str) -> JetLink:
        """Route a resolved m3u8 through the local StreamProxy with a refresh callback
        that re-walks the whole chain when upstream tokens expire (120s-2h lifetimes)."""
        proxy_options = {
            "browser_tls": True,
            "proxy_absolute_urls": True,
            "cache_manifest": True,
            "manifest_ttl": 2.0,
            "add_icy_metadata": False,
        }

        def refresh():
            fresh_url, fresh_headers = self._resolve_stream(original_address)
            if fresh_url:
                return {"url": fresh_url, "headers": fresh_headers or headers}
            return None

        proxy_url = build_proxy_url(
            "totalsportek",
            stream_url,
            headers,
            options=proxy_options,
            per_request_headers=headers,
            refresh_callback=refresh,
        )
        return JetLink(
            proxy_url,
            headers=headers,
            inputstream=JetInputstreamFFmpegDirect.default(),
        )

    def get_link(self, url):
        debug_log(f"[TotalSportek] get_link: {url.address}", xbmc.LOGINFO)

        stream_url, headers = self._resolve_stream(url.address)
        if stream_url:
            return self._proxy_stream(stream_url, headers, url.address)

        return None
