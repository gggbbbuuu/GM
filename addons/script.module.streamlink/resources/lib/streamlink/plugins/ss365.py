import hashlib
import logging
import re
from threading import Event, Thread
from urllib.parse import unquote_plus, urlparse

import websocket

from streamlink import logger
from streamlink.buffers import RingBuffer
from streamlink.plugin import Plugin, PluginArgument, PluginArguments, PluginError
from streamlink.plugin.api import useragents, validate
from streamlink.stream.stream import Stream
from streamlink.stream.stream import StreamIO
from streamlink.utils.url import update_qsd


log = logging.getLogger(__name__)


class SS365(Plugin):
    arguments = PluginArguments(
        PluginArgument(
        "bw",
        argument_name="ss365-bandwidth",
        metavar="BANDWIDTH",
        default=1000000,
        help="""
        The bandwidth in bit/sec.
        Default is 1Mbit/sec.
        """
        )
    )
    _url_re = re.compile(r"http(s)?://sportstream-365.com/viewer\?gameId=(?P<channel>\d+)(?:&tagz=)?", re.VERBOSE)
    _STREAM_INFO_URL = "http://sportstream-365.com/viewer\?gameId={channel}&tagz="
    _STREAM_REAL_URL = "{proto}://{host}/xsport{movie_id}_smooth_1?b={mode}"


    def __init__(self, url):
        Plugin.__init__(self, url)
        match = self._url_re.match(url).groupdict()
        self.channel = match.get("channel")
        self.session.http.headers.update({'User-Agent': useragents.CHROME})

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        #wss://edge1.tvbetstream.com:4433/xsport1049_smooth_1?b=597620
        proto = "wss"
        host = "edge1.tvbetstream.com:4433"
        movie_id = self.channel

        bw = self.options.get("bw")

        if (proto == '') or (host == '') or (not movie_id):
            raise PluginError("No stream available for {}".format(self.channel))

        real_stream_url = self._STREAM_REAL_URL.format(proto=proto, host=host, movie_id=movie_id, mode=bw)

        log.debug("SS365 stream url: {}".format(real_stream_url))

        return {"live": SS365Stream(session=self.session, url=real_stream_url)}


class SS365WsClient(Thread):
    """
    Recieve stream data from SS365 server via WebSocket.
    """
    def __init__(self, url, buffer, proxy=""):
        Thread.__init__(self)
        self.stopped = Event()
        self.url = url
        self.buffer = buffer
        self.proxy = proxy
        self.ws = None

    @staticmethod
    def parse_proxy_url(purl):
        """
        Credit: streamlink/plugins/ustreamtv.py:UHSClient:parse_proxy_url()
        """
        proxy_options = {}
        if purl:
            p = urlparse(purl)
            proxy_options['proxy_type'] = p.scheme
            proxy_options['http_proxy_host'] = p.hostname
            if p.port:
                proxy_options['http_proxy_port'] = p.port
            if p.username:
                proxy_options['http_proxy_auth'] = (unquote_plus(p.username), unquote_plus(p.password or ""))
        return proxy_options

    def stop(self):
        if not self.stopped.wait(0):
            log.debug("Stopping WebSocket client...")
            self.stopped.set()
            self.ws.close()

    def run(self):

        if self.stopped.wait(0):
            return

        def on_message(ws, data):
            if not self.stopped.wait(0):
                try:
                    if data[0] != 7:
                        if data[0] == 1:
                            u = int(''.join(format(x, '02x') for x in data[18:][0:2][::-1]), 16)
                            offset = 20 + u
                        if data[0] == 2:
                            offset = 10
                        self.buffer.write(data[offset:])

                except Exception as err:
                    log.error(err)
                    self.stop()

        def on_error(ws, error):
            log.error(error)

        def on_close(ws):
            log.debug("Disconnected from WebSocket server")

        # Parse proxy string for websocket-client
        proxy_options = self.parse_proxy_url(self.proxy)
        if proxy_options.get('http_proxy_host'):
            log.debug("Connecting to {0} via proxy ({1}://{2}:{3})".format(
                self.url,
                proxy_options.get('proxy_type') or "http",
                proxy_options.get('http_proxy_host'),
                proxy_options.get('http_proxy_port') or 80
            ))
        else:
            log.debug("Connecting to {0} without proxy".format(self.url))

        # Connect to WebSocket server
        self.ws = websocket.WebSocketApp(
            self.url,
            header=["User-Agent: {0}".format(useragents.CHROME)],
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        self.ws.run_forever(origin="http://sportstream-365.com", **proxy_options)


class SS365Reader(StreamIO):
    def __init__(self, stream, timeout=None, **kwargs):
        StreamIO.__init__(self)
        self.stream = stream
        self.session = stream.session
        self.timeout = timeout if timeout else self.session.options.get("stream-timeout")
        self.buffer = None

        if logger.root.level <= logger.DEBUG:
            #websocket.enableTrace(True, log)
            pass

    def open(self):
        # Prepare buffer
        buffer_size = self.session.get_option("ringbuffer-size")
        log.debug("Buffer size: %d" % buffer_size)
        self.buffer = RingBuffer(buffer_size)

        log.debug("Starting WebSocket client")
        self.client = SS365WsClient(
            self.stream.url,
            buffer=self.buffer,
            proxy=self.session.get_option("http-proxy")
        )
        self.client.setDaemon(True)
        self.client.start()

    def close(self):
        self.client.stop()
        self.buffer.close()

    def read(self, size):
        if not self.buffer:
            return b""

        return self.buffer.read(size, block=(not self.client.stopped.wait(0)),
                                timeout=self.timeout)


class SS365Stream(Stream):
    def __init__(self, session, url):
        super().__init__(session)
        self.url = url

    def __repr__(self):
        return "<SS365Stream({0!r})>".format(self.url)

    def open(self):
        reader = SS365Reader(self)
        reader.open()
        return reader


__plugin__ = SS365