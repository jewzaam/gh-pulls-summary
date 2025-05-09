.PHONY: test coverage

test:
	python -m unittest discover -s . -p "test_*.py"

coverage:
	coverage run --omit="test_*.py" -m unittest discover -s . -p "test_*.py"
	coverage report -m
	coverage xml