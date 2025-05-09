.PHONY: default test coverage

# Default target runs both test and coverage
default: test coverage

test:
	python -m unittest discover -s tests

coverage:
	coverage run --omit="test_*.py" -m unittest discover -s tests
	coverage report -m
	coverage xml