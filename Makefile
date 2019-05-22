SOURCES:= \
	MANIFEST.in \
	requirements.txt \
	$(wildcard **/*.py) \

.PHONY: sdist
sdist: $(SOURCES)
	python setup.py sdist

.PHONY: test
test: $(SOURCES)
	tox --skip-missing-interpreters

.PHONY: clean
clean:
	-rm -r build
	-rm -r dist
	-rm -r .tox
	-rm -r cronredux.egg-info
