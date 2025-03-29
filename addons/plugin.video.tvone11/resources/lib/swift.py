# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 RACC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import unicode_literals

import os
import time
import json
import requests
from .peewee import SqliteDatabase, Model, IntegerField, TextField, ForeignKeyField, FloatField, chunked
from requests.exceptions import RequestException
from base64 import b64encode
from random import randint
from hashlib import md5
from future.moves.http.cookiejar import LWPCookieJar
from requests.packages.urllib3.util import Retry
from requests.adapters import HTTPAdapter
from warnings import simplefilter

simplefilter("ignore")
""" disable IPv6 """
import socket

old_getaddrinfo = socket.getaddrinfo


def new_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [response for response in responses if response[0] == socket.AF_INET]


socket.getaddrinfo = new_getaddrinfo

db = SqliteDatabase(None)


class BaseModel(Model):
    class Meta:
        database = db


class Token(BaseModel):
    t_id = IntegerField(unique=True)
    token_link = TextField()
    updated = FloatField(default=time.time)


class Category(BaseModel):
    c_id = IntegerField(unique=True)
    c_image = TextField()
    c_name = TextField()
    c_type = TextField()
    updated = FloatField(default=time.time)


class Channel(BaseModel):
    _id = IntegerField(unique=True)
    c_id = TextField()
    title = TextField()
    thumbnail = TextField()
    updated = FloatField(default=time.time)


class Stream(BaseModel):
    _id = IntegerField(unique=True)
    channel_id = ForeignKeyField(Channel, to_field="_id", backref="streams")
    name = TextField()
    stream_url = TextField()
    token = ForeignKeyField(Token, to_field="t_id", backref="streams")
    agent = TextField()
    referer = TextField()


class Video(BaseModel):
    _id = IntegerField(unique=True)
    c_id = TextField()
    title = TextField()
    thumbnail = TextField()
    updated = FloatField(default=time.time)


class VodStream(BaseModel):
    _id = IntegerField(unique=True)
    channel_id = ForeignKeyField(Video, to_field="_id", backref="streams")
    name = TextField()
    stream_url = TextField()
    token = ForeignKeyField(Token, to_field="t_id", backref="streams")
    agent = TextField()
    referer = TextField()


class SwiftStream:
    def __init__(self, cache_dir):
        self.CACHE_TIME = 8 * 60 * 60
        DB = os.path.join(cache_dir, "swift7.db")
        db.init(DB)
        db.connect()
        db.create_tables([Token, Category, Channel, Stream, Video, VodStream], safe=True)
        self.base_url = "https://www.swiftstreamz.cc/SwiftStreamzv2.4/data.php"
        self.user_agent = "Dalvik/2.1.0 (Linux; U; Android 9; AFTSSS Build/PS7223)"
        self.player_user_agent = "Lavf/56.15.102"
        self.s = requests.Session()
        retries = Retry(total=5, backoff_factor=0, status_forcelist=[502, 503, 504])
        retryable_adapter = HTTPAdapter(max_retries=retries)
        self.s.mount("https://", retryable_adapter)
        self.s.mount("http://", retryable_adapter)

    def __del__(self):
        db.close()
        self.s.close()

    def get_post_data(self):
        data = {}
        _hash_int = str(randint(0, 900 - 1))
        _hash_token = bytearray.fromhex(
            "e5b181e882a1e6b7b7e89b8be4bab2e590bbe68891e79a84e9b8a1e5b7b4e4bb96e5a688e79a84"
        )
        _hash_int_bytes = bytearray(_hash_int, "utf-8")
        _hash = md5(_hash_token + _hash_int_bytes).hexdigest()
        data["data"] = _hash_int
        data["hash"] = _hash
        return data

    def api_request(self, url, params=None, data=None, r_json=True):
        headers = {"Connection": "Keep-Alive", "Accept-Encoding": "gzip"}
        if data:
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
            post_data = {"data": b64encode(json.dumps(data, separators=(",", ":")).encode("utf-8"))}
            req = requests.Request("POST", url, headers=headers, params=params, data=post_data)
        else:
            req = requests.Request("GET", url, headers=headers, params=params)
        prepped = self.s.prepare_request(req)
        del prepped.headers["Accept"]
        r = self.s.send(prepped, timeout=10, verify=False)
        r.raise_for_status()
        if r_json:
            return r.json(strict=False)["SWIFTSTREAMZ"]
        else:
            return r.text

    def update_tokens(self):
        tokens = []
        data = self.get_post_data()
        data["method_name"] = "token_data"
        res = self.api_request(self.base_url, data=data)

        def tokens(res):
            for token in res["token_list"]:
                yield {"t_id": token.get("t_id"), "token_link": token.get("token_link")}

        if len(res["token_list"]) > 2:
            with db.atomic():
                Token.delete().execute()
                for batch in chunked(tokens(res), 79):
                    Token.replace_many(batch).execute()

    def update_categories(self):
        self.update_tokens()
        categories = []
        data = self.get_post_data()
        data["method_name"] = "get_category"
        res = self.api_request(self.base_url, data=data)

        def categories(res):
            for c in res:
                yield {
                    "c_id": c.get("c_id"),
                    "c_image": c.get("c_image"),
                    "c_name": c.get("c_name"),
                    "c_type": c.get("c_type"),
                }

        if len(res) > 2:
            with db.atomic():
                Category.delete().execute()
                for batch in chunked(categories(res), 79):
                    Category.replace_many(batch).execute()

    def update_category_videos(self, c_id):
        data = self.get_post_data()
        data["method_name"] = "get_movies"
        data["cat_id"] = c_id
        res = self.api_request(self.base_url, data=data)

        def videos(res):
            for c in res:
                yield {
                    "_id": c.get("id"),
                    "title": c.get("v_title"),
                    "thumbnail": c.get("v_thumbnail"),
                    "c_id": c.get("c_id"),
                }

        def streams(res):
            for c in res:
                for s in c["stream_list"]:
                    yield {
                        "_id": s.get("vod_stream_id"),
                        "channel_id": c.get("id"),
                        "name": s.get("name"),
                        "stream_url": s.get("stream_url"),
                        "token": s.get("token"),
                        "agent": s.get("agent"),
                        "referer": s.get("referer_vod"),
                    }

        if len(res) > 2:
            with db.atomic():
                cat_channels = [v._id for v in Video.select().where(Video.c_id == c_id)]
                VodStream.delete().where(VodStream.channel_id.in_(cat_channels)).execute()
                Video.delete().where(Video.c_id == c_id).execute()
                for batch in chunked(videos(res), 79):
                    Video.replace_many(batch).execute()
                for batch in chunked(streams(res), 79):
                    VodStream.replace_many(batch).execute()

    def update_category_channels(self, c_id):
        data = self.get_post_data()
        data["method_name"] = "get_channels"
        data["cat_id"] = c_id
        res = self.api_request(self.base_url, data=data)

        def channels(res):
            for c in res:
                yield {
                    "_id": c.get("id"),
                    "title": c.get("c_title"),
                    "thumbnail": c.get("c_thumbnail"),
                    "c_id": c.get("c_id"),
                }

        def streams(res):
            for c in res:
                for s in c["stream_list"]:
                    yield {
                        "_id": s.get("stream_id"),
                        "channel_id": c.get("id"),
                        "name": s.get("name"),
                        "stream_url": s.get("stream_url"),
                        "token": s.get("token"),
                        "agent": s.get("agent"),
                        "referer": s.get("referer"),
                    }

        if len(res) > 2:
            with db.atomic():
                cat_channels = [v._id for v in Channel.select().where(Channel.c_id == c_id)]
                Stream.delete().where(Stream.channel_id.in_(cat_channels)).execute()
                Channel.delete().where(Channel.c_id == c_id).execute()
                for batch in chunked(channels(res), 79):
                    Channel.replace_many(batch).execute()
                for batch in chunked(streams(res), 79):
                    Stream.replace_many(batch).execute()

    def get_categories(self):
        categories = Category.select().order_by(Category.c_type)
        if categories.count() == 0:
            self.update_categories()
        else:
            current_time = int(time.time())
            if current_time - int(categories[0].updated) > self.CACHE_TIME:
                try:
                    self.update_categories()
                except (ValueError, RequestException):
                    print("update_categories failed")
        return Category.select().order_by(Category.c_type)

    def get_channels_by_category(self, c_id):
        channels = Channel.select().where(Channel.c_id == c_id)
        if channels.count() == 0:
            self.update_category_channels(c_id)
        else:
            current_time = int(time.time())
            if current_time - int(channels[0].updated) > self.CACHE_TIME:
                try:
                    self.update_category_channels(c_id)
                except (ValueError, RequestException):
                    print("update_category_channels failed")
        return Channel.select().where(Channel.c_id == c_id)

    def get_videos_by_category(self, c_id):
        videos = Video.select().where(Video.c_id == c_id)
        if videos.count() == 0:
            self.update_category_videos(c_id)
        else:
            current_time = int(time.time())
            if current_time - int(videos[0].updated) > self.CACHE_TIME:
                try:
                    self.update_category_videos(c_id)
                except (ValueError, RequestException):
                    print("update_category_videos failed")
        return Video.select().where(Video.c_id == c_id)

    def get_category(self, c_id):
        cat = Category.get(Category.c_id == c_id)
        if cat.c_type == "live":
            return self.get_channels_by_category(c_id)
        else:
            return self.get_videos_by_category(c_id)

    def get_channel_by_id(self, c_id, _id):
        cat = Category.get(Category.c_id == c_id)
        if cat.c_type == "live":
            return Channel.get(Channel._id == _id)
        else:
            return Video.get(Video._id == _id)

    def get_stream_link(self, stream):
        data = self.get_post_data()
        data["method_name"] = "token_data"
        _token = self.api_request(stream.token.token_link, data=data, r_json=False).partition("=")[2]
        auth_token = "".join(
            [_token[:-59], _token[-58:-47], _token[-46:-35], _token[-34:-23], _token[-22:-11], _token[-10:]]
        )
        return ("{0}?wmsAuthSign={1}".format(stream.stream_url, auth_token), {"User-Agent": self.player_user_agent})
