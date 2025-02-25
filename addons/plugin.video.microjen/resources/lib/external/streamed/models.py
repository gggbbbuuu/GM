from dataclasses import dataclass, field, asdict
from typing import Union, Dict, List
from urllib.parse import urlencode, urlparse, parse_qsl

ICON = "https://funstersplace.net/19repo/plugin.video.sportscentral/icon.png"
FANART = "https://funstersplace.net/19repo/plugin.video.sportscentral/fanart.jpg"

@dataclass
class Item:
    title: str = 'Unknown Title'
    type: str = 'item'
    mode: str = ''
    link: str = ''
    thumbnail: str = ICON
    fanart: str = FANART
    summary: str = ''
    content: str = 'video'
    title2: str = ''
    tv_show_title: str = ''
    year: Union[int, str] = 0
    tmdb_id: Union[str, int] = ''
    imdb_id: str = ''
    season: Union[str, int] = 0
    episode: Union[str, int] = 0
    list_title: str = ''
    page_token: str = ''
    duration: int = 0
    infolabels: Dict[str, Union[str, int]] = field(default_factory=dict)
    cast: List[Dict[str, str]] = field(default_factory=list)
    page: int = 1
    is_playable: bool = False
    set_resolved: bool = False
    
    def to_dict(self) -> Dict:
        # Convert the dataclass to a dictionary and remove falsy values
        return {k: v for k, v in asdict(self).items() if v}
    
    def full_dict(self) -> Dict:
        return asdict(self)
    
    def url_encode(self) -> str:
        # Encode the dataclass attributes into a URL-encoded string
        return urlencode(self.to_dict())


@dataclass
class YoutubePlaylist(Item):
    def __post_init__(self):
        self.type = 'dir'
        self.mode = 'yt_playlist'


@dataclass
class YoutubeItem(Item):
    def __post_init__(self):
        self.mode = 'play_video'
        if not self.link.startswith('plugin://'):
            if self.link.startswith('http'):
                url_parsed = urlparse(self.link)
                video_id = ''
                query = dict(parse_qsl(url_parsed.query))
                path = url_parsed.path
                if 'v' in query:
                    video_id = query['v']
                else:
                    video_id = path.split('/')[-1]
                # Handle cases where video_id is still empty
                if video_id:
                    self.link = f'plugin://plugin.video.youtube/play/?video_id={video_id}'
            else:
                self.link = f'plugin://plugin.video.youtube/play/?video_id={self.link}'
                