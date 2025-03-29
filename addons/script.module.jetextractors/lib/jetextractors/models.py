from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple
from . import config
import re
import threading
from urllib.parse import urlencode, urlparse
import xbmc, xbmcgui

class JetInputstream:
    inputstream_id: str = "None"

    def set_properties(self, list_item: xbmcgui.ListItem) -> None:
        ...

    
    def to_dict(self) -> dict:
        return {}
    
    
    @staticmethod
    def from_dict(d: dict) -> "JetInputstream":
        if "inputstream_id" not in d:
            return None
        
        if d["inputstream_id"] == JetInputstreamAdaptive.inputstream_id:
            return JetInputstreamAdaptive.from_dict(d)
        elif d["inputstream_id"] == JetInputstreamFFmpegDirect.inputstream_id:
            return JetInputstreamFFmpegDirect.from_dict(d)
        else:
            return None


class JetInputstreamAdaptive(JetInputstream):
    inputstream_id: str = "inputstream.adaptive"
    __mime_type_map: Dict[str, str] = {
        "mpd": "application/dash+xml",
        "hls": "application/vnd.apple.mpegurl", # application/x-mpegURL?
        "ism": "application/vnd.ms-sstr+xml"
    }

    manifest_type: Optional[str]
    manifest_params: Optional[dict]
    manifest_headers: Optional[dict]
    manifest_upd_params: Optional[dict]
    stream_params: Optional[dict]
    stream_headers: Optional[dict]
    manifest_config: Optional[dict]
    play_timeshift_buffer: Optional[bool]
    live_delay: Optional[int]
    original_audio_language: Optional[str]
    config: Optional[dict]
    license_type: Optional[str]
    license_key: Optional[str]

    def __init__(
        self,
        manifest_type: Optional[str] = None,
        manifest_params: Optional[dict] = None,
        manifest_headers: Optional[dict] = None,
        manifest_upd_params: Optional[dict] = None,
        stream_params: Optional[dict] = None,
        stream_headers: Optional[dict] = None,
        manifest_config: Optional[dict] = None,
        play_timeshift_buffer: Optional[bool] = None,
        live_delay: Optional[int] = None,
        original_audio_language: Optional[str] = None,
        config: Optional[dict] = None,
        license_type: Optional[str] = None,
        license_key: Optional[str] = None
    ) -> None:
        self.manifest_type = manifest_type
        self.manifest_params = manifest_params
        self.manifest_headers = manifest_headers
        self.manifest_upd_params = manifest_upd_params
        self.stream_params = stream_params
        self.stream_headers = stream_headers
        self.manifest_config = manifest_config
        self.play_timeshift_buffer = play_timeshift_buffer
        self.live_delay = live_delay
        self.original_audio_language = original_audio_language
        self.config = config
        self.license_type = license_type
        self.license_key = license_key


    @staticmethod
    def widevine(license_key: Optional[str] = None) -> "JetInputstreamAdaptive":
        return JetInputstreamAdaptive("mpd", license_key=license_key)
    

    @staticmethod
    def hls(license_key: Optional[str] = None) -> "JetInputstreamAdaptive":
        return JetInputstreamAdaptive("hls", license_key=license_key)
    

    @staticmethod
    def msready() -> "JetInputstreamAdaptive":
        return JetInputstreamAdaptive("ism")


    def set_properties(self, list_item: xbmcgui.ListItem) -> None:
        kodi_version = int(xbmc.getInfoLabel("System.BuildVersion").split(".")[0])
        list_item.setProperty("inputstream", self.inputstream_id)
        
        if self.manifest_type is not None and kodi_version < 21: list_item.setProperty(f"{self.inputstream_id}.manifest_type", self.manifest_type)
        if self.manifest_params is not None: list_item.setProperty(f"{self.inputstream_id}.manifest_params", self.manifest_params)
        if self.manifest_headers is not None: list_item.setProperty(f"{self.inputstream_id}.manifest_headers", self.manifest_headers)
        if self.manifest_upd_params is not None: list_item.setProperty(f"{self.inputstream_id}.manifest_upd_params", self.manifest_upd_params)
        if self.stream_params is not None: list_item.setProperty(f"{self.inputstream_id}.stream_params", self.stream_params)
        if self.stream_headers is not None: list_item.setProperty(f"{self.inputstream_id}.stream_headers", self.stream_headers)
        if self.manifest_config is not None: list_item.setProperty(f"{self.inputstream_id}.manifest_config", self.manifest_config)
        if self.play_timeshift_buffer is not None: list_item.setProperty(f"{self.inputstream_id}.play_timeshift_buffer", self.play_timeshift_buffer)
        if self.live_delay is not None and kodi_version < 22: list_item.setProperty(f"{self.inputstream_id}.live_delay", self.live_delay)
        if self.original_audio_language is not None: list_item.setProperty(f"{self.inputstream_id}.original_audio_language", self.original_audio_language)
        if self.config is not None: list_item.setProperty(f"{self.inputstream_id}.config", self.config)
        if self.license_type is not None: list_item.setProperty(f"{self.inputstream_id}.license_type", self.license_type)
        if self.license_key is not None: list_item.setProperty(f"{self.inputstream_id}.license_key", self.license_key)

        if self.manifest_type in self.__mime_type_map:
            list_item.setMimeType(self.__mime_type_map[self.manifest_type])
            list_item.setContentLookup(False)
        


class JetInputstreamFFmpegDirect(JetInputstream):
    inputstream_id: str = "inputstream.ffmpegdirect"

    is_realtime_stream: Optional[bool]
    stream_mode: Optional[str]
    open_mode: Optional[str]
    manifest_type: Optional[str]
    default_url: Optional[str]
    playback_as_live: Optional[bool]
    programme_start_time: Optional[int]
    programme_end_time: Optional[int]
    catchup_url_format_string: Optional[str]
    catchup_url_near_live_format_string: Optional[str]
    catchup_buffer_start_time: Optional[int]
    catchup_buffer_end_time: Optional[int]
    catchup_buffer_offset: Optional[int]
    catchup_terminates: Optional[bool]
    catchup_granularity: Optional[int]
    timezone_shift: Optional[int]
    default_programme_duration: Optional[int]
    programme_catchup_id: Optional[str]

    def __init__(
        self,
        is_realtime_stream: Optional[bool] = None,
        stream_mode: Optional[str] = None,
        open_mode: Optional[str] = None,
        manifest_type: Optional[str] = None,
        default_url: Optional[str] = None,
        playback_as_live: Optional[bool] = None,
        programme_start_time: Optional[int] = None,
        programme_end_time: Optional[int] = None,
        catchup_url_format_string: Optional[str] = None,
        catchup_url_near_live_format_string: Optional[str] = None,
        catchup_buffer_start_time: Optional[int] = None,
        catchup_buffer_end_time: Optional[int] = None,
        catchup_buffer_offset: Optional[int] = None,
        catchup_terminates: Optional[bool] = None,
        catchup_granularity: Optional[int] = None,
        timezone_shift: Optional[int] = None,
        default_programme_duration: Optional[int] = None,
        programme_catchup_id: Optional[str] = None
    ) -> None:
        self.is_realtime_stream = is_realtime_stream
        self.stream_mode = stream_mode
        self.open_mode = open_mode
        self.manifest_type = manifest_type
        self.default_url = default_url
        self.playback_as_live = playback_as_live
        self.programme_start_time = programme_start_time
        self.programme_end_time = programme_end_time
        self.catchup_url_format_string = catchup_url_format_string
        self.catchup_url_near_live_format_string = catchup_url_near_live_format_string
        self.catchup_buffer_start_time = catchup_buffer_start_time
        self.catchup_buffer_end_time = catchup_buffer_end_time
        self.catchup_buffer_offset = catchup_buffer_offset
        self.catchup_terminates = catchup_terminates
        self.catchup_granularity = catchup_granularity
        self.timezone_shift = timezone_shift
        self.default_programme_duration = default_programme_duration
        self.programme_catchup_id = programme_catchup_id

    @staticmethod
    def from_dict(d: dict) -> "JetInputstreamFFmpegDirect":
        return JetInputstreamFFmpegDirect(
            is_realtime_stream=d.get("is_realtime_stream"),
            stream_mode=d.get("stream_mode"),
            open_mode=d.get("open_mode"),
            manifest_type=d.get("manifest_type"),
            default_url=d.get("default_url"),
            playback_as_live=d.get("playback_as_live"),
            programme_start_time=d.get("programme_start_time"),
            programme_end_time=d.get("programme_end_time"),
            catchup_url_format_string=d.get("catchup_url_format_string"),
            catchup_url_near_live_format_string=d.get("catchup_url_near_live_format_string"),
            catchup_buffer_start_time=d.get("catchup_buffer_start_time"),
            catchup_buffer_end_time=d.get("catchup_buffer_end_time"),
            catchup_buffer_offset=d.get("catchup_buffer_offset"),
            catchup_terminates=d.get("catchup_terminates"),
            catchup_granularity=d.get("catchup_granularity"),
            timezone_shift=d.get("timezone_shift"),
            default_programme_duration=d.get("default_programme_duration"),
            programme_catchup_id=d.get("programme_catchup_id")
        )


    @staticmethod
    def default() -> "JetInputstreamFFmpegDirect":
        return JetInputstreamFFmpegDirect(manifest_type="hls", is_realtime_stream=True, stream_mode="timeshift")


    def to_dict(self) -> dict:
        d = { "inputstream_id": self.inputstream_id }

        if self.is_realtime_stream is not None: d["is_realtime_stream"] = self.is_realtime_stream
        if self.stream_mode is not None: d["stream_mode"] = self.stream_mode
        if self.open_mode is not None: d["open_mode"] = self.open_mode
        if self.manifest_type is not None: d["manifest_type"] = self.manifest_type
        if self.default_url is not None: d["default_url"] = self.default_url
        if self.playback_as_live is not None: d["playback_as_live"] = self.playback_as_live
        if self.programme_start_time is not None: d["programme_start_time"] = self.programme_start_time
        if self.programme_end_time is not None: d["programme_end_time"] = self.programme_end_time
        if self.catchup_url_format_string is not None: d["catchup_url_format_string"] = self.catchup_url_format_string
        if self.catchup_url_near_live_format_string is not None: d["catchup_url_near_live_format_string"] = self.catchup_url_near_live_format_string
        if self.catchup_buffer_start_time is not None: d["catchup_buffer_start_time"] = self.catchup_buffer_start_time
        if self.catchup_buffer_end_time is not None: d["catchup_buffer_end_time"] = self.catchup_buffer_end_time
        if self.catchup_buffer_offset is not None: d["catchup_buffer_offset"] = self.catchup_buffer_offset
        if self.catchup_terminates is not None: d["catchup_terminates"] = self.catchup_terminates
        if self.catchup_granularity is not None: d["catchup_granularity"] = self.catchup_granularity
        if self.timezone_shift is not None: d["timezone_shift"] = self.timezone_shift
        if self.default_programme_duration is not None: d["default_programme_duration"] = self.default_programme_duration
        if self.programme_catchup_id is not None: d["programme_catchup_id"] = self.programme_catchup_id

        return d

    def set_properties(self, list_item: xbmcgui.ListItem) -> None:
        list_item.setProperty("inputstream", self.inputstream_id)

        if self.is_realtime_stream is not None: list_item.setProperty(f"{self.inputstream_id}.is_realtime_stream", str(self.is_realtime_stream).lower())
        if self.stream_mode is not None: list_item.setProperty(f"{self.inputstream_id}.stream_mode", self.stream_mode)
        if self.open_mode is not None: list_item.setProperty(f"{self.inputstream_id}.open_mode", self.open_mode)
        if self.manifest_type is not None: list_item.setProperty(f"{self.inputstream_id}.manifest_type", self.manifest_type)
        if self.default_url is not None: list_item.setProperty(f"{self.inputstream_id}.default_url", self.default_url)
        if self.playback_as_live is not None: list_item.setProperty(f"{self.inputstream_id}.playback_as_live", self.playback_as_live)
        if self.programme_start_time is not None: list_item.setProperty(f"{self.inputstream_id}.programme_start_time", str(self.programme_start_time))
        if self.programme_end_time is not None: list_item.setProperty(f"{self.inputstream_id}.programme_end_time", str(self.programme_end_time))
        if self.catchup_url_format_string is not None: list_item.setProperty(f"{self.inputstream_id}.catchup_url_format_string", self.catchup_url_format_string)
        if self.catchup_url_near_live_format_string is not None: list_item.setProperty(f"{self.inputstream_id}.catchup_url_near_live_format_string", self.catchup_url_near_live_format_string)
        if self.catchup_buffer_start_time is not None: list_item.setProperty(f"{self.inputstream_id}.catchup_buffer_start_time", str(self.catchup_buffer_start_time))
        if self.catchup_buffer_end_time is not None: list_item.setProperty(f"{self.inputstream_id}.catchup_buffer_end_time", str(self.catchup_buffer_end_time))
        if self.catchup_buffer_offset is not None: list_item.setProperty(f"{self.inputstream_id}.catchup_buffer_offset", str(self.catchup_buffer_offset))
        if self.catchup_terminates is not None: list_item.setProperty(f"{self.inputstream_id}.catchup_terminates", str(self.catchup_terminates).lower())
        if self.catchup_granularity is not None: list_item.setProperty(f"{self.inputstream_id}.catchup_granularity", str(self.catchup_granularity))
        if self.timezone_shift is not None: list_item.setProperty(f"{self.inputstream_id}.timezone_shift", str(self.timezone_shift))
        if self.default_programme_duration is not None: list_item.setProperty(f"{self.inputstream_id}.default_programme_duration", str(self.default_programme_duration))
        if self.programme_catchup_id is not None: list_item.setProperty(f"{self.inputstream_id}.programme_catchup_id", self.programme_catchup_id)

        list_item.setMimeType("application/x-mpegURL")
        list_item.setContentLookup(False)


class JetLink:
    address: str
    headers: Optional[dict]
    params: Optional[dict]
    resolveurl: bool
    jetproxy: bool
    unquote: bool
    name: Optional[str]
    inputstream: Optional[JetInputstream]
    links: bool
    direct: bool


    def __init__(
        self, 
        address: str,
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        resolveurl: bool = False,
        jetproxy: bool = False,
        unquote: bool = True,
        name: Optional[str] = None,
        inputstream: Optional[JetInputstream] = None,
        links: bool = False,
        direct: bool = False
    ) -> None:
        self.address = address
        self.headers = headers
        self.params = params
        self.resolveurl = resolveurl
        self.jetproxy = jetproxy
        self.unquote = unquote
        self.name = name
        self.inputstream = inputstream
        self.links = links
        self.direct = direct

        # Fix name
        if "(" in self.address and self.address.endswith(")"):
            split = self.address.split("(")
            self.address = split[0]
            self.name = split[1][:-1]
    

    def to_dict(self) -> dict:
        res = { "address": self.address }
        if self.headers is not None: res["headers"] = self.headers
        if self.params is not None: res["params"] = self.params
        if self.resolveurl: res["resolveurl"] = self.resolveurl
        if self.jetproxy: res["jetproxy"] = self.jetproxy
        if not self.unquote: res["unquote"] = self.unquote
        if self.name is not None: res["name"] = self.name
        if self.inputstream is not None: res["inputstream"] = self.inputstream.to_dict()
        if self.links: res["links"] = self.links
        if self.direct: res["direct"] = self.direct

        return res
    

    @staticmethod
    def from_dict(d: dict) -> "JetLink":
        link = JetLink(
            address=d["address"],
            headers=d.get("headers"),
            params=d.get("params"),
            resolveurl=d.get("resolveurl", d.get("is_resolveurl", False)),
            jetproxy=d.get("jetproxy", d.get("is_jetproxy", False)),
            unquote=d.get("unquote", True),
            name=d.get("name"),
            inputstream=JetInputstream.from_dict(d.get("inputstream", dict())),
            links=d.get("links", d.get("is_links", False)),
            direct=d.get("direct", d.get("is_direct", False))
        )
        
        # Backwards compatability
        if d.get("is_hls", False):
            link.inputstream = JetInputstreamAdaptive.hls(d.get("license_url"))
        if d.get("is_widevine", False):
            link.inputstream = JetInputstreamAdaptive.widevine(d.get("license_url"))
        if d.get("is_msready", False):
            link.inputstream = JetInputstreamAdaptive.msready()
        if d.get("is_ffmpegdirect", False):
            link.inputstream = JetInputstreamFFmpegDirect.default()

        return link
    

    def xbmc_format(self) -> str:
        link = self.address
        if self.headers is not None and len(self.headers) > 0:
            link += "|" + urlencode(self.headers)
        return link

    
    def __str__(self) -> str:
        return self.address


class JetItem:
    title: str
    links: List[JetLink]
    starttime: Optional[datetime]
    status: Optional[str]
    league: Optional[str]
    icon: Optional[str]
    extractor: Optional[str]
    params: Optional[dict]


    def __init__(
        self,
        title: str,
        links: List[JetLink],
        starttime: Optional[datetime] = None,
        status: Optional[str] = None,
        league: Optional[str] = None,
        icon: Optional[str] = None, 
        extractor: Optional[str] = None,
        params: Optional[dict] = None
    ) -> None:
        self.title = title
        self.links = links
        self.starttime = starttime
        self.status = status
        self.league = league
        self.icon = icon
        self.extractor = extractor
        self.params = params

    @staticmethod
    def from_dict(d: dict) -> "JetItem":
        return JetItem(
            title=d["title"],
            links=[JetLink.from_dict(link) for link in d["links"]],
            starttime=datetime.fromtimestamp(d["starttime"]) if "starttime" in d else None,
            status=d.get("status"),
            league=d.get("league"),
            icon=d.get("icon"),
            extractor=d.get("extractor"),
            params=d.get("params")
        )


class JetExtractorProgress:
    items: Optional[List[JetLink]]
    event: Optional[threading.Event]
    status: Optional[str]
    callback: Optional[Callable[["JetExtractorProgress"], None]]
    start: Optional[datetime]


    def __init__(
        self,
        event: Optional[threading.Event] = None,
        callback: Optional[Callable[["JetExtractorProgress"], None]] = None
    ) -> None:
        self.items = None
        self.event = event
        self.status = None
        self.callback = callback
        self.start = None


class JetExtractor:
    user_agent: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
    timeout: int = 5
    domains: List[str] = []
    domains_regex: bool = False
    name: str = None
    short_name: str = None
    shortener: bool = False
    subclasses = []
    disabled = False
    resolve_only = False


    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls.subclasses.append(cls)


    def get_items(self, params: Optional[dict] = None, progress: Optional[JetExtractorProgress] = None) -> List[JetItem]:
        return []
    

    def get_link(self, url: JetLink) -> JetLink:
        return None
    

    def get_links(self, url: JetLink) -> List[JetLink]:
        return []
    

    def get_config(self) -> dict:
        return config.get_config()
    
    
    def is_available(self, url: JetLink) -> bool:
        url_domain = urlparse(url.address).netloc
        for domain in self.domains:
            if self.domains_regex:
                if re.match(domain, url_domain) is not None:
                    return True
            else:
                if url_domain in domain:
                    return True
        return False
    
    def progress_init(self, progress: Optional[JetExtractorProgress], items: List[JetLink]) -> bool:
        if progress is not None:
            progress.items = items
            progress.start = datetime.now()
        return self.progress_callback(progress)


    def progress_update(self, progress: Optional[JetExtractorProgress], status: Optional[str] = None) -> bool:
        if progress is not None:
            progress.status = status
        return self.progress_callback(progress)


    def progress_callback(self, progress: Optional[JetExtractorProgress]) -> bool:
        if progress is None:
            return False
        if progress.callback is not None:
            progress.callback(progress)
        return progress.event is not None and progress.event.is_set()


class JetExtractorSearchProgress:
    total: int
    links: int
    event: threading.Event
    extractors: Dict[str, JetExtractorProgress]


    def __init__(self) -> None:
        self.total = -1
        self.links = 0
        self.event = threading.Event()
        self.extractors = {}
    