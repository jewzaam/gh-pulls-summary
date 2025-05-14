# Default target runs both test and coverage
.PHONY: default
default: test coverage

.PHONY: install-requirements
install-requirements:
	pip install --user -r requirements.txt

.PHONY: install-requirements-test
install-requirements-test:
	pip install -r requirements-test.txt

.PHONY: install-requirements-other
install-requirements-other:
	pip install -r requirements-other.txt

.PHONY: toc
toc: install-requirements-other
	md_toc -p github README.md

.PHONY: test
test: install-requirements-test
	python -m unittest discover -s tests

.PHONY: coverage
coverage: install-requirements-test
	coverage run --omit="tests/*" -m unittest discover -s tests
	coverage report -m
	coverage xml

.PHONY: install
install: install-requirements
	pip install --user -e .

.PHONY: uninstall
uninstall:
	pip uninstall -y gh-pulls-summary
