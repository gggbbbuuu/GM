from typing import Callable, Optional, Dict
from .models import *
from concurrent.futures import ThreadPoolExecutor
import xbmcaddon

_MODULE_ADDON = xbmcaddon.Addon("script.module.jetextractors")

_extractor_cache: Dict[str, JetExtractor] = {}
_cache_initialized = False

def _version_tuple(version_str: str) -> tuple:
    try:
        return tuple(int(x) for x in version_str.split("."))
    except Exception:
        return (0, 0, 0)

def get_extractors() -> List[JetExtractor]:
    global _cache_initialized
    from . import extractors
    from .config import get_config

    conf = get_config()
    if not conf:
        raise Exception("No config available")

    if "min_version" in conf:
        module_version = _MODULE_ADDON.getAddonInfo("version")
        if _version_tuple(module_version) < _version_tuple(conf["min_version"]):
            raise Exception(f"Module too old: v{module_version} < v{conf['min_version']}")

    extractor_list = []
    for cls in JetExtractor.subclasses:
        name = cls.__name__
        if name not in _extractor_cache:
            ext = cls()
            if name in conf.get("domains", {}):
                ext.domains = conf["domains"][name]
            _extractor_cache[name] = ext
        else:
            ext = _extractor_cache[name]
        extractor_list.append(ext)
    
    _cache_initialized = True
    return extractor_list


def get_extractor(name: str) -> Optional[JetExtractor]:
    if name in _extractor_cache:
        return _extractor_cache[name]
    
    from . import extractors
    from .config import get_config
    
    conf = get_config()
    for cls in JetExtractor.subclasses:
        ext_instance = cls()
        if ext_instance.name == name:
            if conf and cls.__name__ in conf.get("domains", {}):
                ext_instance.domains = conf["domains"][cls.__name__]
            _extractor_cache[cls.__name__] = ext_instance
            return ext_instance
    return None


def find_extractor(url: JetLink) -> Optional[JetExtractor]:
    for e in get_extractors():
        if e.is_available(url):
            return e
    return None


def search_extractors(query: str, exclude: Optional[List[str]] = None, include: Optional[List[str]] = None, progress: Callable[[JetExtractorSearchProgress], None] = None, timeout: int = 15) -> List[JetLink]:
    query = query.lower()
    res: list[JetItem] = []
    extractors = filter(
        lambda e: not (
            e.disabled or
            e.resolve_only or
            (exclude is not None and e.name in exclude) or
            (include is not None and len(include) > 0 and e.name not in include)
        ),
        get_extractors()
    )
    
    prog = JetExtractorSearchProgress()
    with ThreadPoolExecutor() as executor:
        threads: List[Tuple[str, object]] = []
        for e in extractors:
            eprog = JetExtractorProgress(event=prog.event)
            prog.extractors[e.name] = eprog
            threads.append((e.name, executor.submit(e.get_items, progress=eprog)))
        prog.total = len(threads)

        for name, thread in threads:
            try:
                items_raw = thread.result(timeout=timeout)
                items = list(filter(lambda x: query in x.title.lower() or query in (x.league.lower() if x.league is not None else ""), items_raw))
                for item in items:
                    item.extractor = name
            except Exception:
                items = []
            res.extend(items)
            prog.links += len(items)
            del prog.extractors[name]
            if progress is not None:
                progress(prog)

    return res


def iframe_extractor(url: str) -> List[JetLink]:
    from .util.find_iframes import find_iframes
    iframes = [JetLink(u) if not isinstance(u, JetLink) else u for u in find_iframes(url, "", [], [])]
    for iframe in iframes:
        if "|" in iframe.address and iframe.headers != {}:
            iframe.address = iframe.address.split("|")[0]
        if "?auth" in iframe.address and "premium" in iframe.address:
            iframe.address = iframe.address.split("?auth")[0]
    return iframes

