import re
import json
import base64
import xbmc
import requests
from datetime import date, datetime
from urllib.parse import urlparse, urljoin, quote, parse_qs
from ..models import *
from ..util import embedsportstop
from ..util.stream_proxy import get_stream_proxy


class Mutstreams(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["mut.st", "mut-streams.info"]
        self.name = "Mutstreams"
        self.short_name = "MUT"
        self.timeout = 10
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "Roku/DVP-9.40 (007.32E04185A)",
            "Mozilla/5.0 (SMART-TV; Linux; Tizen 6.0) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/16.0 TV Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Android 13; Mobile; rv:119.0) Gecko/119.0 Firefox/119.0",
            "Mozilla/5.0 (Linux; U; Android 4.4.2; en-us; SCH-I535 Build/KOT49H) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30",
            "Mozilla/5.0 (Linux; Android 12; AFTN Build/SQKQ.220-XXX) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
        ]

        # Regexes ported from BaseWebStream
        self.IFRAME = re.compile(r'<iframe\b[^>]*\bsrc=["\']([^"\']+)["\']', re.IGNORECASE)
        self.CLAPPR = re.compile(r'Clappr\.Player\(\{.*?source\s*:\s*(?:[^,}\n]*?[\'"]([^\'"]+)[\'"]|(\w+))', re.IGNORECASE | re.DOTALL)
        self.SRC = re.compile(r'var\s+src\s*=\s*(?:[^,;\n]*?[\'"]([^\'"]+)[\'"]|(\w+))', re.IGNORECASE | re.DOTALL)
        self.FIDSRC = re.compile(r'fid="([^"]+)".*?src="//([^"]+\.js)"', re.IGNORECASE | re.DOTALL)
        self.CHAR_ARRAY = re.compile(r'(\["h","t","t","p",.+?\])\.join\(""\)', re.IGNORECASE | re.DOTALL)
        self.M3U8 = re.compile(r"['\"]([^'\"]*\.m3u8[^'\"]*)['\"]", re.IGNORECASE)

    @property
    def _api_ua(self):
        return self.user_agents[0]

    @property
    def _player_ua(self):
        return self.user_agents[3]

    def _session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({
            'User-Agent': self._api_ua,
            'Origin': f'https://{self.domains[0]}',
            'Referer': f'https://{self.domains[0]}/'
        })
        return s

    def _clean_url(self, captured, url):
        if not captured:
            return ""
        try:
            captured = base64.b64decode(captured, validate=True).decode("utf-8")
        except Exception:
            pass
        captured = captured.replace("\\/", "/")
        if captured.startswith("//"):
            captured = "https:" + captured
        elif not captured.startswith("http"):
            captured = urljoin(url, captured)
        return captured

    def _find_iframe(self, html_content, url):
        for match in self.IFRAME.finditer(html_content):
            src = match.group(1)
            if not any(p in src.lower() for p in ("getbanner", "ad.html", "doubleclick", "googlesyndication")):
                return self._clean_url(src, url)
        return ""

    def _follow_iframes(self, s: requests.Session, url: str, user_agent: str = None, max_depth: int = 8):
        user_agent = user_agent or self._player_ua
        headers = {}
        r = s.get(url, timeout=self.timeout)

        for _ in range(max_depth):
            iframe = self._find_iframe(r.text, url)
            if not iframe or iframe == url:
                break

            domain = f"https://{urlparse(url).netloc}"
            hop_headers = {
                "Referer": f"{domain}/",
                "Origin": domain,
                "User-Agent": user_agent
            }

            try:
                r = s.get(iframe, headers=hop_headers, timeout=self.timeout)
            except requests.exceptions.RequestException as e:
                xbmc.log(f"[Mutstreams] Failed to follow iframe {iframe}: {e}", xbmc.LOGERROR)
                break
            url, headers = iframe, hop_headers

        return r, url, headers

    def _find_clappr(self, html_content, url):
        match = self.CLAPPR.search(html_content)
        if not match:
            return ""
        src = match.group(1)
        if not src and match.group(2):
            var = re.search(rf'\b{match.group(2)}\b\s*=\s*[\'"]([^\'"]+)[\'"]', html_content)
            src = var.group(1) if var else ""
        return self._clean_url(src, url) if src else ""

    def _find_src(self, html_content, url):
        match = self.SRC.search(html_content)
        if not match:
            return ""
        src = match.group(1)
        if not src and match.group(2):
            var = re.search(rf'\b{match.group(2)}\b\s*=\s*[\'"]([^\'"]+)[\'"]', html_content)
            src = var.group(1) if var else ""
        return self._clean_url(src, url) if src else ""

    def _find_m3u8(self, html_content, url):
        match = self.M3U8.search(html_content)
        return self._clean_url(match.group(1), url) if match else ""

    def _select_variant(self, session: requests.Session, master_url: str, headers: dict) -> str:
        """Fetch master playlist and return a real HLS variant, skipping PNG decoys."""
        try:
            # Use headers that mimic ffmpeg/Kodi's playlist fetch
            fetch_headers = dict(headers)
            fetch_headers.setdefault("Accept", "*/*")
            fetch_headers.setdefault("Connection", "close")
            fetch_headers.setdefault("Icy-MetaData", "1")

            r = requests.get(master_url, headers=fetch_headers, timeout=self.timeout)
            text = r.text
            xbmc.log(f"[Mutstreams] Master playlist ({len(text)} chars):\n{text[:2000]}", xbmc.LOGINFO)
            if "#EXTM3U" not in text:
                # Retry with the same UA embedsportstop uses for decryption
                xbmc.log("[Mutstreams] Master fetch failed, retrying with Chrome/143 UA", xbmc.LOGWARNING)
                fetch_headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
                r = requests.get(master_url, headers=fetch_headers, timeout=self.timeout)
                text = r.text
                xbmc.log(f"[Mutstreams] Retry master playlist ({len(text)} chars):\n{text[:2000]}", xbmc.LOGINFO)
                if "#EXTM3U" not in text:
                    xbmc.log("[Mutstreams] Upstream did not return a valid M3U8", xbmc.LOGERROR)
                    return ""

            lines = [line.strip() for line in text.splitlines() if line.strip()]
            variants = []
            for i, line in enumerate(lines):
                if line.upper().startswith("#EXT-X-STREAM-INF"):
                    for j in range(i + 1, len(lines)):
                        if not lines[j].startswith("#"):
                            variants.append(lines[j])
                            break
            if not variants:
                xbmc.log("[Mutstreams] No variants found, using master URL", xbmc.LOGINFO)
                return master_url

            xbmc.log(f"[Mutstreams] Found {len(variants)} variant(s): {variants}", xbmc.LOGINFO)
            if len(variants) == 1:
                return urljoin(master_url, variants[0])

            # Prefer highest quality: tiktokcdn PNG-wrapped segments are high-quality
            # real video; plain .ts segments are lower-quality fallback.
            for variant in variants:
                variant_url = urljoin(master_url, variant)
                try:
                    vr = requests.get(variant_url, headers=fetch_headers, timeout=self.timeout)
                    vtext = vr.text
                    vtext_lower = vtext.lower()
                    has_tiktok = "tiktokcdn.com" in vtext_lower
                    has_ts = ".ts" in vtext_lower
                    has_png = ".png" in vtext_lower
                    xbmc.log(
                        f"[Mutstreams] Variant {variant_url} -> tiktok={has_tiktok}, ts={has_ts}, png={has_png}",
                        xbmc.LOGINFO
                    )
                    if has_tiktok or (has_ts and not has_png):
                        return variant_url
                except Exception as e:
                    xbmc.log(f"[Mutstreams] Failed to inspect variant {variant_url}: {e}", xbmc.LOGERROR)
                    continue

            # Fallback to last variant
            return urljoin(master_url, variants[-1])
        except Exception as e:
            xbmc.log(f"[Mutstreams] _select_variant error: {e}", xbmc.LOGERROR)
            return master_url

    def _decode_array(self, html_content, url):
        match = self.CHAR_ARRAY.search(html_content)
        if match:
            char_array = json.loads(match.group(1))
            return self._clean_url("".join(char_array), url)
        return ""

    def _find_fid_src(self, s: requests.Session, html_content):
        try:
            match = self.FIDSRC.search(html_content)
            if not match:
                xbmc.log("[Mutstreams] No fid/src pattern found in page", xbmc.LOGWARNING)
                return "", {}
            fid = match.group(1)
            url = f"https://{match.group(2).replace('.js', '.php')}?player=desktop&live={fid}"
            domain = f"https://{urlparse(url).netloc}"
            headers = {"Referer": domain + "/", "Origin": domain}
            r = s.get(url, headers=headers, timeout=self.timeout)
            stream_url = self._decode_array(r.text, url)
            return stream_url, headers
        except Exception as e:
            xbmc.log(f"[Mutstreams] find_fid_src error: {e}", xbmc.LOGERROR)
            return "", {}

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        xbmc.log("[Mutstreams] get_items: fetching event list", xbmc.LOGINFO)
        try:
            session = self._session()
            api_url = f"https://{self.domains[0]}/api/streams?lite=false"
            xbmc.log(f"[Mutstreams] API URL: {api_url}", xbmc.LOGINFO)
            r = session.get(api_url, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            xbmc.log(f"[Mutstreams] API returned {len(data)} groups", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"[Mutstreams] get_items error: {e}", xbmc.LOGERROR)
            return items

        for group in data:
            category = group.get("title") or group.get("group") or group.get("groupId") or "Other"
            for stream in group.get("streams", []):
                if self.progress_update(progress):
                    return items

                event_time = stream.get("time", "")
                date_match = re.search(r'\((\d{2}/\d{2}/\d{4})\)', event_time)
                if date_match:
                    try:
                        # Avoid datetime.strptime; some Kodi Python builds expose it as None.
                        m, d, y = date_match.group(1).split('/')
                        event_date = datetime(int(y), int(m), int(d)).date()
                        if event_date != date.today():
                            continue
                    except Exception:
                        pass

                links = []
                for source in stream.get("sources", []):
                    embed_url = source.get("embedUrl")
                    if not embed_url:
                        continue
                    if embed_url.startswith("/"):
                        embed_url = f"https://{self.domains[0]}{embed_url}"

                    # The API does not provide a source name, so build the same
                    # label shown on the site from hd/streamNo/language.
                    quality = "HD" if source.get("hd") else "SD"
                    stream_no = source.get("streamNo", "")
                    language = source.get("language", "")
                    src_provider = source.get("source", "").strip().title()

                    source_name = f"{quality} • Stream [COLORyellow]{stream_no}[/COLOR]"
                    if language:
                        source_name += f" [COLORyellow]{language}[/COLOR]"
                    if src_provider:
                        source_name = f"{src_provider} - {source_name}"

                    # Proxy the real embed URL through a mut.st address so
                    # JetExtractors routes it back to this extractor.
                    proxy_url = f"https://{self.domains[0]}/jetextractor/mutstreams?url={quote(embed_url, safe='')}&source={quote(source_name, safe='')}&category={quote(category, safe='')}"
                    links.append(JetLink(proxy_url, name=source_name))

                if not links:
                    continue

                title = stream.get("title", "")
                title = f"[{category}] {title}"
                if event_time:
                    title += f"  |  {event_time}"
                xbmc.log(f"[Mutstreams] Found event: {title} with {len(links)} link(s)", xbmc.LOGINFO)
                items.append(JetItem(
                    title=title,
                    links=links,
                    league=stream.get("group") or stream.get("category") or stream.get("tag") or category,
                    icon=stream.get("image") or stream.get("poster") or "",
                    extractor=self.name
                ))

        xbmc.log(f"[Mutstreams] get_items: returning {len(items)} items", xbmc.LOGINFO)
        return items

    def get_link(self, url: JetLink) -> JetLink:
        xbmc.log(f"[Mutstreams] get_link called for: {url.address}", xbmc.LOGINFO)
        try:
            session = self._session()

            parsed = urlparse(url.address)
            if parsed.path == "/jetextractor/mutstreams" and parsed.netloc in self.domains:
                query = parse_qs(parsed.query)
                real_url = query.get("url", [""])[0]
                category = query.get("category", [""])[0]
                source_name = query.get("source", [""])[0]
                xbmc.log(f"[Mutstreams] Decoded proxy URL -> real_url={real_url}, category={category}, source={source_name}", xbmc.LOGINFO)
                if not real_url:
                    xbmc.log("[Mutstreams] Empty real_url from proxy, aborting", xbmc.LOGERROR)
                    return None
            else:
                real_url = url.address
                xbmc.log("[Mutstreams] Using direct URL (not a proxy)", xbmc.LOGINFO)

            embed_url = real_url.replace("/embed/", "/embed-noads/")
            xbmc.log(f"[Mutstreams] Resolving embed URL: {embed_url}", xbmc.LOGINFO)

            r, final_url, _ = self._follow_iframes(session, embed_url, self._player_ua)
            xbmc.log(f"[Mutstreams] Final iframe URL: {final_url}", xbmc.LOGINFO)

            domain = f"https://{urlparse(final_url).netloc}"
            headers = {
                "Referer": f"{domain}/",
                "Origin": domain,
                "User-Agent": self._player_ua
            }
            xbmc.log(f"[Mutstreams] Playback headers: {headers}", xbmc.LOGINFO)

            stream_url = ""
            if any(host in final_url for host in ("embedsports.top", "pooembed", "embed.st", "embedindia")):
                xbmc.log("[Mutstreams] Resolving via embedsportstop", xbmc.LOGINFO)
                try:
                    stream_url = embedsportstop.get_embedsportstop_stream(final_url)
                except Exception as e:
                    xbmc.log(f"[Mutstreams] embedsportstop failed: {e}", xbmc.LOGERROR)
            if not stream_url and (m3u8 := self._find_clappr(r.text, final_url)):
                xbmc.log(f"[Mutstreams] Resolved via clappr: {m3u8}", xbmc.LOGINFO)
                stream_url = m3u8
            if not stream_url and (m3u8 := self._find_src(r.text, final_url)):
                xbmc.log(f"[Mutstreams] Resolved via var src: {m3u8}", xbmc.LOGINFO)
                stream_url = m3u8
            if not stream_url and (m3u8 := self._find_m3u8(r.text, final_url)):
                xbmc.log(f"[Mutstreams] Resolved via raw m3u8 search: {m3u8}", xbmc.LOGINFO)
                stream_url = m3u8
            if not stream_url:
                xbmc.log("[Mutstreams] Resolving via fid/src fallback", xbmc.LOGINFO)
                stream_url, headers = self._find_fid_src(session, r.text)

            if not stream_url:
                xbmc.log("[Mutstreams] Could not resolve stream URL", xbmc.LOGERROR)
                return None

            xbmc.log(f"[Mutstreams] Resolved master URL: {stream_url}", xbmc.LOGINFO)
            stream_url = self._select_variant(session, stream_url, headers)
            if not stream_url:
                xbmc.log("[Mutstreams] Could not select a valid variant", xbmc.LOGERROR)
                return None
            xbmc.log(f"[Mutstreams] Selected variant URL: {stream_url}", xbmc.LOGINFO)

            # Run the variant through the universal local proxy so PNG-wrapped
            # high-quality segments (tiktokcdn) are stripped back to clean TS data.
            proxy = get_stream_proxy(
                "mutstreams",
                headers,
                options={"strip_png": True, "manifest_png_to_ts": True},
            )
            proxy_url = proxy.get_proxy_url(stream_url, headers)
            xbmc.log(f"[Mutstreams] Proxy URL: {proxy_url}", xbmc.LOGINFO)

            link = JetLink(
                proxy_url,
                headers=headers,
                inputstream=JetInputstreamFFmpegDirect.default()
            )
            xbmc.log(f"[Mutstreams] Final Kodi path: {link.xbmc_format()}", xbmc.LOGINFO)
            return link
        except Exception as e:
            xbmc.log(f"[Mutstreams] get_link error: {e}", xbmc.LOGERROR)
            import traceback
            xbmc.log(traceback.format_exc(), xbmc.LOGERROR)
            return None
