.PHONY: dev test lint migrate seed build pipeline pipeline-download pipeline-import pipeline-analyze pipeline-status
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
pipeline:
	docker compose run --rm api python -m app.cli.comtrade_pipeline all
pipeline-download:
	docker compose run --rm api python -m app.cli.comtrade_pipeline download
pipeline-import:
	docker compose run --rm api python -m app.cli.comtrade_pipeline import
pipeline-analyze:
	docker compose run --rm api python -m app.cli.comtrade_pipeline analyze
pipeline-status:
	curl -fsS http://127.0.0.1:7891/api/v1/admin/comtrade-pipeline
