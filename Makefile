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

.PHONY: test-unit
test-unit: install-requirements-test # Run only unit tests (exclude integration tests)
	python -m unittest discover -s tests -v

.PHONY: test-integration-simple
test-integration-simple: install-requirements-test # Run simple integration tests (requires network)
	RUN_INTEGRATION_TESTS=1 python -m unittest discover -s integration_tests -p "test_integration_simple.py" -v

.PHONY: test-integration
test-integration: install-requirements-test # Run integration tests (requires network)
	RUN_INTEGRATION_TESTS=1 python -m unittest discover -s integration_tests -p "test_integration_simple.py" -v

.PHONY: test-integration-full
test-integration-full: install-requirements-test # Run full integration tests (requires network and higher rate limits)
	RUN_INTEGRATION_TESTS=1 python -m unittest discover -s integration_tests -v

.PHONY: test-all
test-all: test-unit test-integration-simple # Run both unit and simple integration tests

.PHONY: coverage
coverage: install-requirements-test # Run tests with coverage and generate reports
	coverage run --omit="tests/*" -m unittest discover -s tests
	coverage report -m
	coverage xml

.PHONY: coverage-unit
coverage-unit: install-requirements-test # Run coverage on unit tests only
	coverage run --omit="tests/*" -m unittest discover -s tests -p "test_*.py" -k "not test_integration"
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
