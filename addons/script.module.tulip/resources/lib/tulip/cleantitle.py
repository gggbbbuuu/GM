# -*- coding: utf-8 -*-

'''
    Tulip library
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re
import unicodedata
from html import unescape


def get(title, lower=True):

    if title is None:
        return

    title = re.sub(r'&#(\d+);', '', title)
    title = re.sub(r'(&#[0-9]+)([^;^0-9]+)', '\\1;\\2', title)
    title = re.sub(r'\n|([[].+?[]])|([(].+?[)])|\s(vs|v[.])\s|([:;\-,\'\s.?])|\s', '', title)

    if lower:

        title = title.lower()

    return title


def query(title):

    if title is None:
        return

    title = title.replace("'", '').rsplit(':', 1)[0]

    return title


def normalize(title):

    if not title:
        return title

    try:
        if isinstance(title, bytes):
            title = title.decode('utf-8', 'ignore')
        return unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('utf-8')
    except Exception:
        return title


def strip_accents(string):

    result = ''.join(c for c in unicodedata.normalize('NFD', string) if unicodedata.category(c) != 'Mn')

    return result


def transliterate(title):

    """
    Transliterate Greek characters to Latin (Greeklish).
    Uses strip_accents and normalize to return clean ASCII.
    """

    if not title:
        return title

    if isinstance(title, bytes):
        try:
            title = title.decode('utf-8', 'ignore')
        except Exception:
            return title

    text = strip_accents(title)

    # αυ, ευ, ηυ handling:
    # af/ef/if before voiceless (θ, κ, ξ, π, σ, ς, τ, φ, χ, ψ) or word boundaries
    # av/ev/iv before vowels or voiced consonants
    voiceless = 'θκξπστφχψΘΚΞΠΣΤΦΧΨ'

    def _replace_av_af(m):
        prefix, u, next_c = m.group(1), m.group(2), m.group(3)
        is_upper = u.isupper()
        is_voiceless = next_c in voiceless or not next_c.strip()
        v_letter = ('F' if is_upper else 'f') if is_voiceless else ('V' if is_upper else 'v')
        return prefix + v_letter + next_c

    text = re.sub(r'([αεηΑΕΗ])([υΥ])([θκξπστφχψΘΚΞΠΣΤΦΧΨ]|\b|\s|$|[^\w])', _replace_av_af, text)
    text = re.sub(r'([αεηΑΕΗ])([υΥ])', lambda m: m.group(1) + ('V' if m.group(2).isupper() else 'v'), text)

    # Word-initial vs word-medial digraphs:
    # μπ -> b (initial), mp (medial)
    text = re.sub(r'\bΜ[Ππ]', 'B', text)
    text = re.sub(r'\bμπ', 'b', text)
    text = re.sub(r'Μ[Ππ]', 'MP', text)
    text = re.sub(r'μπ', 'mp', text)

    # ντ -> d (initial), nt (medial)
    text = re.sub(r'\bΝ[Ττ]', 'D', text)
    text = re.sub(r'\bντ', 'd', text)
    text = re.sub(r'Ν[Ττ]', 'NT', text)
    text = re.sub(r'ντ', 'nt', text)

    # γκ -> g (initial), gk (medial)
    text = re.sub(r'\bΓ[Κκ]', 'G', text)
    text = re.sub(r'\bγκ', 'g', text)
    text = re.sub(r'Γ[Κκ]', 'GK', text)
    text = re.sub(r'γκ', 'gk', text)

    # other diphthongs
    diphthongs = [
        ('ου', 'ou'), ('ΟΥ', 'OU'), ('Ου', 'Ou'),
        ('γγ', 'ng'), ('ΓΓ', 'NG'), ('Γγ', 'Ng'),
        ('τσ', 'ts'), ('ΤΣ', 'TS'), ('Τσ', 'Ts'),
        ('τζ', 'tz'), ('ΤΖ', 'TZ'), ('Τζ', 'Tz'),
        ('αι', 'ai'), ('ΑΙ', 'AI'), ('Αι', 'Ai'),
        ('ει', 'ei'), ('ΕΙ', 'EI'), ('Ει', 'Ei'),
        ('οι', 'oi'), ('ΟΙ', 'OI'), ('Οι', 'Oi'),
        ('υι', 'yi'), ('ΥΙ', 'YI'), ('Υι', 'Yi'),
    ]

    for gr, lat in diphthongs:
        text = text.replace(gr, lat)

    # Single character mapping:
    # χ -> x, ξ -> ks, φ -> f
    char_map = str.maketrans({
        'α': 'a', 'β': 'v', 'γ': 'g', 'δ': 'd', 'ε': 'e', 'ζ': 'z',
        'η': 'i', 'θ': 'th', 'ι': 'i', 'κ': 'k', 'λ': 'l', 'μ': 'm',
        'ν': 'n', 'ξ': 'ks', 'ο': 'o', 'π': 'p', 'ρ': 'r', 'σ': 's',
        'ς': 's', 'τ': 't', 'υ': 'y', 'φ': 'f', 'χ': 'x', 'ψ': 'ps',
        'ω': 'o',
        'Α': 'A', 'Β': 'V', 'Γ': 'G', 'Δ': 'D', 'Ε': 'E', 'Ζ': 'Z',
        'Η': 'I', 'Θ': 'Th', 'Ι': 'I', 'Κ': 'K', 'Λ': 'L', 'Μ': 'M',
        'Ν': 'N', 'Ξ': 'Ks', 'Ο': 'O', 'Π': 'P', 'Ρ': 'R', 'Σ': 'S',
        'Τ': 'T', 'Υ': 'Y', 'Φ': 'F', 'Χ': 'X', 'Ψ': 'Ps', 'Ω': 'O',
    })

    text = text.translate(char_map)

    return normalize(text)


def stripTags(html):

    sub_start = html.find("<")
    sub_end = html.find(">")
    while sub_end > sub_start > -1:
        html = html.replace(html[sub_start:sub_end + 1], "").strip()
        sub_start = html.find("<")
        sub_end = html.find(">")

    return html


def replaceHTMLCodes(txt):

    if not txt:
        return txt

    txt = re.sub(r'(&#[0-9]+)([^;^0-9]+)', r'\1;\2', txt)
    txt = unescape(txt)
    txt = txt.replace('&#8482;', '(TM)').replace('&#169;', '(c)').replace('&#174;', '(r)')

    return txt


__all__ = ['get', 'replaceHTMLCodes', 'query', 'normalize', 'strip_accents', 'stripTags', 'transliterate']
