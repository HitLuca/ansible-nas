# Development helpers. Run `make` to list the targets.
#
# The linters are run through pre-commit, so their versions match CI.
# pylint and mypy are pinned in pyproject.toml/uv.lock, the rest in
# .pre-commit-config.yaml.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Roles that have a molecule scenario.
ROLES := $(notdir $(patsubst %/molecule,%,$(wildcard roles/*/molecule)))

.PHONY: help lint lint-yaml lint-ansible lint-docs lint-python check-repo check-ports check-images check-yaml-unchanged update-images scan-images check-breaking release test test-unit test-all guard-role

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-13s\033[0m %s\n", $$1, $$2}'

lint: check-repo ## Run every linter plus the repo checks
	uv run pre-commit run --all-files

check-repo: ## Run the repo's own checks: enabled flags, role structure, changelog, ports
check-repo: ## Run the repo's own checks: enabled flags, role structure, changelog
	uv run python scripts/check_enabled_vars.py
	uv run python scripts/check_role_structure.py
	uv run python scripts/check_breaking_changes.py
	uv run python scripts/check_port_conflicts.py

lint-yaml: ## Lint YAML only
	uv run pre-commit run yamllint --all-files

lint-ansible: ## Lint the playbook only
	uv run pre-commit run ansible-lint --all-files

lint-docs: ## Lint Markdown docs only
	uv run pre-commit run markdownlint --all-files

lint-python: ## Lint Python only (pylint + mypy + black)
	uv run pre-commit run pylint --all-files
	uv run pre-commit run mypy --all-files
	uv run pre-commit run black --all-files

check-ports: ## Report host ports claimed by more than one role
	uv run python scripts/check_port_conflicts.py

check-images: ## Report pinned image versions that are behind upstream
	uv run python scripts/check_image_versions.py --check

check-yaml-unchanged: ## Fail if a YAML file's parsed data differs from git (BASE=HEAD); for bulk reformats
	uv run python scripts/check_yaml_unchanged.py $(BASE)

check-breaking: ## Report breaking changes since the last release (optional tag)
	uv run python scripts/check_breaking_changes.py $(TAG)

release: ## Rename Unreleased in the changelog, commit and tag (VERSION=vX.Y.Z); never pushes
	@test -n "$(VERSION)" || { echo "usage: make release VERSION=vX.Y.Z"; exit 1; }
	uv run python scripts/release.py $(VERSION)

update-images: ## Rewrite pinned image versions to the latest same-major tag
	uv run python scripts/check_image_versions.py --patch

scan-images: ## Report pinned images with fixable vulnerabilities (needs trivy)
	uv run python scripts/scan_images.py --severity CRITICAL,HIGH

test: guard-role ## Run one role's molecule test, e.g. make test ROLE=loki
	uv run pytest "tests/test_molecule.py::test_role[$(ROLE)]" -q

test-unit: ## Run the unit tests of the scripts under tests/ (fast, no Docker)
	uv run pytest tests --ignore=tests/test_molecule.py -q

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
