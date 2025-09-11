VENV=.venv

.PHONY: setup lint test run-func clean

setup:
	python3 -m venv $(VENV)
	. $(VENV)/bin/activate && python -m pip install -U pip && pip install -r requirements.txt

lint:
	. $(VENV)/bin/activate && flake8

test:
	. $(VENV)/bin/activate && pytest -q

run-func:
	func start

clean:
	rm -rf $(VENV) .pytest_cache __pycache__ */__pycache__ dist build

