import sys


def _stdlib_first():
    # Kodi puts every add-on library folder ahead of the standard library. On Android those folders are on slow
    # external storage and a fresh interpreter lists each one on its first import, so look in the standard library
    # and Seren's own folders first. Same reorder TMDb Helper 7.0.6 ships; harmless when run again under
    # reuselanguageinvoker (already in order). Seren's Shield gain is unmeasured.
    try:
        import os

        std = os.path.normcase(os.path.normpath(os.path.dirname(os.__file__)))
        zipdir = os.path.dirname(std)

        def in_std(p):
            n = os.path.normcase(os.path.normpath(p))
            if "packages" in os.path.basename(n):
                return False  # site-packages / dist-packages hold third-party code that add-on libraries must override
            return n == std or n.startswith(std + os.sep) or (n.endswith(".zip") and os.path.dirname(n) == zipdir)

        own = ("plugin.video.seren", "script.module.requests", "script.module.beautifulsoup4", "script.module.unidecode",
               "script.module.myconnpy", "script.module.curl_cffi")
        front = [p for p in sys.path if in_std(p)]
        need = [p for p in sys.path if p not in front and any(name in p for name in own)]
        sys.path[:] = front + need + [p for p in sys.path if p not in front and p not in need]
    except Exception:
        pass


_stdlib_first()
del _stdlib_first

from resources.lib.modules import router
from resources.lib.modules.globals import g
from resources.lib.modules.serenMonitor import ONWAKE_NETWORK_UP_DELAY
from resources.lib.modules.timeLogger import TimeLogger


def _sleeping_retry_handler():
    sleeping = False

    if g.PLATFORM == "android":
        attempts = 0
        while (
            attempts <= ONWAKE_NETWORK_UP_DELAY
            and (sleeping := g.get_bool_runtime_setting("system.sleeping", False))
            and not g.wait_for_abort(1)
        ):
            attempts += 1
        if sleeping and not g.abort_requested():
            g.log(
                f"Ignoring {g.REQUEST_PARAMS.get('action', '')} plugin action as system is supposed to be \"sleeping\"",
                "info",
            )

    return not sleeping


def seren_endpoint():
    try:
        g.init_globals(sys.argv)

        if _sleeping_retry_handler() and not g.abort_requested():
            with TimeLogger(f"{g.REQUEST_PARAMS.get('action', '')}"):
                router.dispatch(g.REQUEST_PARAMS)

    except Exception:
        g.cancel_directory()
        raise

    finally:
        g.deinit()


if __name__ == "__main__":  # pragma: no cover
    seren_endpoint()
