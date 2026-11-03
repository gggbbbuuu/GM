import re
import json
import time
import xbmc
import requests
from datetime import datetime
from urllib.parse import urlparse, quote, parse_qs, urljoin
from typing import Optional, List
from bs4 import BeautifulSoup
from ..models import (
    JetExtractor, JetItem, JetLink, JetExtractorProgress,
    JetInputstreamFFmpegDirect,
)
from .._core import get_session, find_m3u8
from ..util import embedsportstop
from ..util import taifood_mint
from ..util.stream_proxy import get_stream_proxy
from ..tools import debug_log

# Homepage TV-channels list ("Live TV" section). embedsport.live can be
# unreachable from some networks (DNS resolves, TCP:443 never accepts);
# JetHttpClient's 3x10s retry burn (~23 s) must never gate the event
# list. Cache both outcomes so a dead host costs at most one short
# fast-fail attempt per TTL window.
_TV_CHANNELS_CACHE: Optional[List[dict]] = None
_TV_CHANNELS_TS: float = 0.0
_TV_CHANNELS_NEGATIVE_TS: float = 0.0
_TV_CACHE_TTL = 30 * 60


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
        self.api_url = "https://api.ppv.st/api/streams"
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

    def _fetch_tv_channels(self) -> list:
        """window.tvChannelsData from the homepage ("Live TV" section).

        The homepage host may be unreachable (TCP connect that can never
        succeed) - use a single direct attempt with a short connect
        timeout (JetHttpClient's 3x10s retry loop is what stalled every
        directory open for ~23 s) and cache both success and failure for
        _TV_CACHE_TTL so the event list never pays this cost.
        """
        global _TV_CHANNELS_CACHE, _TV_CHANNELS_TS, _TV_CHANNELS_NEGATIVE_TS
        now = time.time()
        if _TV_CHANNELS_CACHE is not None and (now - _TV_CHANNELS_TS) < _TV_CACHE_TTL:
            return _TV_CHANNELS_CACHE
        if (now - _TV_CHANNELS_NEGATIVE_TS) < _TV_CACHE_TTL:
            return []
        try:
            resp = requests.get(
                self.base_url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
                timeout=(4, 10),
            )
            if resp.status_code != 200:
                debug_log(f"[Embedsport2] Homepage returned {resp.status_code} for TV channels", xbmc.LOGWARNING)
                _TV_CHANNELS_NEGATIVE_TS = time.time()
                return []
            html = resp.text
        except Exception as e:
            debug_log(f"[Embedsport2] Homepage fetch failed fast for TV channels: {e}", xbmc.LOGWARNING)
            _TV_CHANNELS_NEGATIVE_TS = time.time()
            return []
        try:
            m = re.search(r'window\.tvChannelsData\s*=\s*(\[.*?\])\s*;', html, re.DOTALL)
            if not m:
                debug_log("[Embedsport2] No tvChannelsData found in homepage", xbmc.LOGWARNING)
                return []
            channels = json.loads(m.group(1))
            if not isinstance(channels, list):
                return []
        except Exception as e:
            debug_log(f"[Embedsport2] Failed to parse TV channels: {e}", xbmc.LOGERROR)
            return []
        debug_log(f"[Embedsport2] Found {len(channels)} TV channels", xbmc.LOGINFO)
        _TV_CHANNELS_CACHE = channels
        _TV_CHANNELS_TS = time.time()
        return channels

    def _resolve_daddylive(self, url: str) -> List[JetLink]:
        links: List[JetLink] = []
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Origin": "https://thedaddy.pk",
            "Referer": "https://thedaddy.pk/",
        }
        try:
            resp = get_session().get(url, headers=headers, timeout=self.timeout)
            if resp.status_code != 200:
                debug_log(f"[Embedsport2] DaddyLive page returned {resp.status_code}", xbmc.LOGWARNING)
                return links
            soup = BeautifulSoup(resp.text, "html.parser")
            for btn in soup.select("button.player-btn"):
                btn_url = btn.get("data-url", "")
                btn_title = btn.get_text(strip=True)
                if btn_url:
                    if btn_url.startswith("//"):
                        btn_url = "https:" + btn_url
                    links.append(JetLink(btn_url, name=btn_title, headers={"Referer": resp.url}))
            if not links:
                for a in soup.select("center > a"):
                    href = a.get("href", "")
                    if href:
                        full_url = "https://thedaddy.pk" + href if not href.startswith("http") else href
                        links.append(JetLink(full_url, name=f"Player {len(links) + 1}", headers={"Referer": resp.url}))
            if links:
                return links
            stream_url = find_m3u8(resp.text, "https://thedaddy.pk")
            if stream_url:
                parsed = urlparse(resp.url)
                domain = f"https://{parsed.netloc}"
                links.append(JetLink(
                    address=stream_url,
                    headers={"Referer": resp.url, "User-Agent": self.user_agent, "Origin": domain},
                    inputstream=JetInputstreamFFmpegDirect.default(),
                ))
        except Exception as e:
            debug_log(f"[Embedsport2] DaddyLive resolution failed: {e}", xbmc.LOGERROR)
        return links

    def _follow_iframes_to_stream(self, url: str, max_depth: int = 6) -> List[JetLink]:
        links: List[JetLink] = []
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://thedaddy.pk/",
            "Origin": "https://thedaddy.pk",
        }
        current_url = url
        ad_patterns = ("getbanner", "ad.html", "doubleclick", "googlesyndication", "adskeeper", "ad4.")
        blacklist = ("chatango", "adserv", "live_chat", "ad4", "cloudfront", "image/svg", "getbanner.php", "/ads", "ads.", "min.js", ".jpg", ".png", "mail.ru", "googleusercontent")
        session = get_session()
        for _ in range(max_depth):
            try:
                resp = session.get(current_url, headers=headers, timeout=self.timeout)
            except Exception:
                break
            if resp.status_code != 200:
                break
            stream = find_m3u8(resp.text, current_url)
            if stream:
                parsed = urlparse(current_url)
                domain = f"https://{parsed.netloc}"
                links.append(JetLink(
                    address=stream,
                    headers={"Referer": current_url, "User-Agent": self.user_agent, "Origin": domain},
                    inputstream=JetInputstreamFFmpegDirect.default(),
                ))
                return links
            iframe_src = None
            for match in re.finditer(r'<iframe\b[^>]*\bsrc=["\']([^"\']+)["\']', resp.text, re.IGNORECASE):
                src = match.group(1)
                if any(p in src.lower() for p in ad_patterns):
                    continue
                if any(b in src.lower() for b in blacklist):
                    continue
                if not src.startswith("http"):
                    src = urljoin(current_url, src)
                iframe_src = src
                break
            if not iframe_src or iframe_src == current_url:
                break
            parsed_current = urlparse(current_url)
            domain = f"https://{parsed_current.netloc}"
            headers = {
                "Referer": f"{domain}/",
                "Origin": domain,
                "User-Agent": self.user_agent,
            }
            current_url = iframe_src
        return links

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
            resp = get_session().get(self.api_url, headers=self._headers(), timeout=self.timeout)
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

        tv_channels = self._fetch_tv_channels()
        for ch in tv_channels:
            if self.progress_update(progress):
                return items
            if not isinstance(ch, dict):
                continue
            ch_name = str(ch.get("name") or "").strip()
            ch_url = str(ch.get("url") or "").strip()
            ch_id = ch.get("id")
            if not ch_name or not ch_url:
                continue
            link = JetLink(ch_url, name=ch_name, links=True)
            items.append(JetItem(
                title=ch_name,
                links=[link],
                status="LIVE",
                league="Live TV",
                extractor=self.name,
            ))

        debug_log(f"[Embedsport2] Returning {len(items)} items", xbmc.LOGINFO)
        return items

    def _resolve_taifood(self, iframe_url: str, link_name: str) -> List[JetLink]:
        """Mint a fresh indianservers playlist for a taifood embed and serve
        it through StreamProxy.

        Mint key = the iframe path after /embed/ (== the API's uri_name).
        Tokens are short-window/stateful: re-mint on the proxy refresh
        callback. Segments are WebP-wrapped MPEG-TS - strip_png +
        prefetch_depth are mandatory (Agents_embedhd_api.md v3.3.31), and
        indianservers 403s desktop UA / close-per-request fetches, so
        Samsung TV UA + upstream_keep_alive + prefetch.
        """
        links: List[JetLink] = []
        uri_name = taifood_mint.uri_name_from_iframe(iframe_url)
        if not uri_name:
            debug_log(f"[Embedsport2] No /embed/ path in taifood URL: {iframe_url}", xbmc.LOGERROR)
            return links

        def _refresh_callback():
            # Tokens are short-window; re-mint a brand new one on refresh.
            fresh = taifood_mint.mint(uri_name)
            if not fresh:
                return None
            return {"url": fresh, "headers": taifood_mint.stream_headers()}

        stream_url = taifood_mint.mint(uri_name)
        if stream_url and not taifood_mint.verify_m3u8(stream_url):
            # CDN occasionally 404s a freshly minted token (transient);
            # one re-mint absorbs it.
            debug_log(f"[Embedsport2] Mint verify failed for {uri_name}, re-minting once", xbmc.LOGWARNING)
            stream_url = taifood_mint.mint(uri_name)
        if not stream_url or not taifood_mint.verify_m3u8(stream_url):
            debug_log(f"[Embedsport2] Failed to mint playable stream for {uri_name}", xbmc.LOGWARNING)
            return links

        headers = taifood_mint.stream_headers()
        proxy = get_stream_proxy(
            "embedsport2",
            headers,
            options={
                "cache_manifest": False,
                "proxy_absolute_urls": True,
                # indianservers segments are WebP-wrapped MPEG-TS; without
                # strip_png ffmpeg probes `Video: webp` and hits instant EOF.
                "strip_png": True,
                # indianservers.st rejects Chrome desktop UA + close-per-request
                # segment fetches with 403.
                "user_agent": taifood_mint.STREAMED_TV_UA,
                "upstream_keep_alive": True,
                "prefetch_segments": True,
                # WebP unwrap is expensive; keep the decoder fed.
                "prefetch_depth": 3,
                "keep_alive": False,
            },
        )
        proxy_url = proxy.get_proxy_url(stream_url, headers, refresh_callback=_refresh_callback)
        links.append(JetLink(
            address=proxy_url,
            name=link_name,
            inputstream=taifood_mint.ffmpegdirect_live(),
            resolveurl=False,
        ))
        debug_log(f"[Embedsport2] Taifood mint OK for {uri_name}: {stream_url[:100]}", xbmc.LOGINFO)
        return links

    def get_links(self, url: JetLink) -> List[JetLink]:
        debug_log(f"[Embedsport2] get_links called for: {url.address}", xbmc.LOGINFO)
        links: List[JetLink] = []

        try:
            parsed = urlparse(url.address)
            daddylive_domains = ("thedaddy.pk", "dlhd.st", "daddylive.mov")
            if parsed.netloc in daddylive_domains:
                links = self._resolve_daddylive(url.address)
                if links:
                    final_links = []
                    for link in links:
                        if ".m3u8" in link.address or ".mpd" in link.address:
                            final_links.append(link)
                        elif link.address.startswith("http"):
                            resolved = self._follow_iframes_to_stream(link.address)
                            if resolved:
                                final_links.extend(resolved)
                    debug_log(f"[Embedsport2] DaddyLive resolved {len(final_links)} working links from {len(links)} candidates", xbmc.LOGINFO)
                    return final_links
                return links

            if parsed.netloc not in self.domains:
                return links

            query = parse_qs(parsed.query)
            iframe_url = query.get("url", [""])[0]
            link_name = query.get("name", ["Stream"])[0]

            if not iframe_url:
                debug_log("[Embedsport2] Empty iframe URL in proxy", xbmc.LOGERROR)
                return links

            debug_log(f"[Embedsport2] Resolving embed: {iframe_url}", xbmc.LOGINFO)

            # taifood-blog.asia wrapper (all 383/383 iframes in the 2026-10
            # API payload): the page is armored JS, but the network's
            # server-side issuer mints a fresh indianservers.st playlist
            # from the iframe path after /embed/ (= the API's uri_name,
            # including _540p suffixes and multi-path substreams; proven
            # 2026-10-31 for nfl-network, _540p, and .../skycast).
            if taifood_mint.is_taifood_url(iframe_url):
                return self._resolve_taifood(iframe_url, link_name)

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
                resp = get_session().get(iframe_url, headers=headers, timeout=self.timeout)
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
