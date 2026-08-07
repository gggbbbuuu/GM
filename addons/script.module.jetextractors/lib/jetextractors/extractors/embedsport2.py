import re
import requests
import xbmc
from datetime import datetime
from urllib.parse import urlparse, quote, parse_qs
from typing import Optional, List
from ..models import (
    JetExtractor, JetItem, JetLink, JetExtractorProgress,
    JetInputstreamFFmpegDirect,
)
from ..util import embedsportstop
from ..util.stream_proxy import get_stream_proxy
from ..tools import debug_log


class Embedsport2(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["embedsport.live"]
        self.name = "Embedsport2"
        self.short_name = "ES2"
        self.timeout = 10
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
        )
        self.api_url = "https://api.ppv.is/api/streams"
        self.base_url = "https://embedsport.live"

    def _headers(self) -> dict:
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
        }

    def _proxy_url(self, iframe_url: str, name: str) -> str:
        return f"{self.base_url}/jetextractor/embedsport2?url={quote(iframe_url, safe='')}&name={quote(name, safe='')}"

    def _guess_league(self, title: str, category: str) -> str:
        cat = category.lower()
        if cat in ("football", "soccer"):
            return "Soccer"
        if cat in ("american football",):
            return "NFL"
        if cat in ("combat sports", "mma", "boxing"):
            return "MMA / Boxing"
        if cat == "basketball":
            return "NBA"
        if cat == "baseball":
            return "MLB"
        if cat == "hockey":
            return "NHL"
        if cat == "rugby":
            return "Rugby"
        if cat == "wrestling":
            return "Wrestling"
        if cat == "australian football":
            return "AFL"
        t = title.lower()
        if any(x in t for x in ("ufc", "boxing", "wwe")):
            return "MMA / Boxing"
        if any(x in t for x in ("nba", "basketball", "lakers", "celtics")):
            return "NBA"
        if any(x in t for x in ("mlb", "baseball", "yankees", "dodgers")):
            return "MLB"
        if any(x in t for x in ("nfl", "football", "super bowl", "chiefs")):
            return "NFL"
        if any(x in t for x in ("fifa", "world cup", "epl", "premier league", "la liga", "bundesliga", "serie a", "uefa", "champions league")):
            return "Soccer"
        return "Sports"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items

        try:
            resp = requests.get(self.api_url, headers=self._headers(), timeout=self.timeout)
            if resp.status_code != 200:
                debug_log(f"[Embedsport2] API returned {resp.status_code}", xbmc.LOGWARNING)
                return items
            data = resp.json()
            if not isinstance(data, dict) or not data.get("success"):
                debug_log("[Embedsport2] API returned success=false", xbmc.LOGWARNING)
                return items
        except Exception as e:
            debug_log(f"[Embedsport2] API fetch failed: {e}", xbmc.LOGERROR)
            return items

        categories = data.get("streams", [])
        if not isinstance(categories, list):
            return items

        now = datetime.now().timestamp()
        for category in categories:
            if not isinstance(category, dict):
                continue
            category_name = str(category.get("category") or "Sports").strip()
            cat_always_live = bool(category.get("always_live"))
            streams = category.get("streams", [])
            if not isinstance(streams, list):
                continue

            for stream in streams:
                if self.progress_update(progress):
                    return items
                if not isinstance(stream, dict):
                    continue

                title = str(stream.get("name") or "Stream").strip()
                iframe = stream.get("iframe")
                if not title or not isinstance(iframe, str) or not iframe.startswith(("http://", "https://")):
                    continue

                tag = str(stream.get("tag") or "").strip()
                starts_at = stream.get("starts_at")
                ends_at = stream.get("ends_at")
                always_live = bool(stream.get("always_live")) or cat_always_live

                status = None
                match_time = None
                if always_live:
                    status = "LIVE"
                elif isinstance(starts_at, (int, float)) and starts_at > 0:
                    match_time = datetime.fromtimestamp(starts_at)
                    if now < starts_at:
                        status = "Upcoming"
                    elif isinstance(ends_at, (int, float)) and ends_at > 0 and now > ends_at:
                        status = "Ended"
                    else:
                        status = "LIVE"

                link_name = tag if tag else "Main"
                proxy_url = self._proxy_url(iframe, link_name)
                links = [JetLink(proxy_url, name=link_name, links=True)]

                substreams = stream.get("substreams", [])
                if isinstance(substreams, list):
                    for sub in substreams:
                        if not isinstance(sub, dict):
                            continue
                        sub_iframe = sub.get("iframe")
                        if isinstance(sub_iframe, str) and sub_iframe.startswith(("http://", "https://")):
                            sub_name = str(sub.get("tag") or sub.get("name") or "Alternate")
                            links.append(
                                JetLink(self._proxy_url(sub_iframe, sub_name), name=sub_name, links=True)
                            )

                league = self._guess_league(title, category_name)
                icon = stream.get("poster") or ""

                items.append(JetItem(
                    title=title,
                    links=links,
                    starttime=match_time,
                    status=status,
                    league=league,
                    icon=icon,
                    extractor=self.name,
                ))

        debug_log(f"[Embedsport2] Returning {len(items)} items", xbmc.LOGINFO)
        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        debug_log(f"[Embedsport2] get_links called for: {url.address}", xbmc.LOGINFO)
        links: List[JetLink] = []

        try:
            parsed = urlparse(url.address)
            if parsed.netloc not in self.domains:
                return links

            query = parse_qs(parsed.query)
            iframe_url = query.get("url", [""])[0]
            link_name = query.get("name", ["Stream"])[0]

            if not iframe_url:
                debug_log("[Embedsport2] Empty iframe URL in proxy", xbmc.LOGERROR)
                return links

            debug_log(f"[Embedsport2] Resolving embed: {iframe_url}", xbmc.LOGINFO)

            embed_origin = f"{urlparse(iframe_url).scheme}://{urlparse(iframe_url).netloc}"
            headers = {
                "User-Agent": self.user_agent,
                "Origin": embed_origin,
                "Referer": f"{embed_origin}/",
                "Accept": "*/*",
            }

            if any(h in iframe_url for h in ("embedindia", "embedsports.top", "pooembed", "embed.st")):
                stream_url = embedsportstop.get_embedsportstop_stream(iframe_url)
                if stream_url:
                    debug_log(f"[Embedsport2] Resolved stream URL: {stream_url}", xbmc.LOGINFO)
                    proxy = get_stream_proxy(
                        "embedsport2",
                        headers,
                        options={
                            "strip_png": True,
                            "manifest_png_to_ts": True,
                            "proxy_absolute_urls": True,
                            "cache_manifest": False,
                            "browser_tls": True,
                        },
                    )
                    proxy_url = proxy.get_proxy_url(stream_url, headers)
                    links.append(JetLink(
                        address=proxy_url,
                        name=link_name,
                        inputstream=JetInputstreamFFmpegDirect.default(),
                        resolveurl=False,
                    ))
                    return links
                else:
                    debug_log("[Embedsport2] embedsportstop returned empty", xbmc.LOGERROR)

            if ".m3u8" in iframe_url or ".mpd" in iframe_url:
                links.append(JetLink(
                    address=iframe_url,
                    name=link_name,
                    headers=headers,
                    inputstream=JetInputstreamFFmpegDirect.default(),
                    resolveurl=False,
                ))
                return links

            try:
                resp = requests.get(iframe_url, headers=headers, timeout=self.timeout)
                if resp.status_code != 200:
                    debug_log(f"[Embedsport2] Embed page returned {resp.status_code}", xbmc.LOGWARNING)
                    return links
                html = resp.text
                stream_urls = []
                m = re.search(r'const\s+streamUrl\s*=\s*"([^"]+)"', html)
                if m:
                    stream_urls.append(m.group(1))
                stream_urls.extend(re.findall(r'source\s*[:=]\s*"(https?://[^"]+)"', html))
                stream_urls.extend(re.findall(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html))
                stream_urls.extend(re.findall(r'(https?://[^\s"\'<>]+\.mpd[^\s"\'<>]*)', html))
                valid_urls = [u for u in stream_urls if u.startswith(("http://", "https://"))]
                if valid_urls:
                    links.append(JetLink(
                        address=valid_urls[0],
                        name=link_name,
                        headers=headers,
                        inputstream=JetInputstreamFFmpegDirect.default(),
                        resolveurl=False,
                    ))
            except Exception as e:
                debug_log(f"[Embedsport2] Embed page fetch failed: {e}", xbmc.LOGWARNING)

        except Exception as e:
            debug_log(f"[Embedsport2] get_links error: {e}", xbmc.LOGERROR)

        return links

    def get_link(self, url: JetLink) -> JetLink:
        return JetLink(url.address, inputstream=JetInputstreamFFmpegDirect.default())
