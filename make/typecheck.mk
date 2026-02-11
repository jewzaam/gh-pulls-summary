# Type Checking Targets
# =====================

.PHONY: typecheck

typecheck: requirements-dev ## Run type checking with mypy
	@$(VENV_PYTHON) -m mypy src/gh_pulls_summary
	@printf "$(GREEN)✅ Type checking complete$(RESET)\n"
