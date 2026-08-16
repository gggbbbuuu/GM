from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress, JetInputstreamFFmpegDirect
from .._core import get_headers, find_m3u8, find_iframes
from ..util import embedsportstop
import requests
import re
import json
import xbmc
from datetime import datetime
from typing import Optional, List
from urllib.parse import urljoin, urlparse, quote, parse_qs


def _ffmpegdirect_live() -> JetInputstreamFFmpegDirect:
    """inputstream.ffmpegdirect with stream_mode='live' (NOT 'timeshift').

    stream_mode='timeshift' causes FFmpeg's read thread to block for 20s
    during teardown, freezing the player close. 'live' has no timeshift
    buffer machinery so teardown is instant. Trade-off: no pause/rewind.
    """
    return JetInputstreamFFmpegDirect(manifest_type="hls", is_realtime_stream=True, stream_mode="live")


class MethStreams(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["methstreams.gs", "www.methstreams.gs"]
        self.name = "MethStreams"
        self.short_name = "MST"
        self.timeout = 10
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
        )
        self.base_url = "https://methstreams.gs"

        self.LEAGUES = [
            ("/league/nflstreams", "NFL"),
            ("/league/nbastreams", "NBA"),
            ("/league/mlbstreams", "MLB"),
            ("/league/wnbastreams", "WNBA"),
            ("/league/mmastreams", "MMA"),
            ("/league/boxingstreams", "Boxing"),
            ("/league/f1streams", "F1"),
            ("/league/cfbstreams", "CFB"),
            ("/league/nhlstreams", "NHL"),
            ("/league/ncaab", "NCAAB"),
            ("/league/wwestreams", "WWE"),
            ("/league/tna", "TNA"),
            ("/league/aew", "AEW"),
        ]

    def _headers(self) -> dict:
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": f"{self.base_url}/",
        }

    def _proxy_url(self, stream_url: str, name: str) -> str:
        return f"{self.base_url}/jetextractor/methstreams?url={quote(stream_url, safe='')}&name={quote(name, safe='')}"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items

        for league_path, league_name in self.LEAGUES:
            if self.progress_update(progress):
                return items

            try:
                url = f"{self.base_url}{league_path}"
                if progress:
                    self.progress_update(progress, f"Fetching {league_name}...")

                resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
                if resp.status_code != 200:
                    continue

                html = resp.text
                soup_events = re.findall(
                    r'<a\s+class="card"\s+href="(/stream/[^"]+)".*?'
                    r'<div\s+class="card-title">([^<]+)</div>.*?'
                    r'<div\s+class="card-subtitle">\s*([^<]*?)\s*</div>',
                    html,
                    re.DOTALL,
                )

                for href, title, subtitle in soup_events:
                    title = title.strip()
                    subtitle = subtitle.strip()
                    full_url = f"{self.base_url}{href}"

                    time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM)\s*ET)', subtitle, re.IGNORECASE)
                    match_time = None
                    status = None
                    if time_match:
                        try:
                            time_str = time_match.group(1).strip()
                            today = datetime.now().strftime("%Y-%m-%d")
                            match_time = datetime.strptime(f"{today} {time_str}", "%Y-%m-%d %I:%M %p ET")
                            status = "Upcoming"
                        except Exception:
                            pass
                    elif "live" in subtitle.lower():
                        status = "LIVE"

                    items.append(JetItem(
                        title=title,
                        links=[JetLink(full_url, links=True)],
                        league=league_name,
                        starttime=match_time,
                        status=status,
                    ))

            except Exception as e:
                xbmc.log(f"[MethStreams] Error fetching {league_name}: {e}", xbmc.LOGERROR)

        xbmc.log(f"[MethStreams] Returning {len(items)} items", xbmc.LOGINFO)
        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        links: List[JetLink] = []

        try:
            resp = requests.get(url.address, headers=self._headers(), timeout=self.timeout)
            if resp.status_code != 200:
                xbmc.log(f"[MethStreams] Stream page returned {resp.status_code}", xbmc.LOGWARNING)
                return links

            html = resp.text

            all_streams_match = re.search(
                r'const\s+allStreams\s*=\s*(\[.*?\]);', html, re.DOTALL
            )
            if not all_streams_match:
                xbmc.log("[MethStreams] No allStreams found in page", xbmc.LOGWARNING)
                return links

            try:
                streams_data = json.loads(all_streams_match.group(1))
            except json.JSONDecodeError as e:
                xbmc.log(f"[MethStreams] Failed to parse allStreams JSON: {e}", xbmc.LOGERROR)
                return links

            for stream in streams_data:
                if not isinstance(stream, dict):
                    continue
                label = stream.get("label", "Stream")
                value = stream.get("value", "")
                if not value:
                    continue

                proxy_url = self._proxy_url(value, label)
                links.append(JetLink(proxy_url, name=label))

        except Exception as e:
            xbmc.log(f"[MethStreams] Error getting links: {e}", xbmc.LOGERROR)

        return links

    def get_link(self, url: JetLink) -> JetLink:
        try:
            parsed = urlparse(url.address)

            if parsed.path.startswith("/jetextractor/methstreams") and parsed.netloc in self.domains:
                query = parse_qs(parsed.query)
                real_url = query.get("url", [""])[0]
                link_name = query.get("name", ["Stream"])[0]
                if not real_url:
                    return JetLink(url.address)

                embed_host = urlparse(real_url).netloc

                if any(h in embed_host for h in ("embedindia", "embedsports.top", "pooembed", "embed.st")):
                    stream_url = embedsportstop.get_embedsportstop_stream(real_url)
                    if stream_url:
                        embed_domain = f"https://{embed_host}"
                        proxy = self._get_stream_proxy(embed_domain)
                        proxy_url = proxy.get_proxy_url(stream_url, {
                            "User-Agent": self.user_agent,
                            "Referer": f"{embed_domain}/",
                            "Origin": embed_domain,
                        })
                        return JetLink(
                            proxy_url,
                            name=link_name,
                            inputstream=_ffmpegdirect_live(),
                        )

                headers = {
                    "User-Agent": self.user_agent,
                    "Referer": f"https://{embed_host}/",
                    "Origin": f"https://{embed_host}",
                }

                final_url, final_headers = self._follow_to_stream(real_url, headers)
                if final_url:
                    stream_host = f"https://{urlparse(final_url).netloc}"
                    proxy = self._get_stream_proxy(stream_host)
                    proxy_url = proxy.get_proxy_url(final_url, final_headers or headers)
                    return JetLink(
                        proxy_url,
                        name=link_name,
                        inputstream=_ffmpegdirect_live(),
                    )

        except Exception as e:
            xbmc.log(f"[MethStreams] Error getting link: {e}", xbmc.LOGERROR)

        return JetLink(url.address)

    def _follow_to_stream(self, url: str, headers: dict, max_depth: int = 5) -> tuple:
        current_url = url
        current_headers = dict(headers)

        for _ in range(max_depth):
            try:
                resp = requests.get(current_url, headers=current_headers, timeout=self.timeout)
            except Exception:
                break

            if resp.status_code != 200:
                break

            stream_url = find_m3u8(resp.text, current_url)
            if stream_url:
                parsed = urlparse(current_url)
                domain = f"https://{parsed.netloc}"
                return stream_url, {
                    "User-Agent": self.user_agent,
                    "Referer": f"{domain}/",
                    "Origin": domain,
                }

            iframe_match = re.search(
                r'<iframe[^>]*\bsrc=["\']([^"\']+)["\']', resp.text, re.IGNORECASE
            )
            if not iframe_match:
                break

            src = iframe_match.group(1)
            if src.startswith("//"):
                src = "https:" + src
            elif not src.startswith("http"):
                src = urljoin(current_url, src)

            if src == current_url:
                break

            parsed = urlparse(current_url)
            domain = f"https://{parsed.netloc}"
            current_headers = {
                "User-Agent": self.user_agent,
                "Referer": f"{domain}/",
                "Origin": domain,
            }
            current_url = src

        return None, None

    def _get_stream_proxy(self, origin: str):
        from ..util.stream_proxy import get_stream_proxy
        return get_stream_proxy(
            "methstreams",
            {
                "User-Agent": self.user_agent,
                "Referer": f"{origin}/",
                "Origin": origin,
            },
            options={
                "strip_png": True,
                "manifest_png_to_ts": True,
                "user_agent": "Mozilla/5.0 (SMART-TV; Linux; Tizen 6.0) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/16.0 TV Safari/537.36",
                "browser_tls": True,
                "keep_alive": False,
            },
        )
