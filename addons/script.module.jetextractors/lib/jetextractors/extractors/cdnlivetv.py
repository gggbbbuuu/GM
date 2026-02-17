import requests, re
from urllib.parse import unquote
import xbmc
import base64
from ..models import *
from ..util import m3u8_src, hunter
# 6.1 | # Note: adjust import if cdnutils.py is moved to another location

class CDNLiveTV(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["cdn-live.tv", "api.cdn-live.tv"]
        self.name = "CDNLiveTV"
        self.short_name = "CDN"
        self.user = "cdnlivetv"
        self.plan = "free"
        self.std_headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
        }

    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        items = []
        if self.progress_init(progress, items):
            return items
        
        base_url = "https://api.cdn-live.tv/api/v1"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Referer": "https://cdn-live.tv/",
        }
        
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
        
        return items

    def get_link(self, url: JetLink) -> JetLink:
        original_url = url.address
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
            "Referer": "https://cdn-live.tv/",
        }
        progress = xbmcgui.DialogProgress()
        progress.create('CDNLiveTV', 'Resolving stream...')
        try:
            xbmc.log(f"[CDNLiveTV] Resolving link: {original_url}", xbmc.LOGINFO)
            progress.update(10, 'Fetching channel page...')
            r = requests.get(original_url, timeout=self.timeout, headers=headers)
            html = r.text
            xbmc.log(f"[CDNLiveTV] HTML fetched, length: {len(html)}", xbmc.LOGINFO)
            if '<iframe' in html:
                xbmc.log(f"[CDNLiveTV] iframe detected in HTML", xbmc.LOGINFO)
            else:
                xbmc.log(f"[CDNLiveTV] No iframe found in HTML", xbmc.LOGINFO)
            m3u8_link = m3u8_src.scan_page(original_url, html=html)
            xbmc.log(f"[CDNLiveTV] m3u8_src.scan_page result: {m3u8_link}", xbmc.LOGINFO)
            if m3u8_link:
                xbmc.log(f"[CDNLiveTV] Returning m3u8 link: {m3u8_link}", xbmc.LOGINFO)
                progress.close()
                return m3u8_link
            progress.update(40, 'Decoding stream...')
            stream_url, manifest_headers, player_headers, player2_headers = self._resolve_cdn_stream(original_url)
            xbmc.log(f"[CDNLiveTV] _resolve_cdn_stream result: {stream_url}", xbmc.LOGINFO)
            if stream_url:
                progress.update(80, 'Validating stream...')
                xbmc.log(f"[CDNLiveTV] Skipping validation, returning stream_url", xbmc.LOGINFO)
                try:
                    m3u8_headers = manifest_headers if manifest_headers else headers
                    m3u8_resp = requests.get(stream_url, headers=m3u8_headers, timeout=10)
                    xbmc.log(f"[CDNLiveTV] playlist.m3u8 HTTP status: {m3u8_resp.status_code}", xbmc.LOGINFO)
                except Exception as e:
                    xbmc.log(f"[CDNLiveTV] Error fetching playlist.m3u8: {e}", xbmc.LOGERROR)
                progress.update(100, 'Ready!')
                xbmc.log(f"[CDNLiveTV] Returning JetLink without inputstream", xbmc.LOGINFO)
                progress.close()
                return JetLink(stream_url, headers=manifest_headers, inputstream=JetInputstreamFFmpegDirect.default())
            progress.close()
            return url
        except Exception as e:
            xbmc.log(f"[CDNLiveTV] Exception in get_link: {e}", xbmc.LOGERROR)
            progress.close()
        return url

    def _resolve_cdn_stream(self, link):
        try:
            from urllib.parse import urlparse
            url = link
            hunted_url = self._hunt_stream(url)
            if not hunted_url:
                return None, None, None, None
            parsed_url = urlparse(hunted_url)
            actual_host = parsed_url.netloc
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
                "Origin": "https://cdn-live.tv",
                "Referer": "https://cdn-live.tv/",
            }
            manifest_headers = headers.copy()
            player_headers = headers.copy()
            player2_headers = headers.copy()
            return hunted_url, manifest_headers, player_headers, player2_headers
        except Exception:
            return None, None, None, None

    def _hunt_stream(self, url):
        try:
            r = requests.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
                "Referer": "https://cdn-live.tv/"
            }, timeout=self.timeout)
            html = r.text
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
                # Prefer token= URL (more reliable)
                for url in urls:
                    if 'token=' in url:
                        xbmc.log(f"[CDNLiveTV] Selected token URL: {url}", xbmc.LOGINFO)
                        return url
                # Fall back to first URL
                xbmc.log(f"[CDNLiveTV] Selected first URL: {urls[0]}", xbmc.LOGINFO)
                return urls[0]
            return None
        except Exception:
            return None

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
