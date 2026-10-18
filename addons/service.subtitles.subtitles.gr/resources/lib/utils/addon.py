# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re, unicodedata
import shutil
import threading
from shutil import copy
from os.path import splitext, exists, split as os_split
from resources.lib.providers import s4f, subtitlesgr, subztv, yifi, tvsubs, moviesubs, subdl, addic7ed
from resources.lib.utils import translator
from resources.lib.utils.tools import Cancelled, Gated
from tulip import kodi as control
from tulip.kodi import i18n as lang
from tulip.log import log as log_debug
from urllib.parse import urlencode, unquote_plus

try:
    from fuzzywuzzy import fuzz
    ratio = fuzz.ratio
except ImportError:
    from difflib import SequenceMatcher

    def ratio(a, b):
        return int(SequenceMatcher(None, a, b).ratio() * 100)


if control.condVisibility('Player.HasVideo'):
    infolabel_prefix = 'VideoPlayer'
else:
    infolabel_prefix = 'ListItem'

# English-only result sources (translation origins). Everything else is
# native Greek. Used both for the language flag above and for ranking
# Greek results ahead of English ones below.
TR_SOURCES = ('subdl_tr', 'tvsubs_tr', 'moviesubs_tr', 'yifi_tr', 'addic7ed')


def _lang_rank(item):

    '''Saved first, then native Greek, then English translations.'''

    if item['source'] == 'saved':
        return -1

    return 1 if item['source'] in TR_SOURCES else 0


# Shown on the progress dialog while a source is being queried.
SOURCE_LABELS = {
    'subtitlesgr': 'Subtitles.gr',
    'subztv': 'GreekSubs.net',
    's4f': 'Subs4Free',
    's4f_series': 'Subs4Series',
    'yifi': 'YIFI',
    'tvsubs': 'TVsubtitles.net',
    'moviesubs': 'Moviesubtitles.org',
    'subdl': 'SubDL',
    'yifi_tr': 'YIFI',
    'subdl_tr': 'SubDL',
    'tvsubs_tr': 'TVsubtitles.net',
    'moviesubs_tr': 'Moviesubtitles.org',
    'addic7ed': 'Addic7ed',
    'saved': 'Saved subtitles',
}

# The progress dialog is shown immediately on every search, no delay.
PROGRESS_DELAY = 0

# Upper bound on waiting for stragglers. Generous enough for the slow Greek
# hosts, short enough that a stalled one cannot freeze the modal dialog.
SEARCH_TIMEOUT = 60.0


class Sources(object):

    '''
    Runs the provider calls on daemon threads.

    concurrent.futures was doing this, but its worker threads are non-daemon,
    so Python's atexit hook joins them during interpreter shutdown. With slow
    hosts (subdl and subs4series both sit behind Cloudflare) a pending request
    kept Kodi alive on quit, which presented as a hang. Daemon threads are
    simply abandoned at exit instead.

    Deliberately no thread pool: there are at most a handful of sources and
    each does its own blocking I/O, so one thread per source is enough.
    '''

    def __init__(self, jobs, sink):

        self.jobs = jobs
        self.sink = sink
        self.total = len(jobs)
        self.done = 0
        self._last = ''
        self.lock = threading.Lock()

    def _run(self, source, call):

        try:
            item = call()
        except Exception as e:
            log_debug('{0} raised while searching: {1}'.format(source, e))
            item = None

        with self.lock:
            self.done += 1
            self._last = source

            if item:
                self.sink.extend(item)

    def start(self):

        for source, call in self.jobs:

            thread = threading.Thread(
                target=self._run, args=(source, call), daemon=True,
                # Distinctive name so a thread dump can tell our workers apart
                # from every other addon's default Thread-N threads.
                name='SubtitlesGr-{0}'.format(source)
            )
            thread.start()

    def drain(self, dialog):

        '''
        Waits for the sources, but not forever.

        A stalled Cloudflare host can leave a provider blocked well past any
        sensible wait, and the progress dialog is modal, so an unbounded wait
        would freeze the UI until the user force-quits. After SEARCH_TIMEOUT
        the results gathered so far are returned and the stragglers are left
        to die as daemon threads.
        '''

        waited = 0.0

        while self.done < self.total and waited < SEARCH_TIMEOUT:

            try:
                if control.aborted():
                    log_debug('Search cut short by Kodi shutdown; keeping partial results')
                    break
            except Exception:
                pass

            with self.lock:
                done, source = self.done, self._last

            dialog.update(
                int(done * 100 / self.total),
                '{0}  ({1}/{2})'.format(
                    SOURCE_LABELS.get(source, source), done, self.total
                )
            )
            control.sleep(100)
            waited += 0.1

        if self.done < self.total:

            log_debug(
                'Search gave up after {0:.0f}s with {1}/{2} sources answered'.format(
                    SEARCH_TIMEOUT, self.done, self.total
                )
            )

    def collect(self):

        '''
        Starts every source and blocks until all of them have reported.

        The dialog is delayed (PROGRESS_DELAY) because a cache hit returns
        instantly and a dialog that flashes up and vanishes reads as a glitch.
        '''

        self.start()

        with control.ProgressDialog(
            heading=lang(30281), line1=lang(30282), timer=PROGRESS_DELAY
        ) as dialog:

            self.drain(dialog)


class Search:

    def __init__(self, syshandle, sysaddon, langs, action):

        self.list = []
        self.query = None
        self.query_imdb = None
        self.syshandle = syshandle
        self.sysaddon = sysaddon
        self.langs = langs
        self.action = action

    def run(self, query=None):

        if 'Greek' not in str(self.langs).split(','):

            control.directory(self.syshandle)
            control.infoDialog(lang(30002))

            return

        dup_removal = False

        try:
            imdb = control.infoLabel('{0}.IMDBNumber'.format(infolabel_prefix)) or '0'
        except Exception:
            imdb = '0'

        def _imdb_query(base):
            return '{0}/imdb={1}'.format(base, imdb)

        # English fallback jobs and the saved-scan query, filled per branch
        # below; consumed once after the Greek pass.
        en_jobs = []
        saved_query = None

        if not query:

            title = control.infoLabel('{0}.Title'.format(infolabel_prefix))

            title = match_title = re.sub(r'\[/?COLOR.*?\]', '', title)

            if True:

                if re.search(r'[^\x00-\x7F]+', title) is not None:

                    title = control.infoLabel('{0}.OriginalTitle'.format(infolabel_prefix))

                title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii')
                title = re.sub(r'\[/?COLOR.*?\]', '', title)
                year = control.infoLabel('{0}.Year'.format(infolabel_prefix))
                tvshowtitle = control.infoLabel('{0}.TVshowtitle'.format(infolabel_prefix))
                season = control.infoLabel('{0}.Season'.format(infolabel_prefix))

                if len(season) == 1:

                    season = '0' + season

                episode = control.infoLabel('{0}.Episode'.format(infolabel_prefix))

                if len(episode) == 1:
                    episode = '0' + episode

                if 's' in episode.lower():
                    season, episode = '0', episode[-1:]

                if tvshowtitle != '':  # episode

                    title_query = '{0} {1}'.format(tvshowtitle, title)
                    season_episode_query = '{0} S{1} E{2}'.format(tvshowtitle, season, episode)
                    season_episode_query_nospace = '{0} S{1}E{2}'.format(tvshowtitle, season, episode)

                    threads = [
                        ('subtitlesgr', lambda: self.subtitlesgr(season_episode_query_nospace)),
                        ('s4f_series', lambda: self.s4f_series(_imdb_query(season_episode_query_nospace))),
                        ('subztv', lambda: self.subztv(_imdb_query(season_episode_query_nospace))),
                        ('tvsubs', lambda: self.tvsubs(_imdb_query(season_episode_query_nospace))),
                        ('subdl', lambda: self.subdl(_imdb_query(season_episode_query_nospace)))
                    ]

                    en_jobs = [
                        ('subdl_tr', lambda: self.subdl_en(_imdb_query(season_episode_query_nospace))),
                        ('tvsubs_tr', lambda: self.tvsubs_en(_imdb_query(season_episode_query_nospace))),
                        ('addic7ed', lambda: self.addic7ed(season_episode_query_nospace)),
                    ]

                    saved_query = season_episode_query_nospace

                    dup_removal = True

                    log_debug('Dual query used for subtitles search: ' + title_query + ' / ' + season_episode_query)

                    if control.setting('queries') == 'true':

                        threads.extend(
                            [
                                ('subtitlesgr', lambda: self.subtitlesgr(title_query)),
                                ('subtitlesgr', lambda: self.subtitlesgr(season_episode_query)),
                                ('s4f_series', lambda: self.s4f_series(_imdb_query(title_query))),
                                ('subztv', lambda: self.subztv(_imdb_query(title_query))),
                                ('subdl', lambda: self.subdl(_imdb_query(title_query)))
                            ]
                        )

                elif year != '':  # movie

                    query = '{0} ({1})'.format(title, year)

                    threads = [
                        ('subtitlesgr', lambda: self.subtitlesgr(query)),
                        ('s4f', lambda: self.s4f(_imdb_query(query))),
                        ('subztv', lambda: self.subztv(_imdb_query(query))),
                        ('yifi', lambda: self.yifi(_imdb_query(query))),
                        ('moviesubs', lambda: self.moviesubs(_imdb_query(query))),
                        ('subdl', lambda: self.subdl(_imdb_query(query)))
                    ]

                    en_jobs = [
                        ('subdl_tr', lambda: self.subdl_en(_imdb_query(query))),
                        ('moviesubs_tr', lambda: self.moviesubs_en(_imdb_query(query))),
                        ('yifi_tr', lambda: self.yifi_en(_imdb_query(query))),
                    ]

                    saved_query = query

                else:  # file

                    query, year = control.cleanmovietitle(title)

                    if year != '':

                        query = '{0} ({1})'.format(query, year)

                    threads = [
                        ('subtitlesgr', lambda: self.subtitlesgr(query)),
                        ('s4f', lambda: self.s4f(_imdb_query(query))),
                        ('subztv', lambda: self.subztv(_imdb_query(query))),
                        ('yifi', lambda: self.yifi(_imdb_query(query))),
                        ('moviesubs', lambda: self.moviesubs(_imdb_query(query))),
                        ('subdl', lambda: self.subdl(_imdb_query(query)))
                    ]

                    en_jobs = [
                        ('subdl_tr', lambda: self.subdl_en(_imdb_query(query))),
                        ('moviesubs_tr', lambda: self.moviesubs_en(_imdb_query(query))),
                        ('yifi_tr', lambda: self.yifi_en(_imdb_query(query))),
                    ]

                    saved_query = query

                if control.setting('translate') == 'true':

                    log_debug('Translate enabled, querying English sources too')

                    threads.extend(en_jobs)

                Sources(threads, self.list).collect()

                if not dup_removal:

                    log_debug('Query used for subtitles search: ' + query)

                self.query = str(query) if query is not None else None
                self.query_imdb = _imdb_query(self.query) if self.query else None

        else:  # Manual query

            query = match_title = str(query)

            threads = [
                ('subtitlesgr', lambda: self.subtitlesgr(query)),
                ('s4f', lambda: self.s4f(_imdb_query(query))),
                ('s4f_series', lambda: self.s4f_series(_imdb_query(query))),
                ('subztv', lambda: self.subztv(_imdb_query(query))),
                ('yifi', lambda: self.yifi(_imdb_query(query))),
                ('tvsubs', lambda: self.tvsubs(_imdb_query(query))),
                ('moviesubs', lambda: self.moviesubs(_imdb_query(query))),
                ('subdl', lambda: self.subdl(_imdb_query(query)))
            ]

            en_jobs = [
                ('subdl_tr', lambda: self.subdl_en(_imdb_query(query))),
                ('tvsubs_tr', lambda: self.tvsubs_en(_imdb_query(query))),
                ('moviesubs_tr', lambda: self.moviesubs_en(_imdb_query(query))),
                ('yifi_tr', lambda: self.yifi_en(_imdb_query(query))),
                ('addic7ed', lambda: self.addic7ed(query)),
            ]

            saved_query = query

            if control.setting('translate') == 'true':

                threads.extend(en_jobs)

            Sources(threads, self.list).collect()

        if saved_query is not None:

            self.list.extend(self._saved_scan(saved_query))

        if len(self.list) == 0:

            control.directory(self.syshandle)

            return

        f = []

        # noinspection PyUnresolvedReferences
        f += [i for i in self.list if i['source'] == 'saved']
        f += [i for i in self.list if i['source'] == 'subtitlesgr']
        f += [i for i in self.list if i['source'] == 'subztv']
        f += [i for i in self.list if i['source'] == 's4f']
        f += [i for i in self.list if i['source'] == 's4f_series']
        f += [i for i in self.list if i['source'] == 'yifi']
        f += [i for i in self.list if i['source'] == 'tvsubs']
        f += [i for i in self.list if i['source'] == 'moviesubs']
        f += [i for i in self.list if i['source'] == 'subdl']
        f += [i for i in self.list if i['source'] == 'yifi_tr']
        f += [i for i in self.list if i['source'] == 'subdl_tr']
        f += [i for i in self.list if i['source'] == 'tvsubs_tr']
        f += [i for i in self.list if i['source'] == 'moviesubs_tr']
        f += [i for i in self.list if i['source'] == 'addic7ed']

        self.list = f

        if dup_removal:

            self.list = [dict(t) for t in {tuple(d.items()) for d in self.list}]

        for i in self.list:

            try:

                if i['source'] == 'subztv':
                    i['name'] = u'[SUBZ] {0}'.format(i['name'])
                elif i['source'] == 's4f':
                    i['name'] = u'[S4F] {0}'.format(i['name'])
                elif i['source'] == 's4f_series':
                    i['name'] = u'[S4S] {0}'.format(i['name'])
                elif i['source'] == 'yifi':
                    i['name'] = u'[YIFI] {0}'.format(i['name'])
                elif i['source'] == 'tvsubs':
                    i['name'] = u'[TVSUBS] {0}'.format(i['name'])
                elif i['source'] == 'moviesubs':
                    i['name'] = u'[MSUBS] {0}'.format(i['name'])
                elif i['source'] == 'subdl':
                    i['name'] = u'[SUBDL] {0}'.format(i['name'])
                elif i['source'] == 'yifi_tr':
                    i['name'] = u'[YIFI-TR] {0}'.format(i['name'])
                elif i['source'] == 'subdl_tr':
                    i['name'] = u'[SUBDL-TR] {0}'.format(i['name'])
                elif i['source'] == 'tvsubs_tr':
                    i['name'] = u'[TVSUBS-TR] {0}'.format(i['name'])
                elif i['source'] == 'moviesubs_tr':
                    i['name'] = u'[MSUBS-TR] {0}'.format(i['name'])
                elif i['source'] == 'addic7ed':
                    i['name'] = u'[ADDIC-TR] {0}'.format(i['name'])
                elif i['source'] == 'saved':
                    i['name'] = u'[SAVED] {0}'.format(i['name'])

            except Exception:

                pass

        if control.setting('sorting') == '1':
            key = 'source'
        elif control.setting('sorting') == '2':
            key = 'downloads'
        elif control.setting('sorting') == '3':
            key = 'rating'
        else:
            key = 'title'

        if key == 'source':

            # Canonical source order, Greek providers before English ones.
            # The old reverse-alphabetical sort put yifi_tr/tvsubs_tr on top.
            order = ['saved'] + [s for s in SOURCE_LABELS if s != 'saved']
            rank = {source: index for index, source in enumerate(order)}

            self.list = sorted(self.list, key=lambda k: rank.get(k['source'], 99))

        else:

            if key in ('rating', 'downloads'):

                def sort_key(k):
                    try:
                        return float(k[key])
                    except (TypeError, ValueError):
                        return 0.0

                self.list = sorted(self.list, key=sort_key, reverse=True)
            else:

                def sort_key(k):
                    return str(k[key]).lower()

                self.list = sorted(self.list, key=sort_key)

            # Native Greek first within any ordering; stable sort keeps the
            # chosen ranking inside each language partition.
            self.list = sorted(self.list, key=_lang_rank)

        for i in self.list:

            u = {'action': 'download', 'url': i['url'], 'source': i['source'],
                 'title': i['name']}
            u = '{0}?{1}'.format(self.sysaddon, urlencode(u))

            if i['source'] in TR_SOURCES:
                lang_name, thumb = 'English', 'en'
            else:
                lang_name, thumb = i.get('lang', 'Greek'), i.get('thumb', 'el')

            item = control.item(label=lang_name, label2=i['name'])
            item.setArt({'icon': str(i['rating'])[:1], 'thumb': thumb})
            if ratio(splitext(i['title'].lower())[0], splitext(match_title)[0]) >= int(control.setting('sync_probability')):
                item.setProperty('sync', 'true')
            else:
                item.setProperty('sync', 'false')
            item.setProperty('hearing_imp', i.get('hearing_imp', 'false'))

            control.addItem(handle=self.syshandle, url=u, listitem=item, isFolder=False)

        control.directory(self.syshandle)

    @staticmethod
    def _query_parts(text):

        '''Splits a query into title words plus optional year/season/episode.'''

        text = str(text)

        year = re.search(r'\b(19\d{2}|20\d{2})\b', text)
        year = year.group(1) if year else None

        match = re.search(r'\bS(\d{1,2})[\s.]?E(\d{1,2})\b', text, flags=re.I)

        if match:
            season, episode = int(match.group(1)), int(match.group(2))
        else:
            season = episode = None

        stripped = re.sub(r'\bS\d+E\d+\b|\b\d{4}\b|/imdb=\d*', ' ', text, flags=re.I)
        words = set(re.sub(r'[^a-z0-9 ]+', ' ', stripped.lower()).split())

        return words, year, season, episode

    def _saved_scan(self, query_text):

        '''
        Local subtitles in the output folder matching the query, marked
        [SAVED]. Reuses kept downloads (and past translations) with zero
        network traffic.
        '''

        words, year, season, episode = self._query_parts(query_text)

        if not words:
            return []

        try:
            folder = control.setting('output_folder')

            if folder.startswith('special://'):
                folder = control.transPath(folder)

            _dirs, files = control.listDir(folder)
        except Exception:
            return []

        matches = []

        for name in files:

            if not name.lower().endswith(('.srt', '.sub')):
                continue

            stem = splitext(name)[0]
            flat = re.sub(r'[^a-z0-9]', '', stem.lower())

            if not words <= set(re.sub(r'[^a-z0-9 ]+', ' ', stem.lower()).split()):
                continue

            if year and year not in stem:
                continue

            if season is not None and 's{0:02d}e{1:02d}'.format(season, episode) not in flat:
                continue

            if re.search(r'\b(en|eng|english)\b', stem, flags=re.I):
                lang_name, thumb = 'English', 'en'
            else:
                lang_name, thumb = 'Greek', 'el'

            matches.append(
                {
                    'name': name, 'url': control.join(folder, name), 'source': 'saved',
                    'rating': 5, 'title': name, 'downloads': '0', 'hearing_imp': 'false',
                    'lang': lang_name, 'thumb': thumb,
                }
            )

        if matches:
            log_debug('Saved subtitles matched: {0}'.format(len(matches)))

        return matches

    def subtitlesgr(self, query=None):

        if not query:

            query = self.query

        try:

            if control.setting('subtitles') == 'false':
                raise TypeError

            result = subtitlesgr.Subtitlesgr().get(query)

            return result

        except TypeError:

            pass

    def s4f(self, query=None):

        if not query:

            query = self.query_imdb or self.query

        try:

            if control.setting('s4f') == 'false':
                raise TypeError

            result = s4f.S4f().get(query, mode='movies')

            return result

        except TypeError:

            pass

    def s4f_series(self, query=None):

        if not query:

            query = self.query_imdb or self.query

        try:

            if control.setting('s4f_series') == 'false':
                raise TypeError

            result = s4f.S4f().get(query, mode='series')

            return result

        except TypeError:

            pass

    def subztv(self, query=None):

        if not query:

            query = self.query_imdb or self.query

        try:

            if control.setting('subztv') == 'false':
                raise TypeError

            result = subztv.Subztv().get(query)

            return result

        except TypeError:

            pass

    def moviesubs(self, query=None):

        if not query:

            query = self.query_imdb or self.query

        try:

            if control.setting('moviesubs') == 'false':
                raise TypeError

            result = moviesubs.Moviesubs().get(query)

            return result

        except TypeError:

            pass

    def tvsubs(self, query=None):

        if not query:

            query = self.query_imdb or self.query

        try:

            if control.setting('tvsubs') == 'false':
                raise TypeError

            result = tvsubs.Tvsubs().get(query)

            return result

        except TypeError:

            pass

    def subdl(self, query=None):

        if not query:

            query = self.query_imdb or self.query

        try:

            if control.setting('subdl') == 'false':
                raise TypeError

            result = subdl.Subdl().get(query)

            return result

        except TypeError:

            pass

    def _english(self, call):

        '''
        English listing pass for the translation fallback. Gated on the
        translate toggle alone: the Greek provider toggles do not apply.
        '''

        try:

            if control.setting('translate') == 'false':
                raise TypeError

            return call()

        except TypeError:

            pass

    def subdl_en(self, query=None):

        return self._english(
            lambda: subdl.Subdl().get(query or self.query_imdb or self.query, language='english')
        )

    def tvsubs_en(self, query=None):

        return self._english(
            lambda: tvsubs.Tvsubs().get(query or self.query_imdb or self.query, language='en')
        )

    def moviesubs_en(self, query=None):

        return self._english(
            lambda: moviesubs.Moviesubs().get(query or self.query_imdb or self.query, language='en')
        )

    def addic7ed(self, query=None):

        if not query:

            query = self.query_imdb or self.query

        try:

            if control.setting('translate') == 'false':
                raise TypeError

            if control.setting('addic7ed') == 'false':
                raise TypeError

            result = addic7ed.Addic7ed().get(query)

            return result

        except TypeError:

            pass

    def yifi(self, query=None):

        if not query:

            query = self.query_imdb or self.query

        try:

            if control.setting('yifi') == 'false':
                raise TypeError

            result = yifi.Yifi().get(query)

            return result

        except TypeError:

            pass

    def yifi_en(self, query=None):

        return self._english(
            lambda: yifi.Yifi().get(query or self.query_imdb or self.query, language='english')
        )

class Download:

    def __init__(self, syshandle, sysaddon):

        self.syshandle = syshandle
        self.sysaddon = sysaddon

    # noinspection PyUnboundLocalVariable
    def run(self, url, source, title=None):

        log_debug('Source selected: {0}'.format(source))

        path = control.join(control.dataPath, 'temp')

        shutil.rmtree(control.join(path, ''), ignore_errors=True)
        control.makeFile(control.dataPath)
        control.makeFile(path)

        if control.setting('keep_subs') == 'true':

            if not control.get_info_label('ListItem.Path').startswith('plugin://') and control.setting('destination') == '0':
                output_path = control.get_info_label('Container.FolderPath')
            elif control.setting('output_folder').startswith('special://'):
                output_path = control.transPath(control.setting('output_folder'))
            else:
                output_path = control.setting('output_folder')

            if not exists(output_path):
                control.makeFile(output_path)

        providers = {
            'subtitlesgr': subtitlesgr.Subtitlesgr,
            's4f': s4f.S4f,
            's4f_series': s4f.S4f,
            'subztv': subztv.Subztv,
            'yifi': yifi.Yifi,
            'tvsubs': tvsubs.Tvsubs,
            'moviesubs': moviesubs.Moviesubs,
            'subdl': subdl.Subdl,
        }

        # English sources for the translation fallback: download the English
        # file with the base provider, then machine-translate it.
        tr_sources = {
            'subdl_tr': subdl.Subdl,
            'tvsubs_tr': tvsubs.Tvsubs,
            'moviesubs_tr': moviesubs.Moviesubs,
            'yifi_tr': yifi.Yifi,
            'addic7ed': addic7ed.Addic7ed,
        }

        provider = providers.get(source)

        subtitle = None
        cancelled = False

        if source == 'saved':

            # Local file, no download: just hand back the path, guarding
            # against the entry outliving the file.
            target = unquote_plus(url)

            if exists(target):
                subtitle = target
            else:
                log_debug('Saved subtitle is gone: {0}'.format(target))

        elif source in tr_sources:

            with control.ProgressDialog(
                heading=lang(30283),
                line1=SOURCE_LABELS.get(source, source)
            ) as dialog:

                try:

                    english = tr_sources[source]().download(path, url)

                    if english is None:
                        subtitle = None
                    else:
                        subtitle = self._translate(
                            dialog, path, english, title
                        )

                except Cancelled:

                    log_debug('Translation cancelled by user')

                    subtitle = None
                    cancelled = True

        elif provider is not None:

            try:

                with control.ProgressDialog(
                    heading=lang(30283),
                    line1=SOURCE_LABELS.get(source, source)
                ) as dialog:

                    subtitle = provider().download(path, url)

                    dialog.update(100)

            except Gated:

                # A per-request captcha cannot be solved here, and its address
                # has to stay on screen while the browser does it, so the
                # hand-off runs now that the download dialog has closed.
                subtitle = self._handoff(provider, path, source, url)

        if subtitle is not None:

            if control.setting('keep_subs') == 'true' and source != 'saved':

                # noinspection PyUnboundLocalVariable
                try:
                    if control.setting('destination') in ['0', '2']:
                        if control.infoLabel('{0}.Title'.format(infolabel_prefix)).startswith('plugin://'):
                            copy(subtitle, control.join(output_path, os_split(subtitle)[1]))
                            log_debug('Item currently selected is not a local file, cannot save subtitle next to it')
                        else:
                            output_filename = control.join(
                                    output_path, ''.join(
                                        [
                                            splitext(control.infoLabel('ListItem.FileName'))[0],
                                            splitext(os_split(subtitle)[1])[1]
                                        ]
                                    )
                                )
                            if exists(output_filename):
                                yesno = control.yesnoDialog(lang(30015))
                                if yesno:
                                    copy(subtitle, output_filename)
                            else:
                                copy(subtitle, output_filename)
                            if control.setting('destination') == '2':
                                if control.setting('output_folder').startswith('special://'):
                                    output_path = control.transPath(control.setting('output_folder'))
                                else:
                                    output_path = control.setting('output_folder')
                                copy(subtitle, control.join(output_path, os_split(subtitle)[1]))
                    else:
                        copy(subtitle, control.join(output_path, os_split(subtitle)[1]))
                    control.infoDialog(lang(30008))
                except Exception:
                    control.infoDialog(lang(30013))

            item = control.item(label=subtitle)
            control.addItem(handle=self.syshandle, url=subtitle, listitem=item, isFolder=False)

        elif not cancelled and source != 'saved':

            # Providers signal a failed download by returning None. Without
            # this the progress dialog just closes and nothing else happens,
            # which reads as the addon ignoring the request.
            control.infoDialog(lang(30327) if source == 's4f_series' else lang(30326))

        control.directory(self.syshandle)

    def _handoff(self, provider, path, source, url):

        '''
        Downloads through the user's own browser when a captcha blocks the provider.

        The token is minted per request and answers only the page it was solved
        on, so the file is produced by the browser itself: the listener collects
        the archive address the browser lands on, and that archive is fetched
        here like any other download. Nothing is solved on the user's behalf -
        they tick the box, the address simply crosses over.
        '''

        from resources.lib.utils.s4f_capture import capture

        archive = capture(url)

        if not archive:
            return None

        try:

            with control.ProgressDialog(
                heading=lang(30283),
                line1=SOURCE_LABELS.get(source, source)
            ) as dialog:

                subtitle = provider().download(path, archive)

                dialog.update(100)

        except Gated:

            # A handed-over archive that is gated again means the temp file was
            # already collected; asking for a second browser round would loop.
            log_debug('Handed-over archive is gated again, giving up')

            return None

        return subtitle

    @staticmethod
    def _translate(dialog, path, english, title=None):

        '''
        Machine-translates a downloaded English subtitle to Greek, with
        progress and cancellation on the download dialog. The result keeps
        the listing name it was chosen under, and is always saved to the
        subtitle folder: the wait earns persistence.
        '''

        with open(english, 'rb') as english_file:
            data = english_file.read()

        def _progress(done, total):

            dialog.update(int(done * 100 / total), lang(30323))

        try:
            cancelled = dialog.is_canceled
        except AttributeError:
            cancelled = lambda: False

        greek = translator.translate_srt(
            data, on_progress=_progress, is_cancelled=cancelled
        )

        if title:
            filename = re.sub(r'[\\/:*?"<>|]', '_', unquote_plus(title)).strip()
        else:
            filename = os_split(english)[1]

        # Translated content keeps the input format (SRT stays SRT,
        # MicroDVD stays MicroDVD).
        ext = splitext(english)[1].lower()

        if ext not in ('.srt', '.sub'):
            ext = '.srt'

        filename = re.sub(r'\.(srt|sub)$', '', filename, flags=re.I) + ext

        translated = control.join(path, filename)

        with open(translated, 'wb') as subFile:
            subFile.write(greek)

        try:
            folder = control.setting('output_folder')
            outdir = control.transPath(folder) if folder.startswith('special://') else folder
            control.makeFile(outdir)
            copy(translated, control.join(outdir, os_split(translated)[1]))
        except Exception as e:
            log_debug('Could not save translated subtitle: ' + str(e))

        return translated
