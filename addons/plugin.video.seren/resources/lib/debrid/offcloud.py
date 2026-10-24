import threading
import time
from functools import cached_property
from functools import wraps

import xbmc
import xbmcgui

from resources.lib.common import tools
from resources.lib.modules.globals import g

OC_APIKEY_KEY = "offcloud.apikey"
OC_ENABLED_KEY = "offcloud.enabled"
OC_USERNAME_KEY = "offcloud.username"
OC_STATUS_KEY = "offcloud.premiumstatus"

_BASE_URL = "https://offcloud.com/api/"
_OAUTH_BASE_URL = "https://offcloud.com/oauth/"


def offcloud_guard_response(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        import requests

        try:
            response = func(*args, **kwargs)
            if response is None:
                return None
            if response.status_code in (200, 201):
                return response
            if response.status_code == 429:
                g.log("Offcloud throttling applied, sleeping 2 seconds")
                xbmc.sleep(2 * 1000)
                response = func(*args, **kwargs)
                if response is None:
                    return None
                if response.status_code in (200, 201):
                    return response
            g.log(
                f"Offcloud returned {response.status_code} for {response.url}",
                "warning",
            )
            return None
        except requests.exceptions.ConnectionError:
            return None
        except Exception:
            xbmcgui.Dialog().notification(
                g.ADDON_NAME, g.get_language_string(30024).format("Offcloud")
            )
            raise

    return wrapper


class OffCloud:
    base_url = _BASE_URL

    def __init__(self):
        self.api_key = g.get_setting(OC_APIKEY_KEY) or ""

    @cached_property
    def session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3 import Retry

        s = requests.Session()
        # Only retry on server errors, never on connect/read so failures are fast
        retries = Retry(total=2, connect=0, read=0, backoff_factor=0.5,
                        status_forcelist=[500, 502, 503, 504])
        s.mount("https://", HTTPAdapter(max_retries=retries, pool_maxsize=50))
        return s

    def _headers(self):
        """Send key as both Bearer header AND ?key= param — Offcloud endpoints
        vary: download endpoints use ?key=, account/info uses Bearer."""
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    def _params(self, extra=None):
        p = {"key": self.api_key} if self.api_key else {}
        if extra:
            p.update(extra)
        return p

    @offcloud_guard_response
    def get(self, path, **params):
        if not g.get_bool_setting(OC_ENABLED_KEY):
            return None
        return self.session.get(
            self.base_url + path,
            params=self._params(params),
            headers=self._headers(),
            timeout=15,
        )

    @offcloud_guard_response
    def post(self, path, data=None, **params):
        if not g.get_bool_setting(OC_ENABLED_KEY) or not self.api_key:
            return None
        return self.session.post(
            self.base_url + path,
            params=self._params(params),
            headers=self._headers(),
            json=data,
            timeout=15,
        )

    def _get_json(self, path, **params):
        resp = self.get(path, **params)
        if resp is None:
            return None
        try:
            return resp.json()
        except Exception:
            return None

    def _post_json(self, path, data=None, **params):
        resp = self.post(path, data=data, **params)
        if resp is None:
            return None
        try:
            return resp.json()
        except Exception:
            return None

    # ── Auth (Device Code / QR) ─────────────────────────────────────────────

    def authorize(self):
        """
        Performs Offcloud's device-code authorization: shows a scannable QR
        code alongside the verification URL + code (also copied to
        clipboard), polls until the user approves on another device, then
        stores the resulting access token as the account's API key.

        Undocumented in Offcloud's official API docs (which describe only
        API-key and username/password auth), but confirmed working via a
        live device/code + token call, and independently confirmed by both
        Umbrella's and POV's shipped offcloud implementations - see
        TorBox_Offcloud_QR_Auth_Implementation_Plan.md for the verification
        trail. The resulting access token is stored directly into
        OC_APIKEY_KEY (not a separate field) since get_user_info(), the
        cache/cloud endpoints, and getSources.py/globals.py's enabled-checks
        all read that key by name.
        """
        self.api_key = None
        try:
            resp = self.session.post(_OAUTH_BASE_URL + "device/code", timeout=20)
            data = resp.json()
        except Exception as e:
            g.log(f"Offcloud device-code start failed: {e}", "error")
            data = None

        if not isinstance(data, dict):
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30024).format("Offcloud"))
            return

        try:
            device_code = data["device_code"]
            user_code = data["user_code"]
            verification_url = data.get("verification_uri_complete") or data.get(
                "verification_uri", "https://offcloud.com/activate"
            )
            interval = int(data.get("interval", 5))
            token_ttl = int(data.get("expires_in", 600))
        except (KeyError, ValueError):
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30024).format("Offcloud"))
            return

        tools.copy2clip(user_code)
        qr_image = tools.make_qr(verification_url, "offcloud_qr.png")

        from resources.lib.gui.windows.qr_auth_window import QRAuthWindow

        window = QRAuthWindow("qr_auth_window.xml", g.ADDON_PATH)
        window.set_title(g.get_language_string(30934))
        window.set_qr_image(qr_image)
        window.set_details(
            g.get_language_string(30018).format(verification_url),
            g.get_language_string(30019).format(user_code),
        )
        window_thread = threading.Thread(target=window.doModal)
        window_thread.start()

        failed = False
        try:
            while (
                not failed
                and self.api_key is None
                and token_ttl > 0
                and not window.canceled_by_user
            ):
                xbmc.sleep(1000)
                if token_ttl % interval == 0:
                    failed = self._auth_poll(device_code)
                minutes, seconds = divmod(max(token_ttl, 0), 60)
                window.set_status(f"{minutes:02d}:{seconds:02d}")
                token_ttl -= 1
        finally:
            canceled = window.canceled_by_user
            window.close()
            window_thread.join(5)
            del window

        if self.api_key:
            g.set_setting(OC_APIKEY_KEY, self.api_key)
            self.store_user_info()
        elif not canceled:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30024).format("Offcloud"))

    def _auth_poll(self, device_code):
        """
        Polls the token endpoint once. Returns True if polling should stop
        (success or unrecoverable failure), False to keep waiting.
        """
        try:
            resp = self.session.post(
                _OAUTH_BASE_URL + "token",
                json={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": device_code,
                },
                timeout=20,
            )
            data = resp.json()
        except Exception:
            return False

        if not isinstance(data, dict):
            return False

        error = data.get("error")
        if error in ("authorization_pending", "slow_down"):
            return False
        if error in ("expired_token", "access_denied"):
            return True

        access_token = data.get("access_token")
        if not access_token:
            return False
        self.api_key = access_token
        return True

    # ── Cache Check ────────────────────────────────────────────────────────

    def check_cache(self, hash_list):
        """POST /cache with {"hashes": [...]} → set of lowercase cached hashes.

        Official endpoint: POST https://offcloud.com/api/cache?key=
        Response: {"cachedItems": [list of info hashes present in OC's pool]}
        """
        if not hash_list:
            return set()
        result = self._post_json("cache", data={"hashes": [h.lower() for h in hash_list]})
        if not isinstance(result, dict):
            g.log(f"Offcloud cache check: unexpected response type {type(result)}", "warning")
            return set()
        cached = result.get("cachedItems") or []
        return {h.lower() for h in cached if isinstance(h, str)}

    # ── Cached File Resolution ──────────────────────────────────────────────

    def resolve_cached_files(self, magnet):
        """POST /cache/download → list of {url, filename, size} for cached content."""
        result = self._post_json("cache/download", data={"url": magnet})
        if not isinstance(result, list):
            return []
        return result

    # ── Cloud Operations ──────────────────────────────────────────────────

    def create_transfer(self, magnet):
        """POST /cloud → add magnet to cloud. Returns requestId string or ''."""
        result = self._post_json("cloud", data={"url": magnet})
        if isinstance(result, dict):
            return result.get("requestId", "")
        return ""

    def list_torrents(self):
        """GET /cloud/history → list of cloud items with requestId, fileName, status."""
        result = self._get_json("cloud/history")
        if isinstance(result, list):
            return result
        return []

    def torrent_info(self, request_id):
        """GET /cloud/explore/{id}?format=detailed → {files: [{path, url, size}]}."""
        result = self._get_json(f"cloud/explore/{request_id}", format="detailed")
        return result

    def delete_torrent(self, request_id):
        """GET /cloud/remove/{id} → True on success."""
        result = self._get_json(f"cloud/remove/{request_id}")
        if isinstance(result, dict):
            return bool(result.get("success") or result.get("removed"))
        return result is not None

    # ── Account ────────────────────────────────────────────────────────────

    def get_user_info(self):
        """GET /account/info → account dict.

        Sends both Bearer header and ?key= param since Offcloud's endpoint
        behaviour varies between implementations (POV/Umbrella use Bearer;
        official docs list ?key= for download endpoints).
        """
        if not self.api_key:
            return None
        try:
            resp = self.session.get(
                self.base_url + "account/info",
                params={"key": self.api_key},
                headers=self._headers(),
                timeout=15,
            )
            g.log(
                f"Offcloud /account/info: HTTP {resp.status_code}",
                "info",
            )
            if resp.status_code == 200:
                return resp.json()
            try:
                g.log(f"Offcloud /account/info body: {resp.text[:300]}", "warning")
            except Exception:
                pass
        except Exception as e:
            g.log(f"Offcloud /account/info exception: {e}", "warning")
        return None

    def store_user_info(self):
        if not self.api_key:
            xbmcgui.Dialog().ok(
                g.ADDON_NAME,
                "Offcloud: No API key entered.\n\nEnter your API key from offcloud.com/#/account first.",
            )
            return False
        info = self.get_user_info()
        if not isinstance(info, dict):
            xbmcgui.Dialog().ok(
                g.ADDON_NAME, "Offcloud: Could not connect. Check your API key."
            )
            return False
        username = info.get("email") or info.get("userId") or info.get("user_id", "")
        g.set_setting(OC_USERNAME_KEY, str(username))
        status = "Premium" if info.get("is_premium") or info.get("isPremium") else "Free"
        g.set_setting(OC_STATUS_KEY, status)
        xbmcgui.Dialog().ok(
            g.ADDON_NAME,
            f"Offcloud connected.\nUser: {username}\nStatus: {status}",
        )
        return True

    @staticmethod
    def is_service_enabled():
        return (
            g.get_bool_setting(OC_ENABLED_KEY)
            and bool(g.get_setting(OC_APIKEY_KEY))
        )

    def get_account_status(self, user_info=None):
        if user_info is None:
            user_info = self.get_user_info()
        if not isinstance(user_info, dict):
            return "unknown"
        return "premium" if (user_info.get("is_premium") or user_info.get("isPremium")) else "free"

    def account_info_to_dialog(self):
        try:
            info = self.get_user_info()
            if not isinstance(info, dict):
                xbmcgui.Dialog().ok(g.ADDON_NAME, "Offcloud: Could not retrieve account information.")
                return
            email = info.get("email", "N/A")
            user_id = info.get("userId") or info.get("user_id", "")
            is_premium = info.get("is_premium") or info.get("isPremium")
            expires = info.get("expiration_date") or info.get("expirationDate", "N/A")
            lines = [
                f"Email:    {email}",
                f"User ID:  {user_id}",
                f"Status:   {'Premium' if is_premium else 'Free'}",
                f"Expires:  {expires}",
            ]
            xbmcgui.Dialog().select(f"{g.ADDON_NAME}: Offcloud Account", lines)
        except Exception as e:
            g.log(f"OC account_info_to_dialog error: {e}", "error")
            xbmcgui.Dialog().ok(g.ADDON_NAME, "Offcloud: Could not retrieve account information.")

    def revoke_auth(self):
        if not xbmcgui.Dialog().yesno(g.ADDON_NAME, "Remove Offcloud API key?"):
            return
        g.set_setting(OC_APIKEY_KEY, "")
        g.set_setting(OC_USERNAME_KEY, "")
        g.set_setting(OC_STATUS_KEY, "")
        self.api_key = ""
        xbmcgui.Dialog().ok(g.ADDON_NAME, "Offcloud API key removed.")
