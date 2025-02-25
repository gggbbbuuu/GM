# -*- coding: utf-8 -*-

import pkgutil
import os

__all__ = [x[1] for x in os.walk(os.path.dirname(__file__))][0]

def sources():
    try:
        sourceDict = []
        for i in __all__:
            for loader, module_name, is_pkg in pkgutil.walk_packages([os.path.join(os.path.dirname(__file__), i)]):
                if is_pkg:
                    continue

                try:
                    module = loader.find_spec(module_name).loader.load_module(module_name)
                    sourceDict.append((module_name, module.source()))
                except AttributeError:
                    module = loader.find_module(module_name).load_module(module_name)
                    sourceDict.append((module_name, module.source()))
                except Exception:
                    from resources.lib.modules import log_utils
                    log_utils.log('Could not load "%s"' % module_name, 1)
                    pass
        return sourceDict
    except:
        return []


