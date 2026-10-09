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
from resources.lib.providers import s4f, subtitlesgr, subztv, yifi, tvsubs, moviesubs, subdl
from tulip import kodi as control
from tulip.kodi import i18n as lang
from tulip.log import log as log_debug
from urllib.parse import urlencode

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

            Sources(threads, self.list).collect()

        if len(self.list) == 0:

            control.directory(self.syshandle)

            return

        f = []

        # noinspection PyUnresolvedReferences
        f += [i for i in self.list if i['source'] == 'subtitlesgr']
        f += [i for i in self.list if i['source'] == 'subztv']
        f += [i for i in self.list if i['source'] == 's4f']
        f += [i for i in self.list if i['source'] == 's4f_series']
        f += [i for i in self.list if i['source'] == 'yifi']
        f += [i for i in self.list if i['source'] == 'tvsubs']
        f += [i for i in self.list if i['source'] == 'moviesubs']
        f += [i for i in self.list if i['source'] == 'subdl']

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

        if key in ('rating', 'downloads'):

            def sort_key(k):
                try:
                    return float(k[key])
                except (TypeError, ValueError):
                    return 0.0
        else:

            def sort_key(k):
                return str(k[key]).lower()

        self.list = sorted(self.list, key=sort_key, reverse=control.setting('sorting') in ['1', '2', '3'])

        for i in self.list:

            u = {'action': 'download', 'url': i['url'], 'source': i['source']}
            u = '{0}?{1}'.format(self.sysaddon, urlencode(u))
            item = control.item(label='Greek', label2=i['name'])
            item.setArt({'icon': str(i['rating'])[:1], 'thumb': 'el'})
            if ratio(splitext(i['title'].lower())[0], splitext(match_title)[0]) >= int(control.setting('sync_probability')):
                item.setProperty('sync', 'true')
            else:
                item.setProperty('sync', 'false')
            item.setProperty('hearing_imp', i.get('hearing_imp', 'false'))

            control.addItem(handle=self.syshandle, url=u, listitem=item, isFolder=False)

        control.directory(self.syshandle)

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

class Download:

    def __init__(self, syshandle, sysaddon):

        self.syshandle = syshandle
        self.sysaddon = sysaddon

    # noinspection PyUnboundLocalVariable
    def run(self, url, source):

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

        provider = providers.get(source)

        subtitle = None

        if provider is not None:

            with control.ProgressDialog(
                heading=lang(30283),
                line1=SOURCE_LABELS.get(source, source)
            ) as dialog:

                subtitle = provider().download(path, url)

                dialog.update(100)

        if subtitle is not None:

            if control.setting('keep_subs') == 'true':

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

        control.directory(self.syshandle)
