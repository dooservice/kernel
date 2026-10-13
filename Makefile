.PHONY: help install lint test typecheck check bump

GREEN := \033[0;32m
RED   := \033[0;31m
NC    := \033[0m

help: ## Show this help
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Install the package and its dev tools
	uv sync

lint: ## Ruff
	uv run ruff check src tests

typecheck: ## basedpyright
	uv run basedpyright src

test: ## pytest
	uv run pytest -q

check: lint typecheck test ## Everything the release runs

bump: check ## Release a version: make bump VERSION=0.2.0
	@[ "$(VERSION)" != "" ] || { echo "$(RED)Set VERSION: make bump VERSION=0.2.0$(NC)"; exit 1; }
	@grep -q "## \[$(VERSION)\]" CHANGELOG.md || { \
	    echo "$(RED)Add a ## [$(VERSION)] section to CHANGELOG.md before releasing$(NC)"; exit 1; }
	sed -i 's/^version = .*/version = "$(VERSION)"/' pyproject.toml
	uv lock -q
	git add -A
	git diff --cached --quiet || git commit -m "chore: bump kernel to $(VERSION)"
	git tag $(VERSION)
	git push origin HEAD
	git push origin $(VERSION)
	@echo "$(GREEN)✓ Kernel $(VERSION) released — point its users at tag = \"$(VERSION)\"$(NC)"
