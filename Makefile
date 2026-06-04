.PHONY: up down restart logs logs-flower build deploy shell

COMPOSE = docker compose --env-file .env -f docker/docker-compose-traefik.yml

up:
	$(COMPOSE) up -d --build

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
	$(MAKE) up

shell:
	docker exec -it ahc-web python manage.py shell
