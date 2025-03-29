import os, requests, time, random, uuid, json, re, datetime, string
from urllib.parse import urlparse, urlencode, urljoin, parse_qs
from base64 import b64decode, b64encode
import xbmcaddon
from hashlib import md5
from xbmcvfs import translatePath
from itertools import chain
from collections import OrderedDict

import pyamf
from pyamf import remoting
from pyamf.flex import messaging

from ..models import *

try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad
    from Cryptodome.Random import get_random_bytes
except:
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad, unpad
        from Crypto.Random import get_random_bytes
    except:
        pass


class LNTV(JetExtractor):
    json_config = {}
    api_url = "https://iris.livenettv.io/data/5/"
    player_user_agent = "Lavf/57.83.100"
    api_key = False

    def __init__(self) -> None:
        self.domains = ["lntv.com"]
        self.name = "LNTV"
        self.short_name = "LNTV"
        self.user_agent = "Dalvik/2.1.0 (Linux; U; Android 5.1; AFTM Build/LMY47O)"
        self.resolve_only = True

    def get_link(self, url: JetLink) -> JetLink:
        self.init_config()
        channel_id = url.address.replace("https://lntv.com/play/", "")
        channel = list(filter(lambda x: x["channel_id"] == channel_id, self.json_config["live_channels"]))[0]
        stream = channel["streams"][0]
        resolved_stream = self.resolve_stream(stream)
        return JetLink(address=resolved_stream[0], headers=resolved_stream[1])
    

    def dec_aes_cbc_single(self, msg, key, iv):
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        return unpad(cipher.decrypt(msg), 16)

    def enc_aes_cbc_single(self, msg, key, iv):
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        return b64encode(cipher.encrypt(pad(msg.encode("utf-8"), 16)))

    def enc_aes_cbc_rand(self, plain_bytes):
        rand_key = get_random_bytes(32)
        rand_iv = get_random_bytes(16)
        rand_cipher = AES.new(rand_key, AES.MODE_CBC, iv=rand_iv)
        c_bytes = rand_cipher.encrypt(pad(plain_bytes, 16))
        return b64encode(rand_key + rand_iv + c_bytes)

    def custom_base64(self, encoded):
        custom_translate = bytes.maketrans(
            b"mlkjihgfedcbaZYXWVUTSRQPONMLKJIHGFEDCBA9876543210+zyxwvutsrqpon/",
            b"QRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/ABCDEFGHIJKLMNOP",
        )
        return b64decode(encoded.encode("utf-8").translate(custom_translate)).decode("utf-8")
    
    def init_config(self):
        addon = xbmcaddon.Addon()
        USER_DATA_DIR = translatePath(addon.getAddonInfo("profile"))
        ADDON_DATA_DIR = translatePath(addon.getAddonInfo("path"))
        RESOURCES_DIR = os.path.join(ADDON_DATA_DIR, "resources")
        if self.json_config != {}: return
        cert_file = os.path.join(RESOURCES_DIR, "com.playnet.androidtv.ads.crt")
        cert_key_file = os.path.join(RESOURCES_DIR, "com.playnet.androidtv.ads.key")
        self.s = requests.Session()
        self.s.cert = (cert_file, cert_key_file)
        self.s.headers.update({"User-Agent": self.user_agent})
        self.server_time = str(int(time.time()) * 1000)
        config = os.path.join(USER_DATA_DIR, "lntv_config.json")
        if not os.path.exists(config):
            self.fetch_config()
            self.register_user()
            self.update_vod_channels()
            self.update_live_channels()
            self.write_config()
        else:
            f = open(config)
            json_config = json.loads(f.read())
            f.close()
            self.json_config = json_config
            if time.time() - json_config["data_age"] > 8 * 60 * 60:
                self.fetch_config()
                self.update_vod_channels()
                self.update_live_channels()
                self.write_config()
    
    def fetch_config(self):
        def b64x2(s):
            return b64decode(b64decode(s[1:]).decode("utf-8"))

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
            body=["ConfigEchoCDN"],
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
        res = remoting.decode(r.content).bodies[0][1].body.body

        key_name = "QXBwX2ludmVudG9y"
        key_key = b"fwewokemlesdsdsd"
        key_iv = b"\00" * 16

        config_key = self.dec_aes_cbc_single(b64x2(res[key_name]), key_key, key_iv)
        config_iv = b"896C5F41D8F2A22A"

        self.json_config["updated"] = int(time.mktime(res["updated"].timetuple()))
        self.json_config["api_url"] = self.dec_aes_cbc_single(
            b64decode(res["YXBpS2V5TGluazQ2"]), config_key, config_iv
        ).decode("utf-8")
        self.json_config["api_referer"] = b64decode(res["SXNpc2VrZWxvX3Nlc2lzdGltdV95ZXppbm9tYm9sbzAw"][1:]).decode("utf-8")
        self.json_config["token_url_21"] = self.dec_aes_cbc_single(
            b64decode(res["Y2FsYWFtb19pa3Mw"]), config_key, config_iv
        ).decode("utf-8")
        self.json_config["token_url_23"] = self.dec_aes_cbc_single(
            b64decode(res["dGhlX3RlYXMw"]), config_key, config_iv
        ).decode("utf-8")
        self.json_config["token_url_33"] = self.dec_aes_cbc_single(
            b64decode(res["ZmFtYW50YXJhbmFfdGF0aTAw"]), config_key, config_iv
        ).decode("utf-8")
        self.json_config["token_url_34"] = self.dec_aes_cbc_single(
            b64decode(res["ZGVjcnlwdGV1cl9MaWVu"]), config_key, config_iv
        ).decode("utf-8")
        self.json_config["token_url_38"] = self.dec_aes_cbc_single(
            b64decode(res["YmVsZ2lfMzgw"]), config_key, config_iv
        ).decode("utf-8")
        self.json_config["token_url_44"] = self.dec_aes_cbc_single(
            b64decode(res["YmVsa2lpdW1uXzk2"]), config_key, config_iv
        ).decode("utf-8")
        self.json_config["token_url_45"] = self.dec_aes_cbc_single(
            b64decode(res["bmdhZGVrcmlwUGF0YWxpbmFzazQ1"]), config_key, config_iv
        ).decode("utf-8")
        self.json_config["token_url_48"] = self.dec_aes_cbc_single(
            b64decode(res["Ym9ya3lsd3VyXzQ4"]), config_key, config_iv
        ).decode("utf-8")
        self.json_config["token_url_51"] = self.dec_aes_cbc_single(
            b64decode(res["cHJlZmVjdHVyZTUx"]), config_key, config_iv
        ).decode("utf-8")
        self.json_config["token_url_52"] = self.dec_aes_cbc_single(
            b64decode(res["d2lsYXlhaDUx"]), config_key, config_iv
        ).decode("utf-8")
        self.json_config["token_url_54"] = self.dec_aes_cbc_single(
            b64decode(res["Ym9rYXJpc2hvbDc3"]), config_key, config_iv
        ).decode("utf-8")
    
    def write_config(self):
        addon = xbmcaddon.Addon()
        USER_DATA_DIR = translatePath(addon.getAddonInfo("profile"))
        if not os.path.exists(USER_DATA_DIR):
            os.makedirs(USER_DATA_DIR)
        config = os.path.join(USER_DATA_DIR, "lntv_config.json")
        self.json_config["data_age"] = time.time()
        f = open(config, "w")
        f.write(json.dumps(self.json_config))
        f.close()
    
    def cache_token(self, user):
        index = random.randint(0, 9)
        token = [
            self.server_time,
            md5(user["apk_name"].encode("utf-8")).hexdigest()[index : index + 16],
            md5(user["apk_cert"].encode("utf-8")).hexdigest()[index + 2 : index + 2 + 12],
            md5(self.server_time.encode("utf-8")).hexdigest(),
            str(index),
            "",
        ]
        token1 = self.enc_aes_cbc_single("$".join(token), b"q4trc3t4kj23vtmw", b"\00" * 16)
        return self.enc_aes_cbc_rand(token1)

    def id_token(self, user):
        ms_time = str(int(time.time() * 1000))
        token_1 = [
            user["api_level"].encode("utf-8"),
            b64encode(user["apk_build"].encode("utf-8")),
            b64encode(ms_time.encode("utf-8")),
            b64encode("null".encode("utf-8")),
            b64encode(str(user["device_id"]).encode("utf-8")),
        ]
        token = [
            md5(ms_time.encode("utf-8")).hexdigest().encode("utf-8"),
            b64encode(user["apk_name"].encode("utf-8")),
            b64encode(user["apk_cert"].encode("utf-8")),
            b64encode(user["device_name"].encode("utf-8")),
            b64encode(b"|".join(token_1)),
        ]
        return b64encode(b"|".join(token)).decode("utf-8")

    def allow_token(self, user):
        ms_time = str(int(time.time()) * 1000)
        token = [
            md5(ms_time.encode("utf-8")).hexdigest(),
            user["apk_name"],
            user["apk_cert"],
            ms_time,
            user["user_id"],
            user["provider"]
        ]
        return b64encode("$".join(token).encode("utf-8"))

    def events_allow_token(self, user):
        ms_time = str(int(time.time()) * 1000)
        token = [
            md5(ms_time.encode("utf-8")).hexdigest(),
            user["apk_name"],
            user["apk_cert"],
            ms_time,
            user["user_id"],
            user["apk_build"]
        ]
        return b64encode("$".join(token).encode("utf-8"))

    def get_api_key(self, user):
        headers = OrderedDict(
            [("Accept-Encoding", "gzip"), ("User-Agent", self.user_agent), ("Connection", "Keep-Alive")]
        )
        req = requests.Request("GET", self.json_config["api_url"])
        prepped = req.prepare()
        prepped.headers = headers
        r = self.s.send(prepped, timeout=15, verify=False)
        r.raise_for_status()
        self.server_time = str(int(time.time()) * 1000)

        headers = OrderedDict(
            [
                ("Accept-Encoding", "gzip"),
                ("User-Agent", self.user_agent),
                ("Cache-Control", self.cache_token(user)),
                ("ALLOW", self.allow_token(user)),
                ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"),
                ("Connection", "Keep-Alive"),
                ("Content-Length", "0"),
            ]
        )
        req = requests.Request("POST", self.json_config["api_url"])
        prepped = req.prepare()
        prepped.headers = headers
        r = self.s.send(prepped, timeout=15, verify=False)
        r.raise_for_status()

        if "MTag" in r.headers:
            tag_key = r.headers["MTag"].split(":")
            self.api_key = tag_key[0]
            self.api_stamp, self.api_url = b64decode(tag_key[1]).decode("utf-8").split("|")
            self.rapi_key = r.json(strict=False).get("funguo")
            return self.api_key
    
    def register_user(self):
        user = {
            "device_id": uuid.uuid4().hex,
            "device_name": "Amazon AFTN",
            "android_id": uuid.uuid4().hex[:16],
            "api_level": "28",
            "apk_name": "com.playnet.androidtv.ads",
            "apk_cert": "34:33:F9:0E:F5:E3:4A:39:8D:16:20:8E:B7:5E:AA:3F:00:75:97:7A",
            "apk_version": "4.8.6 (51)",
            "apk_build": "51",
            "provider": "3",
            "user_id": "",
            "channels_updated": 0,
            "vod_updated": 0
        }
        self.get_api_key(user)
        post_data = {
            "device_id": "unknown",
            "key": self.rapi_key,
            "device_name": user["device_name"],
            "api_level": user["api_level"],
            "version": user["apk_version"],
            "id": self.id_token(user),
            "time": self.server_time,
            "android_id": user["android_id"],
            "state": "{}",
            "pro": "true",
        }
        post_dump = json.dumps(post_data, separators=(",", ":")).encode("utf-8")
        post_encoded = urlencode({"_": self.enc_aes_cbc_rand(post_dump)})
        content_length = len(post_encoded)
        headers = OrderedDict(
            [
                ("Referer", self.json_config["api_referer"]),
                ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"),
                ("User-Agent", self.user_agent),
                ("Connection", "Keep-Alive"),
                ("Accept-Encoding", "gzip"),
                ("Content-Length", str(content_length)),
            ]
        )
        req = requests.Request("POST", urljoin(self.api_url, "adduserinfo.nettv/"), data=post_encoded)
        prepped = self.s.prepare_request(req)
        prepped.headers = headers
        r = self.s.send(prepped, timeout=15, verify=False)
        r.raise_for_status()
        res = r.json()
        if "user_id" in res:
            user["user_id"] = res.get("user_id")

        self.json_config["user"] = user
        return user
    
    def fetch_live_events(self):
        post_data = {"ALLOW": self.events_allow_token(self.json_config["user"])}
        post_encoded = urlencode(post_data)
        content_length = len(post_encoded)
        headers = OrderedDict(
            [
                ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"),
                ("User-Agent", self.user_agent),
                ("Connection", "Keep-Alive"),
                ("Accept-Encoding", "gzip"),
                ("Content-Length", str(content_length)),
            ]
        )
        req = requests.Request("POST", urljoin(self.api_url, "live.nettv/"), data=post_encoded)
        prepped = self.s.prepare_request(req)
        prepped.headers = headers
        r = self.s.send(prepped, timeout=15, verify=False)
        r.raise_for_status()
        return r.text
    
    def fetch_vod_channels(self):
        if not self.api_key:
            self.get_api_key(self.json_config["user"])

        post_data = {
            "key": self.rapi_key,
            "check": "5",
            "user_id": self.json_config["user"]["user_id"],
            "version": self.json_config["user"]["apk_build"],
        }
        post_encoded = urlencode(post_data)
        content_length = len(post_encoded)
        headers = OrderedDict(
            [
                ("Referer", self.json_config["api_referer"]),
                ("Meta", self.api_key),
                ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"),
                ("User-Agent", self.user_agent),
                ("Connection", "Keep-Alive"),
                ("Accept-Encoding", "gzip"),
                ("Content-Length", str(content_length)),
            ]
        )
        req = requests.Request("POST", urljoin(self.api_url, "vods.nettv/"), data=post_encoded)
        prepped = self.s.prepare_request(req)
        prepped.headers = headers
        r = self.s.send(prepped, timeout=15, verify=False)
        r.raise_for_status()
        return r.json()
    
    def update_vod_channels(self):
        if self.json_config["user"]["vod_updated"] + 30 * 60 * 60 < int(time.time()):
            res = self.fetch_vod_channels()
            self.json_config["user"]["vod_updated"] = int(time.time())
        else:
            return

        categories = [{"cat_id": category["cat_id"], "cat_name": category["cat_name"]} for category in res["categories_list"]]
        channels = [{
            "cat_id": int(channel["cat_id"]),
            "channel_id": int(b64decode(channel["rY19pZA=="][:-1])),
            "image_path": b64decode(channel.get("abG9nb191cmw=")[1:]).decode("utf-8"),
            "name": b64decode(channel.get("ZY19uYW1l")[:-1]).decode("utf-8"),
            "print_quality": channel.get("print_quality"),
            "release_date": channel.get("release_date"),
            "release_year": channel.get("release_year"),
            "streams": [{
                "channel_id": int(b64decode(channel["rY19pZA=="][:-1])),
                "stream_id": int(b64decode(stream["cc3RyZWFtX2lk"][:-1])),
                "token": int(b64decode(stream["AdG9rZW4="][:-1])),
                "url": b64decode(stream.get("Bc3RyZWFtX3VybA==")[1:]).decode("utf-8"),
                "quality": stream.get("quality"),
                "user_agent": stream.get("user_agent"),
                "referer": stream.get("referer"),
                "player_headers": stream.get("player_headers"),
                "player_referer": stream.get("player_referer"),
                "player_user_agent": stream.get("player_user_agent"),
            } for stream in channel["Qc3RyZWFtX2xpc3Q="]]
        } for channel in res["eY2hhbm5lbHNfbGlzdA=="]]

        self.json_config["vod_categories"] = categories
        self.json_config["vod_channels"] = channels
    
    def fetch_live_channels(self):
        if not self.api_key:
            self.get_api_key(self.json_config["user"])

        post_data = {
            "key": self.rapi_key,
            "user_id": self.json_config["user"]["user_id"],
            "version": self.json_config["user"]["apk_build"],
            "check": "18",
            "time": self.server_time,
            "state": "{}",
            "pro": "true",
        }
        post_dump = json.dumps(post_data, separators=(",", ":")).encode("utf-8")
        post_encoded = urlencode({"_": self.enc_aes_cbc_rand(post_dump)})
        content_length = len(post_encoded)
        headers = OrderedDict(
            [
                ("Referer", self.json_config["api_referer"]),
                ("Meta", self.api_key),
                ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"),
                ("User-Agent", self.user_agent),
                ("Connection", "Keep-Alive"),
                ("Accept-Encoding", "gzip"),
                ("Content-Length", str(content_length)),
            ]
        )
        req = requests.Request("POST", urljoin(self.api_url, "list.nettv/"), data=post_encoded)
        prepped = self.s.prepare_request(req)
        prepped.headers = headers
        r = self.s.send(prepped, timeout=15, verify=False)
        r.raise_for_status()
        return r.json()
    
    def update_live_channels(self):
        if self.json_config["user"]["channels_updated"] + 8 * 60 * 60 < int(time.time()):
            res = self.fetch_live_channels()
            self.json_config["user"]["channels_updated"] = int(time.time())
        else:
            return

        categories = [{"cat_id": int(category["cat_id"]), "cat_name": category["cat_name"]} for category in res["categories_list"]]
        channels = [{
            "cat_id": int(channel["cat_id"]),
            "channel_id": channel["rY19pZA=="],
            "country_id": channel.get("country_id"),
            "country_name": channel.get("country_name"),
            "country_priority": channel.get("country_priority"),
            "image_path": self.custom_base64(channel.get("abG9nb191cmw=")[1:]),
            "name": self.custom_base64(channel.get("ZY19uYW1l")),
            "streams": [{
                "channel_id": channel["rY19pZA=="],
                "stream_id": stream["cc3RyZWFtX2lk"],
                "token": int(stream.get("AdG9rZW4=", "0")),
                "url": self.custom_base64(stream.get("Bc3RyZWFtX3VybA==")[1:]),
                "quality": stream.get("quality"),
                "user_agent": stream.get("user_agent"),
                "referer": stream.get("referer"),
                "player_headers": stream.get("player_headers"),
                "player_referer": stream.get("player_referer"),
                "player_user_agent": stream.get("player_user_agent"),
            } for stream in channel["Qc3RyZWFtX2xpc3Q="]]
        } for channel in res["eY2hhbm5lbHNfbGlzdA=="]]

        self.json_config["live_categories"] = categories
        self.json_config["live_channels"] = channels
    
    def resolve_stream(self, stream):
        headers = {}
        if stream["user_agent"]:
            headers["User-Agent"] = stream["user_agent"]
        else:
            headers["User-Agent"] = self.user_agent
        if stream["referer"]:
            headers["Referer"] = stream["referer"]

        player_headers = {}
        if stream["player_user_agent"]:
            player_headers["User-Agent"] = stream["player_user_agent"]
        else:
            player_headers["User-Agent"] = self.player_user_agent
        if stream["player_referer"]:
            player_headers["Referer"] = stream["player_referer"]

        if stream["token"] == 0:
            """ direct (168) """
            return (stream["url"], player_headers)
        elif stream["token"] == 4:
            """ mak regex ? (7) """
            pass
        elif stream["token"] == 18:
            """ simple m3u8 regex (142) """
            r = self.s.get(stream["url"], headers=headers, timeout=15, verify=False)
            r.raise_for_status()
            m3u8 = re.search("['\"](http[^\"']*m3u8[^\"']*)", r.text).group(1)
            return (m3u8, player_headers)
        elif stream["token"] == 19:
            """ tvtap / uktvnow (90) """
            pass
        elif stream["token"] == 22:
            """ ebound.tv (7) """
            pass
        elif stream["token"] == 21:
            """ VOD """

            def modified_header():
                value = 1234567
                return "".join(list(chain(*zip(str(int(time.time()) ^ value), "0123456789"))))

            _split_url = stream["url"].split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            post_encoded = urlencode({"_": stream_id})

            headers = OrderedDict(
                [
                    ("Public-Key-Pins", b64encode(self.json_config["user"]["user_id"].encode("utf-8"))),
                    ("Modified", modified_header()),
                    ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"),
                    ("User-Agent", self.user_agent),
                    ("Connection", "Keep-Alive"),
                    ("Accept-Encoding", "gzip"),
                    ("Content-Length", str(len(post_encoded))),
                ]
            )
            req = requests.Request("POST", self.json_config["token_url_21"], data=post_encoded)
            prepped = req.prepare()
            prepped.headers = headers
            r = self.s.send(prepped, timeout=15, verify=False)
            r.raise_for_status()

            key = "wecq" + self.json_config["user"]["user_id"][1:5] + self.user_agent[-8:]
            iv = self.user_agent[-8:] + "beps" + self.json_config["user"]["user_id"][1:5]

            res = self.dec_aes_cbc_single(b64decode(r.text), key.encode("utf-8"), iv.encode("utf-8")).decode("utf-8")
            host = b64decode(r.headers["Session"]).decode("utf-8").split("$")
            _split_url[2], _split_url[-3], _split_url[-2] = host
            return (
                "{0}{1}".format("/".join(_split_url), res),
                player_headers,
            )
        elif stream["token"] == 22:
            """ ebound.tv (6) """
            pass
        elif stream["token"] == 23:
            """ main hera: CA & USA Live TV (70) """

            def modified_header():
                value = 1234567
                return "".join(list(chain(*zip(str(int(time.time()) ^ value), "0123456789"))))

            _split_url = stream["url"].split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            post_encoded = urlencode({"_": stream_id})

            headers = OrderedDict(
                [
                    ("Public-Key-Pins", b64encode(self.json_config["user"]["user_id"].encode("utf-8"))),
                    ("Modified", modified_header()),
                    ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"),
                    ("User-Agent", self.user_agent),
                    ("Connection", "Keep-Alive"),
                    ("Accept-Encoding", "gzip"),
                    ("Content-Length", str(len(post_encoded))),
                ]
            )
            req = requests.Request("POST", self.json_config["token_url_23"], data=post_encoded)
            prepped = req.prepare()
            prepped.headers = headers
            r = self.s.send(prepped, timeout=15, verify=False)
            r.raise_for_status()

            key = "wecq" + self.json_config["user"]["user_id"][1:5] + self.user_agent[-8:]
            iv = self.user_agent[-8:] + "beps" + self.json_config["user"]["user_id"][1:5]

            res = self.dec_aes_cbc_single(b64decode(r.text), key.encode("utf-8"), iv.encode("utf-8")).decode("utf-8")
            host = b64decode(r.headers["Session"]).decode("utf-8").split("$")
            _split_url[2], _split_url[-3], _split_url[-2] = host
            return (
                "{0}{1}".format("/".join(_split_url), res),
                player_headers,
            )

        elif stream["token"] == 29:
            """ nettvusa arconai ? (16) """
            pass
        elif stream["token"] == 30:
            """ ar? dead? (2) """
            pass
        elif stream["token"] == 31:
            """ livenettv~be~atv (1)"""
            pass
        elif stream["token"] == 32:
            """ psl (5) """
            pass
        elif stream["token"] == 33:
            """ main (401) """

            def fix_auth(auth):
                return "".join([auth[:-108], auth[-107:-50], auth[-49:-42], auth[-41:-34], auth[-33:]])

            def modified_header():
                value = 1234567
                return "".join(list(chain(*zip(str(int(time.time()) ^ value), "0123456789"))))

            _split_url = stream["url"].split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            post_encoded = urlencode({"_": stream_id})
            headers = OrderedDict(
                [
                    ("Public-Key-Pins", b64encode(self.json_config["user"]["user_id"].encode("utf-8"))),
                    ("Modified", modified_header()),
                    ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"),
                    ("User-Agent", self.user_agent),
                    ("Connection", "Keep-Alive"),
                    ("Accept-Encoding", "gzip"),
                    ("Content-Length", str(len(post_encoded))),
                ]
            )

            req = requests.Request("POST", self.json_config["token_url_33"], data=post_encoded)
            prepped = req.prepare()
            prepped.headers = headers
            r = self.s.send(prepped, timeout=15, verify=False)
            r.raise_for_status()

            key = "pvsd" + self.json_config["user"]["user_id"][1:5] + self.user_agent[-8:]
            iv = self.user_agent[-8:] + "werb" + self.json_config["user"]["user_id"][1:5]

            res = self.dec_aes_cbc_single(b64decode(r.text), key.encode("utf-8"), iv.encode("utf-8")).decode("utf-8")
            host = b64decode(r.headers["Session"]).decode("utf-8").split("$")
            _split_url[2], _split_url[-3], _split_url[-2] = host
            return (
                "{0}{1}".format("/".join(_split_url), fix_auth(res)),
                player_headers,
            )

        elif stream["token"] == 34:
            """ fetch callback (19) """

            def modified_header():
                value = 1234567
                return "".join(list(chain(*zip(str(int(time.time()) ^ value), "0123456789"))))

            page_url = b64decode(stream["url"][1:]).decode("utf-8").split("|")[0]
            headers[
                "User-Agent"
            ] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
            player_headers["User-Agent"] = headers["User-Agent"]
            page_r = self.s.get(page_url, headers=headers, timeout=15, verify=False)
            page_r.raise_for_status()
            data = {"stream_url": stream["url"], "token": "34", "response_body": page_r.text}
            post_encoded = urlencode({"data": json.dumps(data, separators=(",", ":"))})
            headers = OrderedDict(
                [
                    ("Modified", modified_header()),
                    ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"),
                    ("User-Agent", self.user_agent),
                    ("Connection", "Keep-Alive"),
                    ("Accept-Encoding", "gzip"),
                    ("Content-Length", str(len(post_encoded))),
                ]
            )
            req = requests.Request("POST", self.json_config["token_url_34"], data=post_encoded)
            prepped = req.prepare()
            prepped.headers = headers
            r = self.s.send(prepped, timeout=15, verify=False)
            r.raise_for_status()
            return (r.json().get("stream_url"), player_headers)
        elif stream["token"] == 36:
            """ transponder.tv (8) """
            pass
        elif stream["token"] == 38:
            """ main (242) """

            def fix_auth(auth):
                return "".join([auth[:-63], auth[-62:-56], auth[-55:-46], auth[-45:-36], auth[-35:]])

            def modified_header():
                value = 1234567
                return "".join(list(chain(*zip(str(int(time.time()) ^ value), "0123456789"))))

            _split_url = stream["url"].split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            post_encoded = urlencode({"_": stream_id})
            headers = OrderedDict(
                [
                    ("Public-Key-Pins", b64encode(self.json_config["user"]["user_id"].encode("utf-8"))),
                    ("Modified", modified_header()),
                    ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"),
                    ("User-Agent", self.user_agent),
                    ("Connection", "Keep-Alive"),
                    ("Accept-Encoding", "gzip"),
                    ("Content-Length", str(len(post_encoded))),
                ]
            )

            req = requests.Request("POST", self.json_config["token_url_38"], data=post_encoded)
            prepped = req.prepare()
            prepped.headers = headers
            r = self.s.send(prepped, timeout=15, verify=False)
            r.raise_for_status()

            key = "jygh" + self.json_config["user"]["user_id"][1:5] + self.user_agent[-8:]
            iv = self.user_agent[-8:] + "vsdc" + self.json_config["user"]["user_id"][1:5]

            res = self.dec_aes_cbc_single(b64decode(r.text), key.encode("utf-8"), iv.encode("utf-8")).decode("utf-8")
            host = b64decode(r.headers["Session"]).decode("utf-8").split("$")
            _split_url[2], _split_url[-3], _split_url[-2] = host
            return (
                "{0}{1}".format("/".join(_split_url), fix_auth(res)),
                player_headers,
            )
        elif stream["token"] == 42:
            """ crichd (22) """
            pass
        elif stream["token"] == 43:
            """ psl (1) """
            pass
        elif stream["token"] == 44:
            """ main (534) """

            def fix_auth_date(auth):
                now = datetime.datetime.utcnow()
                _in = list(auth)
                _in.pop(len(_in) + 2 - 3 - int(str(now.year)[:2]))
                _in.pop(len(_in) + 3 - 4 - int(str(now.year)[2:]))
                # java January = 0
                _in.pop(len(_in) + 4 - 5 - (now.month - 1 + 1 + 10))
                _in.pop(len(_in) + 5 - 6 - now.day)
                return "".join(_in)

            def modified_header():
                value = 1234567
                return "".join(list(chain(*zip(str(int(time.time()) ^ value), "0123456789"))))

            _split_url = stream["url"].split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            post_encoded = urlencode({"_": stream_id})
            headers = OrderedDict(
                [
                    ("Public-Key-Pins", b64encode(self.json_config["user"]["user_id"].encode("utf-8"))),
                    ("Modified", modified_header()),
                    ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"),
                    ("User-Agent", self.user_agent),
                    ("Connection", "Keep-Alive"),
                    ("Accept-Encoding", "gzip"),
                    ("Content-Length", str(len(post_encoded))),
                ]
            )

            req = requests.Request("POST", self.json_config["token_url_44"], data=post_encoded)
            prepped = req.prepare()
            prepped.headers = headers
            r = self.s.send(prepped, timeout=15, verify=False)
            r.raise_for_status()

            key = "psdz" + self.json_config["user"]["user_id"][1:5] + self.user_agent[-8:]
            iv = self.user_agent[-8:] + "vgpe" + self.json_config["user"]["user_id"][1:5]

            res = self.dec_aes_cbc_single(b64decode(r.text), key.encode("utf-8"), iv.encode("utf-8")).decode("utf-8")
            host = b64decode(r.headers["Session"]).decode("utf-8").split("$")
            _split_url[2], _split_url[-3], _split_url[-2] = host
            return (
                "{0}{1}".format("/".join(_split_url), fix_auth_date(res)),
                player_headers,
            )
        elif stream["token"] == 45:
            """ callback (wstream) """
            link = b64decode(stream["url"][1:]).decode("utf-8").split("|")
            headers["User-Agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                "(KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
            )
            _header = link[1].split(",")
            headers[_header[0]] = _header[1]
            page_r = self.s.get(link[0], headers=headers, timeout=15, verify=False)
            page_r.raise_for_status()
            data = {
                "stream_url": stream["url"],
                "token": stream["token"],
                "docs": [page_r.text],
            }
            post_encoded = urlencode({"data": json.dumps(data, separators=(",", ":"))})
            headers = OrderedDict(
                [
                    ("Accept-Encoding", "gzip"),
                    ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"),
                    ("User-Agent", self.user_agent),
                    ("Connection", "Keep-Alive"),
                    ("Content-Length", str(len(post_encoded))),
                ]
            )
            req = requests.Request("POST", self.json_config["token_url_45"], data=post_encoded)
            prepped = req.prepare()
            prepped.headers = headers
            r = self.s.send(prepped, timeout=15, verify=False)
            r.raise_for_status()
            return (r.json()["stream_url"], player_headers)

        elif stream["token"] == 48:
            """ main (297) """

            def fix_auth_date(auth):
                now = datetime.datetime.utcnow()
                _in = list(auth)
                _in.pop(len(_in) + 2 - 3 - int(str(now.year)[:2]))
                _in.pop(len(_in) + 3 - 4 - int(str(now.year)[2:]))
                # java January = 0
                _in.pop(len(_in) + 4 - 5 - (now.month - 1 + 1 + 10))
                _in.pop(len(_in) + 5 - 6 - now.day)
                return "".join(_in)

            def modified2_header():
                value = 1234567
                s1 = [
                    random.choice(string.digits),
                    random.choice(string.digits),
                    random.choice(string.digits),
                ]
                s2 = [
                    random.choice(string.digits),
                    random.choice(string.digits),
                    random.choice(string.digits),
                ]
                return "".join(s1 + list(chain(*zip(str(int(time.time()) ^ value), "0123456789"))) + s2)

            _split_url = stream["url"].split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            post_encoded = urlencode({"_": stream_id})
            headers = OrderedDict(
                [
                    ("Public-Key-Pins", b64encode(self.json_config["user"]["user_id"].encode("utf-8"))),
                    ("Modified", modified2_header()),
                    ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8"),
                    ("User-Agent", self.user_agent),
                    ("Connection", "Keep-Alive"),
                    ("Accept-Encoding", "gzip"),
                    ("Content-Length", str(len(post_encoded))),
                ]
            )

            req = requests.Request("POST", self.json_config["token_url_48"], data=post_encoded)
            prepped = req.prepare()
            prepped.headers = headers
            r = self.s.send(prepped, timeout=15, verify=False)
            r.raise_for_status()

            key = "mtds" + self.json_config["user"]["user_id"][1:5] + self.user_agent[-8:]
            iv = self.user_agent[-8:] + "cndr" + self.json_config["user"]["user_id"][1:5]

            res = self.dec_aes_cbc_single(b64decode(r.text), key.encode("utf-8"), iv.encode("utf-8")).decode("utf-8")
            host = b64decode(r.headers["Session"]).decode("utf-8").split("$")
            _split_url[2], _split_url[-3], _split_url[-2] = host
            return (
                "{0}{1}".format("/".join(_split_url), fix_auth_date(res)),
                player_headers,
            )

        elif stream["token"] == 50:
            """ yupptv.com (21) """
            pass
        elif stream["token"] == 51:
            """ mirror (39) """

            def fix_auth_date(auth):
                now = datetime.datetime.utcnow()
                _in = list(auth)
                _in.pop(len(_in) + 2 - 3 - int(str(now.year)[:2]))
                _in.pop(len(_in) + 3 - 4 - int(str(now.year)[2:]))
                # java January = 0
                _in.pop(len(_in) + 4 - 5 - (now.month - 1 + 1 + 10))
                _in.pop(len(_in) + 5 - 6 - now.day)
                return "".join(_in)

            def modified_header():
                value = 1234567
                return "".join(list(chain(*zip(str(int(time.time()) ^ value), "0123456789"))))

            _split_url = stream["url"].split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            headers = OrderedDict(
                [
                    (
                        "Public-Key-Pins",
                        b64encode("{0}.{1}".format(self.json_config["user"]["user_id"], stream_id).encode("utf-8")),
                    ),
                    ("Modified", modified_header()),
                    ("Content-Type", "application/x-www-form-urlencoded"),
                    ("User-Agent", self.user_agent),
                    ("Connection", "Keep-Alive"),
                    ("Accept-Encoding", "gzip"),
                    ("Content-Length", "0"),
                ]
            )

            req = requests.Request("POST", self.json_config["token_url_51"], data="")
            prepped = req.prepare()
            prepped.headers = headers
            r = self.s.send(prepped, timeout=15, verify=False)
            r.raise_for_status()

            key = self.json_config["user"]["user_id"][1:6] + "gouk" + self.user_agent[-7:]
            iv = self.user_agent[-8:] + "atyi" + self.json_config["user"]["user_id"][1:5]

            res = self.dec_aes_cbc_single(b64decode(r.text), key.encode("utf-8"), iv.encode("utf-8")).decode("utf-8")
            host = b64decode(r.headers["Session"]).decode("utf-8")
            return (
                "{0}{1}".format(stream["url"].replace("$", host), fix_auth_date(res)),
                player_headers,
            )
        elif stream["token"] == 52:
            """ mirror (42) """

            def fix_auth_date(auth):
                now = datetime.datetime.utcnow()
                _in = list(auth)
                _in.pop(len(_in) + 2 - 3 - int(str(now.year)[:2]))
                _in.pop(len(_in) + 3 - 4 - int(str(now.year)[2:]))
                # java January = 0
                _in.pop(len(_in) + 4 - 5 - (now.month - 1 + 1 + 10))
                _in.pop(len(_in) + 5 - 6 - now.day)
                return "".join(_in)

            def modified_header():
                value = 1234567
                return "".join(list(chain(*zip(str(int(time.time()) ^ value), "0123456789"))))

            _split_url = stream["url"].split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            headers = OrderedDict(
                [
                    (
                        "Public-Key-Pins",
                        b64encode("{0}.{1}".format(self.json_config["user"]["user_id"], stream_id).encode("utf-8")),
                    ),
                    ("Modified", modified_header()),
                    ("Content-Type", "application/x-www-form-urlencoded"),
                    ("User-Agent", self.user_agent),
                    ("Connection", "Keep-Alive"),
                    ("Accept-Encoding", "gzip"),
                    ("Content-Length", "0"),
                ]
            )

            req = requests.Request("POST", self.json_config["token_url_52"], data="")
            prepped = req.prepare()
            prepped.headers = headers
            r = self.s.send(prepped, timeout=15, verify=False)
            r.raise_for_status()

            key = self.json_config["user"]["user_id"][1:6] + "gouk" + self.user_agent[-7:]
            iv = self.user_agent[-8:] + "atyi" + self.json_config["user"]["user_id"][1:5]

            res = self.dec_aes_cbc_single(b64decode(r.text), key.encode("utf-8"), iv.encode("utf-8")).decode("utf-8")
            host = b64decode(r.headers["Session"]).decode("utf-8")
            return (
                "{0}{1}".format(stream["url"].replace("$", host), fix_auth_date(res)),
                player_headers,
            )

        elif stream["token"] == 53:
            """ http://$:8554/tv/bein2/playlist.m3u8 (1) """
            pass
        elif stream["token"] == 54:
            """ cobra sport 240p (43) """
            _split_url = stream["url"].split("/")
            stream_id = "$".join([_split_url[2][1:], _split_url[-3], _split_url[-2]])
            headers = OrderedDict(
                [
                    ("Content-Type", "application/x-www-form-urlencoded"),
                    ("User-Agent", self.user_agent),
                    ("Connection", "Keep-Alive"),
                    ("Accept-Encoding", "gzip"),
                    ("Content-Length", "0"),
                ]
            )

            req = requests.Request("POST", self.json_config["token_url_54"], data="")
            prepped = req.prepare()
            prepped.headers = headers
            r = self.s.send(prepped, timeout=15, verify=False)
            r.raise_for_status()

            _pattern = re.compile("<script>([^<]+)</script>", re.M)
            _split = re.search(_pattern, r.text).group(1).strip().split("\n")
            _upperCase = urlparse(self.json_config["token_url_54"]).path.split("/")[1].upper()
            _c = ord(_upperCase[0]) - ord("@")
            _s2 = _split[ord(_upperCase[(len(_upperCase) - 1)]) - ord("@") - 1].split("?")[1]
            _n = len(_s2) - 1
            _in = list(_s2)
            _in.pop(2 + _n - (_c + 3))
            _in.pop(3 + _n - (_c + 11))
            _in.pop(4 + _n - (_c + 19))
            _in.pop(5 + _n - (_c + 27))

            host = b64decode(r.headers["Session"]).decode("utf-8")
            return (
                "{0}?{1}".format(stream["url"].replace("$", host), "".join(_in)),
                player_headers,
            )
        elif stream["token"] == 56:
            """ jagobd.com (45) """
            pass
        elif stream["token"] == 57:
            """ regex hdcast.me (1) """
            pass
        elif stream["token"] == 58:
            """ youtube (55) """
            pass
        elif stream["token"] == 69:
            """ ICC (3) """
            pass