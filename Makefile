.PHONY: help up up-cd down down-cd restart logs logs-flower build deploy shell
.DEFAULT_GOAL := help

COMPOSE    = docker compose --env-file .env -f docker/docker-compose-traefik.yml
COMPOSE_CD = $(COMPOSE) -f docker/docker-compose.cd.yml

help: ## List available targets
	@awk 'BEGIN {FS = ":.*##"}; /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

up: ## Build images locally and start production stack
	$(COMPOSE) up -d --build

up-cd: ## Start production stack with Watchtower CD overlay (pull from GHCR)
	$(COMPOSE_CD) up -d

down: ## Stop production stack (without Watchtower)
	$(COMPOSE) down

down-cd: ## Stop full CD stack including Watchtower
	$(COMPOSE_CD) down

restart: down up ## Rebuild and restart production stack

logs: ## Follow web container logs
	docker logs -f ahc-web

logs-flower: ## Follow Flower container logs
	docker logs -f ahc-flower

build: ## Build images without starting containers
	$(COMPOSE) build

deploy: ## Pull latest git changes and restart CD stack
	git pull
	$(MAKE) up-cd

shell: ## Open Django shell inside web container
	docker exec -it ahc-web python manage.py shell
