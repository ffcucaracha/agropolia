.PHONY: up down logs migrate test backend-test frontend-test
up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f

migrate:
	docker compose run --rm backend-api alembic upgrade head

backend-test:
	docker compose run --rm backend-api pytest -q /workspace/tests

frontend-test:
	docker compose run --rm client npm test -- --run

test: backend-test frontend-test
