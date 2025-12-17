from ..models import *
import requests
import re
# import xbmc

class StreamsCenter(JetExtractor):
    def __init__(self) -> None:
        self.domains = ["streamcenter.pro", "streamscenter.live", "streamscenter.online", "streams.center", "mainstreams.pro", "edgestreams.pro"]
        self.name = "StreamsCenter"
        self.resolve_only = True

    def get_link(self, url: JetLink) -> JetLink:
        from ..util import m3u8_src
        
        #xbmc.log(f"[StreamsCenter] Starting extraction for: {url.address}", #xbmc.logINFO)
        
        headers = {
            "User-Agent": self.user_agent,
            "Referer": "https://streams.center/",
            "Origin": "https://streams.center"
        }
        
        try:
            # Step 1: Fetch the embed page (e.g., ch72.php)
            #xbmc.log(f"[StreamsCenter] Fetching embed page", #xbmc.logINFO)
            r = requests.get(url.address, headers=headers, timeout=self.timeout)
            #xbmc.log(f"[StreamsCenter] Embed page status: {r.status_code}", #xbmc.logINFO)
            
            # Step 2: Look for iframe in embed page
            iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', r.text, re.IGNORECASE)
            if not iframe_match:
                #xbmc.log(f"[StreamsCenter] No iframe found in embed page", #xbmc.logWARNING)
                return None
            
            iframe_url = iframe_match.group(1)
            # Fix URL construction
            if not iframe_url.startswith("http"):
                if iframe_url.startswith("//"):
                    iframe_url = "https:" + iframe_url
                elif iframe_url.startswith("/"):
                    iframe_url = "https://streams.center" + iframe_url
                else:
                    iframe_url = "https://streams.center/" + iframe_url
            
            #xbmc.log(f"[StreamsCenter] Found iframe: {iframe_url}", #xbmc.logINFO)
            
            # Step 3: Fetch iframe page
            headers["Referer"] = url.address
            r_iframe = requests.get(iframe_url, headers=headers, timeout=self.timeout)
            #xbmc.log(f"[StreamsCenter] Iframe page status: {r_iframe.status_code}", #xbmc.logINFO)
            
            # Step 4: Try multiple patterns to find input/payload
            input_patterns = [
                r'(?:var\s+)?input\s*[=:]\s*["\']([^"\']+)["\']',
                r'data-input=["\']([^"\']+)["\']',
                r'input:\s*["\']([^"\']+)["\']'
            ]
            
            payload = None
            for i, pattern in enumerate(input_patterns):
                input_match = re.search(pattern, r_iframe.text, re.IGNORECASE)
                if input_match:
                    payload = input_match.group(1)
                    #xbmc.log(f"[StreamsCenter] Found payload with pattern {i}: {payload[:20]}...", #xbmc.logINFO)
                    break
            
            if not payload:
                #xbmc.log(f"[StreamsCenter] No payload found, trying m3u8 scan", #xbmc.logWARNING)
                # Try m3u8 scan as fallback
                m3u8 = m3u8_src.scan_page(iframe_url, html=r_iframe.text)
                if m3u8:
                    #xbmc.log(f"[StreamsCenter] Found m3u8 via scan: {m3u8.address}", #xbmc.logINFO)
                    return m3u8
                #xbmc.log(f"[StreamsCenter] M3U8 scan also failed", #xbmc.logWARNING)
                return None
            
            # Step 5: POST to decrypt.php
            decrypt_url = "https://streams.center/embed/decrypt.php"
            post_headers = headers.copy()
            post_headers["Content-Type"] = "application/x-www-form-urlencoded"
            post_headers["X-Requested-With"] = "XMLHttpRequest"
            #xbmc.log(f"[StreamsCenter] POSTing to decrypt.php", #xbmc.logINFO)
            r_decrypt = requests.post(decrypt_url, data={"input": payload}, headers=post_headers, timeout=self.timeout)
            #xbmc.log(f"[StreamsCenter] Decrypt response status: {r_decrypt.status_code}", #xbmc.logINFO)
            
            # Step 6: Extract stream URL from decrypt response
            decrypted = r_decrypt.text.strip()
            #xbmc.log(f"[StreamsCenter] Decrypted response: {decrypted[:100]}", #xbmc.logINFO)
            
            # Try to find direct m3u8 URL first
            m3u8_match = re.search(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', decrypted, re.IGNORECASE)
            if m3u8_match:
                m3u8_url = m3u8_match.group(1)
                #xbmc.log(f"[StreamsCenter] Found direct m3u8: {m3u8_url}", #xbmc.logINFO)
                return JetLink(m3u8_url, headers=headers)
            
            # Look for stream parameter to construct m3u8 URL
            stream_match = re.search(r'stream=([a-z0-9]+)', decrypted)
            if stream_match:
                stream_id = stream_match.group(1)
                m3u8_url = f"https://edgestreams.pro/hls/{stream_id}.m3u8"
                #xbmc.log(f"[StreamsCenter] Constructed m3u8 from stream ID: {m3u8_url}", #xbmc.logINFO)
                return JetLink(m3u8_url, headers=headers)
            
            #xbmc.log(f"[StreamsCenter] No stream ID or m3u8 found in decrypt response", #xbmc.logWARNING)
            
        except requests.exceptions.RequestException as e:
            #xbmc.log(f"[StreamsCenter] Request exception: {str(e)}", #xbmc.logERROR)
            return None
        except Exception as e:
            #xbmc.log(f"[StreamsCenter] Exception: {str(e)}", #xbmc.logERROR)
            return None
        
        #xbmc.log(f"[StreamsCenter] Extraction failed, returning None", #xbmc.logWARNING)
        return None