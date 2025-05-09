.PHONY: default test coverage install uninstall

# Default target runs both test and coverage
default: test coverage

test:
	python -m unittest discover -s tests

coverage:
	coverage run --omit="tests/*" -m unittest discover -s tests
	coverage report -m
	coverage xml

install:
	pip install -e .

uninstall:
	pip uninstall -y gh-pulls-summary