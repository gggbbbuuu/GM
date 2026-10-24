import threading
import time
from functools import cached_property
from functools import wraps
from urllib import parse

import xbmc
import xbmcgui

from resources.lib.common import tools
from resources.lib.indexers.apibase import ApiBase
from resources.lib.modules.exceptions import UnexpectedResponse
from resources.lib.modules.globals import g


def _log_connection_error(args, kwarg, e):
    g.log(f"Connection Error to Simkl: {args} - {kwarg}", "error")
    g.log(e, "error")


def _reset_simkl_auth(notify=True):
    settings = ["simkl.auth", "simkl.expires", "simkl.username", "simkl.account_id"]
    for i in settings:
        g.clear_setting(i)
    if notify and g.get_bool_setting("general.watchAccountNotifications", True):
        xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(31073))


def simkl_guard_response(func):
    """
    Decorator for Simkl API requests, handles connection errors and auth resets
    :param func:
    :return:
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        method_class = args[0]
        method_class._load_settings()
        import requests

        try:
            response = func(*args, **kwargs)
            if response.status_code in [200, 201, 204]:
                return response

            if response.status_code == 401:
                g.log("Simkl: token invalid or revoked, resetting auth", "error")
                _reset_simkl_auth()
                return response

            g.log(
                f"Simkl returned a {response.status_code} while requesting {response.url}",
                "error",
            )
            return response
        except requests.exceptions.ConnectionError as e:
            _log_connection_error(args, kwargs, e)
            raise
        except Exception as e:
            _log_connection_error(args, kwargs, e)
            raise

    return wrapper


class SimklAPI(ApiBase):
    """
    Class to handle interactions with the Simkl API
    """

    ApiUrl = "https://api.simkl.com/"

    username_setting_key = "simkl.username"

    def __init__(self):
        self.access_token = None
        self.token_expires = 0
        self.username = None
        self.account_id = None
        self._load_settings()
        self.language = g.get_language_code()

    @cached_property
    def session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3 import Retry

        session = requests.Session()
        retries = Retry(
            total=4,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 524, 530],
        )
        session.mount("https://", HTTPAdapter(max_retries=retries, pool_maxsize=100))
        return session

    # region Auth
    def _get_headers(self):
        headers = {
            "Content-Type": "application/json",
            "User-Agent": g.USER_AGENT,
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _default_params(self):
        """
        client_id/app-name/app-version are required URL params on every Simkl endpoint
        (not headers - Simkl has no api-key header, unlike Trakt's trakt-api-key)
        """
        return {
            "client_id": self.client_id,
            "app-name": g.ADDON_NAME,
            "app-version": g.CLEAN_VERSION,
        }

    def revoke_auth(self):
        """
        Clears local Simkl authorisation. Simkl has no app-initiated server-side revoke
        endpoint - the user revokes from https://simkl.com/settings/connected-apps/.
        :return:
        """
        _reset_simkl_auth(notify=False)
        self.access_token = None
        self.token_expires = 0
        self.username = None
        self.account_id = None
        xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(31072))

    def auth(self):
        """
        Performs PIN/device OAuth with Simkl
        :return: None
        """
        self.username = None
        response = self.get("oauth/pin")
        if not response.ok:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(31079))
            return
        try:
            data = response.json()
            user_code = data["user_code"]
            verification_uri = data.get("verification_uri") or data.get("verification_url")
            interval = int(data["interval"])
            token_ttl = int(data["expires_in"])
        except (KeyError, ValueError):
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(31080))
            raise

        tools.copy2clip(user_code)

        qr_image = tools.make_qr(verification_uri, "simkl_qr.png")

        from resources.lib.gui.windows.qr_auth_window import QRAuthWindow

        window = QRAuthWindow("qr_auth_window.xml", g.ADDON_PATH)
        window.set_title(g.get_language_string(31074))
        window.set_qr_image(qr_image)
        window.set_details(
            g.get_language_string(31075).format(verification_uri),
            g.get_language_string(31076).format(user_code),
        )
        window_thread = threading.Thread(target=window.doModal)
        window_thread.start()

        failed = False
        try:
            while not failed and self.username is None and token_ttl > 0 and not window.canceled_by_user:
                xbmc.sleep(1000)
                if token_ttl % interval == 0:
                    failed = self._auth_poll(user_code)
                minutes, seconds = divmod(max(token_ttl, 0), 60)
                window.set_status(f"{minutes:02d}:{seconds:02d}")
                token_ttl -= 1
        finally:
            window.close()
            window_thread.join(5)
            del window

        if not failed and self.username:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(31078))
            self._sync_simkl_user_data_if_required()

    def _auth_poll(self, user_code):
        """
        Polls a single PIN check. Simkl distinguishes pending/success/expired by JSON body,
        not HTTP status (unlike Trakt's device flow) - see simkl.apib's PIN polling docs.
        :return: True to stop polling (success or unrecoverable), False to keep polling
        """
        response = self.get(f"oauth/pin/{user_code}")
        if not response.ok:
            return False
        try:
            data = response.json()
        except ValueError:
            return False

        if data.get("access_token"):
            return self._auth_success(data)
        if "device_code" in data:
            # original code expired/was consumed; server silently issued a new one the
            # user was never shown, so continuing to poll here can never succeed
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(31081))
            return True
        return False

    def _auth_success(self, data):
        self._save_settings(data)
        username = self.get_username()
        self.username = username
        g.set_setting(self.username_setting_key, username or "")
        return False

    def _sync_simkl_user_data_if_required(self):
        # Synchronise Simkl Database with new user (mirrors Trakt's
        # _sync_trakt_user_data_if_required)
        from resources.lib.database.simkl_sync import activities

        database = activities.SimklSyncDatabase()
        if database.activities["simkl_username"] != self.username:
            database.flush_activities()
            database.set_simkl_user(self.username)
            xbmc.executebuiltin(f'RunPlugin("{g.BASE_URL}?action=syncSimklActivities")')

    # endregion

    # region settings
    def _save_settings(self, data):
        if "access_token" in data:
            g.set_setting("simkl.auth", data["access_token"])
            self.access_token = data["access_token"]
        expires_in = data.get("expires_in", 157680000)
        self.token_expires = time.time() + expires_in
        g.set_setting("simkl.expires", str(int(self.token_expires)))

    def _load_settings(self):
        self.client_id = g.get_setting(
            "simkl.clientid",
            "59dfdc579d244e1edf6f89874d521d37a69a95a1abd349910cb056a1872ba2c8",
        )
        self.client_secret = g.get_setting("simkl.secret", "")
        self.access_token = g.get_setting("simkl.auth")
        self.token_expires = g.get_float_setting("simkl.expires")
        self.username = g.get_setting(self.username_setting_key)
        self.account_id = g.get_setting("simkl.account_id")

    # endregion

    @simkl_guard_response
    def get(self, url, **params):
        """
        Performs a GET request to specified endpoint and returns response
        :param url: endpoint to perform request against
        :param params: URL params for request
        :return: request response
        """
        timeout = params.pop("timeout", 10)
        params.update(self._default_params())
        return self.session.get(
            parse.urljoin(self.ApiUrl, url),
            params=params,
            headers=self._get_headers(),
            timeout=timeout,
        )

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
            g.log(f"Failed to contact Simkl: {e}", "error")
            return None
        if response is None or not response.ok:
            return None
        try:
            return response.json()
        except ValueError:
            return None

    def get_json_or_raise(self, url, **params):
        """
        Performs a GET request to specified endpoint and returns JSON response.
        Unlike get_json(), raises on a genuine failure (non-ok status,
        unparseable body) instead of returning None - so a legitimate `null`
        JSON body (Simkl's documented empty-result convention for some
        endpoints, e.g. sync/all-items/{type}/{status}) can be trusted by the
        caller as confirmed data, not mistaken for a failed request. A
        connection-level exception from self.get() is left to propagate as-is
        (already logged by simkl_guard_response).
        :param url: endpoint to perform request against
        :param params: URL params for request
        :return: JSON response, which may legitimately be None
        """
        response = self.get(url, **params)
        if response is None or not response.ok:
            raise UnexpectedResponse(response)
        try:
            return response.json()
        except ValueError as e:
            raise UnexpectedResponse(response) from e

    @simkl_guard_response
    def post(self, url, data=None, **params):
        """
        Performs a POST request to the specified endpoint and returns response
        :param url: URL endpoint to perform request to
        :param data: POST data to send to endpoint
        :param params: URL params for request
        :return: requests response
        """
        timeout = params.pop("timeout", 10)
        params.update(self._default_params())
        return self.session.post(
            parse.urljoin(self.ApiUrl, url),
            json=data,
            params=params,
            headers=self._get_headers(),
            timeout=timeout,
        )

    def post_json(self, url, data=None, **params):
        """
        Performs a POST request to specified endpoint and returns JSON response.
        Wraps self.post() in the same try/except get_json() uses, not MDBListAPI's
        post_json() shape - MDBListAPI.post() catches its own connection errors and
        returns None, but SimklAPI.post() is @simkl_guard_response-decorated like get()
        and can raise (the decorator only swallows nothing - it re-raises after logging).
        :param url: endpoint to perform request against
        :param data: POST data to send to endpoint
        :param params: URL params for request
        :return: JSON response, or None on failure
        """
        try:
            response = self.post(url, data, **params)
        except Exception as e:
            g.log(f"Failed to contact Simkl: {e}", "error")
            return None
        if response is None or not response.ok:
            return None
        try:
            return response.json()
        except ValueError:
            return None

    @simkl_guard_response
    def delete(self, url, **params):
        """
        Performs a DELETE request to the specified endpoint and returns response
        :param url: endpoint to perform request against
        :param params: URL params for request
        :return: request response
        """
        timeout = params.pop("timeout", 10)
        params.update(self._default_params())
        return self.session.delete(
            parse.urljoin(self.ApiUrl, url),
            params=params,
            headers=self._get_headers(),
            timeout=timeout,
        )

    def account_info_to_dialog(self):
        """
        Shows the signed-in Simkl account (username, account id/type, time zone, join date) in a select dialog.
        Mirrors Account Manager's Simkl Account Info. Reads only: unlike get_username() it does not cache the
        account id into settings.
        """
        title = f"{g.ADDON_NAME}: Simkl Account"
        saved_user = g.get_setting(self.username_setting_key)

        def _offline(reason):
            items = [f"Username:  {saved_user}"] if saved_user else []
            items.append(f"Status:  Offline ({reason})")
            xbmcgui.Dialog().select(title, items)

        try:
            if not self.access_token:
                xbmcgui.Dialog().ok(g.ADDON_NAME, "Simkl: Not authorized - authorize from settings.")
                return
            response = self.post("users/settings")
            if response is None or response.status_code != 200:
                status = getattr(response, "status_code", None)
                g.log(f"Simkl account info unavailable: HTTP {status}", "warning")
                _offline(f"HTTP {status} from Simkl" if status else "no response from Simkl")
                return
            try:
                data = response.json()
            except ValueError:
                data = None
            if not isinstance(data, dict):
                _offline("unreadable response from Simkl")
                return
            user = data.get("user") or {}
            account = data.get("account") or {}
            items = [f"Username:  {user.get('name') or saved_user or 'N/A'}"]
            if account.get("id"):
                items.append(f"Account ID:  {account['id']}")
            if account.get("type"):
                items.append(f"Account type:  {str(account['type']).capitalize()}")
            if account.get("timezone"):
                items.append(f"Timezone:  {account['timezone']}")
            if user.get("joined_at"):
                items.append(f"Joined:  {str(user['joined_at'])[:19].replace('T', ' ').replace('Z', '')}")
            items.append("Status:  Online")
            xbmcgui.Dialog().select(title, items)
        except Exception as e:
            g.log(f"Simkl account_info_to_dialog error: {type(e).__name__}: {e}", "error")
            _offline("Simkl unreachable")

    def get_username(self):
        """
        Fetch current signed in user's username, caching numeric account id as a side effect
        :return: string username or None
        """
        response = self.post("users/settings")
        if not response.ok:
            return None
        data = response.json()
        self.account_id = data.get("account", {}).get("id")
        if self.account_id:
            g.set_setting("simkl.account_id", str(self.account_id))
        return data.get("user", {}).get("name")
