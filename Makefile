.PHONY: help dev prod build stop logs shell clean db-shell status restart

help: ## Show help
	@echo 'Available commands:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

dev: ## Start development server (web + db + redis)
	docker compose up --build

prod: ## Start production with nginx
	docker compose --profile production up --build -d

build: ## Build images
	docker compose build

stop: ## Stop services
	docker compose --profile production down

logs: ## Show logs (all services)
	docker compose logs -f

logs-web: ## Show web server logs
	docker compose logs -f web

shell: ## Open shell in web container
	docker compose exec web bash

db-shell: ## Open PostgreSQL shell
	docker compose exec db psql -U horilla_user -d horilla_db

status: ## Show status of all services
	docker compose ps

restart: ## Restart all services
	docker compose restart

clean: ## Clean up (removes volumes — data loss!)
	docker compose --profile production down -v
	docker system prune -f
