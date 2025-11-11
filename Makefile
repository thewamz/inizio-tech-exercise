SHELL := /bin/bash

USER_ID := $(shell id -u)
GROUP_ID := $(shell id -g)
APP_NAME := inizio
APP_VERSION := $(shell git describe --tags --dirty --always)

.PHONY: all
all: build

.PHONY: build
build:
	@echo "[Building image]"
	docker build \
	--build-arg APP_VERSION=$(APP_VERSION) \
	--tag $(APP_NAME):$(APP_VERSION) .

.PHONY: up
up: build
	@echo "[Bringing up a dev environment]"
	UID=$(USER_ID) \
	APP_VERSION=$(APP_VERSION) \
	DATABASE_URL=$(DATABASE_URL) \
	docker-compose up --remove-orphans -d

.PHONY: down
down:
	docker-compose down

.PHONY: requirements
requirements:
	@echo "Generate requirements.txt using pip tools"
	pip-compile --generate-hashes --build-isolation --allow-unsafe requirements.in

.PHONY: upgrade-requirements
upgrade-requirements:
	@echo "Generate requirements.txt using pip tools"
	pip-compile --upgrade --generate-hashes --build-isolation --allow-unsafe \
	requirements.in
