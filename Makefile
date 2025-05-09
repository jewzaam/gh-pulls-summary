.PHONY: default test coverage install uninstall install-requirements

# Default target runs both test and coverage
default: test coverage

test:
	python -m unittest discover -s tests

coverage:
	coverage run --omit="tests/*" -m unittest discover -s tests
	coverage report -m
	coverage xml

install-requirements:
	pip install --user -r requirements.txt

install: install-requirements
	pip install --user -e .

uninstall:
	pip uninstall -y gh-pulls-summary