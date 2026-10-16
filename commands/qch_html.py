#   Copyright (C) 2026  Cristian Adam <cristian.adam@gmail.com>
#
#   This file is part of python-doc
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see http://www.gnu.org/licenses/.

"""Fits one page of Sphinx's `qthelp` output to a help viewer.

Two things are done to it, and the rest is left exactly as Sphinx wrote it.

The first is the stylesheets.  The `nonav` theme the builder renders with
links its own sheet and a `pygments.css`, but not the `basic.css` that every
other Sphinx theme builds on -- which is where the signatures, the parameter
lists, the admonitions and the index tables get their layout -- so the pages
arrive flat.  `basic.css` is already in the output directory, unreferenced,
so it is linked ahead of `nonav.css`, which is the order a theme would have
imported it in, and the sheet this package generates is linked after both so
that it has the last word.  Should the theme start linking it upstream, only
that insertion is skipped; the generated sheet is still linked, since it is
needed either way.  See `commands/qch_css.py`.

The second is a footer naming the page online, so that a reader who has
reached a page in the help pane can get to the version that is kept up to
date, and can link someone else to it.
"""

import os
import re

STYLESHEET_RE = re.compile(
    r'<link\s[^>]*rel="stylesheet"[^>]*href="([^"]*)"[^>]*>')

# The sheet the `nonav` theme builds on but does not link.
BASE_CSS_NAME = 'basic.css'

# The page is a transitional XHTML document, so the tags are closed.
LINK_TAG = '<link rel="stylesheet" type="text/css" href="%s" />'

FOOTER = ('<div class="qch-footer">Online: '
          '<a href="%s">%s</a></div>\n')

BODY_END_RE = re.compile(r'(?i)</body>')


def stylesheet_prefix(href):
    """The path a page uses to reach `_static`, taken from a link it has."""
    href = href.split('?')[0]
    marker = '_static/'
    position = href.rfind(marker)
    return href[:position + len(marker)] if position >= 0 else None


def relink_stylesheets(text, linked_css_name):
    """Links `basic.css` before the theme sheet and ours after all of them.

    Returns the page and whether it was one this applies to, which is every
    page the theme rendered.
    """
    matches = list(STYLESHEET_RE.finditer(text))
    if not matches:
        return text, False

    theme = None
    prefix = None
    has_base = False

    for match in matches:
        href = match.group(1).split('?')[0]
        if href.endswith('/' + BASE_CSS_NAME):
            has_base = True
        if href.endswith('/nonav.css'):
            theme = match
            prefix = stylesheet_prefix(href)

    if prefix is None:
        # Not a page of the theme -- the two standalone profiler examples
        # under `_static` are whole documents with styles of their own.
        return text, False

    # Back to front, so that an insertion does not move the one after it.
    last = matches[-1]
    text = (text[:last.end()]
            + '\n    ' + LINK_TAG % (prefix + linked_css_name)
            + text[last.end():])

    if has_base:
        # The theme links it itself, as upstream means it to; ours is then
        # all that was missing.  Linking it twice would override whatever
        # the sheets in between have to say about the same selectors.
        return text, True

    return (text[:theme.start()]
            + LINK_TAG % (prefix + BASE_CSS_NAME) + '\n    '
            + text[theme.start():]), True


def add_footer(text, url):
    footer = FOOTER % (url, url)
    return BODY_END_RE.sub(lambda match: footer + match.group(0), text, count=1)


def preprocess_html_file(src_path, dst_path, rel_path, linked_css_name,
                         online_url):
    """Writes the page at `src_path` to `dst_path`, fitted to a help viewer.

    `rel_path` is where the page sits in the documentation set, which is what
    says where it is to be found online.  Reports whether the stylesheets
    were relinked, which they are on every page the theme rendered.
    """
    with open(src_path, encoding='utf-8') as a_file:
        text = a_file.read()

    text, relinked = relink_stylesheets(text, linked_css_name)

    if online_url:
        url = '%s/%s' % (online_url.rstrip('/'),
                         rel_path.replace(os.sep, '/'))
        text = add_footer(text, url)

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, 'w', encoding='utf-8') as a_file:
        a_file.write(text)

    return relinked
