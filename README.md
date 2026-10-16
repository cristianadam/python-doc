Information
-----------

This package builds the Python language documentation
<https://docs.python.org/3.15/> as a Qt Help archive (`.qch`), so that it can
be read offline in Qt Assistant and in Qt Creator's help pane, and reached
from Qt Creator with F1.

Unlike the cppreference documentation, which has to be scraped off a wiki,
the Python documentation is written in reStructuredText and built with
Sphinx, which carries a Qt Help builder of its own.  So the source here is
not a copy of the website: it is CPython's own `Doc/` tree, which `make
source` clones, and what this package adds is the part Sphinx does not do.

That part is not peculiar to Python.  CMake is written up in Sphinx as well
and ships an official `.qch` of its own, and its build -- `Utilities/Sphinx`
in the CMake sources -- has had to work around the same shortcomings of the
same builder: a `nonav` theme that colors nothing, a namespace that cannot be
configured, identifiers that come out wrong.  The approach taken here is
CMake's, and the stylesheet template is adapted from theirs; what is new is
the part that is Python's own, which is mostly the identifiers.

 1) A stylesheet.  Sphinx's `qthelp` builder renders with its `nonav` theme,
 which drops the sidebar and the scripts -- which is what a help pane wants
 -- but also leaves out `basic.css` and emits a `pygments.css` with no token
 colors in it, so the pages arrive with no layout and no syntax highlighting.
 `static-qthelp/qthelp.css.in` supplies both, and is configured twice: with a
 light palette into `offline.css` and `offline-simple.css`, and with a dark
 one into `offline-dark.css`.  Qt Assistant and Qt Creator serve the dark
 sheet in place of either of the other two when their own theme is dark.

 2) The identifiers.  Qt Creator answers F1 against the `id` of a
 `<keyword>`, and Sphinx derives those by reading the parenthesis off the end
 of each index entry as a qualified name.  That works for the members of a
 class -- `prmonth() (calendar.TextCalendar method)` gives
 `calendar.TextCalendar.prmonth` -- and for nothing else: a module-level
 function reads `join() (in module os.path)`, which it cannot parse, so
 `os.path.join` and 5000 more had no identifier at all, and the C API, whose
 entries read `PyList_New (C function)`, was filed under a scope named `C`.
 So the Python names are taken from the build's own record of what it
 documented, the `C.` is dropped, and every identifier is also given a
 keyword under its dotted name, so that the Index pane can be searched by
 `os.path.join` as well as by the `join() (in module os.path)` the website's
 index uses.  CMake patches the same hole, for the kinds of thing its own
 domain documents, in `Utilities/Sphinx/create_identifiers.py`.

 3) The names.  Sphinx hardcodes the namespace to `org.sphinx.python.<ver>`
 and the virtual folder to `doc`; both are rewritten, so that several
 versions can be registered at once and the virtual folder does not collide
 with every other Sphinx-built archive.  CMake rewrites the namespace too, in
 `Utilities/Sphinx/fixup_qthelp_names.cmake`.

 4) The landing page.  Sphinx roots the table of contents at `contents.html`,
 the page listing every section of every manual; the page the website opens
 on, `index.html`, is in the archive but not in the contents at all, because
 nothing in the documentation links down to it.  The tree is hung off that
 one instead, with the old root kept as its first entry.

Building
--------

    make

That is `make source`, `make venv`, `make doc_qthelp` and `make doc_qch` in
order, and leaves the archive at `output/python-3.15.qch`.  The first run
clones CPython and builds a virtualenv, and takes a few minutes; afterwards
only the steps whose inputs changed are repeated.  The clone stays on the
commit it was made at, so that a rebuild needs no network and two builds of
a version are the same build; `make update` moves it to the tip of its
branch, and the `make` after that picks the new commits up.

The version built is 3.15 unless another is asked for.  Any other lands
beside it rather than replacing it -- the namespace carries the version, so
Qt Creator can hold several at once -- which is what these two would do:

    make                      # output/python-3.15.qch, the default
    make PYTHON_VERSION=3.14  # output/python-3.14.qch, beside it

`make install` copies the archive to `$(docdir)/qch`.  To read it, register
it with Qt Creator under Help > Documentation > Add, or open it directly:

    assistant -register output/python-3.15.qch

Dependencies
------------

`git`, `python3` (3.12 or newer) and `qhelpgenerator`, which ships with Qt in
`libexec`.  `make venv` installs Sphinx and the rest of what CPython's `Doc/`
asks for into `venv/`.  If `qhelpgenerator` is not on the path:

    make QHELPGENERATOR=~/Qt/6.12.0/macos/libexec/qhelpgenerator

License
-------

GPL version 3 or later; see `LICENSE`.

`static-qthelp/qthelp.css.in` is adapted from CMake's
`Utilities/Sphinx/static-qthelp/qthelp.css.in`, which is BSD 3-Clause and
remains so for the parts taken from it; that license permits redistributing
them here under the GPL, and the file's header says as much.

Nothing in this package is Python's own documentation.  What `make` builds
from is CPython's `Doc/` tree, which `make source` clones and which carries
the PSF license of the clone it comes from.

See also
--------

CMake's Qt Help build, under `Utilities/Sphinx` in the CMake sources, which
solves the same problem for the same builder and is where most of what is
here comes from.  Worth reading alongside this:

 * `qthelp_css.cmake` and `static-qthelp/qthelp.css.in` -- the stylesheet
   template and the two palettes, which `commands/qch_css.py` is a port of.
 * `conf.py.in` -- how CMake links the stylesheet, which it can do from its
   own `conf.py`.  CPython's is not ours to edit, so `commands/qch_html.py`
   adds the link to the built pages instead.
 * `fixup_qthelp_names.cmake` and `create_identifiers.py` -- the namespace
   and the identifiers, both of which `commands/qch_project.py` does.

cppreference-doc, which builds the C++ reference the same way for the same
help viewers, and from which this package takes its layout and its license.
