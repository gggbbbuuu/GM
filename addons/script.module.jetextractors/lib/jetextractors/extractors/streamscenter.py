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

    def _fetch_final(self, url: str, referer: str = "https://streamcenter.st/") -> tuple:
        """GET following redirects; returns (text, final_url)."""
        try:
            r = get_session().get(
                url,
                headers={"User-Agent": self.user_agent, "Referer": referer},
                timeout=self.timeout,
                allow_redirects=True,
            )
            if r.status_code == 200:
                return r.text, r.url
        except Exception:
            pass
        return "", ""

    @staticmethod
    def _parse_watch_sources(page: str) -> list:
        """Extract [{id, provider}] from the watch page RSC payload.

        The Next flight chunks carry escaped quotes; try raw then unescaped.
        """
        import json
        for pat in (r'"sources":(\[\{.*?\}\])', r'\\"sources\\":(\[\{.*?\}\])'):
            m = re.search(pat, page)
            if not m:
                continue
            frag = m.group(1).replace('\\"', '"')
            try:
                data = json.loads(frag)
            except Exception:
                continue
            entries = [
                {"id": e.get("id"), "provider": e.get("provider")}
                for e in data
                if isinstance(e, dict) and e.get("id") and e.get("provider")
            ]
            if entries:
                return entries
        ids = re.findall(r'\{"id":"([0-9a-f\-]{36})","provider":"([a-z0-9]+)"', page)
        if not ids:
            ids = re.findall(
                r'\{\\?"id\\?":\\?"([0-9a-f\-]{36})\\?",\\?"provider\\?":\\?"([a-z0-9]+)\\?"',
                page,
            )
        return [{"id": i, "provider": p} for i, p in ids]

    def _fetch_embed_link(self, provider: str, match_id: str, source_id: str) -> Optional[str]:
        """Resolve /api/stream-link/<provider>/<match_id>/<source_id>.

        Live shape (2026-11): 302-redirects to the embed host page
        (e.g. streamec.st/embed/chXX.php). Some sources may return embedUrl JSON.
        """
        import json
        from urllib.parse import quote
        api = (
            f"https://streamcenter.st/api/stream-link/"
            f"{quote(str(provider), safe='')}/{quote(match_id, safe='')}/{quote(str(source_id), safe='')}"
        )
        text, final = self._fetch_final(api, referer=f"https://streamcenter.st/watch/{match_id}")
        if final and "/api/" not in urlparse(final).path:
            return final
        if text:
            try:
                data = json.loads(text)
                if isinstance(data, list):
                    for entry in data:
                        if isinstance(entry, dict) and entry.get("embedUrl"):
                            return entry["embedUrl"]
                elif isinstance(data, dict) and data.get("embedUrl"):
                    return data["embedUrl"]
            except Exception:
                if "<iframe" in text:
                    return final or api
        return None

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

        page = ""
        if not source:
            page = self._fetch(f"https://streamcenter.st/watch/{match_id}")
            if page:
                for entry in self._parse_watch_sources(page):
                    embed = self._fetch_embed_link(
                        entry.get("provider") or "iframe", match_id, entry.get("id")
                    )
                    if embed:
                        return embed

        sources = [source] if source else ["iframe"]
        if not source and page:
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

    @staticmethod
    def _find_input_payload(html: str) -> Optional[str]:
        for pattern in (
            r'(?:var\s+)?input\s*[=:]\s*["\']([^"\']+)["\']',
            r'data-input=["\']([^"\']+)["\']',
            r'input:\s*["\']([^"\']+)["\']',
        ):
            m = re.search(pattern, html, re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    def _resolve(self, url: JetLink) -> JetLink:
        from ..util import m3u8_src

        target = url.address
        if "streamcenter.st" in urlparse(target).netloc:
            embed_url = self._streamcenter_embed_url(target)
            if not embed_url:
                return None
            target = embed_url

        # Follow the embed iframe chain hop-by-hop (live 2026-11 shape:
        # streamcenter.st/api/stream-link -> streamec.st/embed/chXX.php ->
        # embedcenter.st/embed/chXX.php -> embedcenter.st/embed/hls_co.php?stream=X).
        # Per hop: edgestream access grant -> decrypt.php input -> m3u8 scan -> next iframe.
        page_url = target
        page_referer = "https://streamcenter.st/"
        for _hop in range(6):
            parsed = urlparse(page_url)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            headers = {
                "User-Agent": self.user_agent,
                "Referer": page_referer or f"{origin}/",
                "Origin": origin,
            }
            try:
                r = get_session().get(page_url, headers=headers, timeout=self.timeout)
                if r.status_code != 200:
                    return None
                html = r.text
            except Exception:
                return None

            # 1) edgestream access grant (hls_co.php): /sh/access/<token>/...
            #    ending .json -> the same path with .m3u8 is the playable edge
            #    playlist (bare /sh/cdn/... is 403). Refresh: ?grant=1 on this page.
            access_m = re.search(r'(https?://[^\s"\']+?/sh/access/[^\s"\']+?\.json)', html)
            if access_m:
                stream_url = access_m.group(1).rsplit(".", 1)[0] + ".m3u8"
                final_headers = {
                    "User-Agent": self.user_agent,
                    "Referer": f"{origin}/",
                    "Origin": origin,
                }
                return JetLink(stream_url, headers=final_headers)

            # 2) decrypt.php input payload (legacy streams.center class)
            payload = self._find_input_payload(html)
            if payload:
                try:
                    post_headers = dict(headers)
                    post_headers["Content-Type"] = "application/x-www-form-urlencoded"
                    post_headers["X-Requested-With"] = "XMLHttpRequest"
                    r_decrypt = get_session().post(
                        "https://streams.center/embed/decrypt.php",
                        data={"input": payload},
                        headers=post_headers,
                        timeout=self.timeout,
                    )
                    decrypted = (r_decrypt.text or "").strip()
                    m3u8_match = re.search(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', decrypted, re.IGNORECASE)
                    if m3u8_match:
                        return JetLink(m3u8_match.group(1), headers=headers)
                    stream_match = re.search(r'stream=([a-z0-9]+)', decrypted)
                    if stream_match:
                        return JetLink(
                            f"https://edgestreams.pro/hls/{stream_match.group(1)}.m3u8",
                            headers=headers,
                        )
                except Exception:
                    pass

            # 3) no further iframe: scan this page for a stream
            iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if not iframe_match:
                return self._clean_link(m3u8_src.scan_page(page_url, html=html, headers=headers))

            # 4) next hop
            page_referer = page_url
            page_url = urljoin(page_url, iframe_match.group(1))

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
                    # edgestream segments are PNG-wrapped MPEG-TS (tiktokcdn).
                    "strip_png": True,
                },
            )
            link.address = proxy.get_proxy_url(link.address, headers, refresh_callback=refresh)
            return link
        except Exception:
            return link
