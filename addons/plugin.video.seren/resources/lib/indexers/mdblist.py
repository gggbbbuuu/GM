import threading
import time
from functools import cached_property
from urllib import parse

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.common import tools
from resources.lib.indexers.apibase import ApiBase
from resources.lib.modules.exceptions import RanOnceAlready
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g

# Registered at mdblist.com/developer/ for the Seren application itself
# (public OAuth client - device-code and refresh grants only, no
# client_secret involved). Overridable via the mdblist.clientid setting,
# mirroring trakt.clientid.
MDBLIST_CLIENT_ID = "J8KrAgKjNIFGXvK1f9QZUuHsXmTb25d6KBnuVOLX"


class MDBListAPI(ApiBase):
    """
    Class to handle interactions with the MDBList API
    """

    ApiUrl = "https://api.mdblist.com/"
    OAuthUrl = "https://api.mdblist.com/oauth/"

    username_setting_key = "mdblist.username"
    is_supporter_setting_key = "mdblist.is_supporter"

    def __init__(self):
        self.api_key = None
        self.client_id = None
        self.access_token = None
        self.refresh_token = None
        self.token_expires = 0.0
        self.username = None
        self._load_settings()

    @cached_property
    def session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3 import Retry

        class _CappedRetry(Retry):
            """MDBList's documented Retry-After can be up to 12 hours
            (mdblist.apib); urllib3 respects that header by default and
            sleeps the full duration on the calling thread, which can hang
            a foreground Kodi action for hours. Capping the sleep (not
            disabling the header entirely) still honours short, legitimate
            backoff windows correctly - it only bounds the pathological
            case. Retries are exhausted the same as any other failure,
            already caught by get()/get_json()'s try/except."""

            _MAX_RETRY_AFTER = 15

            def get_retry_after(self, response):
                retry_after = super().get_retry_after(response)
                if retry_after is None:
                    return None
                return min(retry_after, self._MAX_RETRY_AFTER)

        session = requests.Session()
        retries = _CappedRetry(
            total=4,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        session.mount("https://", HTTPAdapter(max_retries=retries, pool_maxsize=100))
        return session

    # region Auth
    def authorize(self):
        """
        Performs OAuth device-code authorization with MDBList: shows a
        scannable QR code alongside the verification URL + code (also
        copied to clipboard), polls until the user approves on another
        device, then stores the resulting access/refresh tokens
        :return: None
        """
        self.username = None
        response = self._oauth_post(
            "device-authorization/", {"client_id": self.client_id, "scope": "read write"}
        )
        if response is None or not response.ok:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(31163))
            return
        try:
            device_data = response.json()
            device_code = device_data["device_code"]
            user_code = device_data["user_code"]
            verification_url = device_data.get("verification_uri", "https://mdblist.com/oauth/device/")
            interval = int(device_data.get("interval", 5))
            expiry = int(device_data.get("expires_in", 300))
        except (KeyError, ValueError):
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(31163))
            return

        tools.copy2clip(user_code)
        qr_image = tools.make_qr(verification_url, "mdblist_qr.png")

        from resources.lib.gui.windows.qr_auth_window import QRAuthWindow

        window = QRAuthWindow("qr_auth_window.xml", g.ADDON_PATH)
        window.set_title(g.get_language_string(30948))
        window.set_qr_image(qr_image)
        window.set_details(
            g.get_language_string(30018).format(verification_url),
            g.get_language_string(30019).format(user_code),
        )
        window_thread = threading.Thread(target=window.doModal)
        window_thread.start()

        failed = False
        token_ttl = expiry
        try:
            while (
                not failed
                and self.username is None
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

        if self.username:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30952))
            xbmc.executebuiltin(f'RunPlugin("{g.BASE_URL}?action=syncMDBListActivities")')
        elif not canceled:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(31163))

    def _auth_poll(self, device_code):
        """
        Polls the token endpoint once. Returns True if polling should stop
        (success or unrecoverable failure), False to keep waiting.
        """
        response = self._oauth_post(
            "token/",
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
                "client_id": self.client_id,
            },
        )
        if response is None:
            return True
        if response.status_code == 200:
            return self._auth_success(response)
        try:
            error = response.json().get("error")
        except ValueError:
            error = None
        if response.status_code == 404 or error in ("expired_token", "access_denied"):
            return True
        if error == "slow_down":
            xbmc.sleep(5 * 1000)
        elif response.status_code == 429:
            xbmc.sleep(1 * 1000)
        return False

    def _auth_success(self, response):
        self._save_oauth_settings(response.json())
        username = self.get_username()
        if not username:
            return True
        self.username = username
        g.set_setting(self.username_setting_key, username)
        return False

    def try_refresh_token(self, force=False):
        """
        Attempts to refresh the current MDBList OAuth token
        :param force: Set to True to force refresh regardless of cached expiry
        :return: True if a usable access token is available after this call
        """
        if not self.refresh_token:
            return False
        if not force and self.token_expires > float(time.time()):
            return True
        try:
            with GlobalLock(self.__class__.__name__, True, self.access_token):
                # Account Manager renews this login ahead of expiry, from another process. This instance may still hold the
                # login it loaded earlier, whose refresh token MDBList has already rotated: refreshing with it would fail and
                # wipe the whole login. If the saved login differs from the one in hand, use the saved one instead.
                stored = self._stored_login()
                if stored[0] and stored[0] != self.access_token:
                    g.log("MDBList login was renewed elsewhere - using the saved one")
                    self._adopt_stored_login(stored)
                    return True
                sent_refresh_token = self.refresh_token
                g.log("MDBList Token requires refreshing...")
                response = self._oauth_post(
                    "token/",
                    {
                        "grant_type": "refresh_token",
                        "refresh_token": self.refresh_token,
                        "client_id": self.client_id,
                    },
                )
                if response is not None and response.status_code == 200:
                    self._save_oauth_settings(response.json())
                    g.log("Refreshed MDBList Token")
                    return True
                stored = self._stored_login()
                if stored[1] and stored[1] != sent_refresh_token:
                    # the login was rotated by someone else while this refresh was in flight - theirs is the live one, keep it
                    g.log("MDBList login was renewed elsewhere during the refresh - using the saved one")
                    self._adopt_stored_login(stored)
                    return bool(self.access_token)
                g.log("MDBList token refresh failed, clearing auth", "error")
                self._clear_auth_settings()
                xbmcgui.Dialog().notification(g.ADDON_NAME, g.get_language_string(31163))
                return False
        except RanOnceAlready:
            stored = self._stored_login()
            if stored[0] and stored[0] != self.access_token:
                self._adopt_stored_login(stored)
            else:
                self._load_settings()
            return bool(self.access_token)

    @staticmethod
    def _stored_login():
        """The MDBList login saved in Kodi right now - (access token, refresh token, expiry) - read straight from the
        add-on, not through Seren's settings cache, because Account Manager writes it from another process."""
        addon = xbmcaddon.Addon("plugin.video.seren")
        return (
            addon.getSetting("mdblist.auth") or None,
            addon.getSetting("mdblist.refresh") or None,
            addon.getSetting("mdblist.expires"),
        )

    def _adopt_stored_login(self, stored):
        self.access_token, self.refresh_token = stored[0], stored[1]
        try:
            self.token_expires = float(stored[2] or 0)
        except ValueError:
            self.token_expires = 0.0

    def revoke_auth(self):
        """
        Clears all stored MDBList authorization state (typed API key and/or OAuth tokens)
        :return:
        """
        self._clear_auth_settings()
        xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30950))

    def _clear_auth_settings(self):
        g.clear_setting("mdblist.apikey")
        g.clear_setting("mdblist.auth")
        g.clear_setting("mdblist.refresh")
        g.clear_setting("mdblist.expires")
        g.clear_setting(self.username_setting_key)
        g.clear_setting(self.is_supporter_setting_key)
        self.api_key = None
        self.access_token = None
        self.refresh_token = None
        self.token_expires = 0.0
        self.username = None

    def _save_oauth_settings(self, response):
        if "access_token" in response:
            g.set_setting("mdblist.auth", response["access_token"])
            self.access_token = response["access_token"]
        if "refresh_token" in response:
            g.set_setting("mdblist.refresh", response["refresh_token"])
            self.refresh_token = response["refresh_token"]
        if "expires_in" in response:
            expires_at = time.time() + response["expires_in"]
            g.set_setting("mdblist.expires", str(int(expires_at)))
            self.token_expires = expires_at

    def _load_settings(self):
        self.api_key = g.get_setting("mdblist.apikey") or None
        self.client_id = g.get_setting("mdblist.clientid", MDBLIST_CLIENT_ID)
        self.access_token = g.get_setting("mdblist.auth") or None
        self.refresh_token = g.get_setting("mdblist.refresh") or None
        self.token_expires = g.get_float_setting("mdblist.expires")
        self.username = g.get_setting(self.username_setting_key) or None

    # endregion

    def _oauth_post(self, url, data):
        """
        POSTs form-encoded data to an MDBList OAuth endpoint. MDBList's
        OAuth endpoints reject JSON bodies outright (confirmed live against
        the real API: "Content-Type must be application/x-www-form-urlencoded"),
        so this deliberately bypasses post()/post_json(), which send JSON
        for the regular REST API.
        :return: request response, or None on failure
        """
        try:
            return self.session.post(
                parse.urljoin(self.OAuthUrl, url),
                data=data,
                headers={"User-Agent": g.USER_AGENT},
                timeout=20,
            )
        except Exception as e:
            g.log(f"Failed to contact MDBList OAuth endpoint: {e}", "error")
            return None

    def _get_headers(self):
        headers = {"Content-Type": "application/json", "User-Agent": g.USER_AGENT}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _request(self, method, url, params=None, data=None, timeout=10):
        """
        Shared verb dispatcher: sends Authorization: Bearer when an OAuth
        token is held, otherwise falls back to the legacy apikey= query
        param, so upgrading users with a saved typed key keep working
        until they choose to re-authorize. On a 401 with a live OAuth
        token, tries one token refresh and retries the request once.
        """
        params = dict(params or {})
        if not self.access_token:
            params.setdefault("apikey", self.api_key)
        kwargs = {"params": params, "headers": self._get_headers(), "timeout": timeout}
        if data is not None:
            kwargs["json"] = data
        try:
            response = getattr(self.session, method)(parse.urljoin(self.ApiUrl, url), **kwargs)
            if response.status_code == 401 and self.access_token and self.try_refresh_token(force=True):
                kwargs["headers"] = self._get_headers()
                response = getattr(self.session, method)(parse.urljoin(self.ApiUrl, url), **kwargs)
            return response
        except Exception as e:
            g.log(f"Failed to contact MDBList: {e}", "error")
            return None

    def get(self, url, **params):
        """
        Performs a GET request to specified endpoint and returns response
        :param url: endpoint to perform request against
        :param params: URL params for request
        :return: request response
        """
        timeout = params.pop("timeout", 10)
        return self._request("get", url, params=params, timeout=timeout)

    def get_json(self, url, **params):
        """
        Performs a GET request to specified endpoint and returns JSON response
        :param url: endpoint to perform request against
        :param params: URL params for request
        :return: JSON response, or None on failure
        """
        try:
            response = self.get(url, **params)
        except Exception as e:
            g.log(f"Failed to contact MDBList: {e}", "error")
            return None
        if response is None or not response.ok:
            return None
        try:
            return response.json()
        except ValueError:
            return None

    def post(self, url, data, **params):
        """
        Performs a POST request to specified endpoint and returns response
        :param url: endpoint to perform request against
        :param data: POST data to send to endpoint
        :param params: URL params for request
        :return: request response, or None on failure
        """
        timeout = params.pop("timeout", 10)
        return self._request("post", url, params=params, data=data, timeout=timeout)

    def post_json(self, url, data, **params):
        """
        Performs a POST request to specified endpoint and returns JSON response
        :param url: endpoint to perform request against
        :param data: POST data to send to endpoint
        :param params: URL params for request
        :return: JSON response, or None on failure
        """
        response = self.post(url, data, **params)
        if response is None or not response.ok:
            return None
        try:
            return response.json()
        except ValueError:
            return None

    def put(self, url, data, **params):
        """
        Performs a PUT request to specified endpoint and returns response
        :param url: endpoint to perform request against
        :param data: PUT data to send to endpoint
        :param params: URL params for request
        :return: request response, or None on failure
        """
        timeout = params.pop("timeout", 10)
        return self._request("put", url, params=params, data=data, timeout=timeout)

    def delete(self, url, **params):
        """
        Performs a DELETE request to specified endpoint and returns response
        :param url: endpoint to perform request against
        :param params: URL params for request
        :return: request response, or None on failure
        """
        timeout = params.pop("timeout", 10)
        return self._request("delete", url, params=params, timeout=timeout)

    def get_username(self):
        """
        Fetch the username linked to the currently held credentials (typed API key or OAuth token)
        :return: string username, or None if invalid/unreachable
        """
        user_details = self.get_json("user")
        if not user_details:
            return None
        return user_details.get("username")

    def _fetch_account_info(self):
        """
        One-shot GET /user for the account-info screen. Deliberately bypasses the shared session: its retry
        adapter treats 429 as retryable, so on an exhausted daily quota (the very case this screen explains) it
        would stall for about a minute, then raise and discard the response with its X-RateLimit-* headers.
        Same auth as _request: Bearer when an OAuth token is held (one refresh-and-retry on 401), else apikey=.
        :return: requests.Response of any status, or None if the request itself failed
        """
        import requests

        def _send():
            params = {} if self.access_token else {"apikey": self.api_key}
            return requests.get(
                parse.urljoin(self.ApiUrl, "user"), params=params, headers=self._get_headers(), timeout=10
            )

        try:
            response = _send()
            if response.status_code == 401 and self.access_token and self.try_refresh_token(force=True):
                response = _send()
            return response
        except Exception as e:
            # type name only - a requests exception's text carries the full URL, apikey= included
            g.log(f"MDBList account info request failed: {type(e).__name__}", "error")
            return None

    def account_info_to_dialog(self):
        """
        Shows the account's daily API quota (limit, used, remaining, reset time) in a select dialog, so it is
        visible why MDBList sync goes quiet once the daily quota is used up. Works from the JSON body of /user,
        and from the X-RateLimit-* / Retry-After headers when the body is unavailable (e.g. on a 429).
        """
        from datetime import datetime

        def _int(value):
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        failure = "MDBList: Could not retrieve account information."
        try:
            response = self._fetch_account_info()
            if response is None:
                xbmcgui.Dialog().ok(g.ADDON_NAME, failure)
                return
            try:
                data = response.json()
            except ValueError:
                data = {}
            if not isinstance(data, dict):
                data = {}
            headers = response.headers
            throttled = response.status_code == 429
            if not (response.ok or throttled):
                g.log(f"MDBList account info: HTTP {response.status_code}", "warning")
                xbmcgui.Dialog().ok(g.ADDON_NAME, failure)
                return

            api_requests = _int(data.get("api_requests"))
            api_requests_count = _int(data.get("api_requests_count"))
            limit = _int(data.get("rate_limit"))
            if limit is None:
                limit = api_requests
            if limit is None:
                limit = _int(headers.get("X-RateLimit-Limit"))
            remaining = _int(data.get("rate_limit_remaining"))
            if remaining is None and api_requests is not None and api_requests_count is not None:
                remaining = max(api_requests - api_requests_count, 0)
            if remaining is None:
                remaining = _int(headers.get("X-RateLimit-Remaining"))
            if remaining is None and throttled:
                remaining = 0
            used = api_requests_count
            if used is None and limit is not None and remaining is not None:
                used = max(limit - remaining, 0)
            reset = _int(data.get("rate_limit_reset"))
            if reset is None:
                reset = _int(headers.get("X-RateLimit-Reset"))
            retry_after = _int(headers.get("Retry-After"))
            if reset is None and retry_after is not None:
                reset = int(time.time()) + retry_after

            def _count(value):
                return f"{value:,}" if value is not None else "N/A"

            reset_str = "N/A"
            if reset:
                reset_str = datetime.fromtimestamp(reset).strftime("%Y-%m-%d %H:%M")
                minutes = max(int((reset - time.time()) // 60), 0)
                reset_str += f" (in {minutes // 60}h {minutes % 60:02d}m)" if minutes >= 60 else f" (in {minutes}m)"

            if throttled or remaining == 0:
                status = "Daily limit reached - sync is paused until the reset"
            elif remaining is None:
                status = "N/A"
            else:
                status = "OK"

            lines = [
                f"Username:  {data.get('username') or self.username or 'N/A'}",
                f"Plan:  {data.get('plan') or 'N/A'}",
                f"Status:  {status}",
                f"Daily limit:  {_count(limit)}",
                f"Used today:  {_count(used)}",
                f"Remaining:  {_count(remaining)}",
                f"Resets:  {reset_str}",
            ]
            xbmcgui.Dialog().select(f"{g.ADDON_NAME}: MDBList Account", lines)
        except Exception as e:
            g.log(f"MDBList account_info_to_dialog error: {type(e).__name__}: {e}", "error")
            xbmcgui.Dialog().ok(g.ADDON_NAME, failure)

    def is_supporter(self):
        """
        Whether the current account has MDBList supporter status (gates the
        rating-threshold filters on list-item browsing, which the API rejects
        for non-supporters). Cached after the first check since this rarely
        changes - avoids a GET /user round-trip every time the filter menu opens.
        Accounts authorized before this setting existed have no cached value yet,
        so this lazily backfills on first use rather than requiring re-auth.
        Fails closed (treated as non-supporter) if never cached and the live
        check fails, so a transient API error just hides the feature instead of
        exposing params the server would reject.
        :return: bool
        """
        cached = g.get_setting(self.is_supporter_setting_key)
        if cached:
            return cached == "true"
        user_details = self.get_json("user") or {}
        supporter = bool(user_details.get("is_supporter"))
        if user_details:
            g.set_setting(self.is_supporter_setting_key, "true" if supporter else "false")
        return supporter
