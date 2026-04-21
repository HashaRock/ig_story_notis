.PHONY: build up down restart logs status login refresh shell clean

## Build the Docker image
build:
	docker compose build

## Start the poller daemon in the background
up:
	docker compose up -d

## Stop the daemon
down:
	docker compose down

## Restart the daemon (picks up .env changes without rebuilding)
restart:
	docker compose restart

## Tail live logs (Ctrl+C to exit)
logs:
	docker compose logs -f

## Show running container status
status:
	docker compose ps

## Interactive Instagram login — run this once on first deploy or after session expiry
login:
	docker compose run --rm ig_story_notis python -c "\
from config import Config; from ig_client import IGClient; \
ig = IGClient(Config.load()); ig.login(); print('Session saved successfully.')"

## Force a session refresh (re-authenticates and overwrites the saved session)
refresh:
	docker compose run --rm ig_story_notis python -c "\
from config import Config; from ig_client import IGClient; \
ig = IGClient(Config.load()); ig.refresh_session(); print('Session refreshed.')"

## Open a shell inside the container (useful for debugging)
shell:
	docker compose run --rm ig_story_notis /bin/bash

## Remove built image and clear data (⚠ deletes session + seen-story state)
clean:
	docker compose down --rmi local
	rm -rf data/ig_session data/seen_stories.json
