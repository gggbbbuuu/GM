import base64, requests, uuid, os, time, json, sys
from datetime import datetime
from urllib.parse import urlencode, urlparse
from socket import gethostbyname
from xbmcvfs import translatePath
import xbmcaddon, xbmcgui, xbmc, xbmcplugin
from itertools import chain
from pyamf import remoting, AMF3
from pyamf.flex import messaging
from ..plugin import Plugin
from ..util.dialogs import link_dialog
from resources.lib.plugin import run_hook

try:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad
except:
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad, unpad
    except:
        pass

addon = xbmcaddon.Addon()
USER_DATA_DIR = translatePath(addon.getAddonInfo("profile"))

class RBTV(Plugin):
    name = "rbtv"
    priority = 100
    json_config = {}
    config_url = "https://api.backendless.com/A73E1615-C86F-F0EF-FFDC-58ED0DFC6B00/7B3DFBA7-F6CE-EDB8-FF0F-45195CF5CA00/binary"
    user_agent = "Dalvik/2.1.0 (Linux; U; Android 9; AFTKA Build/PS7255)"
    player_user_agent = "stagefright/1.2 (Linux;Android 9)"

    def process_item(self, item):
        if self.name in item:
            link = item.get(self.name, "")
            if link == "categories":
                item["link"] = "rbtv/categories"
                item["is_dir"] = True
                item["list_item"] = xbmcgui.ListItem(item.get("title", item.get("name", "")), offscreen=True)
                return item
            elif type(link) == int:
                item["link"] = "rbtv/category/" + str(link)
                item["is_dir"] = True
                item["list_item"] = xbmcgui.ListItem(item.get("title", item.get("name", "")), offscreen=True)
                return item
    
    def routes(self, plugin):
        @plugin.route("/rbtv/categories")
        def categories():
            self.__init_config()
            jen_list = [{
                "title": category["title"],
                "thumbnail": "",
                "fanart": "",
                "rbtv": int(category["category_id"]),
                "type": "dir",
            } for category in self.json_config["categories"]]

            jen_list = [run_hook("process_item", item) for item in jen_list]
            run_hook("display_list", jen_list)
        
        @plugin.route("/rbtv/category/<category>")
        def category_videos(category):
            self.__init_config()
            videos = list(filter(lambda x: x["category"] == category, self.json_config["videos"]))
            jen_list = [{
                "title": f'[COLORblue]{video["video_id"]}[/COLOR] | {video["title"]}',
                "thumbnail": video["logo_url"],
                "fanart": video["logo_url"],
                "rbtv": video["streams"],
                "type": "item"
            } for video in videos]

            jen_list = [run_hook("process_item", item) for item in jen_list]
            jen_list = [run_hook("get_metadata", item) for item in jen_list]
            run_hook("display_list", jen_list)
    
    def play_video(self, video: str):
        item = json.loads(video)
        if self.name in item:
            self.__init_config()
            link = item.get(self.name)
            if type(link) == str and link.startswith("play_"):
                video_id = int(link[5:])
                video = list(filter(lambda x: x["video_id"] == video_id, self.json_config["videos"]))[0]
                streams = video["streams"]
            else:
                streams = item[self.name]
            stream = streams[link_dialog([stream["stream_url"] for stream in streams], return_idx=True)]
            if stream == None: return True

            resolved_stream = self.__resolve_stream(stream)
            headers = {
                "User-Agent": self.player_user_agent,
                "Connection": "keep-alive"
            }
            if "playlist.m3u8" in resolved_stream:
                _parsed = urlparse(resolved_stream)
                _host = _parsed.netloc.split(":")
                _host[0] = gethostbyname(_host[0])
                _resolved = _parsed._replace(netloc=":".join(_host)).geturl()
                headers["!Host"] = _parsed.netloc
                resolved_stream = _resolved
            xbmc.Player().play(f"{resolved_stream}|{urlencode(headers)}")
            return True

    def __resolve_stream(self, stream):
        if stream["token"] == 21:
            url = self.json_config["token_url_21"]
            auth = self.json_config["token_auth_21"]
        elif stream["token"] == 38:
            url = self.json_config["token_url_38"]
            auth = self.json_config["token_auth_38"]
        elif stream["token"] == 48:
            url = self.json_config["token_url_48"]
            auth = self.json_config["token_auth_48"]
        else:
            return stream["stream_url"]
        
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Modified": self.modified_header(),
            "Authorization": auth,
        }
        
        req = requests.Request("POST", url, data="")
        prepped = req.prepare()
        prepped.headers = headers
        s = requests.Session()
        r = s.send(prepped, timeout=5, verify=False)
        r.raise_for_status()

        key = "3pgcweowuhv" + self.user_agent[-5:]
        iv = self.user_agent[-5:] + "eru9843dwth"
        token = self.dec_aes_cbc_single(base64.b64decode(r.text), key.encode("utf-8"), iv.encode("utf-8")).decode("utf-8")
        return stream["stream_url"] + token

    def __init_config(self):
        if self.json_config != {}: return
        config = os.path.join(USER_DATA_DIR, "rbtv_config.json")
        if not os.path.exists(config):
            self.__fetch_config()
            self.__register_user()
            self.__fetch_videos()
            self.__write_config()
        else:
            f = open(config)
            json_config = json.loads(f.read())
            f.close()
            self.json_config = json_config
            if time.time() - json_config["data_age"] > 8 * 60 * 60:
                self.__fetch_config()
                self.__fetch_videos()
                self.__write_config()
        
    def __fetch_config(self):
        data = {
            "clientId": None,
            "destination": "GenericDestination",
            "correlationId": None,
            "source": "com.backendless.services.persistence.PersistenceService",
            "operation": "first",
            "messageRefType": None,
            "headers": {"application-type": "ANDROID", "api-version": "1.0"},
            "timestamp": 0,
            "body": ["AppConfigHotel"],
            "timeToLive": 0,
            "messageId": None,
        }
        req = remoting.Request(target="null", body=[messaging.RemotingMessage(**data)])
        ev = remoting.Envelope(AMF3)
        ev["null"] = req
        resp = requests.post(
            self.config_url,
            data=remoting.encode(ev).getvalue(),
            headers={"Content-Type": "application/x-amf", "User-Agent": self.user_agent},
            timeout=5,
            verify=False,
        )
        resp.raise_for_status()
        amf_data = remoting.decode(resp.content).bodies[0][1].body.body
        self.json_config["api_url"] = self.__decode_value(amf_data["YmFzZXVybG5ld3gw"])
        self.json_config["api_referer"] = self.__decode_value(amf_data["SXNpc2VrZWxvX3Nlc2lzdGltdV95ZXppbm9tYm9sbzAw"])
        self.json_config["api_authorization"] = self.__decode_value(amf_data["amFnX3Ryb3JfYXR0X2Vu"])
        self.json_config["token_url_21"] = self.__decode_value(amf_data["Y2FsYWFtb19pa3Mw"])
        self.json_config["token_auth_21"] = self.__decode_value(amf_data["WXJfd3lmX3luX2JhaXMw"])
        self.json_config["token_url_38"] = self.__decode_value(amf_data["YmVsZ2lfMzgw"])
        self.json_config["token_auth_38"] = self.__decode_value(amf_data["Z2Vsb29mc2JyaWVm"])
        self.json_config["token_url_48"] = self.__decode_value(amf_data["Ym9ya3lsd3VyXzQ4"])
        self.json_config["token_auth_48"] = self.__decode_value(amf_data["dGVydHRleWFj"])
        self.json_config["mod_value"] = self.__decode_value(amf_data["TW9vbl9oaWsx"])
    
    def __register_user(self):
        android_id = uuid.uuid4().hex[:16]
        data = {
            "gmail": "",
            "api_level": "28",
            "android_id": android_id,
            "device_id": "unknown",
            "device_name": "Amazon AFTKA",
            "version": "2.3 (41)",
            "hash_id": self.enc_aes_cbc_single(f"{android_id}_wdufherfbweicerwf", android_id.encode("utf-8"), android_id.encode("utf-8"))
        }
        user_id = self.__api_request(self.json_config["api_url"] + "adduserinfo.nettv/", data).get("user_id")
        self.json_config["user"] = {"user_id": user_id, "check": 41}

    def __fetch_videos(self):
        data = {
            "check": self.json_config["user"]["check"],
            "user_id": self.json_config["user"]["user_id"],
            "version": "41",
            "hash_id": self.enc_aes_cbc_single(
                f'{self.json_config["user"]["user_id"]}_wdufherfbweicerwf',
                f'{self.json_config["user"]["user_id"]}cefrecdce'.encode("utf-8")[:16],
                f'{self.json_config["user"]["user_id"]}cwefervwv'.encode("utf-8")[:16],
            )
        }
        self.json_config["user"]["check"] = 1
        res = self.__api_request(self.json_config["api_url"] + "redbox.tv/", data)
        categories = [{"category_id": item["cat_id"], "title": item["cat_name"]} for item in res["categories_list"]]
        countries = [{"country_id": item["country_id"], "title": item["country_name"]} for item in res["countries_list"]]
        videos = [{
            "video_id": int(self.__decode_value2(item["rY19pZA=="])),
            "category": item["cat_id"],
            "country": item["country_id"],
            "title": self.__decode_value2(item["ZY19uYW1l"]),
            "logo_url": self.__decode_value(item["abG9nb191cmw="]) + "|" + self.user_agent,
            "streams": [{
                "stream_id": self.__decode_value2(stream["cc3RyZWFtX2lk"]),
                "video_id": self.__decode_value2(item["rY19pZA=="]),
                "token": int(self.__decode_value2(stream["AdG9rZW4="])),
                "stream_url": self.__decode_value(stream["Bc3RyZWFtX3VybA=="]),
            } for stream in item["Qc3RyZWFtX2xpc3Q="]]
        } for item in res["eY2hhbm5lbHNfbGlzdA=="]]
        self.json_config["categories"] = categories
        self.json_config["countries"] = countries
        self.json_config["videos"] = videos
    
    def __write_config(self):
        if not os.path.exists(USER_DATA_DIR):
            os.makedirs(USER_DATA_DIR)
        config = os.path.join(USER_DATA_DIR, "rbtv_config.json")
        self.json_config["data_age"] = time.time()
        f = open(config, "w")
        f.write(json.dumps(self.json_config))
        f.close()
    
    def __api_request(self, url, data):
        headers = {
            "Referer": self.json_config["api_referer"],
            "Authorization": self.json_config["api_authorization"],
            "User-Agent": self.user_agent
        }
        r = requests.post(url, headers=headers, data=data, timeout=5, verify=False)
        r.raise_for_status()
        return r.json()

    def __decode_value(self, v):
        return base64.b64decode(v[1:]).decode("utf-8")

    def __decode_value2(self, v):
        return base64.b64decode(v[:-1]).decode("utf-8")

    def modified_header(self):
        value = int(self.json_config["mod_value"])
        return "".join(list(chain(*zip(str(int(time.time()) ^ value), "0123456789"))))
    
    def dec_aes_cbc_single(self, msg, key, iv):
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        return unpad(cipher.decrypt(msg), 16)
    
    def enc_aes_cbc_single(self, msg, key, iv):
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        return base64.b64encode(cipher.encrypt(pad(msg.encode("utf-8"), 16)))
    
    
