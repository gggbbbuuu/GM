"""
$description Live TV channels and video on-demand service from RTVE, a Spanish public, state-owned broadcaster.
$url rtve.es
$type live, vod
$region Spain
"""

import logging
import re
from base64 import b64decode
from io import BytesIO
from urllib.parse import urlparse

from streamlink.plugin import Plugin, PluginArgument, PluginError, PluginArguments, pluginmatcher
from streamlink.utils import parse_json
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream
from streamlink.utils.url import update_scheme

log = logging.getLogger(__name__)


class Base64Reader:
    def __init__(self, data: str):
        stream = BytesIO(b64decode(data))

        def _iterate():
            while True:
                chunk = stream.read(1)
                if len(chunk) == 0:  # pragma: no cover
                    return
                yield ord(chunk)

        self._iterator = _iterate()

    def read(self, num):
        res = []
        for _ in range(num):
            item = next(self._iterator, None)
            if item is None:  # pragma: no cover
                break
            res.append(item)
        return res

    def skip(self, num):
        self.read(num)

    def read_chars(self, num):
        return "".join(chr(item) for item in self.read(num))

    def read_int(self):
        a, b, c, d = self.read(4)
        return a << 24 | b << 16 | c << 8 | d

    def read_chunk(self):
        size = self.read_int()
        chunktype = self.read_chars(4)
        chunkdata = self.read(size)
        if len(chunkdata) != size:  # pragma: no cover
            raise ValueError("Invalid chunk length")
        self.skip(4)
        return chunktype, chunkdata
    
    def __iter__(self):
        self.skip(8)
        while True:
            try:
                yield self.read_chunk()
            except ValueError:
                return


class ZTNR:
    @staticmethod
    def _get_alphabet(text):
        res = []
        j = 0
        k = 0
        for char in text:
            if k > 0:
                k -= 1
            else:
                res.append(char)
                j = (j + 1) % 4
                k = j
        return "".join(res)

    @staticmethod
    def _get_url(text, alphabet):
        res = []
        j = 0
        n = 0
        k = 3
        cont = 0
        for char in text:
            if j == 0:
                n = int(char) * 10
                j = 1
            elif k > 0:
                k -= 1
            else:
                res.append(alphabet[n + int(char)])
                j = 0
                k = cont % 4
                cont += 1
        return "".join(res)

    @classmethod
    def _get_source(cls, alphabet, data):
        return cls._get_url(data, cls._get_alphabet(alphabet))

    @classmethod
    def translate(cls, data):
        reader = Base64Reader(data.replace("\n", ""))
        for chunk_type, chunk_data in reader:
            if chunk_type == "IEND":
                break
            if chunk_type == "tEXt":
                content = "".join(chr(item) for item in chunk_data if item > 0)
                if "#" not in content or "%%" not in content:
                    continue
                alphabet, content = content.split("#", 1)
                quality, content = content.split("%%", 1)
                yield quality, cls._get_source(alphabet, content)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?rtve\.es/play/videos/.+"
))
class Rtve(Plugin):
    arguments = PluginArguments(
        PluginArgument("mux-subtitles", is_global=True),
    )

    URL_M3U8 = "https://ztnr.rtve.es/ztnr/{id}.m3u8"
    URL_VIDEOS = "https://ztnr.rtve.es/ztnr/movil/thumbnail/rtveplayw/videos/{id}.png?q=v2"
    URL_SUBTITLES = "https://www.rtve.es/api/videos/{id}/subtitulos.json"

    def _get_streams(self):
        try:
            _src = self.session.http.get(self.url).text
            _src = re.findall(r"\bdata-setup='({.+?})'", _src, re.DOTALL)[0]
            _src = parse_json(_src)
            assert _src["idAsset"].isnumeric()
            self.id = _src["idAsset"]
        except:
            pass
        if not self.id:
            return
        
        # check obfuscated stream URLs via self.URL_VIDEOS and ZTNR.translate() first
        # self.URL_M3U8 appears to be valid for all streams, but doesn't provide any content in same cases
        try:
            urls = self.session.http.get(self.URL_VIDEOS.format(id=self.id)).text
            urls = list(ZTNR.translate(urls))
            if not urls or len(urls) == 0:
                raise PluginError   
        except PluginError:
            # catch HTTP errors and validation errors, and fall back to generic HLS URL template
            url = self.URL_M3U8.format(id=self.id)
                 
        else:
            url = next((url for _, url in urls if urlparse(url).path.endswith(".m3u8")), None)
            if not url:
                url = next((url for _, url in urls if urlparse(url).path.endswith(".mp4")), None)
                if url:
                    yield "vod", HTTPStream(self.session, url)
                return
        
        streams = HLSStream.parse_variant_playlist(self.session, url).items()

        if self.options.get("mux-subtitles"):
            try:
                _src = self.session.http.get(self.URL_SUBTITLES.format(id=self.id)).text
                subs = parse_json(_src)["page"]["items"]
            except:
                subs = []

            if subs and len(subs) > 0:
                subtitles = {
                    s["lang"]: HTTPStream(self.session, update_scheme("https://", s["src"], force=True))
                    for s in subs
                }
                for quality, stream in streams:
                    yield quality, MuxedStream(self.session, stream, subtitles=subtitles)
                return

        yield from streams


__plugin__ = Rtve