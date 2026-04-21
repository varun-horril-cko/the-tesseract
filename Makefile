.PHONY: dashboard stop new-plan clean memory-status memory-reset help

DASHBOARD_PORT ?= 3000
PID_FILE := .dashboard.pid

help: ## Show available commands
	@echo ""
	@echo "  \033[1m\033[38;5;216m🫩  The Tesseract\033[0m"
	@echo "  \033[2m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; { \
			icon = "  "; \
			if ($$1 == "dashboard")     icon = "  \033[38;5;216m🖥️ \033[0m"; \
			if ($$1 == "stop")          icon = "  \033[38;5;167m🛑\033[0m"; \
			if ($$1 == "new-plan")      icon = "  \033[38;5;150m📋\033[0m"; \
			if ($$1 == "clean")         icon = "  \033[38;5;245m🧹\033[0m"; \
			if ($$1 == "memory-status") icon = "  \033[38;5;183m🧠\033[0m"; \
			if ($$1 == "memory-reset")  icon = "  \033[38;5;167m🧠\033[0m"; \
			if ($$1 == "help")          icon = "  \033[38;5;223m❓\033[0m"; \
			printf "%s \033[1m\033[38;5;223m%-18s\033[0m \033[2m%s\033[0m\n", icon, $$1, $$2 \
		}'
	@echo ""
	@echo "  \033[2mExamples:\033[0m"
	@echo "    \033[38;5;150mmake dashboard\033[0m            Start the dashboard"
	@echo "    \033[38;5;150mmake new-plan NAME=auth\033[0m   Create a new plan"
	@echo "    \033[38;5;150mmake memory-status\033[0m        Check agent memory"
	@echo ""

dashboard: ## Start the dashboard at localhost:$(DASHBOARD_PORT)
	@echo ""
	@echo "  \033[1m\033[38;5;216m🫩  The Tesseract — Dashboard\033[0m"
	@echo "  \033[2m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "  \033[38;5;150m✓\033[0m Already running (PID $$(cat $(PID_FILE)))"; \
	else \
		python3 dashboard/server.py --port $(DASHBOARD_PORT) --plans-dir plans --repo-dir . &> /dev/null & echo $$! > $(PID_FILE); \
		sleep 0.3; \
		echo "  \033[38;5;150m✓\033[0m Server started (PID $$!)"; \
	fi
	@echo "  \033[38;5;223m→\033[0m \033[4mhttp://localhost:$(DASHBOARD_PORT)\033[0m"
	@echo ""
	@which open > /dev/null 2>&1 && open "http://localhost:$(DASHBOARD_PORT)" || \
		which xdg-open > /dev/null 2>&1 && xdg-open "http://localhost:$(DASHBOARD_PORT)" || true

stop: ## Stop the dashboard server
	@if [ -f $(PID_FILE) ]; then \
		kill $$(cat $(PID_FILE)) 2>/dev/null && \
			echo "  \033[38;5;167m🛑\033[0m Dashboard stopped." || \
			echo "  \033[2mDashboard not running.\033[0m"; \
		rm -f $(PID_FILE); \
	else \
		echo "  \033[2mNo dashboard PID file found.\033[0m"; \
	fi

new-plan: ## Create a new plan from template (NAME=feature-name)
ifndef NAME
	$(error 📋 NAME is required. Usage: make new-plan NAME=feature-name)
endif
	@cp templates/plan-template.md plans/$(NAME).md
	@sed -i.bak 's/\[Feature Name\]/$(NAME)/g' plans/$(NAME).md && rm -f plans/$(NAME).md.bak
	@DATESTR=$$(date +%Y-%m-%d); \
		sed -i.bak "s/YYYY-MM-DD/$$DATESTR/g" plans/$(NAME).md && rm -f plans/$(NAME).md.bak
	@echo "  \033[38;5;150m📋 Created\033[0m plans/$(NAME).md"

clean: ## Remove completed plans (status: Complete)
	@echo "  \033[38;5;245m🧹 Scanning for completed plans...\033[0m"
	@grep -rli 'Status.*\(COMPLETE\|Complete\)' plans/ 2>/dev/null | while read f; do \
		echo "    \033[38;5;167m✕\033[0m Removing: $$f"; \
		rm -f "$$f"; \
	done || echo "    \033[2mNo completed plans found.\033[0m"

memory-status: ## Show agent memory entry counts
	@echo ""
	@echo "  \033[1m\033[38;5;183m🧠 Agent Memory Status\033[0m"
	@echo "  \033[2m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
	@for agent in odysseus rocky marvin babel muaddib ratatouille; do \
		file="memory/$$agent.md"; \
		if [ -f "$$file" ]; then \
			count=$$(grep -v '^$$\|^#\|^>\|^---\|^<!--' "$$file" | grep -cv '-->$$' 2>/dev/null || echo 0); \
			modified=$$(date -r "$$file" "+%Y-%m-%d %H:%M" 2>/dev/null || echo "unknown"); \
			printf "  \033[38;5;223m%-14s\033[0m \033[38;5;183m%3s entries\033[0m  \033[2m(modified: %s)\033[0m\n" "$$agent" "$$count" "$$modified"; \
		else \
			printf "  \033[38;5;223m%-14s\033[0m \033[2mno memory file\033[0m\n" "$$agent"; \
		fi; \
	done
	@echo ""

memory-reset: ## Reset all agent memory files to empty templates
	@echo ""
	@read -p "  🧠 Reset ALL agent memory? This cannot be undone. [y/N] " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		for agent in odysseus rocky marvin babel muaddib ratatouille; do \
			if [ -f "memory/$$agent.md" ]; then \
				head_line=$$(head -1 "memory/$$agent.md"); \
				git checkout -- "memory/$$agent.md" 2>/dev/null || echo "  \033[2mCould not reset $$agent (not in git?)\033[0m"; \
			fi; \
		done; \
		echo "  \033[38;5;150m✓\033[0m All agent memory reset to templates."; \
	else \
		echo "  \033[2mCancelled.\033[0m"; \
	fi
