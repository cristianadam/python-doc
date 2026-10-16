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

"""Rewrites the help project Sphinx's `qthelp` builder leaves behind.

Three things are changed.

The names.  Sphinx hardcodes the namespace to `org.sphinx.<project>.<ver>`
and the virtual folder to `doc`, and offers no setting for either
(sphinx-doc/sphinx#1448).  `doc` is what every Sphinx-built archive uses, so
left alone it would be shared with all of them; the namespace carries the
version so that several of these can be registered side by side.

The identifiers.  Qt Creator answers F1 by looking up the word under the
cursor among the `id` attributes, and what Sphinx puts there is read off the
end of the index entry, which gets it right for the members of a class and
wrong or missing for everything else (sphinx-doc/sphinx#1491).  Four things
are done about that.  The C API, whose entries read `PyList_New (C
function)`, is filed under `C.PyList_New`; the `C.` is dropped.  Where the
same identifier is on several entries, the ones that are only a mention give
up their claim on it, so that F1 arrives at the page documenting the name.
The Python objects Sphinx could not parse an identifier for at all are taken
from the build's own record of them; see `commands/qch_identifiers.py`.  And
every identifier is given a keyword under the dotted name itself, so that
the Index pane can be searched by it as well as by the `join() (in module
os.path)` the website's index reads as.

The file list.  Sphinx lists what it wrote; this lists what is actually in
the staged tree, which is that plus the stylesheets this package generates,
and leaves out the scripts, which no help viewer runs.
"""

import os
import re

from xml.etree import ElementTree

# What a help viewer has no use for.  The scripts drive the sidebar, the
# search box and the theme switcher of the website, none of which a page
# rendered by litehtml has; `objects.inv` and `.buildinfo` are for Sphinx.
EXCLUDED_SUFFIXES = ('.js', '.qhp', '.qhcp', '.inv', '.buildinfo')
EXCLUDED_NAMES = ('.DS_Store', '.stamp')


def included_files(root):
    """Every file of the staged tree worth carrying, as relative paths."""
    paths = []

    for directory, _, names in os.walk(root):
        for name in names:
            if name in EXCLUDED_NAMES or name.endswith(EXCLUDED_SUFFIXES):
                continue
            path = os.path.join(directory, name)
            paths.append(os.path.relpath(path, root).replace(os.sep, '/'))

    return sorted(paths)


def set_names(root, namespace, virtual_folder):
    for tag, value in (('namespace', namespace),
                       ('virtualFolder', virtual_folder)):
        element = root.find(tag)
        if element is None:
            raise ValueError('the help project has no <%s>' % tag)
        element.text = value


# What Sphinx files the C API under.  `PyList_New (C function)` is read as a
# name inside a parenthesis, so the `C` of `C function` is taken for the
# scope it belongs to.
C_IDENTIFIER_PREFIX = 'C.'


def fix_c_identifiers(keywords):
    """Drops the scope Sphinx invents for the C API from its identifiers."""
    fixed = 0

    for keyword in keywords:
        identifier = keyword.get('id')
        if identifier is None or not identifier.startswith(
                C_IDENTIFIER_PREFIX):
            continue
        keyword.set('id', identifier[len(C_IDENTIFIER_PREFIX):])
        fixed += 1

    return fixed


# What Sphinx anchors an index entry on when the page only brings the name
# up -- an `.. index::` directive, or a term marked up in the prose --
# numbered in the order the page uses them.  The entry for the thing itself
# is anchored on its name instead: `#c.Py_INCREF`, `#object.__bool__`.
MENTION_ANCHOR_RE = re.compile(r'#index-\d+$')


def is_mention(keyword):
    return bool(MENTION_ANCHOR_RE.search(keyword.get('ref', '')))


def prefer_reference_anchors(keywords):
    """Takes the identifier off mentions that a real reference shares.

    Sphinx gives the same identifier to every index entry for a name, the
    page documenting it and the pages that merely bring it up alike, and
    qhelpgenerator keeps only the first entry it sees for an identifier.  F1
    on `Py_INCREF` lands on the sentence in the C API introduction that
    mentions it rather than on the page defining it, and which of the two it
    is comes down to the order Sphinx happened to write them in.

    The identifier is what F1 reads and the name is what the Index pane
    lists, so a mention keeps its place in the index and gives up only its
    claim on the identifier.  Nothing is dropped where every entry for an
    identifier is a mention: there is no reference to prefer.
    """
    referenced = {keyword.get('id') for keyword in keywords
                  if keyword.get('id') is not None and not is_mention(keyword)}
    dropped = 0

    for keyword in keywords:
        if keyword.get('id') not in referenced or not is_mention(keyword):
            continue
        del keyword.attrib['id']
        dropped += 1

    return dropped


def add_keyword(keywords, name, ref, identifier=None):
    element = ElementTree.SubElement(keywords, 'keyword')
    element.set('name', name)
    if identifier is not None:
        element.set('id', identifier)
    element.set('ref', ref)
    return element


def add_python_identifiers(keywords, objects):
    """Adds the objects Sphinx documented but wrote no identifier for."""
    known = {keyword.get('id') for keyword in keywords}
    added = 0

    for name, ref in sorted(objects.items()):
        if name in known:
            continue
        add_keyword(keywords, name, ref, name)
        added += 1

    return added


def add_dotted_keywords(keywords):
    """Adds a keyword under the dotted name of every object that has one.

    These carry no `id` of their own.  The identifier is already on the
    keyword this one was made from, and qhelpgenerator keeps only the first
    entry it sees for an identifier -- repeating it here would mean every
    one of these is thrown away as a duplicate of what it was made from,
    which is the whole set of them.  An entry with no identifier is always
    kept, and F1 is answered by the original either way.
    """
    seen = {(keyword.get('name'), keyword.get('ref'))
            for keyword in keywords}
    added = 0

    for keyword in list(keywords):
        identifier = keyword.get('id')
        ref = keyword.get('ref')
        if identifier is None or (identifier, ref) in seen:
            continue

        seen.add((identifier, ref))
        add_keyword(keywords, identifier, ref)
        added += 1

    return added


def set_landing_page(section, landing_ref, contents_title):
    """Puts the landing page at the root of the table of contents.

    Sphinx roots the contents at `root_doc`, which for CPython is the page
    listing every section of every manual -- useful, and a wall of links to
    arrive at.  The page the website opens on is `index.html`, which is not
    in the contents at all because nothing in the documentation links down to
    it.  Hang the tree off that instead, and keep what was at the root as its
    first entry, since the help viewer opens whatever the root is.
    """
    toc = section.find('toc')
    if toc is None:
        return None

    root = toc.find('section')
    if root is None or root.get('ref') == landing_ref:
        return None

    contents_ref = root.get('ref')
    root.set('ref', landing_ref)

    contents = ElementTree.Element('section')
    contents.set('title', contents_title)
    contents.set('ref', contents_ref)
    root.insert(0, contents)

    return contents_ref


def set_files(section, paths):
    for element in section.findall('files'):
        section.remove(element)

    files = ElementTree.SubElement(section, 'files')
    for path in paths:
        ElementTree.SubElement(files, 'file').text = path


# The page the website opens on, and what to call the one the table of
# contents was rooted at before it.
LANDING_PAGE = 'index.html'
CONTENTS_TITLE = 'Complete table of contents'


def write_help_project(src_path, dst_path, namespace, virtual_folder,
                       stage_root, python_objects):
    """Writes the fixed-up help project, and reports what it changed."""
    tree = ElementTree.parse(src_path)
    root = tree.getroot()

    set_names(root, namespace, virtual_folder)

    section = root.find('filterSection')
    if section is None:
        raise ValueError('the help project has no <filterSection>')

    if os.path.isfile(os.path.join(stage_root, LANDING_PAGE)):
        set_landing_page(section, LANDING_PAGE, CONTENTS_TITLE)

    keywords = section.find('keywords')
    if keywords is None:
        keywords = ElementTree.SubElement(section, 'keywords')

    counts = {'c_identifiers': fix_c_identifiers(keywords)}
    # After the C API is unscoped, so that the entries that collide under
    # `PyList_New` are seen to, and before the dotted names, which are made
    # from whatever identifiers are left standing.
    counts['mentions'] = prefer_reference_anchors(keywords)
    counts['python_identifiers'] = add_python_identifiers(keywords,
                                                          python_objects)
    counts['dotted_keywords'] = add_dotted_keywords(keywords)
    counts['keywords'] = len(keywords)

    paths = included_files(stage_root)
    set_files(section, paths)
    counts['files'] = len(paths)

    ElementTree.indent(tree, space='  ')
    tree.write(dst_path, encoding='utf-8', xml_declaration=True)

    return counts
