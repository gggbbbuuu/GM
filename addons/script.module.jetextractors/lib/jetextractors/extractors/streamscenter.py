from ..models import *
from .._core import get_session
from ..util.stream_proxy import get_stream_proxy
import re
import html as html_lib
from datetime import datetime
from urllib.parse import urlparse, urljoin, parse_qs
# import xbmc

class StreamsCenter(JetExtractor):
    def __init__(self) -> None:
        self.domains = [
            "streamcenter.pro",
            "streamscenter.live",
            "streamscenter.online",
            "streams.center",
            "mainstreams.pro",
            "edgestreams.pro",
            "streamcenter.st",
            "www.streamcenter.st",
        ]
        self.name = "StreamsCenter"
        self.resolve_only = False

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        html = self._fetch("https://streamcenter.st/game-cards/embed")
        if not html:
            html = self._fetch("https://streamcenter.st/")
        if not html:
            return items
        for block in re.findall(r'<article class="game-card-row">.*?</article>', html, re.S):
            title_m = re.search(r'<h3[^>]*aria-label="([^"]+)"', block)
            href_m = re.search(r'href="(/watch/[^"]+)"', block)
            if not title_m or not href_m:
                continue
            league_m = re.search(r'<p class="game-card-league">([^<]*)</p>', block)
            time_m = re.search(r'<time[^>]*dateTime="([^"]+)"', block)
            starttime = None
            if time_m:
                try:
                    starttime = datetime.fromisoformat(time_m.group(1).replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
                except Exception:
                    starttime = None
            status = "LIVE" if "game-card-status-live" in block else None
            items.append(JetItem(
                html_lib.unescape(title_m.group(1)),
                [JetLink(f"https://streamcenter.st{href_m.group(1)}")],
                starttime,
                status=status,
                league=html_lib.unescape(league_m.group(1)) if league_m else None,
            ))
        return items

    def _fetch(self, url: str, referer: str = "https://streamcenter.st/") -> str:
        try:
            r = get_session().get(url, headers={"User-Agent": self.user_agent, "Referer": referer}, timeout=self.timeout)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        return ""

    def _streamcenter_embed_url(self, address: str) -> Optional[str]:
        parsed = urlparse(address)
        match_id = None
        source = None
        m = re.search(r'/watch/([^/?#]+)', parsed.path)
        if m:
            match_id = m.group(1)
        if match_id is None and parsed.path.startswith("/api/stream-link/"):
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) >= 4:
                source = parts[2]
                match_id = parts[3]
        if match_id is None and parsed.path.startswith("/multiview"):
            match_id = parse_qs(parsed.query).get("match", [None])[0]
        if not match_id:
            return None
        sources = [source] if source else ["iframe"]
        if not source:
            page = self._fetch(f"https://streamcenter.st/watch/{match_id}")
            if page:
                providers = re.findall(r'provider\\":\\"([a-z0-9]+)', page) + re.findall(r'"provider":"([a-z0-9]+)', page)
                for p in providers:
                    if p not in sources:
                        sources.append(p)
        for src in sources:
            data = self._fetch(f"https://streamcenter.st/api/stream/{src}/{match_id}")
            if not data:
                continue
            try:
                import json
                entries = json.loads(data)
            except Exception:
                entries = None
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict) and entry.get("embedUrl"):
                        return entry["embedUrl"]
        return None

    def _clean_link(self, link: Optional[JetLink]) -> Optional[JetLink]:
        if link is None:
            return None
        address = link.address
        for raw, rep in (("\\u0026", "&"), ("\\u002F", "/"), ("\\u002f", "/"), ("\\/", "/")):
            address = address.replace(raw, rep)
        link.address = address
        return link

    def get_link(self, url: JetLink) -> JetLink:
        link = self._resolve(url)
        if link is None:
            return None
        return self._register_proxy(link, url.address)

    def _resolve(self, url: JetLink) -> JetLink:
        from ..util import m3u8_src

        #xbmc.log(f"[StreamsCenter] Starting extraction for: {url.address}", #xbmc.logINFO)
        target = url.address
        if "streamcenter.st" in urlparse(target).netloc:
            embed_url = self._streamcenter_embed_url(target)
            if not embed_url:
                return None
            target = embed_url

        parsed = urlparse(target)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        headers = {
            "User-Agent": self.user_agent,
            "Referer": f"{origin}/",
            "Origin": origin,
        }
        try:
            r = get_session().get(target, headers=headers, timeout=self.timeout)

            iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', r.text, re.IGNORECASE)
            if not iframe_match:
                return self._clean_link(m3u8_src.scan_page(target, html=r.text, headers=headers))

            iframe_url = urljoin(target, iframe_match.group(1))

            iframe_headers = dict(headers)
            iframe_headers["Referer"] = target
            r_iframe = get_session().get(iframe_url, headers=iframe_headers, timeout=self.timeout)

            input_patterns = [
                r'(?:var\s+)?input\s*[=:]\s*["\']([^"\']+)["\']',
                r'data-input=["\']([^"\']+)["\']',
                r'input:\s*["\']([^"\']+)["\']'
            ]

            payload = None
            for pattern in input_patterns:
                input_match = re.search(pattern, r_iframe.text, re.IGNORECASE)
                if input_match:
                    payload = input_match.group(1)
                    break

            if not payload:
                return self._clean_link(m3u8_src.scan_page(iframe_url, html=r_iframe.text, headers=iframe_headers))

            decrypt_url = "https://streams.center/embed/decrypt.php"
            post_headers = iframe_headers.copy()
            post_headers["Content-Type"] = "application/x-www-form-urlencoded"
            post_headers["X-Requested-With"] = "XMLHttpRequest"
            r_decrypt = get_session().post(decrypt_url, data={"input": payload}, headers=post_headers, timeout=self.timeout)

            decrypted = r_decrypt.text.strip()

            m3u8_match = re.search(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', decrypted, re.IGNORECASE)
            if m3u8_match:
                return JetLink(m3u8_match.group(1), headers=headers)

            stream_match = re.search(r'stream=([a-z0-9]+)', decrypted)
            if stream_match:
                stream_id = stream_match.group(1)
                return JetLink(f"https://edgestreams.pro/hls/{stream_id}.m3u8", headers=headers)

        except Exception as e:
            #xbmc.log(f"[StreamsCenter] Request exception: {str(e)}", #xbmc.logERROR)
            return None

        #xbmc.log("[StreamsCenter] Extraction failed, returning None", #xbmc.logWARNING)
        return None

    def _register_proxy(self, link: JetLink, original_address: str) -> JetLink:
        try:
            headers = dict(link.headers or {})
            if not link.inputstream:
                link.inputstream = JetInputstreamFFmpegDirect.default()

            def refresh():
                try:
                    fresh = self._resolve(JetLink(original_address))
                except Exception:
                    fresh = None
                if fresh and isinstance(fresh.address, str) and fresh.address.startswith("http") and "127.0.0.1" not in fresh.address:
                    return {"url": fresh.address, "headers": dict(fresh.headers or {})}
                return None

            proxy = get_stream_proxy(
                "streamcenter",
                headers,
                options={
                    "proxy_absolute_urls": True,
                    "keep_alive": False,
                    "upstream_keep_alive": True,
                    "prefetch_segments": True,
                    "prefetch_depth": 3,
                },
            )
            link.address = proxy.get_proxy_url(link.address, headers, refresh_callback=refresh)
            return link
        except Exception:
            return link
