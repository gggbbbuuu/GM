import os
import importlib
import traceback
import xbmc

package_dir = os.path.dirname(__file__)

__all__ = []
for filename in os.listdir(package_dir):
    if filename.endswith(".py") and not filename.startswith("__"):
        module_name = filename[:-3]
        __all__.append(module_name)

for module in __all__:
    try:
        importlib.import_module(f".{module}", package=__name__)
    except ImportError:
        xbmc.log(
            f"Warning: Could not import {module}\n{traceback.format_exc()}",
            xbmc.LOGERROR
        )
    except Exception:
        xbmc.log(
            f"Error while importing {module}\n{traceback.format_exc()}",
            xbmc.LOGERROR
        )