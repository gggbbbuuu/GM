import requests
from urllib.parse import urlparse
from typing import Optional, Dict, Any
import time
import xbmc
from .tools import debug_log

DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

class JetHttpClient:
    _sessions: Dict[str, requests.Session] = {}
    _default_timeout = 10
    _max_retries = 3
    
    @staticmethod
    def get_session(domain: str, headers: Optional[Dict[str, str]] = None) -> requests.Session:
        if domain not in JetHttpClient._sessions:
            sess = requests.Session()
            sess.headers.update({
                "User-Agent": DEFAULT_UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            })
            if headers:
                sess.headers.update(headers)
            JetHttpClient._sessions[domain] = sess
            debug_log(f"[JetHttpClient] Created session for {domain}", xbmc.LOGDEBUG)
        return JetHttpClient._sessions[domain]
    
    @staticmethod
    def fetch(url: str, timeout: Optional[int] = None, headers: Optional[Dict[str, str]] = None, 
              session: Optional[requests.Session] = None, **kwargs) -> requests.Response:
        domain = urlparse(url).netloc
        timeout = timeout or JetHttpClient._default_timeout
        
        if session is None:
            session = JetHttpClient.get_session(domain, headers)
        
        merged_headers = session.headers.copy()
        if headers:
            merged_headers.update(headers)
        
        last_error = None
        for attempt in range(JetHttpClient._max_retries):
            try:
                resp = session.get(url, timeout=timeout, headers=merged_headers, **kwargs)
                resp.raise_for_status()
                if attempt > 0:
                    debug_log(f"[JetHttpClient] Success on retry {attempt + 1} for {url}", xbmc.LOGINFO)
                return resp
            except requests.exceptions.Timeout as e:
                last_error = e
                debug_log(f"[JetHttpClient] Timeout on attempt {attempt + 1} for {url}", xbmc.LOGWARNING)
                if attempt < JetHttpClient._max_retries - 1:
                    time.sleep(1 * (attempt + 1))
            except requests.exceptions.HTTPError as e:
                if e.response.status_code >= 500:
                    last_error = e
                    debug_log(f"[JetHttpClient] Server error {e.response.status_code} on attempt {attempt + 1} for {url}", xbmc.LOGWARNING)
                    if attempt < JetHttpClient._max_retries - 1:
                        time.sleep(1 * (attempt + 1))
                else:
                    raise
            except requests.exceptions.ConnectionError as e:
                last_error = e
                debug_log(f"[JetHttpClient] Connection error on attempt {attempt + 1} for {url}", xbmc.LOGWARNING)
                if attempt < JetHttpClient._max_retries - 1:
                    time.sleep(1 * (attempt + 1))
        
        if last_error:
            debug_log(f"[JetHttpClient] All {JetHttpClient._max_retries} attempts failed for {url}: {last_error}", xbmc.LOGERROR)
            raise last_error
        
        raise RuntimeError("Unexpected state in fetch")
    
    @staticmethod
    def fetch_text(url: str, timeout: Optional[int] = None, headers: Optional[Dict[str, str]] = None, **kwargs) -> str:
        return JetHttpClient.fetch(url, timeout=timeout, headers=headers, **kwargs).text
    
    @staticmethod
    def fetch_json(url: str, timeout: Optional[int] = None, headers: Optional[Dict[str, str]] = None, **kwargs) -> Any:
        return JetHttpClient.fetch(url, timeout=timeout, headers=headers, **kwargs).json()
    
    @staticmethod
    def post(url: str, data: Optional[Any] = None, json: Optional[Any] = None, 
             timeout: Optional[int] = None, headers: Optional[Dict[str, str]] = None, **kwargs) -> requests.Response:
        domain = urlparse(url).netloc
        timeout = timeout or JetHttpClient._default_timeout
        session = JetHttpClient.get_session(domain, headers)
        
        merged_headers = session.headers.copy()
        if headers:
            merged_headers.update(headers)
        
        last_error = None
        for attempt in range(JetHttpClient._max_retries):
            try:
                resp = session.post(url, data=data, json=json, timeout=timeout, headers=merged_headers, **kwargs)
                resp.raise_for_status()
                return resp
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_error = e
                debug_log(f"[JetHttpClient] POST error on attempt {attempt + 1} for {url}: {e}", xbmc.LOGWARNING)
                if attempt < JetHttpClient._max_retries - 1:
                    time.sleep(1 * (attempt + 1))
        
        if last_error:
            raise last_error
        raise RuntimeError("Unexpected state in post")
    
    @staticmethod
    def clear_sessions():
        JetHttpClient._sessions.clear()
        debug_log("[JetHttpClient] Cleared all sessions", xbmc.LOGDEBUG)
