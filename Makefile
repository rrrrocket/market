.PHONY: dev test lint migrate seed build
dev:
	@echo "Run in two terminals:"
	@echo "  cd apps/api && ../../.venv/bin/uvicorn app.main:app --reload"
	@echo "  cd apps/web && npm run dev"
test:
	cd apps/api && ../../.venv/bin/pytest
lint:
	cd apps/api && ../../.venv/bin/ruff check .
	cd apps/web && npm run lint
migrate:
	cd apps/api && ../../.venv/bin/alembic upgrade head
seed:
	cd apps/api && ../../.venv/bin/python -c "from app.core.database import SessionLocal; from app.services.seed import seed_reference_data; db=SessionLocal(); seed_reference_data(db); db.close()"
build:
	cd apps/web && npm run build

