SHELL := /bin/sh

PYTHON ?= python3
VENV ?= /tmp/activity-venv
DEPS_DIR ?= .deps
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
APP_MODULE ?= bot.main
IMAGE ?= activity-bot
CONTAINER ?= activity-bot
ENV_FILE ?= .env
DB_PATH ?= data/activity_bot.db

.DEFAULT_GOAL := help

.PHONY: help venv install test run check-env check-app check-proxy check-telegram docker-build docker-run docker-stop docker-logs compose-up compose-down compose-logs update clean flush

help:
	@printf '%s\n' 'Available targets:'
	@printf '%s\n' '  make venv          Create local Python virtual environment or fallback deps dir'
	@printf '%s\n' '  make install       Install dependencies'
	@printf '%s\n' '  make test          Run pytest'
	@printf '%s\n' '  make run           Run bot locally with python -m $(APP_MODULE)'
	@printf '%s\n' '  make check-proxy   Check configured proxy and CONNECT support'
	@printf '%s\n' '  make check-telegram Check Telegram API access with current env/proxy'
	@printf '%s\n' '  make docker-build  Build Docker image'
	@printf '%s\n' '  make docker-run    Run Docker container using $(ENV_FILE)'
	@printf '%s\n' '  make docker-stop   Stop and remove Docker container'
	@printf '%s\n' '  make docker-logs   Follow Docker container logs'
	@printf '%s\n' '  make compose-up    Build and start with docker compose'
	@printf '%s\n' '  make compose-down  Stop and remove docker compose services'
	@printf '%s\n' '  make compose-logs  Follow docker compose logs'
	@printf '%s\n' '  make update        Pull latest code from GitHub and restart container'
	@printf '%s\n' '  make clean         Remove local caches'
	@printf '%s\n' '  make flush         Delete the local SQLite database (DB_PATH=$(DB_PATH))'

venv:
	@if [ -x "$(VENV)/bin/python" ]; then \
		printf '%s\n' 'Using existing $(VENV).'; \
	elif $(PYTHON) -m venv $(VENV); then \
		$(PIP) install --upgrade pip; \
	else \
		rm -rf $(VENV); \
		printf '%s\n' 'python venv is unavailable; using $(DEPS_DIR) as a local dependency directory.'; \
		mkdir -p $(DEPS_DIR); \
	fi

install: venv
	@if [ ! -f requirements-dev.txt ]; then \
		printf '%s\n' 'requirements-dev.txt not found. Add dependencies before running make install.'; \
		exit 1; \
	fi
	@if [ -x "$(PIP)" ]; then \
		$(PIP) install -r requirements-dev.txt; \
	else \
		$(PYTHON) -m pip install --upgrade --target $(DEPS_DIR) -r requirements-dev.txt; \
	fi

test:
	@if [ -x "$(PYTEST)" ]; then \
		PYTHONPATH=. $(PYTEST); \
	elif [ -d "$(DEPS_DIR)" ]; then \
		PYTHONPATH="$(DEPS_DIR):." $(PYTHON) -m pytest; \
	else \
		printf '%s\n' 'pytest is not installed. Run make install first.'; \
		exit 1; \
	fi

run: check-env check-app
	@if [ -x "$(VENV)/bin/python" ]; then \
		PYTHONPATH=. $(VENV)/bin/python -m $(APP_MODULE); \
	else \
		PYTHONPATH="$(DEPS_DIR):." $(PYTHON) -m $(APP_MODULE); \
	fi

check-telegram: check-env check-app
	@if [ -x "$(VENV)/bin/python" ]; then \
		PYTHONPATH=. $(VENV)/bin/python -m bot.check_telegram; \
	else \
		PYTHONPATH="$(DEPS_DIR):." $(PYTHON) -m bot.check_telegram; \
	fi

check-proxy: check-env check-app
	@if [ -x "$(VENV)/bin/python" ]; then \
		PYTHONPATH=. $(VENV)/bin/python -m bot.check_proxy; \
	else \
		PYTHONPATH="$(DEPS_DIR):." $(PYTHON) -m bot.check_proxy; \
	fi

check-app:
	@if [ ! -f bot/main.py ]; then \
		printf '%s\n' 'bot/main.py not found yet. Create the bot package before running or building the app.'; \
		exit 1; \
	fi
	@if [ ! -f requirements.txt ]; then \
		printf '%s\n' 'requirements.txt not found. Add runtime dependencies before running the app.'; \
		exit 1; \
	fi

check-env:
	@if [ ! -f "$(ENV_FILE)" ]; then \
		printf '%s\n' 'Missing $(ENV_FILE). Create it from .env.example and set real secrets locally.'; \
		exit 1; \
	fi

docker-build: check-app
	@if [ ! -f Dockerfile ]; then \
		printf '%s\n' 'Dockerfile not found yet. Add it when the application entrypoint exists.'; \
		exit 1; \
	fi
	docker build -t $(IMAGE) .

docker-run: check-app
	@if [ ! -f Dockerfile ]; then \
		printf '%s\n' 'Dockerfile not found yet. Add it when the application entrypoint exists.'; \
		exit 1; \
	fi
	@if [ ! -f "$(ENV_FILE)" ]; then \
		printf '%s\n' 'Missing $(ENV_FILE). Create it from .env.example and set real secrets locally.'; \
		exit 1; \
	fi
	docker run --rm --name $(CONTAINER) --env-file $(ENV_FILE) -v "$$(pwd)/data:/app/data" $(IMAGE)

docker-stop:
	-docker stop $(CONTAINER)
	-docker rm $(CONTAINER)

docker-logs:
	docker logs -f $(CONTAINER)

compose-up: check-app
	docker compose up --build -d

compose-down:
	docker compose down

compose-logs:
	docker compose logs -f

update:
	git pull https://github.com/nghtf/sport4me
	docker compose up --build -d

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov $(DEPS_DIR)
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

flush:
	@if [ ! -f "$(DB_PATH)" ]; then \
		printf '%s\n' 'Database not found: $(DB_PATH)'; \
	else \
		rm -f "$(DB_PATH)" && printf '%s\n' 'Deleted $(DB_PATH)'; \
	fi
