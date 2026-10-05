from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress, JetInputstreamFFmpegDirect
from .._core import get_session, get_headers, find_m3u8
from ..util import embedsportstop
import re
import json
import xbmc
from datetime import datetime
from typing import Optional, List, Tuple
from urllib.parse import urljoin, urlparse, quote, parse_qs

# The network runs two interchangeable hosts: some league paths on methstreams.gs
# 301 to crackstreams.mx (e.g. /league/cfbstreams -> /league/ncaa, /league/nhlstreams),
# and the stream pages only exist on the host the league page redirected to.
SITE_HOSTS = ["methstreams.gs", "crackstreams.mx"]
SITE_ORIGINS = [f"https://{h}" for h in SITE_HOSTS]

_404_MARKERS = ('<title>404 Not Found', 'Page is not found')

# wiveophis-style obfuscation: char-code array + xor key + shift, fed to window.eval
_OBFUSCATED_PAYLOAD = re.compile(
    r'var\s+\w+\s*=\s*\[([\d,\s]+)\]\s*,\s*\w+\s*=\s*(\d+)\s*,\s*\w+\s*=\s*(\d+)'
)


def _origin_of(url: str) -> str:
    netloc = urlparse(url).netloc
    return f"https://{netloc}" if netloc else ""


def _is_404_page(html: str) -> bool:
    return any(marker in html for marker in _404_MARKERS)


def _ffmpegdirect_live() -> JetInputstreamFFmpegDirect:
    """inputstream.ffmpegdirect with stream_mode='live' (NOT 'timeshift').

    stream_mode='timeshift' causes FFmpeg's read thread to block for 20s
    during teardown, freezing the player close. 'live' has no timeshift
    buffer machinery so teardown is instant. Trade-off: no pause/rewind.
    """
    return JetInputstreamFFmpegDirect(manifest_type="hls", is_realtime_stream=True, stream_mode="live")


class MethStreams(JetExtractor):
    def __init__(self) -> None:
        self.domains = SITE_HOSTS + [f"www.{h}" for h in SITE_HOSTS]
        self.name = "MethStreams"
        self.short_name = "MST"
        self.timeout = 10
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

    def _proxy_url(self, stream_url: str, name: str) -> str:
        return f"{self.base_url}/jetextractor/methstreams?url={quote(stream_url, safe='')}&name={quote(name, safe='')}"

    def is_available(self, url: JetLink) -> bool:
        netloc = urlparse(url.address).netloc.lower()
        if not netloc:
            return False
        if any(netloc == h or netloc.endswith(f".{h}") for h in SITE_HOSTS):
            return True
        return super().is_available(url)

    def _fetch_final(self, url: str, referer: str = None) -> Tuple[str, str]:
        """GET url following redirects.

        Returns (final_url, html). final_url matters because league pages 301 to a
        sibling host and stream pages only exist on the host we landed on.
        """
        try:
            session = get_session(referer=referer)
            resp = session.get(url, headers=get_headers(referer), timeout=self.timeout, allow_redirects=True)
            if resp.status_code != 200:
                return resp.url, ""
            return resp.url, resp.text
        except Exception as e:
            xbmc.log(f"[MethStreams] _fetch_final failed for {url}: {e}", xbmc.LOGWARNING)
            return url, ""

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

                final_url, html = self._fetch_final(url, referer=f"{self.base_url}/")
                if not html:
                    xbmc.log(f"[MethStreams] Empty response for {url}", xbmc.LOGWARNING)
                    continue

                origin = _origin_of(final_url) or self.base_url
                if origin != self.base_url:
                    xbmc.log(f"[MethStreams] {league_path} redirected to {final_url} (using {origin})", xbmc.LOGINFO)

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
                    full_url = urljoin(f"{origin}/", href.lstrip("/"))

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

    def _extract_all_streams(self, html: str) -> Tuple[bool, list]:
        """Returns (declared, streams). declared=True when the page has an
        allStreams array, even if it is still empty (event not started yet)."""
        all_streams_match = None
        # Try common declarations
        patterns = [
            r'(?:const|let|var)\s+allStreams\s*=\s*(\[[^\]]*\])\s*;?',
            r'allStreams\s*=\s*(\[[^\]]*\])\s*;?',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.DOTALL)
            if m:
                all_streams_match = m
                break
        if not all_streams_match:
            # Fallback: look for allStreams followed by [ ... ]
            idx = html.find('allStreams')
            if idx >= 0:
                b = html.find('[', idx)
                if b >= 0:
                    m2 = re.search(r'(\[.*?\])', html[b:], re.DOTALL)
                    if m2:
                        all_streams_match = m2
        if not all_streams_match:
            return False, []
        try:
            streams_data = json.loads(all_streams_match.group(1))
        except json.JSONDecodeError as e:
            xbmc.log(f"[MethStreams] Failed to parse allStreams JSON: {e}", xbmc.LOGERROR)
            return True, []
        return True, streams_data if isinstance(streams_data, list) else []

    def _iframe_fallback(self, html: str, base_url: str) -> List[JetLink]:
        links: List[JetLink] = []
        try:
            ad_patterns = re.compile(
                r'(getbanner|ad\.html|doubleclick|googlesyndication|adskeeper|ad4|live_chat|ads\.|cloudfront\.net/.*\.html)',
                re.IGNORECASE,
            )
            iframe_matches = re.findall(r'<iframe[^>]*\bsrc=["\']([^"\']+)["\']', html, re.IGNORECASE)
            for candidate in iframe_matches:
                if ad_patterns.search(candidate):
                    continue
                if candidate.startswith("//"):
                    candidate = "https:" + candidate
                elif not candidate.startswith("http"):
                    candidate = urljoin(base_url, candidate)
                if candidate == base_url:
                    continue
                links.append(JetLink(candidate, name="Stream", links=True))
                return links
        except Exception as e:
            xbmc.log(f"[MethStreams] Fallback iframe scan failed: {e}", xbmc.LOGWARNING)
        return links

    def _stream_page_candidates(self, address: str) -> List[str]:
        """Address first, then the same path on the sibling host.

        methstreams.gs answers /stream/<slug> with a soft 404 for leagues that
        were moved to crackstreams.mx, so retrying the identical path on the
        other host recovers the page.
        """
        candidates = [address]
        parsed = urlparse(address)
        if not any(parsed.netloc == h or parsed.netloc.endswith(f".{h}") for h in SITE_HOSTS):
            return candidates
        for origin in SITE_ORIGINS:
            alt = f"{origin}{parsed.path}"
            if parsed.query:
                alt = f"{alt}?{parsed.query}"
            if alt not in candidates:
                candidates.append(alt)
        return candidates

    def get_links(self, url: JetLink) -> List[JetLink]:
        links: List[JetLink] = []

        try:
            fallback_html = ""
            fallback_base = url.address
            declared_empty = False

            for candidate in self._stream_page_candidates(url.address):
                final_url, html = self._fetch_final(candidate, referer=f"{_origin_of(candidate)}/")
                if not html:
                    continue

                # 404 pages still return 200; keep the html for the iframe fallback
                if _is_404_page(html):
                    xbmc.log(f"[MethStreams] Stream page appears to be 404: {final_url}", xbmc.LOGWARNING)
                    if not fallback_html:
                        fallback_html, fallback_base = html, final_url
                    continue

                declared, streams_data = self._extract_all_streams(html)
                if not declared:
                    xbmc.log(f"[MethStreams] No allStreams found in page {final_url}", xbmc.LOGWARNING)
                    if not fallback_html:
                        fallback_html, fallback_base = html, final_url
                    continue

                if not streams_data:
                    xbmc.log(f"[MethStreams] allStreams is empty on {final_url} (no links published yet)", xbmc.LOGINFO)
                    declared_empty = True
                    if not fallback_html:
                        fallback_html, fallback_base = html, final_url
                    continue

                if candidate != url.address:
                    xbmc.log(f"[MethStreams] Recovered stream page via mirror {final_url}", xbmc.LOGINFO)

                for stream in streams_data:
                    if not isinstance(stream, dict):
                        continue
                    label = stream.get("label", "Stream")
                    value = stream.get("value", "")
                    if not value:
                        continue

                    proxy_url = self._proxy_url(value, label)
                    links.append(JetLink(proxy_url, name=label))

                if links:
                    return links

            if fallback_html and not declared_empty:
                return self._iframe_fallback(fallback_html, fallback_base)

        except Exception as e:
            xbmc.log(f"[MethStreams] Error getting links: {e}", xbmc.LOGERROR)

        return links

    def get_link(self, url: JetLink) -> JetLink:
        try:
            parsed = urlparse(url.address)

            if parsed.path.startswith("/jetextractor/methstreams") and (
                parsed.netloc in self.domains or parsed.netloc in SITE_HOSTS
            ):
                query = parse_qs(parsed.query)
                real_url = query.get("url", [""])[0]
                link_name = query.get("name", ["Stream"])[0]
                if not real_url:
                    return JetLink(url.address)

                embed_host = urlparse(real_url).netloc

                if any(h in embed_host for h in ("embedindia", "embedsports.top", "pooembed", "embed.st")):
                    try:
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
                    except Exception as e:
                        xbmc.log(f"[MethStreams] embedsportstop failed, falling back to _follow_to_stream: {e}", xbmc.LOGWARNING)

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

    def _decode_char_arrays(self, html: str) -> str:
        """Decode obfuscated char-code payloads (String.fromCharCode((c^k)-s)) back to JS."""
        chunks: List[str] = []
        for m in _OBFUSCATED_PAYLOAD.finditer(html):
            try:
                codes = [int(x) for x in m.group(1).split(",") if x.strip()]
                key = int(m.group(2))
                shift = int(m.group(3))
                chunks.append("".join(chr(((c ^ key) - shift + 256) % 256) for c in codes))
            except Exception:
                continue
        return "\n".join(chunks)

    def _follow_to_stream(self, url: str, headers: dict, max_depth: int = 5) -> tuple:
        session = get_session()
        current_url = url
        # Referer must be the page we came from (full URL), not the page we are
        # fetching: hosts like exmxbxe.cfd answer 403 "Domain Not Allowed" when
        # the Referer points at their own domain.
        referer = headers.get("Referer") or None
        current_headers = {"User-Agent": self.user_agent}
        if referer:
            current_headers["Referer"] = referer

        for _ in range(max_depth):
            try:
                resp = session.get(current_url, headers=current_headers, timeout=self.timeout)
            except Exception:
                break

            if resp.status_code != 200:
                break

            stream_url = find_m3u8(resp.text, current_url)
            decoded = self._decode_char_arrays(resp.text)
            probe = f"{resp.text}\n{decoded}" if decoded else resp.text
            if not stream_url:
                # some players hide the signed m3u8 behind an eval'd char-code array
                stream_url = find_m3u8(probe, current_url)
            if stream_url:
                parsed = urlparse(current_url)
                domain = f"https://{parsed.netloc}"
                return stream_url, {
                    "User-Agent": self.user_agent,
                    "Referer": f"{domain}/",
                    "Origin": domain,
                }

            # Find all iframes, skip ad iframes, pick the first valid one
            ad_patterns = re.compile(
                r'(getbanner|ad\.html|doubleclick|googlesyndication|adskeeper|ad4|live_chat|ads\.|cloudfront\.net/.*\.html)',
                re.IGNORECASE,
            )
            iframe_matches = re.findall(
                r'<iframe[^>]*\bsrc=["\']([^"\']+)["\']', probe, re.IGNORECASE
            )
            src = None
            for candidate in iframe_matches:
                if ad_patterns.search(candidate):
                    continue
                if candidate.startswith("//"):
                    candidate = "https:" + candidate
                elif not candidate.startswith("http"):
                    candidate = urljoin(current_url, candidate)
                if candidate == current_url:
                    continue
                src = candidate
                break

            if not src:
                break

            current_headers = {"User-Agent": self.user_agent, "Referer": current_url}
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
