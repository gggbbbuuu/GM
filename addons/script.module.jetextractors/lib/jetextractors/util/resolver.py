import re
import base64
import json
import requests
import xbmc
from urllib.parse import urlparse, urljoin
from typing import Optional, List
from ..tools import debug_log

try:
    from . import jsunpack
except ImportError:
    jsunpack = None


class UniversalResolver:
    """Universal resolver for extracting m3u8 streams from various embed types."""

    def __init__(self, user_agent: str = None, log_prefix: str = "[Resolver]"):
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        self.log_prefix = log_prefix
        self.max_depth = 4

    def log(self, msg: str, level: int = xbmc.LOGINFO):
        debug_log(f"{self.log_prefix} {msg}", level)

    def resolve_url(self, url: str, referer: str = None, depth: int = 0, visited: set = None) -> Optional[str]:
        """Main entry point: try to resolve a URL to an m3u8 stream."""
        if visited is None:
            visited = set()

        if url in visited:
            return None
        visited.add(url)

        if depth >= self.max_depth:
            self.log(f"Max depth reached for: {url}", xbmc.LOGWARNING)
            return None

        self.log(f"Resolving (depth={depth}): {url}")

        try:
            headers = {
                "User-Agent": self.user_agent,
                "Referer": referer or url,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            r = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            self.log(f"Status: {r.status_code}, Final URL: {r.url}")

            if r.status_code != 200:
                self.log(f"HTTP error {r.status_code} for {url}", xbmc.LOGWARNING)
                return None

            html = r.text
            final_url = r.url

            stream = self._try_all_patterns(html, final_url, headers)
            if stream:
                return stream

            iframes = self._find_iframes(html, final_url)
            if not iframes:
                self.log(f"No iframes found in HTML (length={len(html)})", xbmc.LOGWARNING)
            for iframe_url in iframes:
                result = self.resolve_url(iframe_url, final_url, depth + 1, visited)
                if result:
                    return result

            return None

        except requests.RequestException as e:
            self.log(f"Request error: {e}", xbmc.LOGWARNING)
            return None
        except Exception as e:
            self.log(f"Error: {e}", xbmc.LOGERROR)
            return None

    def _try_all_patterns(self, html: str, base_url: str, headers: dict = None) -> Optional[str]:
        """Try all extraction patterns in order of specificity."""
        if not headers:
            headers = {"User-Agent": self.user_agent, "Referer": base_url}

        stream = self._find_m3u8(html, base_url)
        if stream:
            return stream

        stream = self._extract_encrypted_worker(html, base_url, headers)
        if stream:
            return stream

        stream = self._extract_worker_endpoint(html, base_url, headers)
        if stream:
            return stream

        stream = self._extract_decrypt_input(html, base_url, headers)
        if stream:
            return stream

        stream = self._extract_fid_src(html, base_url, headers)
        if stream:
            return stream

        stream = self._extract_char_array(html, base_url)
        if stream:
            return stream

        stream = self._extract_hex_source(html)
        if stream:
            return stream

        stream = self._extract_ppcfg(html, base_url, headers)
        if stream:
            return stream

        return None

    def _find_m3u8(self, html: str, base_url: str) -> Optional[str]:
        """Find m3u8 URL in HTML using multiple patterns."""
        patterns = [
            r'(?:source|src|file|streamUrl|videoSrc|sourceUrl|playlistUrl)\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'(?:https?:)?//[^\s"\'<>]+\.m3u8[^\s"\'<>]*',
            r'["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'video.*?src\s*[=:]\s*["\']([^"\']+)["\']',
            r'data-src\s*[=:]\s*["\']([^"\']+)["\']',
            r'src\s*=\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'(?:file|source|url|stream)\s*[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                url = self._clean_url(match, base_url)
                if url and '.m3u8' in url.lower():
                    self.log(f"M3U8 pattern matched: {url}")
                    return url

        b64_matches = re.findall(r'atob\((?:["\'])((?:aHR|Ly)[^"\']*)(?:["\'])', html)
        for b64 in b64_matches:
            try:
                decoded = base64.b64decode(b64).decode('utf-8', errors='ignore')
                if '.m3u8' in decoded:
                    url = self._clean_url(decoded, base_url)
                    if url:
                        self.log(f"Base64 decoded m3u8: {url}")
                        return url
            except Exception:
                pass

        if jsunpack:
            packed_matches = re.findall(r"(eval\(function\(p,a,c,k,e,d\).+?{}\)\))", html)
            for packed in packed_matches:
                try:
                    unpacked = jsunpack.unpack(packed)
                    if unpacked:
                        url = self._find_m3u8(unpacked, base_url)
                        if url:
                            return url
                except Exception:
                    pass

        return None

    def _extract_worker_endpoint(self, html: str, base_url: str, headers: dict) -> Optional[str]:
        """Extract workerEndpoint = _hexDec("...") and resolve to stream."""
        match = re.search(r'workerEndpoint\s*=\s*_hexDec\("([0-9a-fA-F]+)"\)', html)
        if not match:
            return None
        try:
            worker_url = bytes.fromhex(match.group(1)).decode()
            self.log(f"Worker endpoint (hex decoded): {worker_url}")
            r = requests.get(worker_url, headers=headers, timeout=10)
            data = r.json()
            if data.get("success") and data.get("stream"):
                stream = self._unescape_url(data["stream"])
                self.log(f"Worker stream: {stream}")
                return stream
        except Exception as e:
            self.log(f"Worker endpoint failed: {e}", xbmc.LOGWARNING)
        return None

    def _extract_decrypt_input(self, html: str, base_url: str, headers: dict) -> Optional[str]:
        """Extract input: "<base64>" and POST to decrypt.php (streams.center pattern)."""
        match = re.search(r'input:\s*["\']([A-Za-z0-9+/=]+)["\']', html)
        if not match:
            match = re.search(r'var\s+input\s*=\s*["\']([A-Za-z0-9+/=]+)["\']', html)
        if not match:
            return None
        try:
            post_headers = {**headers, "Content-Type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest"}
            input_val = match.group(1)
            parsed = urlparse(base_url)
            decrypt_paths = [
                urljoin(base_url, "decrypt.php"),
                f"{parsed.scheme}://{parsed.netloc}/decrypt.php",
                f"{parsed.scheme}://{parsed.netloc}/embed/decrypt.php",
            ]
            decrypted = None
            for decrypt_url in decrypt_paths:
                try:
                    r = requests.post(decrypt_url, data=f"input={input_val}", headers=post_headers, timeout=10)
                    if r.status_code == 200 and "://" in r.text.strip():
                        decrypted = r.text.strip()
                        self.log(f"Decrypt OK from {decrypt_url}: {decrypted[:200]}")
                        break
                except Exception:
                    continue
            if not decrypted:
                self.log("All decrypt.php endpoints failed", xbmc.LOGWARNING)
                return None
            url = self._clean_url(decrypted, base_url)
            if url:
                return url
            stream_match = re.search(r'(https?://[^\s\'"]+\.m3u8[^\s\'"]*)', decrypted, re.IGNORECASE)
            if stream_match:
                return self._clean_url(stream_match.group(1), base_url)
        except Exception as e:
            self.log(f"Decrypt input failed: {e}", xbmc.LOGWARNING)
        return None

    def _extract_encrypted_worker(self, html: str, base_url: str, headers: dict) -> Optional[str]:
        """Extract and resolve iframe.st encrypted worker URL with Origin header."""
        config = self.extract_worker_config(html)
        if not config:
            return None
        wd, wk, wri = config
        worker_url = self.decrypt_worker_url(wd, wk, wri)
        if not worker_url:
            self.log("Failed to decrypt worker URL", xbmc.LOGWARNING)
            return None
        self.log(f"Encrypted worker resolved to: {worker_url}")
        try:
            worker_headers = {
                **headers,
                "Origin": "https://iframe.st",
                "Referer": base_url,
            }
            r = requests.get(worker_url, headers=worker_headers, timeout=10)
            self.log(f"Worker response status: {r.status_code}")
            try:
                data = r.json()
                if data.get("success") and data.get("stream"):
                    stream = self._unescape_url(data["stream"])
                    self.log(f"Encrypted worker stream: {stream}")
                    return stream
            except Exception:
                pass
            stream = self._find_m3u8(r.text, worker_url)
            if stream:
                return stream
        except Exception as e:
            self.log(f"Encrypted worker failed: {e}", xbmc.LOGWARNING)
        return None

    def _extract_fid_src(self, html: str, base_url: str, headers: dict) -> Optional[str]:
        """Extract fid+src pattern: fid="X" ... src="//host/x.js" -> host/x.php?...&live=X -> char array URL."""
        match = re.search(r'fid="([^"]+)".*?src="//([^"]+\.js)"', html, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        fid = match.group(1)
        host = match.group(2).replace('.js', '.php')
        php_url = f"https://{host}?player=desktop&live={fid}"
        self.log(f"FID+SRC PHP URL: {php_url}")
        try:
            r = requests.get(php_url, headers=headers, timeout=10)
            char_match = re.search(r'(\["h","t","t","p",.+?\])\.join\(""\)', r.text, re.IGNORECASE)
            if char_match:
                chars = json.loads(char_match.group(1))
                url = "".join(chars)
                self.log(f"FID+SRC char array URL: {url}")
                return self._clean_url(url, php_url)
            stream = self._find_m3u8(r.text, php_url)
            if stream:
                return stream
        except Exception as e:
            self.log(f"FID+SRC failed: {e}", xbmc.LOGWARNING)
        return None

    def _extract_char_array(self, html: str, base_url: str) -> Optional[str]:
        """Extract URL from char array: ["h","t","t","p",...].join("")"""
        match = re.search(r'(\["h","t","t","p",.+?\])\.join\(""\)', html, re.IGNORECASE)
        if not match:
            return None
        try:
            chars = json.loads(match.group(1))
            url = "".join(chars)
            self.log(f"Char array URL: {url}")
            return self._clean_url(url, base_url)
        except Exception as e:
            self.log(f"Char array decode failed: {e}", xbmc.LOGWARNING)
        return None

    def _extract_hex_source(self, html: str) -> Optional[str]:
        """Extract hexEncoded = "deadbeef..." and decode to stream URL."""
        match = re.search(r'hexEncoded\s*=\s*"([0-9a-fA-F]{16,})"', html)
        if not match:
            return None
        try:
            url = bytes.fromhex(match.group(1)).decode("utf-8", "ignore")
            if "://" in url:
                self.log(f"Hex decoded URL: {url}")
                return self._unescape_url(url)
        except Exception as e:
            self.log(f"Hex decode failed: {e}", xbmc.LOGWARNING)
        return None

    def _extract_ppcfg(self, html: str, base_url: str, headers: dict) -> Optional[str]:
        """Try ppcfg=1 pattern to get stream config."""
        iframes = self._find_iframes(html, base_url)
        for iframe_url in iframes:
            if any(ad in iframe_url.lower() for ad in ["youtube", "doubleclick", "googlesyndication"]):
                continue
            try:
                cfg_url = iframe_url + ("&" if "?" in iframe_url else "?") + f"ppcfg=1&_={int(__import__('time').time() * 1000)}"
                r = requests.get(cfg_url, headers={**headers, "Referer": iframe_url}, timeout=10)
                data = r.json()
                stream = data.get("src") or data.get("srcBase")
                if stream:
                    self.log(f"ppcfg stream: {stream}")
                    return self._clean_url(stream, iframe_url)
            except Exception:
                pass
        return None

    def resolve_iframes(self, html: str, base_url: str) -> List[str]:
        """Extract and return all valid iframe URLs from HTML."""
        return self._find_iframes(html, base_url)

    def _find_iframes(self, html: str, base_url: str) -> List[str]:
        """Extract iframe URLs from HTML, filtering out ad/tracking iframes."""
        iframe_matches = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        self.log(f"Raw iframe matches: {len(iframe_matches)}")

        AD_IFRAMES = ("live_chat", "live-chat", "getbanner", "ad.html", "doubleclick",
                      "googlesyndication", "livetv786.pro", "youtube.com/live_chat")

        results = []
        for raw_url in iframe_matches:
            if not raw_url:
                continue
            cleaned = self._clean_url(raw_url, base_url)
            if not cleaned:
                continue
            if any(ad in cleaned.lower() for ad in AD_IFRAMES):
                self.log(f"Filtered ad iframe: {cleaned}")
                continue
            if cleaned and self._is_valid_iframe_url(cleaned):
                results.append(cleaned)
            else:
                self.log(f"Invalid iframe: raw={raw_url}, cleaned={cleaned}")

        self.log(f"Valid iframes: {len(results)} -> {results}")
        return results

    def _clean_url(self, url: str, base_url: str) -> Optional[str]:
        """Clean and normalize a URL."""
        if not url:
            return None

        url = self._unescape_url(url)

        try:
            decoded = base64.b64decode(url).decode("utf-8")
            if "://" in decoded:
                url = decoded
        except Exception:
            pass

        url = re.sub(r"\\[nrt]", "", url)

        if '<' in url or '${' in url:
            return None

        if url.startswith("//"):
            url = "https:" + url
        elif not url.startswith("http"):
            parsed = urlparse(base_url)
            if url.startswith("/"):
                url = f"{parsed.scheme}://{parsed.netloc}{url}"
            else:
                path_parts = parsed.path.split('/')[:-1]
                url = f"{parsed.scheme}://{parsed.netloc}{'/'.join(path_parts)}/{url}"

        url = url.split("#", 1)[0]

        tail = url.rsplit("/", 1)[-1].split("?", 1)[0]
        if len(tail) >= 16 and len(tail) % 2 == 0:
            try:
                decoded = bytes.fromhex(tail).decode("utf-8")
                if decoded.startswith("http"):
                    return decoded
            except (ValueError, UnicodeDecodeError):
                pass

        return url

    def _is_valid_iframe_url(self, url: str) -> bool:
        """Check if an iframe URL is valid."""
        if not url:
            return False
        if '<' in url or '${' in url:
            return False
        if not url.startswith("http"):
            return False
        invalid_extensions = ['.jpg', '.png', '.gif', '.css', '.ico']
        if any(url.lower().endswith(ext) for ext in invalid_extensions):
            return False
        return True

    def _unescape_url(self, url: str) -> str:
        """Unescape URL strings (fix JSON escaping)."""
        if not url:
            return url
        url = url.replace("\\/", "/")
        url = url.replace("\\u002F", "/")
        url = url.replace("\\x2F", "/")
        return url

    def extract_worker_config(self, html: str):
        """Extract iframe.st worker configuration from HTML (legacy method)."""
        wd_match = re.search(r'_wd\s*=\s*["\']([^"\']+)["\']', html)
        wk_match = re.search(r'_wk\s*=\s*(\d+)', html)
        wri_match = re.search(r'_wri\s*=\s*\[([^\]]+)\]', html)
        if wd_match and wk_match and wri_match:
            wd = wd_match.group(1)
            wk = int(wk_match.group(1))
            wri = [int(x) for x in wri_match.group(1).split(',')]
            return wd, wk, wri
        return None

    def decrypt_worker_url(self, encoded: str, xor_key: int, rev_indices: list):
        """Decrypt iframe.st style worker URLs (legacy method)."""
        try:
            chars = list(encoded)
            unshuffled = [''] * len(chars)
            for i in range(len(chars)):
                unshuffled[rev_indices[i]] = chars[i]
            xor_encoded = ''.join(unshuffled)
            hex_encoded = ''
            for i in range(0, len(xor_encoded), 2):
                byte = int(xor_encoded[i:i+2], 16)
                hex_encoded += chr(byte ^ xor_key)
            rot13_str = ''
            for i in range(0, len(hex_encoded), 2):
                rot13_str += chr(int(hex_encoded[i:i+2], 16))
            def rot13_char(c):
                code = ord(c)
                if c.isalpha():
                    base = ord('A') if c.isupper() else ord('a')
                    return chr(base + (code - base + 13) % 26)
                return c
            reversed_str = ''.join(rot13_char(c) for c in rot13_str)
            base64_str = reversed_str[::-1]
            return base64.b64decode(base64_str).decode('utf-8')
        except Exception:
            return None

    def resolve_worker(self, worker_url: str, referer: str) -> Optional[str]:
        """Resolve a worker URL to get the stream URL."""
        try:
            headers = {
                "User-Agent": self.user_agent,
                "Referer": referer
            }
            r = requests.get(worker_url, headers=headers, timeout=10)
            self.log(f"Worker status: {r.status_code}, content-type: {r.headers.get('content-type', 'unknown')}")

            try:
                data = r.json()
                if data.get("success") and data.get("stream"):
                    stream = self._unescape_url(data["stream"])
                    return stream
            except Exception:
                pass

            return self._find_m3u8(r.text, worker_url)
        except Exception as e:
            self.log(f"Worker resolution failed: {e}", xbmc.LOGWARNING)
            return None
