.PHONY: up down reset logs migrate seed-dev bootstrap test backend-test frontend-test

up:
	docker compose up -d --build --wait

down:
	docker compose down

reset:
	docker compose down -v

logs:
	docker compose logs -f

migrate:
	docker compose exec backend-api alembic upgrade head

seed-dev:
	docker compose exec backend-api python -m agropolia.dev.seed

bootstrap: up migrate seed-dev

backend-test:
	docker compose exec backend-api pytest -q /workspace/tests

frontend-test:
	docker compose exec client npm test -- --run

test: backend-test frontend-test
