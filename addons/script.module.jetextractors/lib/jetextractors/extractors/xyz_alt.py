from ..models import *
from typing import List, Optional
import re
import time
from urllib.parse import urlparse, parse_qs, quote

from ..tools import debug_log
from .._core import get_session
import xbmc
from ..util import embedsportstop
from ..util.stream_proxy import get_stream_proxy

from .XYZ import XYZ


class XYZAlt(XYZ):
    """Alt-site extractor, split out of XYZ.

    Lists streams from the ppv.st alt API and resolves third-party embeds
    (embedindia via embedsportstop, taifood via the browser-relay daemon,
    plus generic embed-page scraping shared with XYZ).
    """

    _ALT_HOST = "xyz-alt.invalid"
    _TAIFOOD_HOST = "taifood-blog.asia"
    _TAIFOOD_DAEMON_PORT = 18927

    def __init__(self) -> None:
        super().__init__()
        self.name = "XYZAlt"
        self.short_name = "XYZAlt"
        self.domains = [self._ALT_HOST]
        self.alt_streams_api = "https://api.ppv.st/api/streams"

    def _alt_resolver_url(self, iframe_url: str) -> str:
        return f"https://{self._ALT_HOST}/resolve?url={quote(iframe_url, safe='')}"

    def _fetch_alt_streams(self) -> List[JetItem]:
        items: List[JetItem] = []
        try:
            headers = dict(self.stream_headers)
            headers.update({
                "Accept": "application/json",
                "Origin": self.base_url,
                "Referer": f"{self.base_url}/alt",
            })
            resp = get_session().get(
                self.alt_streams_api,
                timeout=self.timeout,
                headers=headers,
            )
            if resp.status_code != 200:
                debug_log(f"[XYZAlt] Alt streams API returned {resp.status_code}", xbmc.LOGWARNING)
                return items
            data = resp.json()
            if not isinstance(data, dict) or not data.get("success"):
                return items
            categories = data.get("streams", [])
            if not isinstance(categories, list):
                return items
            now = time.time()
            for category in categories:
                if not isinstance(category, dict):
                    continue
                category_name = str(category.get("category") or "Sports").strip()
                streams = category.get("streams", [])
                if not isinstance(streams, list):
                    continue
                for stream in streams:
                    if not isinstance(stream, dict):
                        continue
                    title = str(stream.get("name") or "Stream").strip()
                    iframe = stream.get("iframe")
                    if not title or not isinstance(iframe, str) or not iframe.startswith(("http://", "https://")):
                        continue
                    links = [JetLink(self._alt_resolver_url(iframe), name=str(stream.get("tag") or "Main"), links=True)]
                    substreams = stream.get("substreams", [])
                    if isinstance(substreams, list):
                        for substream in substreams:
                            if not isinstance(substream, dict):
                                continue
                            sub_iframe = substream.get("iframe")
                            if isinstance(sub_iframe, str) and sub_iframe.startswith(("http://", "https://")):
                                links.append(
                                    JetLink(
                                        self._alt_resolver_url(sub_iframe),
                                        name=str(substream.get("tag") or substream.get("name") or "Alternate"),
                                        links=True,
                                    )
                                )
                    starts_at = stream.get("starts_at")
                    ends_at = stream.get("ends_at")
                    always_live = bool(stream.get("always_live") or category.get("always_live"))
                    status = "LIVE" if always_live else None
                    if not always_live and isinstance(starts_at, (int, float)):
                        if now < starts_at:
                            status = "Upcoming"
                        elif isinstance(ends_at, (int, float)) and now > ends_at:
                            status = "Ended"
                        else:
                            status = "LIVE"
                    items.append(
                        JetItem(
                            title=title,
                            league=self._guess_league(title, category_name),
                            links=links,
                            status=status,
                            icon=stream.get("poster"),
                        )
                    )
        except Exception as e:
            debug_log(f"[XYZAlt] Alt streams fetch failed: {e}", xbmc.LOGWARNING)
        return items

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items
        alt_items = self._fetch_alt_streams()
        items.extend(alt_items)

        # Attach matching homepage event-page links as fallbacks.
        try:
            homepage_items, _ = self._fetch_homepage_data()
            for alt in alt_items:
                alt_title_clean = re.sub(r'\[.*?\]\s*', '', alt.title).strip().lower()
                for event in homepage_items:
                    event_title_clean = re.sub(r'\[.*?\]\s*', '', event.title).strip().lower()
                    if alt_title_clean and event_title_clean and alt_title_clean == event_title_clean:
                        existing_addrs = {l.address for l in alt.links if hasattr(l, 'address')}
                        for link in event.links:
                            if hasattr(link, 'address') and link.links and link.address not in existing_addrs:
                                alt.links.append(JetLink(
                                    address=link.address,
                                    name="Event Page",
                                    links=True,
                                ))
                                debug_log(f"[XYZAlt] Added event page link to alt item: {alt.title} -> {link.address}", xbmc.LOGINFO)
                        break
        except Exception as e:
            debug_log(f"[XYZAlt] Homepage merge failed: {e}", xbmc.LOGDEBUG)

        for alt in alt_items:
            link_addrs = [l.address for l in alt.links if hasattr(l, "address")]
            debug_log(f"[XYZAlt] Alt: {alt.title} -> {link_addrs}", xbmc.LOGINFO)
        debug_log(f"[XYZAlt] Total items: {len(items)} (Alt={len(alt_items)})", xbmc.LOGINFO)
        return items

    def get_links(self, url: JetLink) -> List[JetLink]:
        debug_log(f"[XYZAlt] get_links called for: {url.address}", xbmc.LOGINFO)
        links: List[JetLink] = []

        parsed = urlparse(url.address)
        if parsed.netloc == self._ALT_HOST or parsed.path == "/jetextractor/alt":
            iframe_urls = parse_qs(parsed.query).get("url", [])
            if not iframe_urls:
                return links
            embed_url = iframe_urls[0]
        else:
            embed_url = url.address

        if "embedindia" in urlparse(embed_url).netloc:
            try:
                stream_url = embedsportstop.get_embedsportstop_stream(embed_url)
                if stream_url:
                    embed_origin = f"{urlparse(embed_url).scheme}://{urlparse(embed_url).netloc}"
                    headers = {
                        "Origin": embed_origin,
                        "Referer": f"{embed_origin}/",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
                        "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
                        "sec-ch-ua-mobile": "?0",
                        "sec-ch-ua-platform": '"Windows"',
                        "Accept": "*/*",
                    }
                    debug_log(f"[XYZAlt] Resolved embedindia stream URL: {stream_url}", xbmc.LOGINFO)
                    proxy = get_stream_proxy(
                        "xyz_alt",
                        headers,
                        options={
                            "strip_png": True,
                            "manifest_png_to_ts": True,
                            "proxy_absolute_urls": True,
                            "cache_manifest": False,
                            "add_icy_metadata": False,
                            "browser_tls": True,
                        },
                    )
                    proxy_url = proxy.get_proxy_url(stream_url, headers)
                    links.append(
                        JetLink(
                            address=proxy_url,
                            name=url.name or "Stream",
                            inputstream=JetInputstreamAdaptive(
                                manifest_type="hls",
                                manifest_headers=headers,
                            ),
                            resolveurl=False,
                        )
                    )
            except Exception as e:
                debug_log(f"[XYZAlt] EmbedIndia resolution failed: {e}", xbmc.LOGWARNING)
            return links

        if self._TAIFOOD_HOST in embed_url:
            tlink = self._resolve_taifood_stream(embed_url)
            if tlink:
                links.append(tlink)
                return links

        try:
            return self._resolve_embed_page(embed_url, url)
        except Exception as e:
            debug_log(f"[XYZAlt] Error in get_links: {e}", xbmc.LOGERROR)

        return links

    @staticmethod
    def _taifood_resolver_dir() -> str:
        import os
        return os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "util", "taifood_resolver",
        ))

    def _ensure_taifood_daemon(self) -> Optional[int]:
        """Start (or reuse) the local taifood browser-relay daemon.

        The daemon keeps headless Chrome playing the taifood embed page and
        serves its rolling media playlist over local HTTP — the /fetch relay
        crypto and the indianservers TLS fingerprint cannot be reproduced from
        Python. Returns the daemon port, or None when node/npm/Chrome are
        unavailable.
        """
        import os
        import shutil
        import subprocess
        port = self._TAIFOOD_DAEMON_PORT
        base = f"http://127.0.0.1:{port}"
        try:
            r = get_session().get(f"{base}/health", timeout=2)
            if r.status_code == 200 and r.json().get("ok"):
                return port
        except Exception:
            pass

        node = shutil.which("node")
        if not node:
            debug_log("[XYZAlt] taifood daemon needs node on PATH (install Node.js)", xbmc.LOGWARNING)
            return None
        resolver_dir = self._taifood_resolver_dir()
        daemon_js = os.path.join(resolver_dir, "taifood_daemon.js")
        if not os.path.isfile(daemon_js):
            debug_log(f"[XYZAlt] taifood daemon script missing: {daemon_js}", xbmc.LOGWARNING)
            return None
        if not os.path.isdir(os.path.join(resolver_dir, "node_modules", "puppeteer-core")):
            npm = shutil.which("npm")
            if not npm:
                debug_log("[XYZAlt] taifood resolver needs `npm install puppeteer-core` (npm not found)", xbmc.LOGWARNING)
                return None
            debug_log("[XYZAlt] Installing taifood resolver dependencies (npm install)…", xbmc.LOGINFO)
            try:
                kwargs = {"cwd": resolver_dir, "timeout": 240}
                if os.name == "nt":
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                subprocess.run([npm, "install", "--no-audit", "--no-fund"], **kwargs)
            except Exception as e:
                debug_log(f"[XYZAlt] npm install failed: {e}", xbmc.LOGWARNING)
                return None
            if not os.path.isdir(os.path.join(resolver_dir, "node_modules", "puppeteer-core")):
                debug_log("[XYZAlt] puppeteer-core still missing after npm install", xbmc.LOGWARNING)
                return None
        try:
            kwargs = {
                "cwd": resolver_dir,
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }
            if os.name == "nt":
                kwargs["creationflags"] = (
                    subprocess.CREATE_NEW_PROCESS_GROUP
                    | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
                    | subprocess.CREATE_NO_WINDOW
                )
            else:
                kwargs["start_new_session"] = True
            subprocess.Popen([node, daemon_js, str(port)], **kwargs)
        except Exception as e:
            debug_log(f"[XYZAlt] taifood daemon spawn failed: {e}", xbmc.LOGWARNING)
            return None
        import time as _t
        for _ in range(30):
            _t.sleep(0.4)
            try:
                r = get_session().get(f"{base}/health", timeout=2)
                if r.status_code == 200 and r.json().get("ok"):
                    debug_log(f"[XYZAlt] taifood daemon ready on {base}", xbmc.LOGINFO)
                    return port
            except Exception:
                continue
        debug_log("[XYZAlt] taifood daemon did not become healthy in time", xbmc.LOGWARNING)
        return None

    def _resolve_taifood_stream(self, iframe_url: str) -> Optional[JetLink]:
        """Resolve a taifood-blog.asia alt embed via the local browser daemon.

        The embed's stream URL is minted by an obfuscated wasm relay and the
        indianservers manifests are TLS-fingerprint bound, so the daemon plays
        the page in headless Chrome and relays the rolling media playlist on
        localhost. Video segments are public tiktokcdn URLs (WebP-wrapped TS)
        which the stream proxy fetches and unwraps directly.
        """
        try:
            port = self._ensure_taifood_daemon()
            if not port:
                return None
            resp = get_session().get(
                f"http://127.0.0.1:{port}/resolve",
                params={"url": iframe_url},
                timeout=75,
            )
            data = resp.json() if resp.status_code == 200 else {}
            if not data.get("ok"):
                debug_log(f"[XYZAlt] taifood daemon resolve failed: {data}", xbmc.LOGWARNING)
                return None
            upstream = f"http://127.0.0.1:{port}/m/{data['id']}.m3u8"
            proxy_url = self._build_proxy_link(upstream, dict(self.stream_headers))
            parsed = urlparse(iframe_url)
            name = (parsed.path.rstrip("/").rsplit("/", 1)[-1] or "Stream")
            debug_log(
                f"[XYZAlt] taifood session {data['id']} variant={data.get('variant_url')} "
                f"segments={data.get('segments')}",
                xbmc.LOGINFO,
            )
            return JetLink(
                address=proxy_url,
                name=name,
                headers=dict(self.stream_headers),
                inputstream=JetInputstreamAdaptive(manifest_type="hls"),
                resolveurl=False,
            )
        except Exception as e:
            debug_log(f"[XYZAlt] taifood resolve failed: {e}", xbmc.LOGWARNING)
            return None
