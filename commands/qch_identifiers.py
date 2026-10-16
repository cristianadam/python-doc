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

"""Reads the objects Sphinx documented, so that F1 can find them.

Qt Creator answers F1 by looking the word under the cursor up among the `id`
attributes of the help project.  Sphinx fills those in by picking the
parenthesis off the end of each index entry and reading what is inside it as
a qualified name (sphinx-doc/sphinx#1491), which works for the members of a
class -- `prmonth() (calendar.TextCalendar method)` gives
`calendar.TextCalendar.prmonth` -- and not for anything else.  A module-level
function reads `join() (in module os.path)`, which it cannot parse at all, so
`os.path.join` and the 2000-odd like it have no identifier; see
`qch_project.add_dotted_keywords` for the other half of what it gets wrong.

What the index entry spells out, the Python domain holds exactly, so take it
from there instead.  It is in the environment Sphinx pickles beside the
doctrees, which is the build's own record of what it documented and where it
put it, and is read here with the Sphinx that wrote it.
"""

import os
import pickle
import sys

ENVIRONMENT_PATH = os.path.join('build', 'doctrees', 'environment.pickle')

# CPython's `conf.py` loads extensions from here, and they have to be
# importable for the environment to unpickle: it holds instances of the node
# classes they define.
EXTENSIONS_PATH = os.path.join('tools', 'extensions')


def load_environment(doc_dir):
    path = os.path.join(doc_dir, ENVIRONMENT_PATH)
    if not os.path.isfile(path):
        return None

    sys.path.insert(0, os.path.join(doc_dir, EXTENSIONS_PATH))
    try:
        with open(path, 'rb') as a_file:
            return pickle.load(a_file)
    finally:
        sys.path.pop(0)


def python_objects(doc_dir):
    """Every documented Python object, as `{qualified name: page#anchor}`.

    Empty, with a word about why, if the environment cannot be read: the
    archive is worth building without the identifiers Sphinx missed.
    """
    try:
        environment = load_environment(doc_dir)
    except Exception as error:                  # noqa: BLE001 -- see below
        # Unpickling runs arbitrary imports, and a CPython that has moved its
        # extensions or a Sphinx that has changed the environment format can
        # fail in a good many ways, none of which is worth stopping over.
        print('Could not read the Sphinx environment (%s); building without '
              'the identifiers it holds' % error)
        return {}

    if environment is None:
        print('No Sphinx environment beside the doctrees; building without '
              'the identifiers it holds')
        return {}

    objects = environment.domaindata['py']['objects']
    return {name: '%s.html#%s' % (entry.docname, entry.node_id)
            for name, entry in objects.items()}
