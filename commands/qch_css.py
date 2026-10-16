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

"""Builds the stylesheets the Qt Help rendition of the pages links.

`static-qthelp/qthelp.css.in` is configured twice, once with each of the two
palettes below, and written out under the three names the help viewers go
looking for.  Asked for `offline-simple.css`, Qt Assistant and Qt Creator
serve `offline-dark.css` in its place when their own theme is dark; older Qt
Creator asks for `offline.css` instead when its theme is light.  So the light
palette is written under both of those names and the dark one under the
third, and the pages link `offline-simple.css`.

The syntax highlighting is not in the template.  Sphinx's `qthelp` builder
emits a `pygments.css` holding the line-number rules and nothing else -- the
token colors belong to the html theme, which the `nonav` theme it renders
with does not have -- so a full set is generated here from Pygments itself,
in the two styles the python-docs-theme names for a light and a dark page.
"""

import os
import re

from pygments.formatters import HtmlFormatter

# The names the viewers go looking for, and which palette each one holds.
LIGHT_CSS_NAMES = ['offline.css', 'offline-simple.css']
DARK_CSS_NAME = 'offline-dark.css'

# The one the pages link.  It has to be one of the light names: the viewer
# substitutes the dark sheet for it, rather than the page asking for it.
LINKED_CSS_NAME = 'offline-simple.css'

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'static-qthelp', 'qthelp.css.in')

# The Pygments styles python-docs-theme names in its `theme.toml`, so that
# the code samples read the way they do on the website.
LIGHT_PYGMENTS_STYLE = 'default'
DARK_PYGMENTS_STYLE = 'monokai'


# The colors of the light page are what docs.python.org renders as.  They
# are read off the stylesheets it serves -- `classic.css`, which Sphinx
# generates from the theme's options, and `pydoctheme.css`, which overrides a
# good deal of it -- rather than out of python-docs-theme's `theme.toml`:
# what a reader sees for a link in the body of a page is the `#0072aa` of
# `pydoctheme.css`, not the `linkcolor` of `#0090c0` the options still name.
LIGHT_PALETTE = {
    'body_bg': '#ffffff',
    'body_fg': '#222222',
    'link': '#0072aa',
    'link_visited': '#6363bb',
    'link_hover': '#00b0e4',
    'head_fg': '#1a1a1a',
    'head_border': '#cccccc',
    'headerlink': '#aaaaaa',
    'muted': '#777777',
    'pre_bg': '#eeffcc',
    'pre_fg': '#333333',
    'pre_border': '#aacc99',
    'code_bg': '#ecf0f3',
    'code_fg': '#333333',
    'note_code_bg': '#d6d6d6',
    'warning_code_bg': '#efc2c2',
    'field_bg': '#eeddee',
    'note_bg': '#eeeeee',
    'note_border': '#cccccc',
    'seealso_bg': '#ffffcc',
    'seealso_border': '#ffff66',
    'warning_bg': '#ffe4e4',
    'warning_border': '#ff6666',
    'versionadded': '#296433',
    'versionadded_border': '#4fc464',
    'versionchanged': '#854826',
    'versionchanged_border': '#f4e34c',
    'deprecated': '#9f3133',
    'deprecated_border': '#f44c4e',
    'border': '#dddddd',
    'table_head_bg': '#eeeeee',
    'caption_fg': '#efefef',
    'caption_bg': '#1c4e63',
    'hll_bg': '#ffffcc',
    'image_rule': '/* Nothing to do: the page is white underneath. */',
}

# The page color and the text color of the dark scheme are those of the
# stylesheet Qt Creator falls back to for documentation that ships no dark
# variant, so that the Python pages sit well next to the Qt pages in the same
# help pane.  The rest is laid out from them.
DARK_PALETTE = {
    'body_bg': '#262626',
    'body_fg': '#d0d0d0',
    'link': '#6ab0f3',
    'link_visited': '#a99ae0',
    'link_hover': '#8cc6ff',
    'head_fg': '#a8c8ea',
    'head_border': '#4a4b4c',
    'headerlink': '#6ab0f3',
    'muted': '#9a9a9a',
    'pre_bg': '#2d2e2f',
    'pre_fg': '#d0d0d0',
    'pre_border': '#4e5a46',
    'code_bg': '#353637',
    'code_fg': '#d0d0d0',
    'note_code_bg': '#3f4041',
    'warning_code_bg': '#4a3232',
    'field_bg': '#3a3340',
    'note_bg': '#2d2e2f',
    'note_border': '#4a4b4c',
    'seealso_bg': '#39381f',
    'seealso_border': '#5c5a30',
    'warning_bg': '#3d2727',
    'warning_border': '#7a4040',
    'versionadded': '#6fc96f',
    'versionadded_border': '#4a8f58',
    'versionchanged': '#d9a05a',
    'versionchanged_border': '#8f8438',
    'deprecated': '#e08080',
    'deprecated_border': '#9f4a4b',
    'border': '#4a4b4c',
    'table_head_bg': '#353637',
    'caption_fg': '#d6e4ea',
    'caption_bg': '#1c4e63',
    'hll_bg': '#4a4a2a',
    # The figures are screenshots of light interfaces and diagrams drawn as
    # black marks on nothing at all, both of which are lost on a dark page.
    # A raster image can only be handed the ground it was drawn against, and
    # the three SVGs here are drawn the same way, so they are given it too.
    'image_rule': '\n'.join([
        'img {',
        '  background-color: #ffffff;',
        '  padding: 3px;',
        '  border-radius: 2px;',
        '}',
    ]),
}

PLACEHOLDER_RE = re.compile(r'@([a-z_]+)@')


def render(template, palette):
    def replace(match):
        name = match.group(1)
        if name not in palette:
            raise KeyError('the template names "%s", which no palette sets'
                           % name)
        return palette[name]

    return PLACEHOLDER_RE.sub(replace, template)


def pygments_rules(style):
    # Pygments writes the background of the block into the `.highlight` rule
    # as well as the token colors.  The template settles the background --
    # the two have to agree with the border it draws around it -- and says so
    # after this, which is why this goes first.
    return HtmlFormatter(style=style).get_style_defs('.highlight')


def stylesheet(template, palette, pygments_style):
    return '\n'.join([
        '/* Generated by "commands/qch_css.py" from',
        ' * "static-qthelp/qthelp.css.in".  Edit those rather than this. */',
        '',
        '/* -- syntax highlighting, from the Pygments "%s" style ------ */'
        % pygments_style,
        '',
        pygments_rules(pygments_style),
        '',
        render(template, palette),
    ])


def write_stylesheets(css_dir):
    """Writes the three stylesheets into `css_dir`, and names the files."""
    with open(TEMPLATE_PATH, encoding='utf-8') as a_file:
        template = a_file.read()

    light = stylesheet(template, LIGHT_PALETTE, LIGHT_PYGMENTS_STYLE)
    dark = stylesheet(template, DARK_PALETTE, DARK_PYGMENTS_STYLE)

    os.makedirs(css_dir, exist_ok=True)
    written = []

    for name, text in [(name, light) for name in LIGHT_CSS_NAMES] + \
                      [(DARK_CSS_NAME, dark)]:
        path = os.path.join(css_dir, name)
        with open(path, 'w', encoding='utf-8') as a_file:
            a_file.write(text)
        written.append(name)

    return written
