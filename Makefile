SHELL = /bin/bash

.PHONY: help test

help: ## display help on Makefile targets
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.DEFAULT_GOAL := help

test: ## run tests
	. env.sh; \
	. env/bin/activate; \
	pytest -v -s
