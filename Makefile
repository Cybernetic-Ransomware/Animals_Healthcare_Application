.PHONY: up up-cd down restart logs logs-flower build deploy shell

COMPOSE    = docker compose --env-file .env -f docker/docker-compose-traefik.yml
COMPOSE_CD = $(COMPOSE) -f docker/docker-compose.cd.yml

up:
	$(COMPOSE) up -d --build

up-cd:
	$(COMPOSE_CD) up -d

down:
	$(COMPOSE) down

restart: down up

logs:
	docker logs -f ahc-web

logs-flower:
	docker logs -f ahc-flower

build:
	$(COMPOSE) build

deploy:
	git pull
	$(MAKE) up-cd

shell:
	docker exec -it ahc-web python manage.py shell
