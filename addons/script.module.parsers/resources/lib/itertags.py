# -*- coding: utf-8 -*-

'''
    Tulip library
    Author Twilight0

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
'''

import re
from collections import namedtuple

# A set of HTML tags that are void and don't have a closing tag.
# From: https://developer.mozilla.org/en-US/docs/Web/HTML/Element#void_elements

VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr"
}


def itertags(html, tag):
    """
    Brute force regex based HTML tag parser. This is a rough-and-ready searcher to find HTML tags when
    standards compliance is not required. Will find tags that are commented out, or inside script tag etc.
    Shamelessly taken from streamlink library: https://github.com/streamlink/streamlink

    :param html: HTML page
    :param tag: tag name to find
    :return: generator with Tags
    """
    # This regex finds all opening or self-closing tags.
    # We iterate through these and then find their corresponding closing tags,
    # which allows us to handle nested tags correctly.
    opening_tag_re = re.compile(
        r'''<(?P<tag>[\w:-]+)(?P<attr>.*?)(?P<end>/)?>''',
        re.MULTILINE | re.DOTALL
    )
    attr_re = re.compile(
        r'''\s*(?P<key>[\w-]+)\s*(?:=\s*(?P<quote>["']?)(?P<value>.*?)(?P=quote)\s*)?'''
    )
    Match = namedtuple("Match", "tag attributes text")

    for match in opening_tag_re.finditer(html):
        matched_tag = match.group("tag")

        # Filter for the tag we are interested in
        if not (matched_tag == tag or re.fullmatch(tag, matched_tag)):
            continue

        attrs = dict((a.group("key").lower(), a.group("value")) for a in attr_re.finditer(match.group("attr")))

        # Handle self-closing tags and void elements that don't need a closing tag
        if match.group("end") or matched_tag in VOID_ELEMENTS:
            yield Match(matched_tag, attrs, None)
            continue

        # It's an opening tag. Find its matching closing tag, handling nesting.
        nesting_re = re.compile(fr'</?\s*{re.escape(matched_tag)}\b', re.IGNORECASE | re.DOTALL)

        content_start = match.end()
        depth = 1
        scan_pos = content_start

        try:

            while depth > 0:
                next_tag_match = nesting_re.search(html, scan_pos)
                if not next_tag_match:
                    # Unclosed tag, break and do not yield.
                    break

                if next_tag_match.group(0).startswith('</'):
                    depth -= 1
                else:  # It's another opening tag of the same type
                    depth += 1

                scan_pos = next_tag_match.end()

                if depth == 0:
                    # We found the corresponding closing tag.
                    inner_text = html[content_start:next_tag_match.start()]
                    yield Match(matched_tag, attrs, inner_text)
                    break

        except StopIteration:

            return ()


class LazyResult:
    """
    A lazy-loading, list-like object that wraps a generator.
    The generator is only consumed and converted to a list on first access
    (e.g., indexing, iteration, or getting the length).
    """
    def __init__(self, generator):
        self._generator = generator
        self._list = None

    def _materialize(self):
        """Consumes the generator and stores the items in a list."""
        if self._list is None:
            self._list = list(self._generator)

    def __getitem__(self, key):
        """Enables list-style indexing (e.g., result[0], result[-1])."""
        self._materialize()
        return self._list[key]

    def __iter__(self):
        """Enables iteration (e.g., for item in result:)."""
        self._materialize()
        return iter(self._list)

    def __len__(self):
        """Enables getting the length (e.g., len(result))."""
        self._materialize()
        return len(self._list)

    def __repr__(self):
        """Provides a string representation, will materialize the list."""
        self._materialize()
        return repr(self._list)


def iwrapper(html, tag, attrs=None, ret=False, lazify=False):

    try:

        # Start with the base generator from itertags
        result = itertags(html, tag)

        # If attributes are provided, chain a filtering generator expression
        if isinstance(attrs, dict):

            attrs_to_match = list(attrs.items())
            result = (
                i for i in result if all(
                    any(
                        (attr_key == k or re.fullmatch(attr_key, k)) and (
                            # Value match: if expected value is None, check for an attribute without a value.
                            # Otherwise, treat the expected value as a regex.
                            (v is None) if attr_value is None
                            else re.match(attr_value, v if v is not None else '')
                        )
                        for k, v in i.attributes.items()
                    )
                    for attr_key, attr_value in attrs_to_match
                )
            )

        # If a return attribute is specified, chain another generator expression
        if ret:
            result = (i.attributes[ret] for i in result if ret in i.attributes)

        if lazify:
            return LazyResult(result)
        else:
            return result

    except Exception:
        # If there's an error during generator setup, return an empty generator
        if lazify:
            return LazyResult((i for i in []))
        else:
            return (i for i in [])


__all__ = ['itertags', 'iwrapper']