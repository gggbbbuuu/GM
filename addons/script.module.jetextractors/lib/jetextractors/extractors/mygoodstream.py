import base64, json, hashlib
from ..models import *
from urllib.parse import urlparse, parse_qs
try:
    from Crypto.Cipher import AES
except:
    try:
        from Cryptodome.Cipher import AES
    except:
        pass

class MyGoodStream(JetExtractor):
    def __init__(self) -> None:
        self.name = "MyGoodStream"
        self.domains = ["mygoodstream.pw"]
        self.passphrase = "~ç$jiÞ®Ü¬×"
        self.resolve_only = True
    
    def evpKDF(self, passwd, salt, key_size=8, iv_size=4, iterations=1, hash_algorithm="md5"):
        """
        https://github.com/Shani-08/ShaniXBMCWork2/blob/master/plugin.video.serialzone/jscrypto.py
        """
        target_key_size = key_size + iv_size
        derived_bytes = bytearray()
        number_of_derived_words = 0
        block = None
        hasher = hashlib.new(hash_algorithm)
        while number_of_derived_words < target_key_size:
            if block is not None:
                hasher.update(block)

            hasher.update(passwd)
            hasher.update(salt)
            block = hasher.digest()
            hasher = hashlib.new(hash_algorithm)

            for i in range(1, iterations):
                hasher.update(block)
                block = hasher.digest()
                hasher = hashlib.new(hash_algorithm)

            derived_bytes += block[0: min(len(block), (target_key_size - number_of_derived_words) * 4)]

            number_of_derived_words += len(block)/4

        return {
            "key": derived_bytes[0: key_size * 4],
            "iv": derived_bytes[key_size * 4:]
        }
    
    def decrypt(self, passphrase, salt, encrypted_text):
        resp = self.evpKDF(passphrase, salt, key_size=12)
        key = resp.get("key")
        iv = key[len(key)-16:]
        key = key[:len(key)-16]
        aes = AES.new(key, AES.MODE_CBC, iv)
        decrypted_text = aes.decrypt(encrypted_text)
        return decrypted_text


    def get_link(self, url: JetLink) -> JetLink:
        qs = parse_qs(urlparse(url).query)
        jsonEncB64 = qs["id"][0]
        jsonEnc = json.loads(base64.b64decode(jsonEncB64).decode("ascii"))
        ct = base64.b64decode(jsonEnc["ct"])
        iv = bytes.fromhex(jsonEnc["iv"])
        salt = bytes.fromhex(jsonEnc["s"])
        embed_url = self.decrypt(self.passphrase.encode("utf-8"), salt, ct).decode("ascii").replace("\x05", "").replace('"', "").strip()
        embed_qs = parse_qs(urlparse(embed_url).query)
        mpd_url = f"https://d302z9my8oligm.cloudfront.net/Content/DASH_WV/Live/channel({embed_qs['id'][0]})/manifest.mpd"
        license_url = "https://widevine.licenses4.me/widek.php|Referer=https://eplayer.click/|R{SSM}|"
        return JetLink(address=mpd_url, inputstream=JetInputstreamAdaptive("mpd", license_key=license_url))
