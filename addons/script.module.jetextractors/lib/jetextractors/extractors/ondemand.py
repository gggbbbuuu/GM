from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress, JetInputstreamAdaptive, JetInputstreamFFmpegDirect
from .._core import get_headers, get_session, find_m3u8, find_iframes, make_link, fetch_json
from ..util.stream_proxy import get_stream_proxy
from ..tools import debug_log
import re
import time
import xbmc
from urllib.parse import urlparse, parse_qs, quote, unquote
from typing import Optional, List, Dict, Any

_TV_UA = "Mozilla/5.0 (SMART-TV; Linux; Tizen 6.0) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/16.0 TV Safari/537.36"

# Live TV: only these countries are listed (site country codes from /data/dlhd-channels.json
# and the name-based detector used for PPV always-live channels).
LIVETV_ALLOWED_COUNTRIES = {"us", "uk", "ca", "au", "za"}
LIVETV_COUNTRY_NAMES = {
    "us": "United States",
    "uk": "United Kingdom",
    "ca": "Canada",
    "au": "Australia",
    "za": "South Africa",
}
_LIVETV_DLHD_JSON = "https://ondemand.st/data/dlhd-channels.json?v=1017"
_LIVETV_MATCHES_API = "https://ondemand.st/papi/matches/all"
_LIVETV_HLS_TOKEN = "https://ondemand.st/papi/hls-token"


def _is_valid_m3u8_url(url: str) -> bool:
    if not url or not url.startswith("http"):
        return False
    if any(c in url for c in " \t\n\r(){}[];"):
        return False
    if url.count("://") != 1:
        return False
    parsed = urlparse(url)
    if not parsed.netloc or "." not in parsed.netloc:
        return False
    return ".m3u8" in url


def _detect_channel_country(name: str) -> str:
    n = (name or "").lower()
    if re.search(r"\bfox (footy|league|cricket|sports)|kayo|channel 7|channel 9|\bafl\b|\bnrl\b", n):
        return "au"
    if re.search(r"sky sports|tnt sport|\bbbc\b|\bitv\b|premier sports", n):
        return "uk"
    if re.search(r"nfl|nba|mlb|nhl|espn|fox sports [12]|willow|cbs|nbc|usa", n):
        return "us"
    return "intl"

class OnDemand(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["ondemand.st", "damitv.st", "messi.damitv.st"]
        self.name = "OnDemand"
        self.short_name = "OD"
        self.api_url = "https://ondemand.st/papi/api/streams"
        self.extract_url_api = "https://ondemand.st/papi/extract-url"
        self.base_url = "https://ondemand.st"
        self._cache: List[dict] = []
        self._cache_time: float = 0.0
        self._cache_duration: int = 120
        self._ltv_cache: List[Dict[str, Any]] = []
        self._ltv_cache_time: float = 0.0

    def _normalize_iframe_url(self, iframe: str) -> str:
        if not iframe:
            return iframe
        if iframe.startswith("//"):
            return "https:" + iframe
        if not iframe.startswith("http"):
            if iframe.startswith("/"):
                return f"https://messi.damitv.st{iframe}"
            return f"https://messi.damitv.st/{iframe}"
        if "damitv.st" in iframe and "messi.damitv.st" not in iframe:
            iframe = iframe.replace("damitv.st", "messi.damitv.st")
        return iframe

    def _build_resolver_url(self, iframe_url: str) -> str:
        return f"{self.base_url}/jetextractor/embed?url={quote(iframe_url, safe='')}"

    def _fetch_streams(self) -> List[dict]:
        now = time.time()
        if self._cache and (now - self._cache_time) < self._cache_duration:
            debug_log(f"[OnDemand] Using cached data", xbmc.LOGINFO)
            return self._cache

        try:
            data = fetch_json(self.api_url)
            if data is None:
                debug_log("[OnDemand] API returned no data", xbmc.LOGWARNING)
                return []
            if not data.get("success"):
                debug_log("[OnDemand] API indicated failure", xbmc.LOGWARNING)
                return []
            streams = data.get("streams", [])
            self._cache = streams
            self._cache_time = now
            debug_log(f"[OnDemand] Fetched {len(streams)} categories", xbmc.LOGINFO)
            return streams
        except Exception as e:
            debug_log(f"[OnDemand] Fetch failed: {e}", xbmc.LOGWARNING)
            return []

    def _get_category_label(self, category: str) -> str:
        category_map = {
            "football": "Soccer",
            "basketball": "NBA",
            "american-football": "NFL",
            "baseball": "MLB",
            "hockey": "NHL",
            "combat": "MMA / Boxing",
            "golf": "Golf",
            "tennis": "Tennis",
        }
        return category_map.get(category.lower(), category.upper())

    def _get_status(self, starts_at: int, ends_at: int) -> Optional[str]:
        now = time.time()
        if starts_at:
            if now < starts_at:
                return "Upcoming"
            elif ends_at and now > ends_at:
                return "Ended"
        return "LIVE"

    def _extract_stream_id(self, iframe_url: str) -> Optional[str]:
        parsed = urlparse(iframe_url)
        params = parse_qs(parsed.query)
        stream_id = params.get("id", [None])[0]
        if stream_id:
            return unquote(stream_id)
        if parsed.path.startswith("/embed/"):
            parts = parsed.path.replace("/embed/", "").split("/")
            return "/".join(parts) if parts[0] else None
        return None

    def _is_dlhd(self, url: str) -> bool:
        if not url:
            return False
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        sid = params.get("id", [""])[0]
        return unquote(sid).startswith("dlhd-")

    def _try_extract_api(self, stream_id: str) -> Optional[dict]:
        api_endpoint = f"{self.extract_url_api}/{stream_id}"
        
        try:
            headers = get_headers(referer="https://ondemand.st/", origin="https://ondemand.st/")
            resp = get_session().get(api_endpoint, headers=headers, timeout=self.timeout)
            
            if resp.status_code == 200:
                data = resp.json()
                return data
            
            elif resp.status_code == 404 or "no sources" in resp.text.lower():
                debug_log(f"[OnDemand] No sources for stream: {stream_id}", xbmc.LOGWARNING)
        except Exception as e:
            debug_log(f"[OnDemand] Extract API failed: {e}", xbmc.LOGWARNING)
        
        return None

    def _fetch_livetv_channels(self) -> List[Dict[str, Any]]:
        now = time.time()
        if self._ltv_cache and (now - self._ltv_cache_time) < self._cache_duration:
            return self._ltv_cache

        channels: List[Dict[str, Any]] = []
        seen_keys = set()

        # 1) PPV always-live channels from /papi/matches/all (site treats these as Live TV cards)
        try:
            ml = fetch_json(_LIVETV_MATCHES_API, referer=f"{self.base_url}/")
            matches = ml if isinstance(ml, list) else (ml.get("matches") if isinstance(ml, dict) else [])
            for m in matches or []:
                if not isinstance(m, dict) or not m.get("id") or m.get("status") != "live":
                    continue
                mid = str(m.get("id", ""))
                if not (m.get("always_live") or re.match(r"^(247-|ch-)", mid) or m.get("category") == "24/7-streams"):
                    continue
                name = re.sub(r"^24/7\s*", "", str(m.get("title", "") or ""), flags=re.I)
                name = re.sub(r"^[A-Z]{2}\s*\|\s*", "", name).strip() or "Channel"
                cc = _detect_channel_country(name)
                if cc not in LIVETV_ALLOWED_COUNTRIES:
                    continue
                key = f"ppv:{mid}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                channels.append({
                    "kind": "ppv",
                    "id": mid,
                    "name": name,
                    "country": cc,
                    "image": m.get("poster") or None,
                })
            debug_log(f"[OnDemand] LiveTV PPV channels kept: {len(channels)}", xbmc.LOGINFO)
        except Exception as e:
            debug_log(f"[OnDemand] LiveTV matches fetch failed: {e}", xbmc.LOGWARNING)

        # 2) DLHD 24/7 channel list
        try:
            dd = fetch_json(_LIVETV_DLHD_JSON, referer=f"{self.base_url}/")
            dlhd_channels = (dd or {}).get("channels") or []
            kept = 0
            for c in dlhd_channels:
                if not isinstance(c, dict) or not c.get("id") or not c.get("name"):
                    continue
                cc = str(c.get("country") or "intl").lower()
                if cc not in LIVETV_ALLOWED_COUNTRIES:
                    continue
                key = f"dlhd:{c['id']}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                image = c.get("image") or ""
                if image.startswith("/"):
                    image = self.base_url + image
                channels.append({
                    "kind": "dlhd",
                    "id": str(c["id"]),
                    "name": str(c["name"]).strip(),
                    "country": cc,
                    "image": image or None,
                })
                kept += 1
            debug_log(f"[OnDemand] LiveTV DLHD channels kept: {kept}", xbmc.LOGINFO)
        except Exception as e:
            debug_log(f"[OnDemand] LiveTV dlhd list fetch failed: {e}", xbmc.LOGWARNING)

        self._ltv_cache = channels
        self._ltv_cache_time = now
        return channels

    def _mint_hls_token(self) -> Optional[Dict[str, Any]]:
        try:
            data = fetch_json(_LIVETV_HLS_TOKEN, referer=f"{self.base_url}/livetv")
            if isinstance(data, dict) and data.get("tk"):
                return data
        except Exception as e:
            debug_log(f"[OnDemand] hls-token failed: {e}", xbmc.LOGWARNING)
        return None

    def _resolve_dlhd_channel(self, channel_id: str, name: str) -> Optional[JetLink]:
        token = self._mint_hls_token()
        if not token:
            debug_log(f"[OnDemand] No hls-token for dlhd-{channel_id}", xbmc.LOGWARNING)
            return None
        m3u8_url = f"{self.base_url}/dl/{channel_id}.m3u8?tk={quote(str(token['tk']))}&e={token.get('e', '')}"
        headers = {
            "User-Agent": _TV_UA,
            "Referer": f"{self.base_url}/livetv",
            "Origin": self.base_url,
        }

        def _refresh() -> Optional[dict]:
            t = self._mint_hls_token()
            if not t:
                return None
            return {
                "url": f"{self.base_url}/dl/{channel_id}.m3u8?tk={quote(str(t['tk']))}&e={t.get('e', '')}",
                "headers": headers,
            }

        try:
            proxy = get_stream_proxy(
                "ondemand",
                headers,
                options={"cache_manifest": False, "keep_alive": True, "strip_png": True, "upstream_keep_alive": True, "prefetch_segments": True},
            )
            proxy_url = proxy.get_proxy_url(m3u8_url, headers, refresh_callback=_refresh)
            debug_log(f"[OnDemand] DLHD proxy ({name}): {proxy_url[:120]}", xbmc.LOGINFO)
            return JetLink(
                address=proxy_url,
                name=name,
                inputstream=JetInputstreamFFmpegDirect(manifest_type="hls", is_realtime_stream=True, stream_mode="live"),
            )
        except Exception as e:
            debug_log(f"[OnDemand] DLHD proxy failed for {name}: {e}", xbmc.LOGWARNING)
            return None

    def _livetv_link_url(self, ch: Dict[str, Any]) -> str:
        if ch.get("kind") == "dlhd":
            return f"{self.base_url}/livetv/dlhd/{ch['id']}"
        return f"{self.base_url}/livetv/ppv/{quote(str(ch['id']), safe='')}"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items

        categories = self._fetch_streams()

        for category in categories or []:
            if not isinstance(category, dict):
                continue
            category_name = str(category.get("category", "Events")).strip()
            streams = category.get("streams", [])
            if not isinstance(streams, list):
                continue

            for stream in streams:
                if not isinstance(stream, dict):
                    continue
                name = stream.get("name", "Stream").strip()
                poster = stream.get("poster")
                iframe_url = self._normalize_iframe_url(stream.get("iframe"))
                if not iframe_url:
                    continue

                sources = stream.get("sources", [])
                if isinstance(sources, list):
                    sources = [s for s in sources if isinstance(s, dict) and not self._is_dlhd(s.get("embed", ""))]

                starts_at = stream.get("starts_at", 0)
                ends_at = stream.get("ends_at", 0)
                if not isinstance(starts_at, (int, float)):
                    starts_at = 0
                if not isinstance(ends_at, (int, float)):
                    ends_at = 0

                status = self._get_status(starts_at, ends_at)
                league = stream.get("league") or category_name
                if league:
                    league = self._get_category_label(str(league))

                title = name
                if status:
                    title = f"[{status}] {name}"

                resolver_url = self._build_resolver_url(iframe_url)
                links = [JetLink(resolver_url, links=True, name=f"Main")]

                if isinstance(sources, list):
                    for source in sources:
                        if isinstance(source, dict):
                            source_embed = self._normalize_iframe_url(source.get("embed"))
                            source_name = source.get("name", "Source")
                            if source_embed and source_embed != iframe_url:
                                source_resolver = self._build_resolver_url(source_embed)
                                links.append(
                                    JetLink(source_resolver, links=True, name=source_name)
                                )

                item = JetItem(
                    title=title,
                    league=league,
                    links=links,
                    icon=poster if poster else None,
                )
                items.append(item)

        for ch in self._fetch_livetv_channels():
            cc = ch.get("country", "intl")
            country_label = LIVETV_COUNTRY_NAMES.get(cc, cc.upper())
            link_url = self._livetv_link_url(ch)
            items.append(JetItem(
                title=ch.get("name", "Channel"),
                league=f"Live TV - {country_label}",
                links=[JetLink(link_url, links=True, name="Main")],
                icon=ch.get("image"),
            ))

        debug_log(f"[OnDemand] Total items: {len(items)}", xbmc.LOGINFO)
        return items

    def _proxy_m3u8(self, m3u8_url: str, name: str, referer: str = None, origin: str = None) -> Optional[JetLink]:
        try:
            headers = {
                "User-Agent": _TV_UA,
            }
            if referer:
                headers["Referer"] = referer
            if origin:
                headers["Origin"] = origin
            proxy = get_stream_proxy("ondemand", headers, options={"cache_manifest": False, "keep_alive": True, "strip_png": True, "upstream_keep_alive": True, "prefetch_segments": True})
            proxy_url = proxy.get_proxy_url(m3u8_url, headers)
            debug_log(f"[OnDemand] Proxy URL ({name}): {proxy_url[:120]}", xbmc.LOGINFO)
            return JetLink(
                address=proxy_url,
                name=name,
                inputstream=JetInputstreamFFmpegDirect(manifest_type="hls", is_realtime_stream=True, stream_mode="live"),
            )
        except Exception as e:
            debug_log(f"[OnDemand] Proxy failed for {name}: {e}", xbmc.LOGWARNING)
            return None

    def _resolve_embedst(self, embed_url: str, name: str) -> Optional[JetLink]:
        try:
            from ..util import embedsportstop
            stream_url = embedsportstop.get_embedsportstop_stream(embed_url)
            if stream_url and stream_url.startswith("http"):
                debug_log(f"[OnDemand] Resolved {name} via embedsportstop: {stream_url[:80]}", xbmc.LOGINFO)
                link = self._proxy_m3u8(stream_url, name, referer="https://embed.st/", origin="https://embed.st")
                if link:
                    return link
                return JetLink(
                    address=stream_url,
                    name=name,
                    inputstream=JetInputstreamFFmpegDirect(manifest_type="hls", is_realtime_stream=True, stream_mode="live"),
                )
        except Exception as e:
            debug_log(f"[OnDemand] embedsportstop resolution failed for {name}: {e}", xbmc.LOGWARNING)
        return None

    def get_links(self, url: JetLink) -> List[JetLink]:
        links: List[JetLink] = []
        url_address = url.address

        parsed = urlparse(url_address)

        if "ondemand.st" in parsed.netloc and parsed.path.startswith("/livetv/dlhd/"):
            channel_id = parsed.path.rstrip("/").split("/")[-1]
            if channel_id.isdigit():
                link = self._resolve_dlhd_channel(channel_id, f"DLHD {channel_id}")
                if link:
                    links.append(link)
            return links

        if "ondemand.st" in parsed.netloc and parsed.path.startswith("/livetv/ppv/"):
            stream_id = unquote(parsed.path.rstrip("/").split("/")[-1])
            if not stream_id:
                return links
            iframe_url = f"https://messi.damitv.st/embed/?id={quote(stream_id, safe='')}"
        else:
            is_resolver = "/jetextractor/embed" in url_address
            is_embed = ("damitv.st" in parsed.netloc or "messi.damitv.st" in parsed.netloc or "embedindia.st" in parsed.netloc) and ("/embed/" in parsed.path or parsed.path == "/embed")
            is_watch_page = "ondemand.st" in parsed.netloc and "/watch/" in parsed.path

            if not (is_resolver or is_embed or is_watch_page):
                return links

            if is_resolver:
                params = parse_qs(parsed.query)
                iframe_url = params.get("url", [None])[0]
            else:
                iframe_url = url_address

        if not iframe_url:
            return links

        iframe_url = self._normalize_iframe_url(iframe_url)

        try:
            stream_id = self._extract_stream_id(iframe_url)
            
            if stream_id:
                api_data = self._try_extract_api(stream_id)
                if api_data:
                    embed_referrer = f"https://messi.damitv.st/embed/?id={stream_id}"

                    hls_url = api_data.get("hlsUrl")
                    if hls_url and isinstance(hls_url, str) and hls_url.startswith(("http://", "https://")) and ".m3u8" in hls_url:
                        debug_log(f"[OnDemand] Found m3u8 via API: {hls_url[:80]}", xbmc.LOGINFO)
                        link = self._proxy_m3u8(hls_url, "HD", referer=embed_referrer, origin="https://messi.damitv.st")
                        if link:
                            links.append(link)
                        else:
                            links.append(JetLink(
                                hls_url,
                                name="HD",
                                headers=get_headers(referer=embed_referrer, origin="https://messi.damitv.st"),
                                inputstream=JetInputstreamAdaptive.hls(),
                            ))

                    sd_url = api_data.get("sdUrl")
                    if sd_url and isinstance(sd_url, str) and sd_url.startswith(("http://", "https://")) and ".m3u8" in sd_url and sd_url != hls_url:
                        debug_log(f"[OnDemand] Found SD m3u8: {sd_url[:80]}", xbmc.LOGINFO)
                        link = self._proxy_m3u8(sd_url, "SD", referer=embed_referrer, origin="https://messi.damitv.st")
                        if link:
                            links.append(link)
                        else:
                            links.append(JetLink(
                                sd_url,
                                name="SD",
                                headers=get_headers(referer=embed_referrer, origin="https://messi.damitv.st"),
                                inputstream=JetInputstreamAdaptive.hls(),
                            ))

                    sd_streams = api_data.get("sdStreams", [])
                    if isinstance(sd_streams, list):
                        for idx, sds in enumerate(sd_streams):
                            if not isinstance(sds, dict):
                                continue
                            sds_url = sds.get("url")
                            sds_name = sds.get("name") or f"Source {idx + 1}"
                            sds_hd = sds.get("hd", False)
                            if not sds_url or not isinstance(sds_url, str):
                                continue
                            if not sds_url.startswith("http"):
                                sds_url = "https:" + sds_url if sds_url.startswith("//") else f"https://{sds_url}"
                            label = f"{sds_name} (HD)" if sds_hd else sds_name
                            debug_log(f"[OnDemand] Resolving sdStream: {label} -> {sds_url[:80]}", xbmc.LOGINFO)
                            resolved = self._resolve_embedst(sds_url, label)
                            if resolved:
                                links.append(resolved)
                            else:
                                links.append(JetLink(sds_url, name=label, resolveurl=True))

                    embed_url = api_data.get("embedUrl")
                    if embed_url and isinstance(embed_url, str) and embed_url.startswith("http"):
                        debug_log(f"[OnDemand] Resolving embed: {embed_url[:80]}", xbmc.LOGINFO)
                        resolved = self._resolve_embedst(embed_url, "Embed")
                        if resolved:
                            links.append(resolved)
                        else:
                            links.append(JetLink(embed_url, name="Embed", resolveurl=True))

                    if links:
                        return links

                debug_log(f"[OnDemand] No m3u8 for stream_id={stream_id}, skipping", xbmc.LOGINFO)
                return links

            html = ""
            _parsed_iframe = urlparse(iframe_url)
            _iframe_origin = f"{_parsed_iframe.scheme}://{_parsed_iframe.netloc}"
            session = get_session(referer=iframe_url, origin=_iframe_origin)
            resp = session.get(iframe_url, timeout=self.timeout, allow_redirects=True)
            if resp.status_code != 200:
                debug_log(f"[OnDemand] Embed page returned {resp.status_code}", xbmc.LOGWARNING)
                return links

            html = resp.text
            final_url = resp.url
            if ".m3u8" in final_url and _is_valid_m3u8_url(final_url):
                debug_log(f"[OnDemand] Found m3u8 via redirect: {final_url[:80]}", xbmc.LOGINFO)
                links.append(JetLink(
                    final_url,
                    inputstream=JetInputstreamAdaptive.hls(),
                ))
                return links

            m3u8_url = find_m3u8(html, final_url)
            if m3u8_url and _is_valid_m3u8_url(m3u8_url):
                _parsed_final = urlparse(final_url)
                _final_origin = f"{_parsed_final.scheme}://{_parsed_final.netloc}"
                debug_log(f"[OnDemand] Found m3u8 in HTML: {m3u8_url[:80]}", xbmc.LOGINFO)
                links.append(JetLink(
                    m3u8_url,
                    headers=get_headers(referer=final_url, origin=_final_origin),
                    inputstream=JetInputstreamAdaptive.hls(),
                ))
                return links

            iframes = find_iframes(html, final_url)
            for iframe_src in iframes[:2]:
                if "javascript:" not in iframe_src:
                    links.append(JetLink(iframe_src, resolveurl=True))

        except Exception as e:
            debug_log(f"[OnDemand] get_links failed: {e}", xbmc.LOGWARNING)

        return links

    def get_link(self, url: JetLink) -> JetLink:
        links = self.get_links(url)
        if links:
            return links[0]
        return JetLink(url.address)