.PHONY: setup backend frontend test ui-test build docker sample

setup:            ## install everything
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
	cd frontend && npm install
	@test -f backend/.env || cp backend/.env.example backend/.env

backend:          ## run API on :8000 (dev, auto-reload)
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend:         ## run UI on :5173 (dev)
	cd frontend && npm run dev

test:             ## stage + pipeline + API tests (offline)
	cd backend && .venv/bin/pytest -v

ui-test:          ## headless browser test (backend must be running)
	backend/.venv/bin/python scripts/ui_smoke_test.py

build:            ## build UI into frontend/dist (served by FastAPI)
	cd frontend && npm run build

docker:           ## production container on :8000
	docker compose up --build -d

sample:           ## regenerate the sample HR PDF
	backend/.venv/bin/python scripts/generate_hr_policy_pdf.py
	cp docs/HR_Policy_Handbook.pdf backend/data/sample_docs/
