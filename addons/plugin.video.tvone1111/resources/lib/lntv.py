import os
import time
import uuid
import random
import json
import string
import re
import datetime
from socket import gethostbyname
from base64 import b64decode, b64encode
from itertools import chain
from hashlib import md5
from future.moves.urllib.parse import urljoin, urlparse, parse_qs
from future.builtins import bytes

from .peewee import SqliteDatabase, Model, IntegerField, TextField, chunked, fn, JOIN
import requests

import pyamf
from pyamf import remoting
from pyamf.flex import messaging

from Cryptodome.Cipher import AES, DES
from Cryptodome.Util.Padding import pad, unpad
from Cryptodome.Random import get_random_bytes
import warnings

warnings.simplefilter("ignore")
db = SqliteDatabase(None, pragmas={"foreign_keys": 1})


class BaseModel(Model):
    class Meta:
        database = db


class Config(BaseModel):
    data_age = IntegerField(default=time.time)
    updated = IntegerField()
    api_url = TextField()
    api_referer = TextField()
    token_url_19 = TextField()
    token_url_21 = TextField()
    token_url_23 = TextField()
    token_url_33 = TextField()
    token_url_34 = TextField()
    token_url_38 = TextField()
    token_url_44 = TextField()
    token_url_45 = TextField()
    token_url_48 = TextField()
    token_url_51 = TextField()
    token_url_52 = TextField()
    token_url_54 = TextField()


class User(BaseModel):
    device_id = TextField(default=uuid.uuid4)
    device_name = TextField(default="Amazon AFTN")
    android_id = TextField(default=uuid.uuid4().hex[:16])
    api_level = TextField(default="28")
    apk_name = TextField(default="com.playnet.androidtv.ads")
    apk_cert = TextField(default="34:33:F9:0E:F5:E3:4A:39:8D:16:20:8E:B7:5E:AA:3F:00:75:97:7A")
    apk_version = TextField(default="4.9 (54)")
    apk_build = TextField(default="54")
    provider = TextField(default="3")
    user_id = TextField(default="")
    channels_updated = IntegerField(default=0)
    vod_updated = IntegerField(default=0)


class LiveCategory(BaseModel):
    cat_id = IntegerField(primary_key=True)
    cat_name = TextField()


class LiveChannel(BaseModel):
    cat_id = IntegerField()
    channel_id = IntegerField(primary_key=True)
    country_id = IntegerField(null=True)
    country_priority = IntegerField(null=True)
    country_name = TextField(null=True)
    image_path = TextField(null=True)
    name = TextField()


class LiveStream(BaseModel):
    channel_id = IntegerField()
    stream_id = IntegerField(primary_key=True)
    token = IntegerField(null=True)
    url = TextField(null=True)
    quality = TextField(null=True)
    user_agent = TextField(null=True)
    referer = TextField(null=True)
    player_headers = TextField(null=True)
    player_referer = TextField(null=True)
    player_user_agent = TextField(null=True)


class VodCategory(BaseModel):
    cat_id = IntegerField(primary_key=True)
    cat_name = TextField()


class VodChannel(BaseModel):
    cat_id = IntegerField()
    channel_id = IntegerField(primary_key=True)
    image_path = TextField(null=True)
    name = TextField()
    print_quality = TextField(null=True)
    release_date = TextField(null=True)
    release_year = TextField(null=True)


class VodStream(BaseModel):
    channel_id = IntegerField()
    stream_id = IntegerField(primary_key=True)
    token = IntegerField(null=True)
    url = TextField(null=True)
    quality = TextField(null=True)
    user_agent = TextField(null=True)
    referer = TextField(null=True)
    player_headers = TextField(null=True)
    player_referer = TextField(null=True)
    player_user_agent = TextField(null=True)


class LiveEvents(BaseModel):
    updated = IntegerField()
    events = TextField()


class LnTv(object):
    def __init__(self, cache_dir, cert, cert_key):
        self.live_implemented = [0, 19, 23, 33, 38, 44, 48, 51, 52]
        self.vod_implemented = [21]
        self.server_time = str(int(time.time()) * 1000)
        self.api_key = None
        self.rapi_key = None
        self.api_url = "https://iris.livenettv.io/data/6/"
        self.user_agent = "Dalvik/2.1.0 (Linux; U; Android 9; AFTM Build/LMY47O)"
        self.player_user_agent = "Lavf/57.83.100"
        self.post_ct = "application/x-www-form-urlencoded; charset=UTF-8"
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": self.user_agent, "Accept-Encoding": "gzip"})
        self.s.cert = (cert, cert_key)
        self.s.verify = False
        DB = os.path.join(cache_dir, "lntv5.db")
        db.init(DB)
        db.connect()
        db.create_tables(
            [Config, User, LiveCategory, LiveChannel, LiveStream, VodCategory, VodChannel, VodStream, LiveEvents],
            safe=True,
        )
        if Config.select().where(Config.data_age + 8 * 60 * 60 > int(time.time())).count() == 0:
            try:
                self.config = self.update_config()
            except requests.exceptions.RequestException:
                self.config = Config.select()[0]
                _next_update = self.config.data_age + 60 * 60
                self.config.data_age = _next_update
                self.config.save()
        else:
            self.config = Config.select()[0]

        if User.select().count() == 0:
            self.user = self.register_user()
        else:
            self.user = User.select()[0]

    def __del__(self):
        db.close()
        self.s.close()

    @staticmethod
    def dec_aes_cbc_single(msg, key, iv):
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        return unpad(cipher.decrypt(b64decode(msg)), 16).decode("utf-8")

    @staticmethod
    def enc_aes_cbc_single(msg, key, iv):
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        return b64encode(cipher.encrypt(pad(msg.encode("utf-8"), 16)))

    @staticmethod
    def enc_aes_cbc_rand(plain_bytes):
        rand_key = get_random_bytes(32)
        rand_iv = get_random_bytes(16)
        rand_cipher = AES.new(rand_key, AES.MODE_CBC, iv=rand_iv)
        c_bytes = rand_cipher.encrypt(pad(plain_bytes, 16))
        return b64encode(rand_key + rand_iv + c_bytes)

    @staticmethod
    def ct_b64dec(encoded):
        custom_translate = bytes.maketrans(
            b"mlkjihgfedcbaZYXWVUTSRQPONMLKJIHGFEDCBA9876543210+zyxwvutsrqpon/",
            b"QRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/ABCDEFGHIJKLMNOP",
        )
        return b64decode(encoded.encode("utf-8").translate(custom_translate)).decode("utf-8")

    @staticmethod
    def c1_b64dec(encoded):
        return b64decode(encoded[1:]).decode("utf-8")

    @staticmethod
    def modified_header():
        return "".join(list(chain(*zip(str(int(time.time()) ^ 1234567), "0123456789"))))

    @staticmethod
    def modified2_header():
        s1 = [random.choice(string.digits), random.choice(string.digits), random.choice(string.digits)]
        s2 = [random.choice(string.digits), random.choice(string.digits), random.choice(string.digits)]
        return "".join(s1 + list(chain(*zip(str(int(time.time()) ^ 1234567), "0123456789"))) + s2)

    @staticmethod
    def fix_auth_date(auth):
        now = datetime.datetime.utcnow()
        _in = list(auth)
        _in.pop(len(_in) - (1 + now.year // 100))
        _in.pop(len(_in) - (1 + now.year % 100))
        _in.pop(len(_in) - (1 + now.month + 10))
        _in.pop(len(_in) - (1 + now.day))
        return "".join(_in)

    @staticmethod
    def resolve_stream_host(stream):
        _parsed = urlparse(stream[0])
        _host = _parsed.netloc.split(":")
        _host[0] = gethostbyname(_host[0])
        _resolved = _parsed._replace(netloc=":".join(_host)).geturl()
        stream[1]["!Host"] = _parsed.netloc
        return (_resolved, stream[1])

    def fetch_config(self):
        url = "https://api.backendless.com/762F7A10-3072-016F-FF64-33280EE6EC00/E9A27666-CD62-10CD-FF05-ED45B12ABE00/binary"
        msg = messaging.RemotingMessage(
            clientId=None,
            destination="GenericDestination",
            correlationId=None,
            source="com.backendless.services.persistence.PersistenceService",
            operation="first",
            messageRefType=None,
            headers={"application-type": "ANDROID", "api-version": "1.0"},
            timestamp=0,
            body=["ConfigEchoAdsN"],
            timeToLive=0,
            messageId=None,
        )
        request_form = remoting.Envelope(pyamf.AMF3)
        request_form["null"] = remoting.Request(target="null", body=[msg])
        r = self.s.post(
            url,
            data=remoting.encode(request_form).getvalue(),
            headers={"Content-Type": "application/x-amf"},
            verify=False,
        )
        r.raise_for_status()
        res = remoting.decode(r.content)
        return res.bodies[0][1].body.body

    def update_config(self):
        new_config = self.fetch_config()
        if Config.select().count() > 0:
            old_config = Config.select()[0]
            if old_config.updated == int(time.mktime(new_config["updated"].timetuple())):
                old_config.data_age = int(time.time())
                old_config.save()
                return old_config
        cc_key = self.c1_b64dec(new_config["QXBwX2ludmVudG9y"])
        key = self.dec_aes_cbc_single(cc_key, b"fwewokemlesdsdsd", b"\00" * 16).encode("utf-8")
        iv = b"896C5F41D8F2A22A"

        Config.delete().execute()
        config = Config()
        config.updated = int(time.mktime(new_config["updated"].timetuple()))
        config.api_url = self.dec_aes_cbc_single(new_config["YXBpS2V5TGluazQ2"], key, iv)
        config.api_referer = self.c1_b64dec(new_config["SXNpc2VrZWxvX3Nlc2lzdGltdV95ZXppbm9tYm9sbzAw"])
        config.token_url_19 = self.dec_aes_cbc_single(new_config["eW9va2F5X09zbm92bmFfcG90"], key, iv)
        config.token_url_21 = self.dec_aes_cbc_single(new_config["Y2FsYWFtb19pa3Mw"], key, iv)
        config.token_url_23 = self.dec_aes_cbc_single(new_config["dGhlX3RlYXMw"], key, iv)
        config.token_url_33 = self.dec_aes_cbc_single(new_config["ZmFtYW50YXJhbmFfdGF0aTAw"], key, iv)
        config.token_url_34 = self.dec_aes_cbc_single(new_config["ZGVjcnlwdGV1cl9MaWVu"], key, iv)
        config.token_url_38 = self.dec_aes_cbc_single(new_config["YmVsZ2lfMzgw"], key, iv)
        config.token_url_44 = self.dec_aes_cbc_single(new_config["YmVsa2lpdW1uXzk2"], key, iv)
        config.token_url_45 = self.dec_aes_cbc_single(new_config["bmdhZGVrcmlwUGF0YWxpbmFzazQ1"], key, iv)
        config.token_url_48 = self.dec_aes_cbc_single(new_config["Ym9ya3lsd3VyXzQ4"], key, iv)
        config.token_url_51 = self.dec_aes_cbc_single(new_config["cHJlZmVjdHVyZTUx"], key, iv)
        config.token_url_52 = self.dec_aes_cbc_single(new_config["d2lsYXlhaDUx"], key, iv)
        config.token_url_54 = self.dec_aes_cbc_single(new_config["Ym9rYXJpc2hvbDc3"], key, iv)
        config.save()
        return config

    def cache_token(self, user):
        index = random.randint(0, 9)
        token = [
            self.server_time,
            md5(user.apk_name.encode("utf-8")).hexdigest()[index : index + 16],
            md5(user.apk_cert.encode("utf-8")).hexdigest()[index + 2 : index + 2 + 12],
            md5(self.server_time.encode("utf-8")).hexdigest(),
            str(index),
            "",
        ]
        token1 = self.enc_aes_cbc_single("$".join(token), b"q4trc3t4kj23vtmw", b"\00" * 16)
        return self.enc_aes_cbc_rand(token1)

    def id_token(self, user):
        ms_time = str(int(time.time() * 1000))
        token_1 = [
            user.api_level.encode("utf-8"),
            b64encode(user.apk_build.encode("utf-8")),
            b64encode(ms_time.encode("utf-8")),
            b64encode("null".encode("utf-8")),
            b64encode(str(user.device_id).encode("utf-8")),
        ]
        token = [
            md5(ms_time.encode("utf-8")).hexdigest().encode("utf-8"),
            b64encode(user.apk_name.encode("utf-8")),
            b64encode(user.apk_cert.encode("utf-8")),
            b64encode(user.device_name.encode("utf-8")),
            b64encode(b"|".join(token_1)),
        ]
        return b64encode(b"|".join(token)).decode("utf-8")

    def allow_token(self, user):
        ms_time = str(int(time.time()) * 1000)
        token = [
            md5(ms_time.encode("utf-8")).hexdigest(),
            user.apk_name,
            user.apk_cert,
            ms_time,
            user.user_id,
            user.provider,
        ]
        return b64encode("$".join(token).encode("utf-8"))

    def events_allow_token(self, user):
        ms_time = str(int(time.time()) * 1000)
        token = [
            md5(ms_time.encode("utf-8")).hexdigest(),
            user.apk_name,
            user.apk_cert,
            ms_time,
            user.user_id,
            user.apk_build,
        ]
        return b64encode("$".join(token).encode("utf-8"))

    def get_api_key(self, user):
        r = self.s.get(self.config.api_url)
        r.raise_for_status()
        self.server_time = str(int(time.time()) * 1000)
        headers = {
            "Content-Type": self.post_ct,
            "Cache-Control": self.cache_token(user),
            "ALLOW": self.allow_token(user),
        }
        r = self.s.post(self.config.api_url, headers=headers, timeout=15)
        r.raise_for_status()

        if "MTag" in r.headers:
            tag_key = r.headers["MTag"].split(":")
            self.api_key = tag_key[0]
            self.api_stamp, self.api_url = b64decode(tag_key[1]).decode("utf-8").split("|")
            self.rapi_key = r.json(strict=False).get("funguo")
            return self.api_key

    def register_user(self):
        user = User()
        self.get_api_key(user)
        post_data = {
            "device_id": "unknown",
            "key": self.rapi_key,
            "device_name": user.device_name,
            "device_type": "0,0,",
            "type_detection": "0,0,0,0,0,0,0,0,0,0,",
            "api_level": user.api_level,
            "version": user.apk_version,
            "id": self.id_token(user),
            "time": self.server_time,
            "android_id": user.android_id,
            "pro": "true",
        }
        post_dump = json.dumps(post_data, separators=(",", ":")).encode("utf-8")
        data = {"_": self.enc_aes_cbc_rand(post_dump)}
        headers = {"Content-Type": self.post_ct, "Referer": self.config.api_referer}
        r = self.s.post(urljoin(self.api_url, "adduserinfo.nettv/"), headers=headers, data=data, timeout=15)
        r.raise_for_status()
        res = r.json()
        if "user_id" in res:
            user.user_id = res.get("user_id")

        user.save()
        return user

    def fetch_live_events(self):
        data = {"ALLOW": self.events_allow_token(self.user)}
        headers = {"Content-Type": self.post_ct}
        r = self.s.post(urljoin(self.api_url, "live.nettv/"), headers=headers, data=data, timeout=15)
        r.raise_for_status()
        return r.text

    def get_live_events(self):
        if LiveEvents.select().where(LiveEvents.updated + 10 * 60 > int(time.time())).count() == 0:
            LiveEvents.delete().execute()
            new_events = LiveEvents()
            new_events.events = self.fetch_live_events()
            new_events.updated = int(time.time())
            new_events.save()
            return json.loads(new_events.events, strict=False)
        else:
            return json.loads(LiveEvents.select()[0].events, strict=False)

    def fetch_vod_channels(self):
        if not self.api_key:
            self.get_api_key(self.user)

        data = {"key": self.rapi_key, "check": "5", "user_id": self.user.user_id, "version": self.user.apk_build}
        headers = {"Content-Type": self.post_ct, "Meta": self.api_key, "Referer": self.config.api_referer}
        r = self.s.post(urljoin(self.api_url, "vods.nettv/"), headers=headers, data=data, timeout=15)
        r.raise_for_status()
        return r.json()

    def update_vod_channels(self):
        if self.user.vod_updated + 30 * 60 * 60 < int(time.time()):
            res = self.fetch_vod_channels()
            self.user.vod_updated = int(time.time())
            self.user.save()
            print("vod_updated: " + str(self.user.vod_updated))
        else:
            print("vod_old: " + str(self.user.vod_updated))
            return

        def categories(res):
            for category in res["categories_list"]:
                yield {"cat_id": category["cat_id"], "cat_name": category["cat_name"]}

        def channels(res):
            for channel in res["eY2hhbm5lbHNfbGlzdA=="]:
                yield {
                    "cat_id": channel["cat_id"],
                    "channel_id": int(b64decode(channel["rY19pZA=="][:-1])),
                    "image_path": b64decode(channel.get("abG9nb191cmw=")[1:]),
                    "name": b64decode(channel.get("ZY19uYW1l")[:-1]),
                    "print_quality": channel.get("print_quality"),
                    "release_date": channel.get("release_date"),
                    "release_year": channel.get("release_year"),
                }

        def streams(res):
            for channel in res["eY2hhbm5lbHNfbGlzdA=="]:
                for stream in channel["Qc3RyZWFtX2xpc3Q="]:
                    yield {
                        "channel_id": int(b64decode(channel["rY19pZA=="][:-1])),
                        "stream_id": int(b64decode(stream["cc3RyZWFtX2lk"][:-1])),
                        "token": int(b64decode(stream["AdG9rZW4="][:-1])),
                        "url": b64decode(stream.get("Bc3RyZWFtX3VybA==")[1:]),
                        "quality": stream.get("quality"),
                        "user_agent": stream.get("user_agent"),
                        "referer": stream.get("referer"),
                        "player_headers": stream.get("player_headers"),
                        "player_referer": stream.get("player_referer"),
                        "player_user_agent": stream.get("player_user_agent"),
                    }

        with db.atomic():
            VodCategory.delete().execute()
            VodChannel.delete().execute()
            VodStream.delete().execute()
            for batch in chunked(categories(res), 79):
                VodCategory.replace_many(batch).execute()
            for batch in chunked(channels(res), 79):
                VodChannel.replace_many(batch).execute()
            for batch in chunked(streams(res), 79):
                VodStream.replace_many(batch).execute()

    def fetch_live_channels(self):
        if not self.api_key:
            self.get_api_key(self.user)

        post_data = {
            "key": self.rapi_key,
            "user_id": self.user.user_id,
            "version": self.user.apk_build,
            "check": "22",
            "time": self.server_time,
            "pro": "true",
        }
        post_dump = json.dumps(post_data, separators=(",", ":")).encode("utf-8")
        data = {"_": self.enc_aes_cbc_rand(post_dump)}
        headers = {"Content-Type": self.post_ct, "Meta": self.api_key, "Referer": self.config.api_referer}
        r = self.s.post(urljoin(self.api_url, "list.nettv/"), headers=headers, data=data, timeout=15)
        r.raise_for_status()
        return r.json()

    def update_live_channels(self):
        if self.user.channels_updated + 8 * 60 * 60 < int(time.time()):
            res = self.fetch_live_channels()
            self.user.channels_updated = int(time.time())
            self.user.save()
            print("live_updated: " + str(self.user.channels_updated))
        else:
            print("live_old: " + str(self.user.channels_updated))
            return

        def categories(res):
            for category in res["categories_list"]:
                yield {"cat_id": category["cat_id"], "cat_name": category["cat_name"]}

        def channels(res):
            for channel in res["eY2hhbm5lbHNfbGlzdA=="]:
                yield {
                    "cat_id": channel["cat_id"],
                    "channel_id": channel["rY19pZA=="],
                    "country_id": channel.get("country_id"),
                    "country_name": channel.get("country_name"),
                    "country_priority": channel.get("country_priority"),
                    "image_path": self.ct_b64dec(channel.get("abG9nb191cmw=")[1:]),
                    "name": self.ct_b64dec(channel.get("ZY19uYW1l")),
                }

        def streams(res):
            for channel in res["eY2hhbm5lbHNfbGlzdA=="]:
                for stream in channel["Qc3RyZWFtX2xpc3Q="]:
                    yield {
                        "channel_id": channel["rY19pZA=="],
                        "stream_id": stream["cc3RyZWFtX2lk"],
                        "token": stream.get("AdG9rZW4=", "0"),
                        "url": self.ct_b64dec(stream.get("Bc3RyZWFtX3VybA==")[1:]),
                        "quality": stream.get("quality"),
                        "user_agent": stream.get("user_agent"),
                        "referer": stream.get("referer"),
                        "player_headers": stream.get("player_headers"),
                        "player_referer": stream.get("player_referer"),
                        "player_user_agent": stream.get("player_user_agent"),
                    }

        with db.atomic():
            LiveCategory.delete().execute()
            LiveChannel.delete().execute()
            LiveStream.delete().execute()
            for batch in chunked(categories(res), 79):
                LiveCategory.replace_many(batch).execute()
            for batch in chunked(channels(res), 79):
                LiveChannel.replace_many(batch).execute()
            for batch in chunked(streams(res), 79):
                LiveStream.replace_many(batch).execute()

    def get_vod_categories(self):
        return VodCategory.select().order_by(VodCategory.cat_id)

    def get_vod_channels_by_category(self, cat_id):
        return (
            VodChannel.select(VodChannel)
            .join(VodStream, JOIN.LEFT_OUTER, on=(VodStream.channel_id == VodChannel.channel_id))
            .where((VodChannel.cat_id == cat_id) & (VodStream.token << self.vod_implemented))
            .group_by(VodChannel)
            .order_by(fn.Lower(VodChannel.name))
        )

    def get_vodstreams_by_channel_id(self, channel_id):
        return (
            VodStream.select(VodStream, VodChannel)
            .join(VodChannel, on=(VodChannel.channel_id == VodStream.channel_id))
            .where((VodStream.channel_id == channel_id) & (VodStream.token << self.vod_implemented))
            .order_by(VodStream.token)
        )

    def get_live_categories(self):
        return LiveCategory.select().order_by(LiveCategory.cat_id)

    def get_live_channels_by_category(self, cat_id):
        return (
            LiveChannel.select(LiveChannel)
            .join(LiveStream, JOIN.LEFT_OUTER, on=(LiveStream.channel_id == LiveChannel.channel_id))
            .where((LiveChannel.cat_id == cat_id) & (LiveStream.token << self.live_implemented))
            .group_by(LiveChannel)
            .order_by(LiveChannel.country_priority, fn.Lower(LiveChannel.name))
        )

    def get_streams_by_channel_id(self, channel_id):
        return (
            LiveStream.select(LiveStream, LiveChannel)
            .join(LiveChannel, on=(LiveChannel.channel_id == LiveStream.channel_id))
            .where((LiveStream.channel_id == channel_id) & (LiveStream.token << self.live_implemented))
            .order_by(LiveStream.token)
        )

    def get_streams_by_channel_name(self, name):
        return (
            LiveStream.select(LiveStream, LiveChannel)
            .join(LiveChannel, on=(LiveChannel.channel_id == LiveStream.channel_id))
            .where((LiveChannel.name == name) & (LiveStream.token << self.live_implemented))
            .order_by(LiveStream.token)
        )

    def get_live_link(self, link):
        data = {"v": parse_qs(urlparse(link).query)["id"][0], "ALLOW": self.events_allow_token(self.user)}
        headers = {"Content-Type": self.post_ct}
        r = self.s.post(link, headers=headers, data=data, timeout=15)
        r.raise_for_status()
        return json.loads(b64decode(r.text.strip()[3:]).decode("utf-8"))

    def resolve_stream(self, stream):
        headers = {}
        if stream.user_agent:
            headers["User-Agent"] = stream.user_agent
        else:
            headers["User-Agent"] = self.user_agent
        if stream.referer:
            headers["Referer"] = stream.referer

        player_headers = {}
        if stream.player_user_agent:
            player_headers["User-Agent"] = stream.player_user_agent
        else:
            player_headers["User-Agent"] = self.player_user_agent
        if stream.player_referer:
            player_headers["Referer"] = stream.player_referer

        if stream.token == 0:
            """direct (168)"""
            return (stream.url, player_headers)
        elif stream.token == 4:
            """mak regex ? (6)"""
            pass
        elif stream.token == 18:
            """simple m3u8 regex (138)"""
            r = self.s.get(stream.url, headers=headers, timeout=15)
            r.raise_for_status()
            m3u8 = re.search("['\"](http[^\"']*m3u8[^\"']*)", r.text).group(1)
            return (m3u8, player_headers)
        elif stream.token == 19:
            """tvmob / tvtap / uktvnow (78)"""
            l, h, d, k = stream.url.split("|")[:4]
            h = h.split(",")
            headers = dict(zip(h[::2], h[1::2]))
            d = d.split(",")
            data = dict(zip(d[::2], d[1::2]))
            headers["User-Agent"] = stream.user_agent
            r = self.s.post(l, headers=headers, data=data, timeout=15)
            r.raise_for_status()
            res = r.json()
            if res["success"]:
                for ch in res["msg"]["channel"]:
                    _crypt_link = ch[k]
                    d = DES.new(b"98221122", DES.MODE_ECB)
                    link = unpad(d.decrypt(b64decode(_crypt_link)), 8).decode("utf-8")
                    return self.resolve_stream_host((link, player_headers))

            modified = self.modified_header()
            headers = {"Modified": modified, "Content-Type": self.post_ct}
            data = {"plaintext": _crypt_link, "time": modified, "type": ""}
            r = self.s.post(self.config.token_url_19, headers=headers, data=data, timeout=15)
            r.raise_for_status()
            return self.resolve_stream_host((r.text, player_headers))
        elif stream.token == 21:
            """VOD"""
            _split_url = stream.url.split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            data = {"_": stream_id}
            headers = {
                "Public-Key-Pins": b64encode(self.user.user_id.encode("utf-8")),
                "Modified": self.modified_header(),
                "Content-Type": self.post_ct,
            }
            r = self.s.post(self.config.token_url_21, headers=headers, data=data, timeout=15)
            r.raise_for_status()

            key = "wecq" + self.user.user_id[1:5] + self.user_agent[-8:]
            iv = self.user_agent[-8:] + "beps" + self.user.user_id[1:5]

            res = self.dec_aes_cbc_single(r.text, key.encode("utf-8"), iv.encode("utf-8"))
            host = b64decode(r.headers["Session"]).decode("utf-8").split("$")
            _split_url[2], _split_url[-3], _split_url[-2] = host
            return ("{0}{1}".format("/".join(_split_url), res), player_headers)
        elif stream.token == 22:
            """ebound.tv (5)"""
            pass
        elif stream.token == 23:
            """main hera: CA & USA Live TV (32) (dyna.livenettv.sx:21321)"""
            _split_url = stream.url.split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            data = {"_": stream_id}
            headers = {
                "Public-Key-Pins": b64encode(self.user.user_id.encode("utf-8")),
                "Modified": self.modified_header(),
                "Content-Type": self.post_ct,
            }
            r = self.s.post(self.config.token_url_23, headers=headers, data=data, timeout=15)
            r.raise_for_status()

            key = "wecq" + self.user.user_id[1:5] + self.user_agent[-8:]
            iv = self.user_agent[-8:] + "beps" + self.user.user_id[1:5]

            res = self.dec_aes_cbc_single(r.text, key.encode("utf-8"), iv.encode("utf-8"))
            host = b64decode(r.headers["Session"]).decode("utf-8").split("$")
            _split_url[2], _split_url[-3], _split_url[-2] = host
            return ("{0}{1}".format("/".join(_split_url), res), player_headers)

        elif stream.token == 29:
            """nettvusa arconai ? (16)"""
            pass
        elif stream.token == 30:
            """ar? dead? (2)"""
            pass
        elif stream.token == 31:
            """livenettv~be~atv (1)"""
            pass
        elif stream.token == 33:
            """main (306) (can.lnt.sh)"""

            def fix_auth(auth):
                return "".join([auth[:-108], auth[-107:-50], auth[-49:-42], auth[-41:-34], auth[-33:]])

            _split_url = stream.url.split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            data = {"_": stream_id}
            headers = {
                "Public-Key-Pins": b64encode(self.user.user_id.encode("utf-8")),
                "Modified": self.modified_header(),
                "Content-Type": self.post_ct,
            }
            r = self.s.post(self.config.token_url_33, headers=headers, data=data, timeout=15)
            r.raise_for_status()

            key = "pvsd" + self.user.user_id[1:5] + self.user_agent[-8:]
            iv = self.user_agent[-8:] + "werb" + self.user.user_id[1:5]

            res = self.dec_aes_cbc_single(r.text, key.encode("utf-8"), iv.encode("utf-8"))
            host = b64decode(r.headers["Session"]).decode("utf-8").split("$")
            _split_url[2], _split_url[-3], _split_url[-2] = host
            return ("{0}{1}".format("/".join(_split_url), fix_auth(res)), player_headers)

        elif stream.token == 34:
            """fetch callback (19)"""
            page_url = b64decode(stream.url[1:]).decode("utf-8").split("|")[0]
            headers["User-Agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                " (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
            )
            player_headers["User-Agent"] = headers["User-Agent"]
            page_r = self.s.get(page_url, headers=headers, timeout=15, verify=False)
            page_r.raise_for_status()
            data = {"stream_url": stream.url, "token": "34", "response_body": page_r.text}
            data = {"data": json.dumps(data, separators=(",", ":"))}
            headers = {"Modified": self.modified_header(), "Content-Type": self.post_ct}
            r = self.s.post(self.config.token_url_34, headers=headers, data=data, timeout=15)
            r.raise_for_status()
            return (r.json().get("stream_url"), player_headers)
        elif stream.token == 36:
            """transponder.tv (8)"""
            pass
        elif stream.token == 38:
            """main (233) (pod.lnt.sh)"""

            def fix_auth(auth):
                return "".join([auth[:-63], auth[-62:-56], auth[-55:-46], auth[-45:-36], auth[-35:]])

            _split_url = stream.url.split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            data = {"_": stream_id}
            headers = {
                "Public-Key-Pins": b64encode(self.user.user_id.encode("utf-8")),
                "Modified": self.modified_header(),
                "Content-Type": self.post_ct,
            }
            r = self.s.post(self.config.token_url_38, headers=headers, data=data, timeout=15)
            r.raise_for_status()

            key = "jygh" + self.user.user_id[1:5] + self.user_agent[-8:]
            iv = self.user_agent[-8:] + "vsdc" + self.user.user_id[1:5]

            res = self.dec_aes_cbc_single(r.text, key.encode("utf-8"), iv.encode("utf-8"))
            host = b64decode(r.headers["Session"]).decode("utf-8").split("$")
            _split_url[2], _split_url[-3], _split_url[-2] = host
            return ("{0}{1}".format("/".join(_split_url), fix_auth(res)), player_headers)
        elif stream.token == 42:
            """crichd (21)"""
            pass
        elif stream.token == 43:
            """psl (1)"""
            pass
        elif stream.token == 44:
            """main (645) (dna.lnt.sh)"""
            _split_url = stream.url.split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            data = {"_": stream_id}
            headers = {
                "Public-Key-Pins": b64encode(self.user.user_id.encode("utf-8")),
                "Modified": self.modified_header(),
                "Content-Type": self.post_ct,
            }
            r = self.s.post(self.config.token_url_44, headers=headers, data=data, timeout=15)
            r.raise_for_status()

            key = "psdz" + self.user.user_id[1:5] + self.user_agent[-8:]
            iv = self.user_agent[-8:] + "vgpe" + self.user.user_id[1:5]

            res = self.dec_aes_cbc_single(r.text, key.encode("utf-8"), iv.encode("utf-8"))
            host = b64decode(r.headers["Session"]).decode("utf-8").split("$")
            _split_url[2], _split_url[-3], _split_url[-2] = host
            return ("{0}{1}".format("/".join(_split_url), self.fix_auth_date(res)), player_headers)
        elif stream.token == 45:
            """callback (wstream) (0)"""
            link = b64decode(stream.url[1:]).decode("utf-8").split("|")
            headers["User-Agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                " (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
            )
            _header = link[1].split(",")
            headers[_header[0]] = _header[1]
            page_r = self.s.get(link[0], headers=headers, timeout=15, verify=False)
            page_r.raise_for_status()
            data = {"stream_url": stream.url, "token": stream.token, "docs": [page_r.text]}
            data = {"data": json.dumps(data, separators=(",", ":"))}
            headers = {"Content-Type": self.post_ct}
            r = self.s.post(self.config.token_url_45, headers=headers, data=data, timeout=15)
            r.raise_for_status()
            return (r.json()["stream_url"], player_headers)
        elif stream.token == 48:
            """main (289) (mnp.lnt.sh)"""
            _split_url = stream.url.split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            data = {"_": stream_id}
            headers = {
                "Public-Key-Pins": b64encode(self.user.user_id.encode("utf-8")),
                "Modified": self.modified2_header(),
                "Content-Type": self.post_ct,
            }
            r = self.s.post(self.config.token_url_48, headers=headers, data=data, timeout=15)
            r.raise_for_status()

            key = "mtds" + self.user.user_id[1:5] + self.user_agent[-8:]
            iv = self.user_agent[-8:] + "cndr" + self.user.user_id[1:5]

            res = self.dec_aes_cbc_single(r.text, key.encode("utf-8"), iv.encode("utf-8"))
            host = b64decode(r.headers["Session"]).decode("utf-8").split("$")
            _split_url[2], _split_url[-3], _split_url[-2] = host
            return ("{0}{1}".format("/".join(_split_url), self.fix_auth_date(res)), player_headers)

        elif stream.token == 50:
            """yupptv.com (21)"""
            pass
        elif stream.token == 51:
            """mirror (36)"""
            _split_url = stream.url.split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            headers = {
                "Public-Key-Pins": b64encode(".".join([self.user.user_id, stream_id]).encode("utf-8")),
                "Modified": self.modified_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            }
            r = self.s.post(self.config.token_url_51, headers=headers, data="", timeout=15)
            r.raise_for_status()

            key = self.user.user_id[1:6] + "gouk" + self.user_agent[-7:]
            iv = self.user_agent[-8:] + "atyi" + self.user.user_id[1:5]
            res = self.dec_aes_cbc_single(r.text, key.encode("utf-8"), iv.encode("utf-8"))
            host = b64decode(r.headers["Session"]).decode("utf-8")
            return ("{0}{1}".format(stream.url.replace("$", host), self.fix_auth_date(res)), player_headers)
        elif stream.token == 52:
            """mirror (40)"""
            _split_url = stream.url.split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            headers = {
                "Public-Key-Pins": b64encode(".".join([self.user.user_id, stream_id]).encode("utf-8")),
                "Modified": self.modified_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            }
            r = self.s.post(self.config.token_url_52, headers=headers, data="", timeout=15)
            r.raise_for_status()

            key = self.user.user_id[1:6] + "gouk" + self.user_agent[-7:]
            iv = self.user_agent[-8:] + "atyi" + self.user.user_id[1:5]
            res = self.dec_aes_cbc_single(r.text, key.encode("utf-8"), iv.encode("utf-8"))
            host = b64decode(r.headers["Session"]).decode("utf-8")
            return ("{0}{1}".format(stream.url.replace("$", host), self.fix_auth_date(res)), player_headers)

        elif stream.token == 53:
            """http://$:8554/tv/bein2/playlist.m3u8 (1)"""
            pass
        elif stream.token == 54:
            """cobra sport 240p (3)"""
            _split_url = stream.url.split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            r = self.s.post(self.config.token_url_52, headers=headers, data="", timeout=15)
            r.raise_for_status()

            _pattern = re.compile("<script>([^<]+)</script>", re.M)
            _split = re.search(_pattern, r.text).group(1).strip().split("\n")
            _upperCase = urlparse(self.config.token_url_54).path.split("/")[1].upper()
            _c = ord(_upperCase[0]) - ord("@")
            _s2 = _split[ord(_upperCase[(len(_upperCase) - 1)]) - ord("@") - 1].split("?")[1]
            _n = len(_s2) - 1
            _in = list(_s2)
            _in.pop(2 + _n - (_c + 3))
            _in.pop(3 + _n - (_c + 11))
            _in.pop(4 + _n - (_c + 19))
            _in.pop(5 + _n - (_c + 27))

            host = b64decode(r.headers["Session"]).decode("utf-8")
            return ("{0}?{1}".format(stream.url.replace("$", host), "".join(_in)), player_headers)
        elif stream.token == 56:
            """jagobd.com (45)"""
            pass
        elif stream.token == 57:
            """regex hdcast.me (1)"""
            pass
        elif stream.token == 58:
            """youtube (55)"""
            pass
        elif stream.token == 69:
            """ICC (3)"""
            pass
