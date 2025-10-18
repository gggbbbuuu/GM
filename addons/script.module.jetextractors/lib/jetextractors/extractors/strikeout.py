import requests
import re
import base64
import os
import logging
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pytz
import xbmcvfs
from urllib.parse import quote_plus
from ..models import JetExtractor, JetItem, JetLink, JetExtractorProgress, JetInputstreamAdaptive
from typing import Optional, List

# Logging setup
logger = logging.getLogger(__name__)
LOGPATH = xbmcvfs.translatePath('special://logpath/')
FILENAME = 'strikeout.log'
LOG_FILE = os.path.join(LOGPATH, FILENAME)

def log_debug(msg):
    print(msg)
    # try:
    #     os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    #     with open(LOG_FILE, 'a', encoding='utf-8') as f:
    #         f.write(f"{datetime.now()}: {msg}\n")
    #     logger.debug(msg)
    # except Exception as e:
    #     logger.error(f"Logging failed: {str(e)}")

class Strikeout(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["strikeout.im"]
        self.name = "Strikeout"
        self.league_dict = {
            "nba": "NBA",
            "nfl": "NFL",
            "nhl": "NHL",
            "mlb": "MLB",
            "soccer": "Soccer",
            "mma": "MMA",
            "boxing": "Boxing",
            "tennis": "Tennis",
            "cricket": "Cricket"
        }
        self.sport_pages = ["nba", "nfl", "nhl", "mlb", "soccer", "mma", "boxing", "tennis", "cricket"]
        self.plytv_referer = "https://omuzaani.me/"

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            log_debug("Progress init stopped")
            return items

        # Timezone setup
        utc_tz = pytz.UTC
        eastern_tz = pytz.timezone("America/New_York")
        try:
            local_tz = datetime.now().astimezone().tzinfo
        except Exception:
            local_tz = pytz.timezone("America/Los_Angeles")
        log_debug(f"Using local timezone: {local_tz}")

        now_utc = datetime.now(utc_tz)
        now_local = now_utc.astimezone(local_tz)
        offset_hours = int((now_local.utcoffset().total_seconds() / 3600))
        correction_hours = abs(offset_hours)
        log_debug(f"Timezone offset: {offset_hours} hours, Correction: +{correction_hours} hours")

        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
        session.headers.update(headers)

        events_by_league = {}
        for league in self.sport_pages:
            url = f"https://{self.domains[0]}/{league}"
            schedule_url = f"https://{self.domains[0]}/schedule/{base64.b64encode((league + '|').encode('utf-8')).decode('utf-8')}/"
            log_debug(f"Scraping page: {url}")
            try:
                r = session.get(url, timeout=self.timeout)
                log_debug(f"Status code: {r.status_code}, Content length: {len(r.text)}")
                log_debug(f"HTML snippet: {r.text[:500]}")

                r_schedule = session.get(schedule_url, timeout=self.timeout).json()

                games = re.findall(r'aria-controls="(.+?)".+?href="/(.*?)".+?title=\"(.*?)\"', r.text, re.DOTALL)
                log_debug(f"Found {len(games)} games for {league}")

                for game_id, game_url, title in games:
                    try:
                        if game_id not in r_schedule["links"]:
                            continue
                        
                        event_time_et = datetime.now(eastern_tz)
                        event_time_local = event_time_et.astimezone(local_tz)
                        event_time = event_time_local.replace(tzinfo=None) + timedelta(hours=correction_hours)
                        log_debug(f"Event: {title}, ET: {event_time_et}, Local: {event_time_local}, Naive: {event_time}")

                        league_name = self.league_dict.get(league, "Other")
                        event_item = JetItem(
                            title=title,
                            league=league_name,
                            icon=f"https://{self.domains[0]}/favicon.ico",
                            links=[JetLink(f"https://{self.domains[0]}/{r_schedule['linkAppends'][game_id]}/{i + 1}/{r_schedule['slugs'][game_id]}-stream", name=f"Stream {i + 1} [{link.get('player', 'N/A')}]") for i, link in enumerate(r_schedule["links"][game_id])],
                            starttime=event_time
                        )

                        log_debug(f"Added event: {title}, League: {league_name}")

                        if league_name not in events_by_league:
                            events_by_league[league_name] = []
                        events_by_league[league_name].append(event_item)

                    except Exception as e:
                        log_debug(f"Error processing game {title}: {str(e)}")
                        continue

            except Exception as e:
                log_debug(f"Error scraping {url}: {str(e)}")
                continue

        for league in sorted(events_by_league.keys()):
            league_events = sorted(events_by_league[league], key=lambda x: x.starttime)
            items.extend(league_events)
            log_debug(f"Added {len(league_events)} events for league {league}")

        log_debug(f"Total items: {len(items)}")
        return items

    def authenticate(self, html, referer, session):
        try:
            auth_url_match = re.search(r"const secTokenUrl\s*=\s*['\"](.*?)['\"]", html)
            scode_match = re.search(r"const sCode\s*=\s*['\"](.*?)['\"]", html)
            ts_match = re.search(r"const expireTs\s*=\s*(\d+);", html)
            unique_id_match = re.search(r"const strUnqId\s*=\s*['\"](.*?)['\"]", html)

            if not all([auth_url_match, scode_match, ts_match, unique_id_match]):
                log_debug(f"Missing auth parameters: url={bool(auth_url_match)}, scode={bool(scode_match)}, ts={bool(ts_match)}, unique_id={bool(unique_id_match)}")
                return False

            auth_url = base64.b64decode(auth_url_match.group(1)).decode('utf-8')
            scode = scode_match.group(1)
            ts = ts_match.group(1)
            unique_id = unique_id_match.group(1)
            auth_payload = f"{auth_url}/?stream={unique_id}&scode={scode}&expires={ts}"
            log_debug(f"Auth URL: {auth_payload}")

            headers = session.headers.copy()
            headers['Referer'] = referer
            r = session.get(auth_payload, headers=headers, timeout=self.timeout)
            log_debug(f"Auth status code: {r.status_code}, Content length: {len(r.text)}")
            log_debug(f"Auth response: {r.text[:200]}")
            return r.status_code == 200
        except Exception as e:
            log_debug(f"Authentication error: {str(e)}")
            return False

    def get_alternative_url(self, url):
        """Generate alternative URL by swapping team order."""
        match = re.search(r'stream-(.+)-vs-(.+)-live', url)
        if match:
            team1, team2 = match.groups()
            return url.replace(f"{team1}-vs-{team2}", f"{team2}-vs-{team1}")
        return None

    def get_link(self, url: JetLink) -> JetLink:
        try:
            session = requests.Session()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1'
            }
            session.headers.update(headers)

            urls_to_try = [url.address]
            alt_url = self.get_alternative_url(url.address)
            if alt_url:
                urls_to_try.append(alt_url)  # Try both URLs

            for try_url in urls_to_try:
                log_debug(f"Fetching link: {try_url}")
                r = session.get(try_url, timeout=self.timeout)
                log_debug(f"Game page status code: {r.status_code}, Content length: {len(r.text)}")
                log_debug(f"Game page HTML: {r.text[:500]}")

                # Log all const variables
                const_vars = re.findall(r'const\s+(\w+)\s*=\s*[\'"](.*?)[\'"]|const\s+(\w+)\s*=\s*(\d+);', r.text)
                log_debug(f"Const variables: {const_vars}")

                # Try main.py's regex
                try:
                    plytv_data = re.search(
                        r'const gameText="(.*?)".*?gameCat="(.*?)".*?const zmid = "(.*?)".*?pid = (.*?);.*?edm = "(.*?)"',
                        r.text, re.DOTALL
                    )
                    if not plytv_data:
                        log_debug(f"No plytv data found in {try_url} with primary regex")
                        # Try broader regex
                        plytv_data = re.search(
                            r'(?:const\s+)?gameText\s*=\s*[\'\"](.*?)[\'"].*?'
                            r'(?:const\s+)?gameCat\s*=\s*[\'\"](.*?)[\'"].*?'
                            r'(?:const\s+)?zmid\s*=\s*[\'\"](.*?)[\'"].*?'
                            r'pid\s*=\s*(\d+).*?'
                            r'edm\s*=\s*[\'\"](.*?)[\'"]',
                            r.text, re.DOTALL
                        )
                        if not plytv_data:
                            log_debug("No plytv data found with broader regex")
                            # Try broadest regex
                            plytv_data = re.search(
                                r'gameText\s*[:=]\s*[\'\"](.*?)[\'"].*?'
                                r'gameCat\s*[:=]\s*[\'\"](.*?)[\'"].*?'
                                r'zmid\s*[:=]\s*[\'\"](.*?)[\'"].*?'
                                r'pid\s*[:=]\s*(\d+).*?'
                                r'edm\s*[:=]\s*[\'\"](.*?)[\'"]',
                                r.text, re.DOTALL | re.IGNORECASE
                            )
                            if not plytv_data:
                                log_debug("No plytv data found with broadest regex")
                                # Try siteConfig JSON
                                siteconfig_data = re.search(
                                    r'const siteConfig\s*=\s*(\{.*?\})',
                                    r.text, re.DOTALL
                                )
                                if siteconfig_data:
                                    log_debug(f"SiteConfig JSON: {siteconfig_data.group(1)}")
                                    try:
                                        data = json.loads(siteconfig_data.group(1))
                                        buttonad = data.get("buttonad", {})
                                        gameText = buttonad.get("title", "")
                                        gameCat = buttonad.get("sports", "").upper()
                                        zmid = data.get("trackImgId", "") or "default_zmid"
                                        pid = data.get("trackEndTime", "1")[-1] or "1"
                                        edm = "wavewalt.me"
                                        if gameText and gameCat:
                                            plytv_data = type('obj', (), {
                                                'groups': lambda: (gameText, gameCat, zmid, pid, edm)
                                            })()
                                    except json.JSONDecodeError as e:
                                        log_debug(f"JSON decode error in siteConfig: {str(e)}")
                except Exception as e:
                    log_debug(f"Error in regex parsing for {try_url}: {str(e)}")
                    plytv_data = None

                if plytv_data:
                    try:
                        gameText, gameCat, zmid, pid, edm = plytv_data.groups()
                        log_debug(f"plytv data: gameText={gameText}, gameCat={gameCat}, zmid={zmid}, pid={pid}, edm={edm}")
                        _gameCat = quote_plus(gameCat)
                        _zmid = quote_plus(zmid)
                        _gameText = quote_plus(gameText)
                        fetcher_url = f"https://{edm}/sd0embed/{_gameCat}?pid={pid}&gacat={_gameText}&gatxt={_gameCat}&v={_zmid}"
                        log_debug(f"Fetcher URL: {fetcher_url}")

                        headers['Referer'] = f'https://{self.domains[0]}/'
                        r_fetcher = session.get(fetcher_url, headers=headers, timeout=self.timeout)
                        log_debug(f"Fetcher status code: {r_fetcher.status_code}, Content length: {len(r_fetcher.text)}")
                        log_debug(f"Fetcher HTML: {r_fetcher.text[:500]}")

                        enc_stream_url = re.search(r"const sourceUrl\s*=\s*['\"](.*?)['\"]", r_fetcher.text)
                        if not enc_stream_url:
                            log_debug(f"No videoUrl found in {fetcher_url}")
                            soup = BeautifulSoup(r_fetcher.text, "html.parser")
                            iframes = soup.select("iframe")
                            if iframes:
                                for i, iframe in enumerate(iframes):
                                    src = iframe.get("src", "")
                                    log_debug(f"Fetcher iframe {i}: src={src}")
                                    if src and src.startswith("http"):
                                        log_debug(f"Using fetcher iframe src: {src}")
                                        return JetLink(src, headers=headers)
                            videos = soup.select("video source")
                            if videos:
                                for i, video in enumerate(videos):
                                    src = video.get("src", "")
                                    log_debug(f"Fetcher video source {i}: src={src}")
                                    if src and src.startswith("http"):
                                        log_debug(f"Using fetcher video src: {src}")
                                        return JetLink(src, headers=headers)
                            scripts = soup.select("script")
                            for i, script in enumerate(scripts):
                                content = script.string
                                if content:
                                    log_debug(f"Fetcher script {i} content: {content[:200]}")
                                    try:
                                        json_match = re.search(r'const siteConfig\s*=\s*(\{.*?\})', content, re.DOTALL)
                                        if json_match:
                                            log_debug(f"Fetcher script {i} siteConfig: {json_match.group(1)}")
                                            try:
                                                data = json.loads(json_match.group(1))
                                                buttonad_url = data.get("buttonad", {}).get("url")
                                                if buttonad_url and buttonad_url.startswith("http"):
                                                    log_debug(f"Found fetcher buttonad URL: {buttonad_url}")
                                                    return JetLink(buttonad_url, headers=headers)
                                            except json.JSONDecodeError as e:
                                                log_debug(f"JSON decode error in fetcher siteConfig: {str(e)}")
                                        ad_match = re.search(r"window\['x4G9Tq2Kw6R7v1Dy3P0B5N8Lc9M2zF'\]\s*=\s*(\{.*?\})", content, re.DOTALL)
                                        if ad_match:
                                            log_debug(f"Fetcher script {i} ad variable: {ad_match.group(1)}")
                                            try:
                                                data = json.loads(ad_match.group(1))
                                                cdn_path = data.get("suv5", {}).get("cdnPath")
                                                if cdn_path and cdn_path.startswith("http"):
                                                    log_debug(f"Found fetcher suv5 cdnPath: {cdn_path}")
                                                    return JetLink(cdn_path, headers=headers)
                                            except json.JSONDecodeError as e:
                                                log_debug(f"JSON decode error in fetcher ad variable: {str(e)}")
                                        url_match = re.search(r'(https?://[^\s\'"]+\.m3u8)', content)
                                        if url_match:
                                            log_debug(f"Fetcher script {i} m3u8: {url_match.group(1)}")
                                            return JetLink(url_match.group(1), headers=headers)
                                    except Exception as e:
                                        log_debug(f"Error parsing fetcher script {i}: {str(e)}")
                                        continue
                            log_debug("No valid fetcher data found")
                            continue

                        log_debug(f"Encoded videoUrl: {enc_stream_url.group(1)}")
                        if not self.authenticate(r_fetcher.text, self.plytv_referer, session):
                            log_debug(f"Authentication failed for {fetcher_url}")
                            continue

                        stream_url = base64.b64decode(base64.b64decode(enc_stream_url.group(1))).decode('utf-8')
                        log_debug(f"Resolved stream: {stream_url}")

                        return JetLink(
                            address=stream_url,
                            headers={
                                "User-Agent": headers["User-Agent"],
                                "Referer": self.plytv_referer,
                                "Origin": self.plytv_referer.rstrip('/')
                            }
                        )
                    except Exception as e:
                        log_debug(f"Error processing plytv_data for {try_url}: {str(e)}")
                        continue

                
                soup = BeautifulSoup(r.text, "html.parser")
                iframes = soup.select("iframe")
                if iframes:
                    for i, iframe in enumerate(iframes):
                        src = iframe.get("src", "")
                        log_debug(f"Iframe {i}: src={src}")
                        if src and src.startswith("http"):
                            log_debug(f"Using iframe src: {src}")
                            return JetLink(src, headers=headers)
                log_debug("No valid iframes found")
                
                videos = soup.select("video source")
                if videos:
                    for i, video in enumerate(videos):
                        src = video.get("src", "")
                        log_debug(f"Video source {i}: src={src}")
                        if src and src.startswith("http"):
                            log_debug(f"Using video src: {src}")
                            return JetLink(src, headers=headers)
                log_debug("No valid video sources found")
                scripts = soup.select("script")
                for i, script in enumerate(scripts):
                    content = script.string
                    if content:
                        log_debug(f"Script {i} content: {content[:200]}")
                        try:
                            json_match = re.search(r'const siteConfig\s*=\s*(\{.*?\})', content, re.DOTALL)
                            if json_match:
                                log_debug(f"Script {i} siteConfig: {json_match.group(1)}")
                                try:
                                    data = json.loads(json_match.group(1))
                                    buttonad_url = data.get("buttonad", {}).get("url")
                                    if buttonad_url and buttonad_url.startswith("http"):
                                        log_debug(f"Found buttonad URL: {buttonad_url}")
                                        # Follow redirect
                                        r_buttonad = session.get(buttonad_url, headers=headers, allow_redirects=True, timeout=self.timeout)
                                        log_debug(f"Buttonad redirect URL: {r_buttonad.url}, Status: {r_buttonad.status_code}")
                                        if r_buttonad.url.endswith(".m3u8"):
                                            return JetLink(r_buttonad.url, headers=headers)
                                except json.JSONDecodeError as e:
                                    log_debug(f"JSON decode error in siteConfig: {str(e)}")
                            ad_match = re.search(r"window\['x4G9Tq2Kw6R7v1Dy3P0B5N8Lc9M2zF'\]\s*=\s*(\{.*?\})", content, re.DOTALL)
                            if ad_match:
                                log_debug(f"Script {i} ad variable: {ad_match.group(1)}")
                                try:
                                    data = json.loads(ad_match.group(1))
                                    cdn_path = data.get("suv5", {}).get("cdnPath")
                                    if cdn_path and cdn_path.startswith("http"):
                                        log_debug(f"Found suv5 cdnPath: {cdn_path}")
                                        return JetLink(cdn_path, headers=headers)
                                except json.JSONDecodeError as e:
                                    log_debug(f"JSON decode error in ad variable: {str(e)}")
                            url_match = re.search(r'(https?://[^\s\'"]+\.m3u8)', content)
                            if url_match:
                                log_debug(f"Script {i} m3u8: {url_match.group(1)}")
                                return JetLink(url_match.group(1), headers=headers)
                        except Exception as e:
                            log_debug(f"Error parsing script {i}: {str(e)}")
                            continue
                log_debug("No valid script data found")
                player_urls = re.findall(r'(https?://wavewalt\.me/[^\s\'"]+)', r.text)
                if player_urls:
                    for i, player_url in enumerate(player_urls):
                        log_debug(f"Embedded player URL {i}: {player_url}")
                        return JetLink(player_url, headers=headers)
                log_debug("No embedded player URLs found")

                redirect_match = re.search(r'window\.location\.replace\([\'"](\/[^\'"]+)[\'"]\)', r.text)
                if redirect_match:
                    redirect_url = f"https://{self.domains[0]}{redirect_match.group(1)}"
                    log_debug(f"Found redirect URL: {redirect_url}")
                    r_redirect = session.get(redirect_url, headers=headers, timeout=self.timeout)
                    log_debug(f"Redirect status code: {r_redirect.status_code}, Content length: {len(r_redirect.text)}")
                    soup = BeautifulSoup(r_redirect.text, "html.parser")
                    plytv_data = re.search(
                        r'const gameText="(.*?)".*?gameCat="(.*?)".*?const zmid = "(.*?)".*?pid = (.*?);.*?edm = "(.*?)"',
                        r_redirect.text, re.DOTALL
                    )
                    if plytv_data:
                        gameText, gameCat, zmid, pid, edm = plytv_data.groups()
                        log_debug(f"Redirect plytv data: gameText={gameText}, gameCat={gameCat}, zmid={zmid}, pid={pid}, edm={edm}")
                        _gameCat = quote_plus(gameCat)
                        _zmid = quote_plus(zmid)
                        fetcher_url = f"https://{edm}/sd0embed/{gameText}?pid={pid}&gacat={gameText}&gatxt={_gameCat}&v={_zmid}"
                        log_debug(f"Redirect Fetcher URL: {fetcher_url}")
                        r_fetcher = session.get(fetcher_url, headers=headers, timeout=self.timeout)
                        enc_stream_url = re.search(r"const videoUrl\s*=\s*['\"](.*?)['\"]", r_fetcher.text)
                        if enc_stream_url and self.authenticate(r_fetcher.text, self.plytv_referer, session):
                            stream_url = base64.b64decode(base64.b64decode(enc_stream_url.group(1))).decode('utf-8')
                            log_debug(f"Redirect Resolved stream: {stream_url}")
                            return JetLink(
                                address=stream_url,
                                headers={
                                    "User-Agent": headers["User-Agent"],
                                    "Referer": self.plytv_referer,
                                    "Origin": self.plytv_referer.rstrip('/')
                                },
                                inputstream=JetInputstreamAdaptive.hls()
                            )

            log_debug(f"No stream found for {url.address} after trying all URLs")
            return None
        except Exception as e:
            log_debug(f"Error resolving link {url.address}: {str(e)}")
            return None