#!/usr/bin/env python3

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

"""Turns Sphinx's `qthelp` output into a tree qhelpgenerator can compress.

The builder leaves a directory of pages and a help project that is almost,
but not quite, what a Qt Help archive wants: the pages link no stylesheet
that colors them, the help project names itself after Sphinx, and the
identifiers F1 matches are only half there.  Each of those is dealt with by
one module under `commands/`; this walks the tree and calls them.

Run by the makefile.  See README.md.
"""

import argparse
import os
import shutil
import sys

from commands import qch_css
from commands import qch_html
from commands import qch_identifiers
from commands import qch_project

# Where the stylesheets go, which is where the pages already look for the
# ones Sphinx wrote.
CSS_DIR = '_static'

# What the builder calls the help project it writes.
HELP_PROJECT_NAME = 'Python.qhp'

# What this writes, beside the pages, for qhelpgenerator to read.
OUTPUT_PROJECT_NAME = 'python.qhp'

# How much of the output can sensibly go unrecognised by the relinking: the
# standalone examples under `_static` are whole documents of their own, and
# there are two of them.  Much past that and the theme has changed the markup
# `qch_html` reads, which would otherwise be an archive of unstyled pages
# built without complaint.
UNSTYLED_SHARE = 0.05


def excluded(name):
    return (name in qch_project.EXCLUDED_NAMES
            or name.endswith(qch_project.EXCLUDED_SUFFIXES))


def stage_tree(source_root, dest_root, online_url):
    """Copies the output of the builder, fitting the pages on the way.

    Counts the pages whose stylesheets were relinked as well as the pages
    seen, since a page the theme rendered that this did not recognise is
    one that arrives unstyled.
    """
    pages = 0
    relinked = 0
    copied = 0

    for directory, _, names in os.walk(source_root):
        for name in sorted(names):
            if excluded(name):
                continue

            src_path = os.path.join(directory, name)
            rel_path = os.path.relpath(src_path, source_root)
            dst_path = os.path.join(dest_root, rel_path)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)

            if name.endswith('.html'):
                relinked += qch_html.preprocess_html_file(
                    src_path, dst_path, rel_path,
                    qch_css.LINKED_CSS_NAME, online_url)
                pages += 1
            else:
                shutil.copyfile(src_path, dst_path)
                copied += 1

    return pages, relinked, copied


def main():
    parser = argparse.ArgumentParser(prog='build_qch.py')
    parser.add_argument(
        '--src', required=True,
        help='the directory Sphinx\'s qthelp builder wrote')
    parser.add_argument(
        '--dst', required=True,
        help='the directory to stage the Qt Help archive in')
    parser.add_argument(
        '--namespace', required=True,
        help='the Qt Help namespace to register the archive under')
    parser.add_argument(
        '--virtual-folder', required=True,
        help='the Qt Help virtual folder the pages sit in')
    parser.add_argument(
        '--online-url', default='',
        help='the documentation online, which each page links in a footer')
    parser.add_argument(
        '--doc-dir', default='',
        help="CPython's Doc directory, which holds the record of what "
             'Sphinx documented')
    args = parser.parse_args()

    project_path = os.path.join(args.src, HELP_PROJECT_NAME)
    if not os.path.isfile(project_path):
        sys.exit('No help project at %s; has the qthelp builder run?'
                 % project_path)

    # Start from nothing: the help project lists what is in the staged tree,
    # so anything a previous run left behind and this one does not write
    # would be carried into the archive.
    if os.path.isdir(args.dst):
        shutil.rmtree(args.dst)

    pages, relinked, copied = stage_tree(args.src, args.dst, args.online_url)
    print('Fitted %d pages, %d of them relinked, and copied %d other files'
          % (pages, relinked, copied))
    if pages - relinked > pages * UNSTYLED_SHARE:
        print('Warning: %d of the %d pages link no stylesheet this knows how '
              'to relink, so they will arrive unstyled; the theme has '
              'probably changed' % (pages - relinked, pages), file=sys.stderr)

    written = qch_css.write_stylesheets(os.path.join(args.dst, CSS_DIR))
    print('Wrote %s' % ', '.join(written))

    objects = (qch_identifiers.python_objects(args.doc_dir)
               if args.doc_dir else {})

    counts = qch_project.write_help_project(
        project_path, os.path.join(args.dst, OUTPUT_PROJECT_NAME),
        args.namespace, args.virtual_folder, args.dst, objects)

    print('Help project: %d keywords over %d files'
          % (counts['keywords'], counts['files']))
    print('  %d C API identifiers unscoped, %d mentions unidentified, '
          '%d Python objects added, %d dotted names added'
          % (counts['c_identifiers'], counts['mentions'],
             counts['python_identifiers'], counts['dotted_keywords']))
    print('Namespace %s, virtual folder %s'
          % (args.namespace, args.virtual_folder))


if __name__ == '__main__':
    main()
