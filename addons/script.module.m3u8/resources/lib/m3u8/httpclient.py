import gzip
import ssl
import urllib.request
from http.cookiejar import CookieJar
from urllib.parse import urljoin
try:
    import certifi
except ImportError:
    certifi = None


class DefaultHTTPClient:
    def __init__(self, proxies=None, cookie_jar=None):
        self.proxies = proxies
        self.cookie_jar = CookieJar() if cookie_jar is None else cookie_jar

    def download(self, uri, timeout=None, headers=None, verify_ssl=True):
        if headers is None:
            header_items = []
        elif isinstance(headers, dict):
            header_items = list(headers.items())
        else:
            header_items = list(headers)

        proxy_handler = urllib.request.ProxyHandler(self.proxies)
        https_handler = HTTPSHandler(verify_ssl=verify_ssl)
        cookie_handler = urllib.request.HTTPCookieProcessor(self.cookie_jar)
        opener = urllib.request.build_opener(proxy_handler, https_handler, cookie_handler)
        opener.addheaders = header_items
        resource = opener.open(uri, timeout=timeout)
        base_uri = urljoin(resource.geturl(), ".")

        encoding = resource.info().get("Content-Encoding", "").lower()
        raw_data = resource.read()
        if encoding == "gzip":
            content = gzip.decompress(raw_data).decode(
                resource.headers.get_content_charset(failobj="utf-8")
            )
        else:
            content = raw_data.decode(
                resource.headers.get_content_charset(failobj="utf-8")
            )
        return content, base_uri


class HTTPSHandler:
    def __new__(self, verify_ssl=True):
        if verify_ssl:
            if certifi:
                try:
                    context = ssl.create_default_context(cafile=certifi.where())
                except Exception:
                    context = ssl.create_default_context()
            else:
                context = ssl.create_default_context()
        else:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return urllib.request.HTTPSHandler(context=context)
