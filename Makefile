SHELL := /bin/bash
ROOT_DIR := $(shell pwd)

PROJECT_NAME := worth
PROJECT_DOCKER_TAG := worthit/$(PROJECT_NAME)
PROJECT_DOCKER_RUN_ARGS := --link db:db

default: build

.PHONY: test run test-all test-utils test-server test-worth test-lint fmt test-with-build build docs

docs:
	pdoc --html worth --html-dir docs --overwrite

build:
	docker build -t $(PROJECT_DOCKER_TAG) .

run:
	docker run -it $(PROJECT_DOCKER_RUN_ARGS) $(PROJECT_DOCKER_TAG) /bin/bash

compose:
	docker-compose up -d

db:
	docker run -d --name worth_db -p 5432:5432 -e POSTGRES_PASSWORD=root_password -e POSTGRES_DATABASE=worthpy postgres

mysql:
	docker run --env DATABASE_URL=mysql://root:root_password@mysql:3306/testdb -p 4000:8080 worth

serve-local:
	pipenv run python worth/server/serve.py --port 8080 --database_url='mysql://root:root_password@127.0.0.1:3306/testdb'

.PHONY: db-head-state
db-head-state:
	curl -H 'Content-Type: application/json' -d '{"id":1,"jsonrpc":"2.0","method":"db_head_state"}' http://localhost:8080

.PHONY: dump-schema
dump-schema:
	pg_dump -s -x --use-set-session-authorization worthpytest  | sed -e '/^--/d' | awk -v RS= -v ORS='\n\n' '1' > schema.sql

ipython:
	docker run -it $(PROJECT_DOCKER_RUN_ARGS) $(PROJECT_DOCKER_TAG) ipython

test: test-all test-lint

test-with-build: test build

test-all:
	py.test --cov=worth --capture=sys

test-utils:
	py.test tests/utils --cov=worth/utils --capture=sys

test-worth:
	py.test tests/worth --cov=worth/worth --capture=sys

test-server:
	py.test tests/server --cov=worth/server --capture=sys

test-lint:
	py.test --pylint -m pylint $(PROJECT_NAME) --pylint-error-types WEF

fmt:
	yapf --recursive --in-place --style pep8 .
	autopep8 --recursive --in-place .

requirements.txt: serve.py
	pip freeze > $@

clean: clean-build clean-pyc

clean-build:
	rm -fr build/ dist/ *.egg-info .eggs/ .tox/ __pycache__/ .cache/ .coverage htmlcov src

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

install: clean
	pip3 install -e .
