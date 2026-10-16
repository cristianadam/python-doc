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

# Builds the Python documentation as a Qt Help archive.  See README.md.

PYTHON         ?= python3
PYTHON_VERSION ?= 3.15

# The branch of CPython the documentation is built from.  A released version
# has a maintenance branch of its own; `main` is what the next one is on.
CPYTHON_URL    ?= https://github.com/python/cpython.git
CPYTHON_BRANCH ?= $(PYTHON_VERSION)
CPYTHON_DIR    ?= cpython-src

VENV_DIR       ?= venv
QHELPGENERATOR ?= qhelpgenerator

# What the archive is known by once it is registered.  The version is in the
# namespace rather than in the virtual folder so that the URLs stay short,
# and in one of the two so that several versions can be registered at once.
NAMESPACE      ?= org.python.$(PYTHON_VERSION)
VIRTUAL_FOLDER ?= python

# Where the pages say they came from, which the footer of each one links.
ONLINE_URL     ?= https://docs.python.org/$(PYTHON_VERSION)

prefix  ?= /usr/local
datadir ?= $(prefix)/share
docdir  ?= $(datadir)/doc/python-doc

DOC_DIR      = $(CPYTHON_DIR)/Doc
QTHELP_DIR   = $(DOC_DIR)/build/qthelp
OUTPUT_DIR   = output
STAGE_DIR    = $(OUTPUT_DIR)/python-$(PYTHON_VERSION)-qch
QCH          = $(OUTPUT_DIR)/python-$(PYTHON_VERSION).qch

SPHINX_BUILD = $(VENV_DIR)/bin/sphinx-build
VENV_PYTHON  = $(VENV_DIR)/bin/python

# `make` cannot depend on a directory, whose timestamp says only when
# something was last added to it, so each step that fills one leaves a stamp.
SOURCE_STAMP = $(CPYTHON_DIR)/.stamp-$(CPYTHON_BRANCH)
VENV_STAMP   = $(VENV_DIR)/.stamp
QTHELP_STAMP = $(QTHELP_DIR)/.stamp
STAGE_STAMP  = $(STAGE_DIR)/.stamp

.PHONY: all
all: doc_qch

.PHONY: help
help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  source      to clone the CPython documentation sources"
	@echo "  venv        to create the virtualenv Sphinx is run from"
	@echo "  doc_qthelp  to run Sphinx's Qt Help builder over the sources"
	@echo "  doc_qch     to build $(QCH)"
	@echo "  install     to install the archive under $(docdir)"
	@echo "  clean       to remove everything built here"
	@echo "  distclean   to remove the CPython clone and the virtualenv too"

# -- the sources -----------------------------------------------------------

.PHONY: source
source: $(SOURCE_STAMP)

# Shallow, because nothing here reads the history, and of one branch, because
# the clone is pinned to the version being built.  A clone that is already
# here is moved onto the branch asked for and brought up to date, so that
# switching versions does not call for a fresh one.
$(SOURCE_STAMP):
	@if [ -d "$(CPYTHON_DIR)/.git" ]; then \
		echo "Updating $(CPYTHON_DIR) to $(CPYTHON_BRANCH)"; \
		git -C "$(CPYTHON_DIR)" fetch --depth 1 origin "$(CPYTHON_BRANCH)" && \
		git -C "$(CPYTHON_DIR)" checkout --detach FETCH_HEAD; \
	else \
		echo "Cloning $(CPYTHON_URL) at $(CPYTHON_BRANCH)"; \
		git clone --depth 1 --branch "$(CPYTHON_BRANCH)" \
			"$(CPYTHON_URL)" "$(CPYTHON_DIR)"; \
	fi
	rm -f $(CPYTHON_DIR)/.stamp-*
	touch "$@"

# -- the virtualenv --------------------------------------------------------

.PHONY: venv
venv: $(VENV_STAMP)

# CPython pins what its documentation builds with, so take the list from the
# clone rather than keeping one of our own that would drift from it.  That
# is also why the clone, and not the list in it, is what this waits on: the
# list cannot be read to decide whether to run until the clone is here.
$(VENV_STAMP): $(SOURCE_STAMP)
	$(PYTHON) -m venv "$(VENV_DIR)"
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r "$(DOC_DIR)/requirements.txt"
	touch "$@"

# -- the Sphinx build ------------------------------------------------------

.PHONY: doc_qthelp
doc_qthelp: $(QTHELP_STAMP)

# Driven through CPython's own makefile, which assembles the changelog from
# `Misc/NEWS.d` before it runs Sphinx.  Its `--fail-on-warning` is dropped:
# it is there to hold contributors to a clean build, and a warning from a
# builder upstream does not use is no reason to produce no archive here.
$(QTHELP_STAMP): $(VENV_STAMP) $(SOURCE_STAMP)
	$(MAKE) -C "$(DOC_DIR)" build BUILDER=qthelp \
		VENVDIR="$(abspath $(VENV_DIR))" SPHINXERRORHANDLING=
	touch "$@"

# -- the Qt Help archive ---------------------------------------------------

# The pages, the stylesheets and the help project, ready for qhelpgenerator.
$(STAGE_STAMP): $(QTHELP_STAMP) build_qch.py \
		$(wildcard commands/*.py) static-qthelp/qthelp.css.in
	$(VENV_PYTHON) build_qch.py \
		--src "$(QTHELP_DIR)" \
		--dst "$(STAGE_DIR)" \
		--namespace "$(NAMESPACE)" \
		--virtual-folder "$(VIRTUAL_FOLDER)" \
		--online-url "$(ONLINE_URL)" \
		--doc-dir "$(DOC_DIR)"
	touch "$@"

# qhelpgenerator resolves the file list against its own directory, so the
# help project has to sit among the pages it lists.
$(QCH): $(STAGE_STAMP)
	@mkdir -p "$(OUTPUT_DIR)"
	"$(QHELPGENERATOR)" "$(STAGE_DIR)/python.qhp" -o "$(abspath $(QCH))"

.PHONY: doc_qch
doc_qch: $(QCH)

# -- installing and cleaning -----------------------------------------------

.PHONY: install
install: doc_qch
	install -d "$(DESTDIR)$(docdir)/qch"
	install -m 644 "$(QCH)" "$(DESTDIR)$(docdir)/qch/"

.PHONY: clean
clean:
	rm -rf "$(OUTPUT_DIR)"
	rm -rf "$(DOC_DIR)/build"

.PHONY: distclean
distclean: clean
	rm -rf "$(CPYTHON_DIR)" "$(VENV_DIR)"
