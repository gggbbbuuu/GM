import requests, re
from urllib.parse import unquote
from datetime import datetime
import xbmc
import xbmcgui
import base64
from ..models import *
from ..util import m3u8_src, hunter
from ..util.stream_proxy import get_stream_proxy
# 6.1 | # Note: adjust import if cdnutils.py is moved to another location

class CDNLiveTV(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["cdnlivetv.tv", "api.cdnlivetv.tv"]
        self.name = "CDNLiveTV"
        self.short_name = "CDN"
        self.user = "streamsports99"
        self.plan = "vip"
        self.std_headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",            
            "Referer" : "https://streamsports99.su/"            
        }

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        base_url = 'https://api.cdnlivetv.tv/api/v1' 
        headers = self.std_headers
        
        try:
            r = requests.get(
                f"{base_url}/channels/?user={self.user}&plan={self.plan}",
                timeout=self.timeout,
                headers=headers
            )
            data = r.json()
        except Exception:
            return items
        
        channels = data.get("channels", [])
        
        for channel in channels:
            name = channel.get("name", "")
            url = channel.get("url", "")
            image = channel.get("image", "")
            status = channel.get("status", "")
            
            if not name or not url:
                continue
            
            title = name
            if status == "online":
                title = f"[LIVE] {name}"
            
            items.append(JetItem(
                icon=image if image else None,
                league="CHANNELS",
                title=title,
                links=[JetLink(url, name=name)]
            ))
        
        # Append sports event listings
        try:
            r = requests.get(
                f"{base_url}/events/sports/?user={self.user}&plan={self.plan}",
                timeout=self.timeout,
                headers=headers
            )
            events_data = r.json()
        except Exception:
            return items
        
        for sport, events in events_data.get("cdn-live-tv", {}).items():
            if not isinstance(events, list):
                continue
            for event in events:
                if not isinstance(event, dict):
                    continue
                channels = event.get("channels", [])
                if not channels:
                    continue
                
                home = event.get("homeTeam", "")
                away = event.get("awayTeam", "")
                event_name = event.get("event", "")
                tournament = event.get("tournament", "")
                country = event.get("country", "")
                status = event.get("status", "")
                start = event.get("start", "")
                time_str = event.get("time", "")
                
                if event_name:
                    title = event_name
                elif home and away:
                    title = f"{home} vs {away}"
                else:
                    title = event.get("gameID", "Unknown Event")
                
                meta_parts = []
                if tournament:
                    meta_parts.append(tournament)
                if country:
                    meta_parts.append(country)
                if time_str:
                    meta_parts.append(time_str)
                if meta_parts:
                    title = f"{title}  -  {' | '.join(meta_parts)}"
                
                if status:
                    title = f"[{status}] {title}"
                
                starttime = None
                if start:
                    try:
                        starttime = datetime.strptime(start, "%Y-%m-%d %H:%M")
                    except Exception:
                        pass
                
                icon = event.get("homeTeamIMG") or event.get("awayTeamIMG") or event.get("countryIMG") or None
                
                links = []
                for ch in channels:
                    ch_url = ch.get("url", "")
                    ch_name = ch.get("channel_name", "")
                    if ch_url:
                        links.append(JetLink(ch_url, name=ch_name or None))
                
                if links:
                    items.append(JetItem(
                        icon=icon,
                        league=f"{sport} - {tournament}" if tournament else sport,
                        title=title,
                        starttime=starttime,
                        status=status if status else None,
                        links=links
                    ))
        
        return items

    def get_link(self, url: JetLink) -> JetLink:
        original_url = url.address
        headers = self.std_headers
        progress = xbmcgui.DialogProgress()
        progress.create('CDNLiveTV', 'Resolving stream...')
        try:
            xbmc.log(f"[CDNLiveTV] Resolving link: {original_url}", xbmc.LOGINFO)
            progress.update(10, 'Fetching channel page...')
            r = requests.get(original_url, timeout=self.timeout, headers=headers)
            html = r.text
            xbmc.log(f"[CDNLiveTV] HTML fetched, length: {len(html)}", xbmc.LOGINFO)
            m3u8_link = m3u8_src.scan_page(original_url, html=html)
            xbmc.log(f"[CDNLiveTV] m3u8_src.scan_page result: {m3u8_link}", xbmc.LOGINFO)
            if m3u8_link:
                xbmc.log(f"[CDNLiveTV] Returning m3u8 link: {m3u8_link}", xbmc.LOGINFO)
                progress.close()
                return self._proxy_link(m3u8_link)
            progress.update(40, 'Decoding stream...')
            stream_url = self._hunt_stream(original_url, html)
            xbmc.log(f"[CDNLiveTV] _hunt_stream result: {stream_url}", xbmc.LOGINFO)
            if stream_url:
                progress.update(100, 'Ready!')
                progress.close()
                return self._proxy_link(stream_url)
            progress.close()
            return url
        except Exception as e:
            xbmc.log(f"[CDNLiveTV] Exception in get_link: {e}", xbmc.LOGERROR)
            progress.close()
        return url

    def _proxy_link(self, stream_url: str) -> JetLink:
        """Run the HLS URL through the local proxy so Kodi gets the right Referer/Origin."""
        manifest_headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
            "Referer": "https://cdnlivetv.tv/",
            "Origin": "https://cdnlivetv.tv",
        }
        proxy = get_stream_proxy(
            "cdnlivetv",
            manifest_headers,
            options={"cache_manifest": False, "proxy_absolute_urls": True},
        )
        proxy_url = proxy.get_proxy_url(stream_url, manifest_headers)
        xbmc.log(f"[CDNLiveTV] Proxy URL: {proxy_url}", xbmc.LOGINFO)
        return JetLink(proxy_url, headers=manifest_headers, inputstream=JetInputstreamFFmpegDirect.default())

    def _resolve_cdn_stream(self, link):
        try:
            r = requests.get(link, headers={
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
                "Referer": "https://streamsports99.su/"
            }, timeout=self.timeout)
            return self._hunt_stream(link, r.text)
        except Exception:
            return None

    def _hunt_stream(self, url, html=None):
        try:
            if html is None:
                r = requests.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
                    "Referer": "https://streamsports99.su/"
                }, timeout=self.timeout)
                html = r.text

            # Current site obfuscation: base64 variables concatenated through a tiny decoder.
            stream_url = self._extract_b64_concat_url(html)
            if stream_url:
                xbmc.log(f"[CDNLiveTV] Found base64-concat stream URL: {stream_url}", xbmc.LOGINFO)
                return stream_url

            # Older hunter-style obfuscation fallback.
            params = self._extract_hunter_params(html)
            if not params:
                return None
            decoded_result = hunter.hunter(
                h=params['encoded'],
                u=params['base'],
                n=params['alphabet'],
                t=params['subtract'],
                e=params['decode_base'],
                r=params['param6']
            )
            urls = self._extract_urls_from_code(decoded_result)
            xbmc.log(f"[CDNLiveTV] Extracted URLs: {urls}", xbmc.LOGINFO)
            if urls:
                for url in urls:
                    if 'token=' in url:
                        xbmc.log(f"[CDNLiveTV] Selected token URL: {url}", xbmc.LOGINFO)
                        return url
                xbmc.log(f"[CDNLiveTV] Selected first URL: {urls[0]}", xbmc.LOGINFO)
                return urls[0]
            return None
        except Exception:
            return None

    def _extract_b64_concat_url(self, html: str) -> str:
        """Extract the m3u8 URL built from base64 variables (current player page layout)."""
        try:
            decoder_match = re.search(r'function\s+(\w+)\(s\)\s*\{[^}]*atob\(s\)[^}]*\}', html)
            if not decoder_match:
                return None
            decoder_name = decoder_match.group(1)
            concat_pattern = rf'var\s+(\w+)\s*=\s*((?:{decoder_name}\(\w+\)\s*\+\s*)+{decoder_name}\(\w+\))\s*;'
            concat_match = re.search(concat_pattern, html)
            if not concat_match:
                return None
            var_names = re.findall(rf'{decoder_name}\((\w+)\)', concat_match.group(2))
            url_parts = []
            for var_name in var_names:
                m = re.search(rf"var\s+{re.escape(var_name)}\s*=\s*['\"]([^'\"]+)['\"]", html)
                if not m:
                    return None
                url_parts.append(self._decode_b64_web(m.group(1)))
            if not url_parts:
                return None
            stream_url = ''.join(url_parts)
            if not stream_url.startswith('http'):
                return None
            return stream_url
        except Exception as e:
            xbmc.log(f"[CDNLiveTV] Base64 concat extraction error: {e}", xbmc.LOGDEBUG)
            return None

    def _decode_b64_web(self, encoded: str) -> str:
        """Decode a URL-safe base64 string (matches the player page decoder)."""
        try:
            encoded = encoded.replace('-', '+').replace('_', '/')
            while len(encoded) % 4:
                encoded += '='
            decoded = base64.b64decode(encoded)
            try:
                return decoded.decode('utf-8')
            except UnicodeDecodeError:
                return decoded.decode('latin-1')
        except Exception as e:
            xbmc.log(f"[CDNLiveTV] Base64 decode error: {e}", xbmc.LOGDEBUG)
            return ""

    def _extract_urls_from_code(self, code):
        try:
            decoder_match = re.search(r'function\s+(\w+)\(str\)\s*\{', code)
            if not decoder_match:
                return None
            decoder_name = decoder_match.group(1)
            const_pattern = r'const\s+(\w+)\s*=\s*[\'\"]([^\'\"]+)[\'\"]'
            variables = {}
            for match in re.finditer(const_pattern, code):
                var_name = match.group(1)
                var_value = match.group(2)
                variables[var_name] = var_value
            decoder_pattern = rf'{decoder_name}\(\w+\)'
            url_lines = []
            lines = code.split('\n')
            for line in lines:
                decoder_calls = re.findall(decoder_pattern, line)
                if len(decoder_calls) >= 5:
                    url_lines.append(line.strip())
            urls = []
            for line in url_lines:
                var_names = re.findall(rf'{decoder_name}\((\w+)\)', line)
                url_parts = []
                for var_name in var_names:
                    if var_name in variables:
                        decoded = self._decode_hunter_string(variables[var_name])
                        url_parts.append(decoded)
                if url_parts:
                    url = ''.join(url_parts)
                    urls.append(url)
            return urls
        except Exception:
            return None

    def _decode_hunter_string(self, encoded_str: str) -> str:
        try:
            encoded_str = encoded_str.replace('-', '+').replace('_', '/')
            while len(encoded_str) % 4:
                encoded_str += '='
            decoded_bytes = base64.b64decode(encoded_str)
            decoded_str = decoded_bytes.decode('latin-1')
            result = unquote(decoded_str)
            xbmc.log(f"[CDNLIVETV] Hunter decoded string (truncated): {result[:500]}", xbmc.LOGDEBUG)
            return result
        except Exception as e:
            xbmc.log(f"[CDNLIVETV] Hunter decode error: {e}", xbmc.LOGERROR)
            return encoded_str
    
    def _extract_hunter_params(self, html: str):
        try:
            xbmc.log(f"[CDNLIVETV] HTML for hunter param extraction (truncated): {html[:500]}", xbmc.LOGDEBUG)
            start_idx = html.find('eval(function(h,u,n,t,e,r)')
            if start_idx == -1:
                xbmc.log("[CDNLIVETV] No eval(function(h,u,n,t,e,r) found in HTML", xbmc.LOGDEBUG)
                return None
            
            text_from_eval = html[start_idx:]
            
            paren_count = 0
            in_string = False
            escape = False
            result = ''
            
            for char in text_from_eval:
                result += char
                if char == '(' and not in_string:
                    paren_count += 1
                elif char == ')' and not in_string:
                    paren_count -= 1
                    if paren_count == 0:
                        break
                elif char == '"' and not escape:
                    in_string = not in_string
                elif char == '\\':
                    escape = not escape
                else:
                    escape = False
            
            args_start = result.find('}("') + 2
            args_text = result[args_start:-1]
            
            args = []
            current = ''
            in_quote = False
            quote_char = None
            
            for char in args_text:
                if not in_quote and char == ',':
                    args.append(current.strip())
                    current = ''
                elif not in_quote and char in ('"', "'"):
                    in_quote = True
                    quote_char = char
                    current += char
                elif in_quote and char == quote_char and (len(current) == 0 or current[-1] != '\\'):
                    in_quote = False
                    current += char
                else:
                    current += char
            
            if current:
                current = current.strip()
                if current.endswith(')'):
                    while current.endswith(')'):
                        current = current[:-1]
                args.append(current)
            
            xbmc.log(f"[CDNLIVETV] Hunter param args extracted: {args}", xbmc.LOGDEBUG)
            if len(args) == 6:
                params = {
                    'encoded': args[0].strip('"'),
                    'base': int(args[1]),
                    'alphabet': args[2].strip('"'),
                    'subtract': int(args[3]),
                    'decode_base': int(args[4]),
                    'param6': int(args[5])
                }
                xbmc.log(f"[CDNLIVETV] Hunter params dict: {params}", xbmc.LOGDEBUG)
                return params
        
        except Exception as e:
            xbmc.log(f"[CDNLIVETV] Hunter param extraction error: {e}", xbmc.LOGERROR)
            pass
        
        return None
