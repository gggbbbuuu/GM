# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    Machine-translation fallback. Downloads an English subtitle and translates
    it to Greek through Google's keyless endpoint, in batches, with progress
    and cancellation.

    Only ever runs at download time for entries explicitly tagged [TR], and
    only when the user enabled the translate toggle.

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re
import json
import urllib.parse

from resources.lib.utils import impersonate
from resources.lib.utils.tools import Cancelled
from tulip.log import log as log_debug


# Cues per request. Verified: 20 cues come back complete in under a second;
# repeated q params do NOT batch (the server answers only the first).
BATCH = 20

# Joins cue texts inside one request. Split on the same marker afterwards.
SEP = '\n<<<>>>\n'

GTX = 'https://translate.googleapis.com/translate_a/single'

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)


def decode_bytes(raw):

    '''Best-effort text out of a subtitle file of unknown encoding.'''

    for encoding in ('utf-8', 'cp1253', 'latin-1'):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, ValueError):
            continue

    return raw.decode('utf-8', errors='replace')


def parse_srt(text):

    '''
    Returns [(index, start, end, text)] cues. Timestamps are kept verbatim;
    only cue text is ever translated.
    '''

    text = text.replace('\r\n', '\n').replace('\r', '\n')

    cues = []

    for block in re.split(r'\n\s*\n', text.strip()):
        lines = block.strip().split('\n')

        if len(lines) < 3 or '-->' not in lines[1]:
            continue

        try:
            index = int(lines[0].strip())
        except (TypeError, ValueError):
            continue

        start, _, end = lines[1].partition('-->')

        cues.append((index, start.strip(), end.strip(), '\n'.join(lines[2:])))

    return cues


def assemble_srt(cues):

    '''Serialises cues back to UTF-8 SRT bytes.'''

    out = []

    for index, start, end, text in cues:
        out.append('{0}\n{1} --> {2}\n{3}'.format(index, start, end, text))

    return ('\n\n'.join(out) + '\n').encode('utf-8')


# MicroDVD (.sub) cues address frames, not time. Frames pass through the
# pipeline untouched and only the text is translated, so no FPS assumption
# is needed anywhere: a .sub in, translated .sub out.


def parse_microdvd(text):

    '''
    Returns [(index, start_frame, end_frame, text)] cues from MicroDVD
    `{start}{end}` lines. `|` separators become line breaks; `{y:i}`/`{c:...}` style
    control tags are left in place for the tag shelter to handle.
    '''

    cues = []
    index = 0

    for line in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):

        match = re.match(r'^\{(\d+)\}\{(\d+)\}(.*)$', line.strip())

        if not match:
            continue

        index += 1

        cues.append(
            (
                index,
                int(match.group(1)),
                int(match.group(2)),
                match.group(3).replace('|', '\n'),
            )
        )

    return cues


def assemble_microdvd(cues):

    '''Serialises cues back to MicroDVD bytes, frames verbatim.'''

    out = []

    for _index, start, end, text in cues:
        out.append('{{{0}}}{{{1}}}{2}'.format(start, end, text.replace('\n', '|')))

    return ('\n'.join(out) + '\n').encode('utf-8')


def detect_format(text):

    ''''srt' for --> cue blocks, 'microdvd' for {n}{m} lines, else None.'''

    if '-->' in text:
        return 'srt'

    if re.search(r'^\{\d+\}\{\d+\}', text, flags=re.M):
        return 'microdvd'

    return None


def _split_tags(text):

    '''
    Splits leading/trailing ASS override tags ({\\an8}, {\\pos...}) off cue
    text. Google mangles these ({\\an8} came back as "{\\ an8}"), while
    HTML tags (<i>, <b>, <font>) survive translation untouched, so only the
    brace tags are sheltered. Mid-line tags stay in the core; positioning
    tags live at the edges, which is the case that matters.
    '''

    prefix, core = '', text

    match = re.match(r'(\s*\{[^}]*\})+', core)

    if match:
        prefix, core = match.group(0), core[match.end():]

    suffix = ''

    if core.strip():
        match = re.search(r'(\s*\{[^}]*\})+\s*$', core)

        if match and match.start() > 0:
            suffix, core = core[match.start():], core[:match.start()]

    return prefix, core, suffix


def _translate_batch(session, texts, target):

    '''
    One request for up to BATCH cue texts, joined with a marker and split
    afterwards. Repeated q params do NOT batch (the server answers only the
    first), hence the delimiter.
    '''

    joined = SEP.join(texts)

    params = 'sl=en&tl={0}&dt=t&q={1}'.format(target, urllib.parse.quote(joined))

    response = session.get('{0}?client=gtx&{1}'.format(GTX, params), timeout=30)

    if response.status_code == 429:
        raise Exception('translation rate limited (HTTP 429)')

    if response.status_code != 200:
        raise Exception('translation failed (HTTP {0})'.format(response.status_code))

    data = json.loads(response.text)

    full = ''.join((seg[0] or '') for seg in (data[0] or []) if seg)

    return [part.strip() for part in full.split('<<<>>>')]


def translate_texts(texts, target='el', on_progress=None, is_cancelled=None):

    '''
    Translates cue texts, honouring cancellation between batches.

    Raises Cancelled when the user aborts, so Download.run treats it like
    dismissing the subtitle picker: quiet, no traceback.
    '''

    if not texts:
        return []

    sess = impersonate.session(timeout=30)

    if sess is None:
        raise Exception('translation needs script.module.curlcffi')

    translated = []

    try:

        batches = [texts[i:i + BATCH] for i in range(0, len(texts), BATCH)]

        for done, batch in enumerate(batches):

            if is_cancelled is not None and is_cancelled():
                raise Cancelled

            parts = _translate_batch(sess, batch, target)

            if len(parts) != len(batch):
                # Never silently misalign cues with translations: a partial
                # batch would shift every later subtitle out of sync.
                raise Exception(
                    'translation batch returned {0} parts for {1} cues'.format(
                        len(parts), len(batch)
                    )
                )

            translated.extend(parts)

            if on_progress is not None:
                on_progress(done + 1, len(batches))

    finally:

        impersonate.close(sess)

    return translated


def translate_srt(data, target='el', on_progress=None, is_cancelled=None):

    '''End to end: subtitle bytes in, translated bytes out, same format.'''

    text = decode_bytes(data)
    kind = detect_format(text)

    if kind == 'microdvd':
        log_debug('Translator: MicroDVD input, frames pass through untouched')
        cues = parse_microdvd(text)
        microdvd = True
    else:
        microdvd = False
        cues = parse_srt(text)

    if not cues:
        raise Exception('no cues found in subtitle file')

    log_debug('Translator: {0} cues to translate'.format(len(cues)))

    # Shelter ASS override tags outside the translated core; cues holding
    # only tags skip the request entirely and keep their original text.
    jobs, passthrough = [], {}

    for number, cue in enumerate(cues):
        prefix, core, suffix = _split_tags(cue[3])

        if core.strip():
            jobs.append((number, prefix, core, suffix))
        else:
            passthrough[number] = cue[3]

    if jobs:
        cores = translate_texts(
            [core for _, _, core, _ in jobs], target=target,
            on_progress=on_progress, is_cancelled=is_cancelled
        )
    else:
        cores = []

    rebuilt = dict(passthrough)

    for (number, prefix, _, suffix), text in zip(jobs, cores):
        rebuilt[number] = prefix + text + suffix

    out = [
        (cues[n][0], cues[n][1], cues[n][2], rebuilt[n]) for n in range(len(cues))
    ]

    if microdvd:
        return assemble_microdvd(out)

    return assemble_srt(out)
