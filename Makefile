.PHONY: help venv install test run clean
PY?=python

help:
	@echo "make venv     - create venv (./venv)"
	@echo "make install  - install base requirements into venv"
	@echo "make test     - run pytest"
	@echo "make run      - run demo entrypoint"
	@echo "make clean    - remove build artifacts"

venv:
	$(PY) -m venv venv

install:
	. venv/bin/activate && python -m pip install --upgrade pip setuptools wheel && python -m pip install -r $$HOME/PycharmProjects/requirements_base.txt

test:
	. venv/bin/activate && pytest -q

run:
	. venv/bin/activate && python -m template_pkg.main

clean:
	rm -rf dist build *.egg-info .pytest_cache __pycache__
