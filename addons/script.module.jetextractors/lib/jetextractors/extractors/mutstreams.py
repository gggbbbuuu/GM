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
from ..tools import debug_log


def _slugify(title: str) -> str:
    s = title.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_]+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')


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
                debug_log(f"[Mutstreams] Failed to follow iframe {iframe}: {e}", xbmc.LOGERROR)
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
            debug_log(f"[Mutstreams] Master playlist ({len(text)} chars):\n{text[:2000]}", xbmc.LOGINFO)
            if "#EXTM3U" not in text:
                # Retry with the same UA embedsportstop uses for decryption
                debug_log("[Mutstreams] Master fetch failed, retrying with Chrome/143 UA", xbmc.LOGWARNING)
                fetch_headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
                r = requests.get(master_url, headers=fetch_headers, timeout=self.timeout)
                text = r.text
                debug_log(f"[Mutstreams] Retry master playlist ({len(text)} chars):\n{text[:2000]}", xbmc.LOGINFO)
                if "#EXTM3U" not in text:
                    debug_log("[Mutstreams] Upstream did not return a valid M3U8", xbmc.LOGERROR)
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
                debug_log("[Mutstreams] No variants found, using master URL", xbmc.LOGINFO)
                return master_url

            debug_log(f"[Mutstreams] Found {len(variants)} variant(s): {variants}", xbmc.LOGINFO)
            if len(variants) == 1:
                return urljoin(master_url, variants[0])

            # Prefer highest quality: tiktokcdn PNG-wrapped segments are high-quality
            # real video; .mp4 segments from cdn.files-text.com are also good;
            # plain .ts segments are lower-quality fallback (may return 403).
            for variant in variants:
                variant_url = urljoin(master_url, variant)
                try:
                    vr = requests.get(variant_url, headers=fetch_headers, timeout=self.timeout)
                    vtext = vr.text
                    vtext_lower = vtext.lower()
                    has_tiktok = "tiktokcdn.com" in vtext_lower
                    has_ts = ".ts" in vtext_lower
                    has_png = ".png" in vtext_lower
                    has_mp4 = ".mp4" in vtext_lower
                    debug_log(
                        f"[Mutstreams] Variant {variant_url} -> tiktok={has_tiktok}, ts={has_ts}, png={has_png}, mp4={has_mp4}",
                        xbmc.LOGINFO
                    )
                    if has_tiktok or has_mp4 or (has_ts and not has_png):
                        return variant_url
                except Exception as e:
                    debug_log(f"[Mutstreams] Failed to inspect variant {variant_url}: {e}", xbmc.LOGERROR)
                    continue

            # Fallback to last variant
            return urljoin(master_url, variants[-1])
        except Exception as e:
            debug_log(f"[Mutstreams] _select_variant error: {e}", xbmc.LOGERROR)
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
                debug_log("[Mutstreams] No fid/src pattern found in page", xbmc.LOGWARNING)
                return "", {}
            fid = match.group(1)
            url = f"https://{match.group(2).replace('.js', '.php')}?player=desktop&live={fid}"
            domain = f"https://{urlparse(url).netloc}"
            headers = {"Referer": domain + "/", "Origin": domain}
            r = s.get(url, headers=headers, timeout=self.timeout)
            stream_url = self._decode_array(r.text, url)
            return stream_url, headers
        except Exception as e:
            debug_log(f"[Mutstreams] find_fid_src error: {e}", xbmc.LOGERROR)
            return "", {}

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items

        debug_log("[Mutstreams] get_items: fetching event list", xbmc.LOGINFO)
        try:
            session = self._session()
            api_url = f"https://{self.domains[0]}/api/streams?lite=false"
            debug_log(f"[Mutstreams] API URL: {api_url}", xbmc.LOGINFO)
            r = session.get(api_url, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            debug_log(f"[Mutstreams] API returned {len(data)} groups", xbmc.LOGINFO)
        except Exception as e:
            debug_log(f"[Mutstreams] get_items error: {e}", xbmc.LOGERROR)
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

                links = self._build_source_links(stream, category)

                if not links:
                    continue

                title = stream.get("title", "")
                title = f"[{category}] {title}"
                if event_time:
                    title += f"  |  {event_time}"
                debug_log(f"[Mutstreams] Found event: {title} with {len(links)} link(s)", xbmc.LOGINFO)
                items.append(JetItem(
                    title=title,
                    links=links,
                    league=stream.get("group") or stream.get("category") or stream.get("tag") or category,
                    icon=stream.get("image") or stream.get("poster") or "",
                    extractor=self.name
                ))

        debug_log(f"[Mutstreams] get_items: returning {len(items)} items", xbmc.LOGINFO)
        return items

    def _build_source_links(self, stream: dict, category: str) -> list:
        sources = stream.get("sources", [])
        debug_log(f"[Mutstreams] _build_source_links: stream keys={list(stream.keys())}, sources count={len(sources)}", xbmc.LOGINFO)

        providers = {}
        for source in sources:
            provider = (source.get("source") or "").strip() or "Unknown"
            providers.setdefault(provider, []).append(source)

        links = []
        for provider, provider_sources in providers.items():
            provider_label = provider.title()
            source_infos = []
            for s in provider_sources:
                embed_url = s.get("embedUrl", "")
                if embed_url.startswith("/"):
                    embed_url = f"https://{self.domains[0]}{embed_url}"
                quality = "HD" if s.get("hd") else "SD"
                stream_no = s.get("streamNo", "")
                language = s.get("language", "") or "N/A"
                source_infos.append({
                    "url": embed_url,
                    "name": f"Stream {stream_no} {language}, {quality}"
                })
            sources_json = json.dumps(source_infos)
            encoded = quote(sources_json, safe='')
            proxy_url = (
                f"https://{self.domains[0]}/jetextractor/mutstreams"
                f"?sources={encoded}"
                f"&category={quote(category, safe='')}"
                f"&provider={quote(provider_label, safe='')}"
            )
            links.append(JetLink(proxy_url, name=provider_label, links=True))

        debug_log(f"[Mutstreams] _build_source_links: returning {len(links)} provider(s), names={[l.name for l in links]}", xbmc.LOGINFO)
        return links

    def get_links(self, url):
        debug_log(f"[Mutstreams] get_links called for: {url.address}", xbmc.LOGINFO)
        try:
            session = self._session()

            parsed = urlparse(url.address)
            is_proxy = (parsed.path == "/jetextractor/mutstreams"
                        and parsed.netloc in self.domains)
            is_watch = "/watch/" in url.address and any(
                d in url.address for d in self.domains
            )

            if is_proxy:
                query = parse_qs(parsed.query)

                sources_json = query.get("sources", [""])[0]
                if sources_json:
                    source_infos = json.loads(sources_json)
                    provider = query.get("provider", [""])[0]
                    category = query.get("category", [""])[0]
                    links = []
                    for info in source_infos:
                        embed_url = info["url"]
                        stream_label = info["name"]
                        source_proxy_url = (
                            f"https://{self.domains[0]}/jetextractor/mutstreams"
                            f"?url={quote(embed_url, safe='')}"
                            f"&source={quote(provider, safe='')}"
                            f"&category={quote(category, safe='')}"
                        )
                        links.append(JetLink(source_proxy_url, name=f"{provider} - {stream_label}", links=True))
                    debug_log(f"[Mutstreams] get_links: returning {len(links)} source(s) for provider {provider}", xbmc.LOGINFO)
                    return links

                real_url = query.get("url", [""])[0]
                source_name = query.get("source", [""])[0].replace("(", "").replace(")", "")
                category = query.get("category", [""])[0]
                if not real_url:
                    debug_log("[Mutstreams] get_links: empty real_url from proxy", xbmc.LOGERROR)
                    return []
                debug_log(f"[Mutstreams] get_links: exploring embed page {real_url}", xbmc.LOGINFO)
                embed_url = real_url.replace("/embed/", "/embed-noads/")
                r, final_url, _ = self._follow_iframes(session, embed_url, self._player_ua)
                debug_log(f"[Mutstreams] get_links: final iframe URL {final_url}", xbmc.LOGINFO)

                links = []
                seen = set()

                def _add(stream_url, label):
                    if stream_url and stream_url not in seen:
                        seen.add(stream_url)
                        proxy_url = f"https://{self.domains[0]}/jetextractor/mutstreams_direct?url={quote(stream_url, safe='')}&source={quote(source_name, safe='')}&category={quote(category, safe='')}&label={quote(label, safe='')}"
                        links.append(JetLink(proxy_url, name=label))

                if any(host in final_url for host in ("embedsports.top", "pooembed", "embed.st", "embedindia")):
                    try:
                        stream_url = embedsportstop.get_embedsportstop_stream(final_url)
                        if stream_url:
                            _add(stream_url, f"{source_name} - EmbedSports" if source_name else "EmbedSports")
                    except Exception as e:
                        debug_log(f"[Mutstreams] get_links embedsportstop failed: {e}", xbmc.LOGERROR)

                if (m3u8 := self._find_clappr(r.text, final_url)):
                    _add(m3u8, f"{source_name} - Clappr" if source_name else "Clappr")
                if (m3u8 := self._find_src(r.text, final_url)):
                    _add(m3u8, f"{source_name} - Source" if source_name else "Source")
                if (m3u8 := self._find_m3u8(r.text, final_url)):
                    _add(m3u8, f"{source_name} - M3U8" if source_name else "M3U8")

                if not links:
                    stream_url, _ = self._find_fid_src(session, r.text)
                    if stream_url:
                        _add(stream_url, f"{source_name} - FID" if source_name else "FID")

                if not links:
                    _add(real_url, source_name or "Stream")

                debug_log(f"[Mutstreams] get_links: returning {len(links)} link(s)", xbmc.LOGINFO)
                return links

            elif is_watch:
                slug = url.address.rstrip("/").split("/")[-1]
                debug_log(f"[Mutstreams] get_links: watch URL slug={slug}", xbmc.LOGINFO)
                try:
                    api_url = f"https://{self.domains[0]}/api/streams?lite=false"
                    data = session.get(api_url, timeout=self.timeout).json()
                except Exception as e:
                    debug_log(f"[Mutstreams] get_links: API fetch failed: {e}", xbmc.LOGERROR)
                    return []

                for group in data:
                    category = group.get("title") or group.get("group") or group.get("groupId") or "Other"
                    for stream in group.get("streams", []):
                        title = stream.get("title", "")
                        if _slugify(title) == slug:
                            debug_log(f"[Mutstreams] get_links: matched stream '{title}'", xbmc.LOGINFO)
                            links = self._build_source_links(stream, category)
                            if links:
                                return links

                debug_log(f"[Mutstreams] get_links: no match for slug '{slug}'", xbmc.LOGWARNING)
                return []

            else:
                debug_log("[Mutstreams] get_links: unrecognized URL format", xbmc.LOGWARNING)
                return []
        except Exception as e:
            debug_log(f"[Mutstreams] get_links error: {e}", xbmc.LOGERROR)
            import traceback
            debug_log(traceback.format_exc(), xbmc.LOGERROR)
            return []

    def get_link(self, url: JetLink) -> JetLink:
        debug_log(f"[Mutstreams] get_link called for: {url.address}", xbmc.LOGINFO)
        try:
            session = self._session()

            parsed = urlparse(url.address)
            if parsed.path == "/jetextractor/mutstreams_direct" and parsed.netloc in self.domains:
                query = parse_qs(parsed.query)
                real_url = query.get("url", [""])[0]
                category = query.get("category", [""])[0]
                source_name = query.get("source", [""])[0].replace("(", "").replace(")", "")
                debug_log(f"[Mutstreams] Decoded direct proxy -> real_url={real_url}", xbmc.LOGINFO)
                if not real_url:
                    debug_log("[Mutstreams] Empty real_url from direct proxy, aborting", xbmc.LOGERROR)
                    return None
                stream_url = real_url
                domain = f"https://{urlparse(real_url).netloc}"
                headers = {
                    "Referer": f"{domain}/",
                    "Origin": domain,
                    "User-Agent": self._player_ua
                }
                debug_log(f"[Mutstreams] Direct stream URL: {stream_url}", xbmc.LOGINFO)
                stream_url = self._select_variant(session, stream_url, headers)
                if not stream_url:
                    debug_log("[Mutstreams] Could not select a valid variant", xbmc.LOGERROR)
                    return None
                proxy = get_stream_proxy(
                    "mutstreams",
                    headers,
                    options={"strip_png": True, "manifest_png_to_ts": True},
                )
                proxy_url = proxy.get_proxy_url(stream_url, headers)
                link = JetLink(
                    proxy_url,
                    headers=headers,
                    inputstream=JetInputstreamFFmpegDirect.default()
                )
                debug_log(f"[Mutstreams] Final Kodi path (direct): {link.xbmc_format()}", xbmc.LOGINFO)
                return link

            elif parsed.path == "/jetextractor/mutstreams" and parsed.netloc in self.domains:
                query = parse_qs(parsed.query)
                real_url = query.get("url", [""])[0]
                category = query.get("category", [""])[0]
                source_name = query.get("source", [""])[0].replace("(", "").replace(")", "")
                debug_log(f"[Mutstreams] Decoded proxy URL -> real_url={real_url}, category={category}, source={source_name}", xbmc.LOGINFO)
                if not real_url:
                    debug_log("[Mutstreams] Empty real_url from proxy, aborting", xbmc.LOGERROR)
                    return None
            else:
                real_url = url.address
                debug_log("[Mutstreams] Using direct URL (not a proxy)", xbmc.LOGINFO)

            embed_url = real_url.replace("/embed/", "/embed-noads/")
            debug_log(f"[Mutstreams] Resolving embed URL: {embed_url}", xbmc.LOGINFO)

            r, final_url, _ = self._follow_iframes(session, embed_url, self._player_ua)
            debug_log(f"[Mutstreams] Final iframe URL: {final_url}", xbmc.LOGINFO)

            domain = f"https://{urlparse(final_url).netloc}"
            headers = {
                "Referer": f"{domain}/",
                "Origin": domain,
                "User-Agent": self._player_ua
            }
            debug_log(f"[Mutstreams] Playback headers: {headers}", xbmc.LOGINFO)

            stream_url = ""
            if any(host in final_url for host in ("embedsports.top", "pooembed", "embed.st", "embedindia")):
                debug_log("[Mutstreams] Resolving via embedsportstop", xbmc.LOGINFO)
                try:
                    stream_url = embedsportstop.get_embedsportstop_stream(final_url)
                except Exception as e:
                    debug_log(f"[Mutstreams] embedsportstop failed: {e}", xbmc.LOGERROR)
            if not stream_url and (m3u8 := self._find_clappr(r.text, final_url)):
                debug_log(f"[Mutstreams] Resolved via clappr: {m3u8}", xbmc.LOGINFO)
                stream_url = m3u8
            if not stream_url and (m3u8 := self._find_src(r.text, final_url)):
                debug_log(f"[Mutstreams] Resolved via var src: {m3u8}", xbmc.LOGINFO)
                stream_url = m3u8
            if not stream_url and (m3u8 := self._find_m3u8(r.text, final_url)):
                debug_log(f"[Mutstreams] Resolved via raw m3u8 search: {m3u8}", xbmc.LOGINFO)
                stream_url = m3u8
            if not stream_url:
                debug_log("[Mutstreams] Resolving via fid/src fallback", xbmc.LOGINFO)
                stream_url, headers = self._find_fid_src(session, r.text)

            if not stream_url:
                debug_log("[Mutstreams] Could not resolve stream URL", xbmc.LOGERROR)
                return None

            debug_log(f"[Mutstreams] Resolved master URL: {stream_url}", xbmc.LOGINFO)
            stream_url = self._select_variant(session, stream_url, headers)
            if not stream_url:
                debug_log("[Mutstreams] Could not select a valid variant", xbmc.LOGERROR)
                return None
            debug_log(f"[Mutstreams] Selected variant URL: {stream_url}", xbmc.LOGINFO)

            # Run the variant through the universal local proxy so PNG-wrapped
            # high-quality segments (tiktokcdn) are stripped back to clean TS data.
            proxy = get_stream_proxy(
                "mutstreams",
                headers,
                options={"strip_png": True, "manifest_png_to_ts": True},
            )
            proxy_url = proxy.get_proxy_url(stream_url, headers)
            debug_log(f"[Mutstreams] Proxy URL: {proxy_url}", xbmc.LOGINFO)

            link = JetLink(
                proxy_url,
                headers=headers,
                inputstream=JetInputstreamFFmpegDirect.default()
            )
            debug_log(f"[Mutstreams] Final Kodi path: {link.xbmc_format()}", xbmc.LOGINFO)
            return link
        except Exception as e:
            debug_log(f"[Mutstreams] get_link error: {e}", xbmc.LOGERROR)
            import traceback
            debug_log(traceback.format_exc(), xbmc.LOGERROR)
            return None
