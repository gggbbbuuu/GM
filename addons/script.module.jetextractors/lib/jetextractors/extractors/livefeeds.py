import json
import re
import time
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse
import xbmc

from .._core import fetch_page
from ..models import (
    JetExtractor,
    JetExtractorProgress,
    JetInputstreamFFmpegDirect,
    JetItem,
    JetLink,
)
from ..tools import debug_log
from ..util.resolver import UniversalResolver

CDNSPORT_URL = "https://cdnsport.ru/data.json"
TOPSURGE_URL = "https://topsurge.st/api_proxy.php"


class LiveFeeds(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["cdnsport.ru", "www.cdnsport.ru", "topsurge.st", "www.topsurge.st"]
        self.name = "LiveFeeds"
        self.short_name = "LF"
        self.resolver = UniversalResolver(self.user_agent, "[LiveFeeds]")
        self._cache = {"ts": 0.0, "cdn": None, "top": None}
        self._cache_ttl = 60.0

    def _load_feeds(self) -> bool:
        now = time.time()
        if self._cache["cdn"] is not None and (now - self._cache["ts"]) < self._cache_ttl:
            return True
        cdn = top = None
        try:
            raw = fetch_page(CDNSPORT_URL, referer="https://cdnsport.ru/")
            if raw:
                cdn = json.loads(raw)
        except Exception as e:
            debug_log(f"[LiveFeeds] cdnsport fetch failed: {e}", xbmc.LOGWARNING)
        try:
            raw = fetch_page(TOPSURGE_URL, referer="https://topsurge.st/")
            if raw:
                top = json.loads(raw)
        except Exception as e:
            debug_log(f"[LiveFeeds] topsurge fetch failed: {e}", xbmc.LOGWARNING)
        if not cdn and not top:
            return False
        self._cache = {"ts": now, "cdn": cdn, "top": top}
        debug_log(
            f"[LiveFeeds] feeds loaded: cdnsport={len((cdn or {}).get('matches', []))} topsurge={len((top or {}).get('matches', []))}",
            xbmc.LOGINFO,
        )
        return True

    def _match_links(self, cd_match: dict) -> List[tuple]:
        out = []
        seen = set()

        def add(name, lang, url):
            if not isinstance(url, str) or not url.startswith("http"):
                return
            if url in seen:
                return
            seen.add(url)
            label = name or "Stream"
            if lang:
                label = f"{label} [{lang}]"
            out.append((label, url))

        for ch in cd_match.get("channels") or []:
            if not isinstance(ch, dict):
                continue
            for u in ch.get("links") or []:
                add(ch.get("name"), ch.get("language"), u)

        def norm(s: str) -> str:
            return " ".join((s or "").lower().split())

        team1 = norm(cd_match.get("team1"))
        team2 = norm(cd_match.get("team2"))
        if team2:
            want = {f"{team1} vs {team2}", f"{team2} vs {team1}"}
        else:
            want = {team1}
        top = self._cache.get("top") or {}
        for tm in top.get("matches") or []:
            if not isinstance(tm, dict):
                continue
            if norm(tm.get("matchstr")) not in want:
                continue
            for ch in tm.get("channels") or []:
                if not isinstance(ch, dict):
                    continue
                for u in ch.get("links") or []:
                    add(ch.get("name"), ch.get("language"), u)
        return out

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items: List[JetItem] = []
        if self.progress_init(progress, items):
            return items
        if progress:
            self.progress_update(progress, "Fetching feeds...")
        if not self._load_feeds():
            return items
        cdn = self._cache.get("cdn") or {}
        for match in cdn.get("matches") or []:
            if not isinstance(match, dict):
                continue
            match_id = match.get("id") or ""
            if not match_id:
                continue
            team1 = (match.get("team1") or "").strip()
            team2 = (match.get("team2") or "").strip()
            title = f"{team1} vs {team2}" if team2 else team1
            if not title:
                continue
            status = (match.get("status") or "").strip().lower()
            status = "LIVE" if status == "live" else (status.capitalize() if status else None)
            starttime = None
            utc = match.get("datetime_utc")
            if utc:
                try:
                    starttime = datetime.fromisoformat(utc.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
                except Exception:
                    starttime = None
            items.append(JetItem(
                title=title,
                links=[JetLink(f"https://cdnsport.ru/#{match_id}", links=True)],
                starttime=starttime,
                status=status,
                league=(match.get("league") or None),
            ))
        debug_log(f"[LiveFeeds] Returning {len(items)} matches", xbmc.LOGINFO)
        return items

    def _find_cd_match(self, match_id: str) -> Optional[dict]:
        cdn = self._cache.get("cdn") or {}
        for match in cdn.get("matches") or []:
            if isinstance(match, dict) and match.get("id") == match_id:
                return match
        return None

    def get_links(self, event_url) -> List[JetLink]:
        address = event_url.address if isinstance(event_url, JetLink) else event_url
        match_id = urlparse(address).fragment or ""
        if not match_id:
            return []
        if not self._load_feeds():
            return []
        match = self._find_cd_match(match_id)
        if not match:
            return []
        links = []
        for label, url in self._match_links(match):
            links.append(JetLink(
                url,
                name=label,
                headers={"Referer": "https://cdnsport.ru/"},
                resolveurl=True,
                extractor=self.name,
            ))
        debug_log(f"[LiveFeeds] {len(links)} links for {match.get('matchstr') or match_id}", xbmc.LOGINFO)
        return links

    def get_link(self, url: JetLink) -> JetLink:
        target = url.address if isinstance(url, JetLink) else url
        if "cdnsport.ru" in urlparse(target).netloc:
            match_id = urlparse(target).fragment or ""
            if not self._load_feeds():
                return None
            match = self._find_cd_match(match_id)
            if not match:
                return None
            candidates = self._match_links(match)
            if not candidates:
                return None
            target = candidates[0][1]

        try:
            stream = self.resolver.resolve_url(target, "https://cdnsport.ru/")
        except Exception:
            return None
        if not stream:
            return None
        referer = getattr(self.resolver, "stream_referer", None) or target
        headers = {"User-Agent": self.user_agent, "Referer": referer}
        origin = getattr(self.resolver, "stream_origin", None)
        if origin:
            headers["Origin"] = origin
        return JetLink(stream, headers=headers, inputstream=JetInputstreamFFmpegDirect.default())
