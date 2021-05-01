import sys

from resources.lib.DI import DI
from resources.lib.plugin import run_hook

import resources.lib.plugins

from typing import List

import xbmcgui

root_xml_url = "https://textbin.net/raw/vknsvg0g91"
plugin = DI.plugin

@plugin.route("/")
def root() -> None:
    get_list(root_xml_url)


@plugin.route("/get_list/<path:url>")
def get_list(url: str) -> None:
    _get_list(url)


def _get_list(url):
    response = run_hook("get_list", url)
    jen_list = run_hook("parse_list", url, response)
    jen_list = [run_hook("process_item", item) for item in jen_list]
    jen_list = [
        run_hook("get_metadata", item, return_item_on_failure=True) for item in jen_list
    ]
    run_hook("display_list", jen_list)


@plugin.route("/play_video/<path:video>")
def play_video(video: str):
    import urllib.parse
    video = urllib.parse.unquote_plus(video)
    _play_video(video)


def _play_video(video):
    video = video.replace("'", '"')
    run_hook("play_video", video)


def main():
    plugin.run()
    return 0


if __name__ == "__main__":
    main()
