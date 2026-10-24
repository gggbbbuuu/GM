import re
import base64
import json
import requests
import xbmc
from urllib.parse import urlparse, urljoin, parse_qsl, quote
from typing import Optional, List
from ..tools import debug_log

try:
    from . import jsunpack
except ImportError:
    jsunpack = None

try:
    from .tls_adapter import _ProxyTLSAdapter
    _HAS_TLS_ADAPTER = True
except ImportError:
    _HAS_TLS_ADAPTER = False


def _get_ssl_session() -> requests.Session:
    """Create a requests Session with SSL verification disabled for streaming sites."""
    sess = requests.Session()
    if _HAS_TLS_ADAPTER:
        sess.mount("https://", _ProxyTLSAdapter())
        sess.mount("http://", _ProxyTLSAdapter())
        sess.verify = False
    return sess


class UniversalResolver:
    """Universal resolver for extracting m3u8 streams from various embed types."""

    def __init__(self, user_agent: str = None, log_prefix: str = "[Resolver]"):
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        self._session = _get_ssl_session()
        self.log_prefix = log_prefix
        self.max_depth = 4
        self.stream_referer = None
        self.stream_origin = None

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

        if depth == 0:
            self.stream_referer = None
            self.stream_origin = None

        self.log(f"Resolving (depth={depth}): {url}")

        try:
            headers = {
                "User-Agent": self.user_agent,
                "Referer": referer or url,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            r = self._session.get(url, headers=headers, timeout=10, allow_redirects=True)
            self.log(f"Status: {r.status_code}, Final URL: {r.url}")

            if r.status_code != 200:
                self.log(f"HTTP error {r.status_code} for {url}", xbmc.LOGWARNING)
                return None

            html = r.text
            final_url = r.url

            stream = self._try_all_patterns(html, final_url, headers)
            if stream:
                self.stream_referer = final_url
                self.stream_origin = f"{urlparse(final_url).scheme}://{urlparse(final_url).netloc}"
                return stream

            api_stream, api_page = self._extract_fetch_api(html, final_url, headers)
            if api_stream:
                self.stream_referer = final_url
                self.stream_origin = f"{urlparse(final_url).scheme}://{urlparse(final_url).netloc}"
                return api_stream
            if api_page:
                result = self.resolve_url(api_page, final_url, depth + 1, visited)
                if result:
                    return result

            for candidate in self._extract_apiproxy_candidates(html, final_url, headers):
                result = self.resolve_url(candidate, final_url, depth + 1, visited)
                if result:
                    return result

            for candidate in self._extract_postapi_candidates(html, final_url, headers):
                result = self.resolve_url(candidate, final_url, depth + 1, visited)
                if result:
                    return result

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

        stream = self._extract_edge_token_stream(html, base_url, headers)
        if stream:
            return stream

        stream = self._extract_econfig_stream(html, base_url, headers)
        if stream:
            return stream

        stream = self._extract_xyz_token_stream(html, base_url, headers)
        if stream:
            return stream

        stream = self._extract_watchfa_stream(html, base_url, headers)
        if stream:
            return stream

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

        stream = self._extract_xor_payload(html, base_url, headers)
        if stream:
            return stream

        return None

    def _find_m3u8(self, html: str, base_url: str) -> Optional[str]:
        """Find m3u8 URL in HTML using multiple patterns."""
        html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
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
                    try:
                        url_path = urlparse(url).path
                        if url_path.endswith("/.m3u8") or url_path == ".m3u8":
                            continue
                    except Exception:
                        pass
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
            r = self._session.get(worker_url, headers=headers, timeout=10)
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
                    r = self._session.post(decrypt_url, data=f"input={input_val}", headers=post_headers, timeout=10)
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
            r = self._session.get(worker_url, headers=worker_headers, timeout=10)
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
            r = self._session.get(php_url, headers=headers, timeout=10)
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
                r = self._session.get(cfg_url, headers={**headers, "Referer": iframe_url}, timeout=10)
                data = r.json()
                stream = data.get("src") or data.get("srcBase")
                if stream:
                    self.log(f"ppcfg stream: {stream}")
                    return self._clean_url(stream, iframe_url)
            except Exception:
                pass
        return None

    def _extract_watchfa_stream(self, html: str, base_url: str, headers: dict) -> Optional[str]:
        """watchfa.st loader: <script src="...player-js/player.js" data-id="N"> -> config.php JSON with srcBase m3u8."""
        tag = re.search(r'<script\b[^>]*player-js/player\.js[^>]*>', html, re.IGNORECASE)
        if not tag:
            return None
        src_m = re.search(r'src=["\']([^"\']+)["\']', tag.group(0))
        id_m = re.search(r'data-id=["\']([^"\']+)["\']', tag.group(0))
        code_m = re.search(r'data-code=["\']([^"\']+)["\']', tag.group(0))
        if not src_m or (not id_m and not code_m):
            return None
        query = f"id={id_m.group(1)}" if id_m else f"code={code_m.group(1)}"
        script_url = urljoin(base_url, src_m.group(1))
        config_url = urljoin(script_url, f"config.php?{query}")
        self.log(f"watchfa config: {config_url}")
        try:
            r = self._session.get(config_url, headers={**headers, "Referer": base_url}, timeout=10)
            if r.status_code == 200:
                stream = self._find_m3u8(r.text, config_url)
                if stream:
                    return stream
        except Exception as e:
            self.log(f"watchfa config failed: {e}", xbmc.LOGWARNING)
        return None

    def _extract_edge_token_stream(self, html: str, base_url: str, headers: dict) -> Optional[str]:
        """Cowedd/vivatops edge players: const EDGE/CHANNEL/SRC + /api/playlist-token -> SRC?t=<token>.
        The manifest requires Origin of the hosting player page (checked by the edge)."""
        if "/api/playlist-token" not in html:
            return None
        edge_m = re.search(r'const\s+EDGE\s*=\s*["\']([^"\']+)["\']', html)
        ch_m = re.search(r'const\s+CHANNEL\s*=\s*["\']([^"\']+)["\']', html)
        src_m = re.search(r'const\s+SRC\s*=\s*["\']([^"\']+)["\']', html)
        if not (edge_m and ch_m and src_m):
            return None
        parsed = urlparse(base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        token_url = f"{edge_m.group(1).rstrip('/')}/api/playlist-token?slug={quote(ch_m.group(1))}"
        self.log(f"edge token: {token_url}")
        try:
            r = self._session.get(token_url, headers={**headers, "Origin": origin}, timeout=10)
            token = None
            if r.status_code == 200:
                token = (r.json() or {}).get("token")
        except Exception as e:
            self.log(f"edge token failed: {e}", xbmc.LOGWARNING)
            return None
        if not token:
            self.log(f"edge token status {r.status_code}", xbmc.LOGWARNING)
            return None
        src = src_m.group(1)
        sep = "&" if "?" in src else "?"
        stream = f"{src}{sep}t={token}"
        self.log(f"edge stream: {stream}")
        return stream

    def _extract_econfig_stream(self, html: str, base_url: str, headers: dict) -> Optional[str]:
        """lineagest.click / kora class: window._econfig b64 blob decoded by assets/stream.js:
        atob -> split 4 chunks -> drop idx3 char -> atob each -> reorder [2,0,3,1] -> join -> atob -> JSON {stream_url}."""
        m = re.search(r"window\._econfig='([A-Za-z0-9+/=]+)'", html)
        if not m:
            return None
        try:
            import base64 as _b64
            inner = _b64.b64decode(m.group(1) + "=" * (-len(m.group(1)) % 4)).decode("utf-8", "strict")

            def four_way(stage: str) -> Optional[str]:
                chunk = len(stage) // 4
                if chunk < 4:
                    return None
                chunks = [stage[i * chunk:(i + 1) * chunk] for i in range(4)]
                order = [2, 0, 3, 1]
                out = [""] * 4
                for i in range(4):
                    stripped = chunks[i][:3] + chunks[i][4:]
                    out[order[i]] = _b64.b64decode(stripped + "=" * (-len(stripped) % 4)).decode("utf-8", "strict")
                joined = "".join(out)
                return _b64.b64decode(joined + "=" * (-len(joined) % 4)).decode("utf-8", "strict")

            import json as _json
            payload = None
            for stage in (inner, None):
                if stage is None:
                    stage = _b64.b64decode(inner + "=" * (-len(inner) % 4)).decode("utf-8", "strict")
                try:
                    payload = _json.loads(four_way(stage))
                    break
                except Exception:
                    continue
            if not isinstance(payload, dict):
                return None
            url = payload.get("stream_url") or payload.get("stream_url_nop2p")
            if isinstance(url, str) and url.startswith("http"):
                self.log(f"econfig stream: {url[:120]}")
                return self._clean_url(url, base_url)
        except Exception as e:
            self.log(f"econfig decode failed: {e}", xbmc.LOGWARNING)
        return None

    def _extract_xyz_token_stream(self, html: str, base_url: str, headers: dict) -> Optional[str]:
        """xyzstreams.st embedserver2 class: servers map + SECRET_KEY AES token.
        -> https://<host>/<streamId>/mono.ts.m3u8?token=<tok>&server=2 (query form works + proxy-safe)."""
        if "mono.ts.m3u8" not in html or "SECRET_KEY" not in html:
            return None
        key_m = re.search(r'SECRET_KEY\s*=\s*"([^"]+)"', html)
        path_m = re.search(r"const streamPath = `([^`]+)`", html)
        srv_m = re.search(r"'1': `https://([^`$]+?)(?:\$\{|`)", html)
        if not (key_m and path_m and srv_m):
            return None
        query = urlparse(base_url).query
        if not query:
            return None
        stream_id = query
        path = path_m.group(1).replace("${streamId}", stream_id)
        host = "https://" + srv_m.group(1).split("$")[0].rstrip("/")
        self.log(f"xyz token host: {host} path: {path}")
        try:
            r = self._session.get(
                f"{host}/api/token",
                headers={**headers, "Origin": f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"},
                timeout=10,
            )
            if r.status_code != 200:
                self.log(f"xyz token api status {r.status_code}", xbmc.LOGWARNING)
                return None
            data = r.json()
            token = self._aes_sha256_decrypt(key_m.group(1), data["iv"], data["token"])
            if not token:
                return None
            from urllib.parse import quote as _quote
            stream = f"{host}{path}?token={_quote(token)}&server=2"
            self.log(f"xyz stream: {stream[:140]}")
            return stream
        except Exception as e:
            self.log(f"xyz token failed: {e}", xbmc.LOGWARNING)
            return None

    def _aes_sha256_decrypt(self, secret: str, iv_hex: str, token_hex: str) -> Optional[str]:
        import hashlib
        import binascii
        key = hashlib.sha256(secret.encode()).digest()
        iv = binascii.unhexlify(iv_hex)
        ct = binascii.unhexlify(token_hex)
        raw = None
        try:
            from Cryptodome.Cipher import AES
            raw = AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
        except Exception:
            try:
                from Crypto.Cipher import AES
                raw = AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
            except Exception:
                from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
                dec = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
                raw = dec.update(ct) + dec.finalize()
        pad = raw[-1]
        if 1 <= pad <= 16 and len(raw) >= pad:
            raw = raw[:-pad]
        return raw.decode("utf-8", "ignore").strip()

    def _extract_xor_payload(self, html: str, base_url: str, headers: dict) -> Optional[str]:
        """Decode String.fromCharCode(((arr[i]^k)-s+256)%256)+eval payloads (trefoxy/trendy48 class),
        then decrypt loadStreamUrl XOR-blob endpoints to the signed m3u8."""
        arr_m = re.search(r'([\w$]+)\s*=\s*\[((?:\d+\s*,\s*){50,}\d+)\]', html)
        const_m = re.search(r'String\.fromCharCode\(\(\(\s*[\w$]+\s*\[\s*[\w$]+\s*\]\s*\^\s*([\w$]+)\s*\)\s*-\s*([\w$]+)\s*\+256\)%256\)', html)
        if not arr_m or not const_m:
            return None
        xvar, svar = const_m.groups()
        mx = re.search(rf'\b{re.escape(xvar)}\s*=\s*(\d+)', html)
        ms = re.search(rf'\b{re.escape(svar)}\s*=\s*(\d+)', html)
        if not mx or not ms:
            return None
        xor_key, sub = int(mx.group(1)), int(ms.group(1))
        numbers = [int(x) for x in arr_m.group(2).split(",")]
        try:
            decoded = "".join(chr(((n ^ xor_key) - sub + 256) % 256) for n in numbers)
        except Exception:
            return None
        printable = sum(1 for c in decoded if 32 <= ord(c) < 127 or c in "\n\r\t")
        if printable < max(50, int(len(decoded) * 0.85)):
            return None
        self.log(f"XOR payload decoded ({len(decoded)} chars)")
        stream = self._find_m3u8(decoded, base_url)
        if stream:
            return stream
        call = re.search(r'loadStreamUrl\(\s*["\']([^"\']+)["\']', decoded)
        if not call:
            return None
        enc_url = call.group(1)
        try:
            parsed = urlparse(base_url)
            r = self._session.get(
                enc_url,
                headers={**headers, "Referer": base_url, "Origin": f"{parsed.scheme}://{parsed.netloc}"},
                timeout=10,
            )
            if r.status_code != 200 or len(r.content) < 2:
                self.log(f"XOR payload endpoint status {r.status_code}", xbmc.LOGWARNING)
                return None
            blob = r.content
            first = blob[0]
            key = enc_url.rsplit("/", 1)[-1]
            plain = bytes(
                [blob[i] ^ ord(key[(i - 1) % len(key)]) ^ ((first + i - 1) & 255) for i in range(1, len(blob))]
            ).decode("utf-8", "ignore")
            self.log(f"XOR payload decrypted: {plain[:160]}")
            stream = self._find_m3u8(plain, enc_url)
            if stream:
                return stream
        except Exception as e:
            self.log(f"XOR payload decrypt failed: {e}", xbmc.LOGWARNING)
        return None

    def _extract_fetch_api(self, html: str, base_url: str, headers: dict):
        """Follow fetch(\"api/x.php?k=\") JSON hops (ripple.kora.st / s3.vertex.st api/player.php class).
        Returns (stream, next_page): one of the two is set on success."""
        m = re.search(r'fetch\(\s*["\']([^"\']+\.php[^"\']*)["\']', html)
        if not m:
            return None, None
        path = m.group(1)
        if "<" in path or "${" in path:
            return None, None
        if "?" in path:
            base_part, query = path.split("?", 1)
            if query.endswith("="):
                base_params = dict(parse_qsl(urlparse(base_url).query))
                parts = []
                for kv in query.split("&"):
                    k, _, v = kv.partition("=")
                    if v:
                        parts.append(kv)
                    elif k in base_params and base_params[k]:
                        parts.append(f"{k}={base_params[k]}")
                    else:
                        return None, None
                path = f"{base_part}?{'&'.join(parts)}"
                if path.split("?", 1)[1].endswith("="):
                    return None, None
        api_url = urljoin(base_url, path)
        if not urlparse(api_url).netloc:
            return None, None
        self.log(f"Fetch-API hop: {api_url}")
        try:
            r = self._session.get(api_url, headers={**headers, "Referer": base_url}, timeout=10)
        except Exception as e:
            self.log(f"Fetch-API hop failed: {e}", xbmc.LOGWARNING)
            return None, None
        if r.status_code != 200:
            self.log(f"Fetch-API hop status {r.status_code}", xbmc.LOGWARNING)
            return None, None
        stream = self._find_m3u8(r.text, api_url)
        if stream:
            return stream, None
        try:
            data = r.json()
        except Exception:
            data = None
        if isinstance(data, dict):
            for key in ("url", "src", "stream", "file", "srcBase"):
                value = data.get(key)
                if isinstance(value, str) and value.startswith("http"):
                    value = self._unescape_url(value)
                    if ".m3u8" in value:
                        return value, None
                    return None, value
        return None, None

    def _extract_apiproxy_candidates(self, html: str, base_url: str, headers: dict) -> List[str]:
        """bestropes/esportsurge/topsurge player.php family: api_proxy.php match list -> channel embed links."""
        if "api_proxy.php" not in html:
            return []
        endpoint = urljoin(re.sub(r"player\.php/.*$", "", base_url), "api_proxy.php")
        self.log(f"api_proxy hop: {endpoint}")
        try:
            r = self._session.get(endpoint, headers={**headers, "Referer": base_url}, timeout=15)
            if r.status_code != 200:
                self.log(f"api_proxy hop status {r.status_code}", xbmc.LOGWARNING)
                return []
            payload = r.json()
        except Exception as e:
            self.log(f"api_proxy hop failed: {e}", xbmc.LOGWARNING)
            return []
        matches = payload.get("matches") if isinstance(payload, dict) else None
        if not isinstance(matches, list):
            return []
        base_slug = urlparse(base_url).path
        if "player.php/" in base_slug:
            base_slug = base_slug.split("player.php/", 1)[1]
        base_slug = base_slug.strip("/").lower()

        def slugify(value):
            return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")

        found = None
        for match in matches:
            if not isinstance(match, dict):
                continue
            pair = f"{slugify(match.get('team1'))}-vs-{slugify(match.get('team2'))}"
            matchstr = slugify(match.get("matchstr"))
            if (pair.strip("-") and pair in base_slug) or (matchstr and matchstr in base_slug):
                found = match
                break
        if not found:
            self.log(f"api_proxy: no match for slug '{base_slug}'", xbmc.LOGWARNING)
            return []
        candidates = []
        for channel in found.get("channels") or []:
            if not isinstance(channel, dict):
                continue
            for key in ("links", "oldLinks"):
                for link in channel.get(key) or []:
                    if isinstance(link, str) and link.startswith("http") and link not in candidates:
                        candidates.append(link)
        self.log(f"api_proxy: {len(candidates)} channel links for '{found.get('matchstr')}'")
        return candidates

    def _extract_postapi_candidates(self, html: str, base_url: str, headers: dict) -> List[str]:
        """opturspapa-style client render (post.js): Site.json('/api/post/<slug>') -> JSON streams[].url."""
        if "/api/post/" not in html and "/assets/js/post.js" not in html and "Site.json(" not in html:
            return []
        slug = urlparse(base_url).path.strip("/")
        if not slug or slug.startswith("api/"):
            return []
        api_url = urljoin(base_url, f"/api/post/{quote(slug, safe='')}")
        self.log(f"postapi hop: {api_url}")
        try:
            r = self._session.get(api_url, headers={**headers, "Referer": base_url}, timeout=10)
            if r.status_code != 200:
                self.log(f"postapi hop status {r.status_code}", xbmc.LOGWARNING)
                return []
            data = r.json()
        except Exception as e:
            self.log(f"postapi hop failed: {e}", xbmc.LOGWARNING)
            return []
        candidates = []
        streams = data.get("streams") if isinstance(data, dict) else None
        for entry in streams if isinstance(streams, list) else []:
            if isinstance(entry, dict):
                url = entry.get("url")
                if isinstance(url, str) and url.startswith("http") and url not in candidates:
                    candidates.append(url)
        self.log(f"postapi: {len(candidates)} stream urls")
        return candidates

    def resolve_iframes(self, html: str, base_url: str) -> List[str]:
        """Extract and return all valid iframe URLs from HTML."""
        return self._find_iframes(html, base_url)

    def _find_iframes(self, html: str, base_url: str) -> List[str]:
        """Extract iframe URLs from HTML, filtering out ad/tracking iframes.
        Also decodes atob()-built iframe srcs (rockyembed/fetch.php pattern)."""
        html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
        iframe_matches = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        for b64 in re.findall(r'atob\(\s*["\']([A-Za-z0-9+/=]{16,})["\']\s*\)', html):
            try:
                decoded = base64.b64decode(b64).decode("utf-8", errors="ignore")
            except Exception:
                continue
            if decoded.startswith(("http://", "https://")):
                iframe_matches.append(decoded)
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
        url = url.replace("\\u0026", "&")
        url = url.replace("\\x26", "&")
        url = url.replace("\\u003D", "=")
        url = url.replace("\\u003d", "=")
        url = url.replace("\\u0025", "%")
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
            r = self._session.get(worker_url, headers=headers, timeout=10)
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
