# Default target runs both test and coverage
.PHONY: default
default: test coverage # Run all tests and generate coverage report

.PHONY: install-requirements
install-requirements: # Install main requirements
	pip install -r requirements.txt

.PHONY: install-requirements-test
install-requirements-test: # Install test requirements
	pip install -r requirements-test.txt

.PHONY: install-requirements-other
install-requirements-other: # Install other requirements (for tools like md_toc)
	pip install -r requirements-other.txt

.PHONY: toc
toc: install-requirements-other # Update the Markdown TOC in README.md
	md_toc -p github README.md

.PHONY: test
test: install-requirements-test # Run all unit tests
	python -m unittest discover -s tests

.PHONY: coverage
coverage: install-requirements-test # Run tests with coverage and generate reports
	coverage run --omit="tests/*" -m unittest discover -s tests
	coverage report -m
	coverage xml

.PHONY: install
install: install-requirements # Install this package in editable mode
	pip install -e .

.PHONY: uninstall
uninstall: # Uninstall this package
	pip uninstall -y gh-pulls-summary

.PHONY: help
help: # Show help for all targets
	@awk -F':|#' '/^[a-zA-Z0-9_-]+:/{if ($$2 ~ /[^=]/) {printf "\033[36m%-28s\033[0m %s\n", $$1, $$3}}' $(MAKEFILE_LIST)
