# Development helpers. Run `make` to list the targets.
#
# The linters are run through pre-commit, so their versions match CI.
# pylint and mypy are pinned in pyproject.toml/uv.lock, the rest in
# .pre-commit-config.yaml.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Roles that have a molecule scenario.
ROLES := $(notdir $(patsubst %/molecule,%,$(wildcard roles/*/molecule)))

.PHONY: help lint lint-yaml lint-ansible lint-docs lint-python check-ports check-images update-images test test-all guard-role

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-13s\033[0m %s\n", $$1, $$2}'

lint: ## Run every linter plus the enabled-flag and role-structure checks
	uv run pre-commit run --all-files
	tests/check-enabled-vars.sh
	tests/check-role-structure.sh

lint-yaml: ## Lint YAML only
	uv run pre-commit run yamllint --all-files

lint-ansible: ## Lint the playbook only
	uv run pre-commit run ansible-lint --all-files

lint-docs: ## Lint Markdown docs only
	uv run pre-commit run markdownlint --all-files

lint-python: ## Lint Python only (pylint + mypy)
	uv run pre-commit run pylint --all-files
	uv run pre-commit run mypy --all-files

check-ports: ## Report host ports claimed by more than one role
	tests/check-port-conflicts.sh

check-images: ## Report pinned image versions that are behind upstream
	uv run python tests/check_image_versions.py --check

update-images: ## Rewrite pinned image versions to the latest same-major tag
	uv run python tests/check_image_versions.py --patch

test: guard-role ## Run one role's molecule test, e.g. make test ROLE=loki
	uv run pytest "tests/test_molecule.py::test_role[$(ROLE)]" -q

test-all: ## Run every role's molecule test (slow, needs Docker)
	uv run pytest tests/test_molecule.py

guard-role:
	@test -n "$(ROLE)" || { \
		echo "Usage: make test ROLE=<role>"; \
		printf '\nRoles with tests:\n'; printf '%s\n' $(ROLES) | fmt -w 76 | sed 's/^/  /'; \
		exit 2; }
	@test -d "roles/$(ROLE)/molecule" || { \
		echo "No molecule scenario for '$(ROLE)'."; \
		printf '\nRoles with tests:\n'; printf '%s\n' $(ROLES) | fmt -w 76 | sed 's/^/  /'; \
		exit 2; }
