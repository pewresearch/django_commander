# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS	=
SPHINXBUILD = sphinx-build
SOURCEDIR   = docs_source
BUILDDIR    = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

github:
	@make html
	@cp -a _build/html/. ./docs
	aws s3 sync --delete docs s3://docs.pewresearch.tech/django_commander/

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
