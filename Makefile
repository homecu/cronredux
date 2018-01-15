VERSION:=2.4

SOURCES:= \
	MANIFEST.in \
	requirements.txt \
	$(wildcard **/*.py) \

SDIST_TAR:=dist/cronredux-$(VERSION).tar.gz

.PHONY: sdist
sdist: $(SDIST_TAR)

.PHONY: test
test: $(SOURCES)
	tox --skip-missing-interpreters

.PHONY: clean
clean:
	-rm -r build
	-rm -r dist
	-rm -r .tox
	-rm -r cronredux.egg-info

$(SDIST_TAR): $(SOURCES)
	CRONREDUX_VERSION=$(VERSION) python setup.py sdist
