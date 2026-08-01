.PHONY: help dev prod build stop logs logs-web shell clean db-shell status restart makemessages compilemessages

COMPOSE ?= docker compose
COMPOSE_PROD ?= $(COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml
I18N_EXCLUDES ?= --ignore=static/build/* --ignore=static/images/ionicons/*

help: ## Show help
	@echo 'Available commands:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

dev: ## Start development stack (web + db + redis; bind-mount source)
	$(COMPOSE) up --build

prod: ## Start production overlay (no source bind-mount; requires .env)
	@test -f .env || (echo "Missing .env — copy .env.dist and set production secrets:" && echo "  cp .env.dist .env" && exit 1)
	$(COMPOSE_PROD) up --build -d

build: ## Build images
	$(COMPOSE) build

stop: ## Stop services (includes prod overlay / nginx)
	$(COMPOSE_PROD) down

logs: ## Show logs (all services)
	$(COMPOSE) logs -f

logs-web: ## Show web server logs
	$(COMPOSE) logs -f web

shell: ## Open shell in web container
	$(COMPOSE) exec web bash

db-shell: ## Open PostgreSQL shell
	$(COMPOSE) exec db psql -U horilla_user -d horilla_db

status: ## Show status of all services
	$(COMPOSE) ps

restart: ## Restart all services
	$(COMPOSE) restart

makemessages: ## Refresh catalogs without extracting vendored JavaScript identifiers
	python manage.py makemessages -a $(I18N_EXCLUDES)

compilemessages: ## Compile all gettext catalogs
	python manage.py compilemessages

clean: ## Clean up (removes volumes — data loss!)
	$(COMPOSE_PROD) down -v
	docker system prune -f
