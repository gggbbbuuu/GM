import requests
from ..tools import debug_log

def validate_xtream_credentials(address: str, username: str, password: str, timeout: int = 10) -> tuple:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = requests.get(
            f"{address}/player_api.php",
            params={"username": username, "password": password},
            headers=headers,
            timeout=timeout
        )
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"

        user_data = resp.json()
        if not isinstance(user_data, dict):
            return False, "Invalid response from player API"

        info = user_data.get("user_info", {})
        debug_log(f"[Xtream] Validation response for {address}: status={info.get('status')}, max_conn={info.get('max_connections')}")

        if info.get("status") == "Disabled":
            return False, f"Account status: {info.get('status', 'Unknown')}"

        return True, user_data
    except requests.exceptions.ConnectionError:
        return False, "Connection failed - host unreachable"
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def get_xtream_channels(address: str, username: str, password: str, timeout: int = 15) -> list:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
        }
        resp = requests.get(
            f"{address}/panel_api.php",
            params={"username": username, "password": password},
            headers=headers,
            timeout=timeout
        )
        data = resp.json()
        if not isinstance(data, dict):
            return []

        channels = data.get("available_channels", {})
        if isinstance(channels, dict):
            channels = channels.values()

        return [
            {
                "stream_id": ch.get("stream_id"),
                "name": (ch.get("name") or "").strip(),
                "category_name": (ch.get("category_name") or "").strip(),
            }
            for ch in channels
            if ch.get("name", "").strip()
        ]
    except Exception as e:
        debug_log(f"[Xtream] Failed to fetch channels: {e}")
        return []


def build_xtream_stream_url(address: str, username: str, password: str, stream_id: int, proxy: bool = False) -> str:
    base_url = f"{address}/live/{username}/{password}/{stream_id}.m3u8"
    if proxy:
        base_url += f"?username={username}&password={password}"
    return base_url