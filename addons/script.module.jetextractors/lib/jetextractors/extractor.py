from typing import Callable, Optional
from .models import *
from concurrent.futures import ThreadPoolExecutor

def get_extractors() -> List[JetExtractor]:
    from . import extractors
    from .config import get_config
    classes = JetExtractor.subclasses
    extractor_list = []
    conf = get_config()
    
    for extractor in classes:
        ext = extractor()
        if extractor.__name__ in conf.get("domains", {}):
            ext.domains = conf["domains"][extractor.__name__]
        extractor_list.append(ext)
    return extractor_list


def get_extractor(name: str) -> Optional[JetExtractor]:
    for extractor in get_extractors():
        if extractor.name == name:
            return extractor
    return None


def find_extractor(url: JetLink) -> Optional[JetExtractor]:
    for e in get_extractors():
        if e.is_available(url):
            return e
    return None


def search_extractors(query: str, exclude: Optional[List[str]] = None, include: Optional[List[str]] = None, progress: Callable[[JetExtractorSearchProgress], None] = None) -> List[JetLink]:
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
                items = list(filter(lambda x: query in x.title.lower() or query in (x.league.lower() if x.league is not None else ""), thread.result()))
                for item in items:
                    item.extractor = name
            except:
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

