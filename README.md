# NotePlus Backend — FastAPI (Fase 0)

Clean Architecture · Python 3.11+ · FastAPI · SQLAlchemy 2.0 async · PostgreSQL · Pydantic v2 · Alembic

```
backend/app/
├── domain/         # entidades, value_objects, services, errors — sin dependencias externas
├── application/    # ports (Protocol) + use_cases
├── infrastructure/ # persistence (SQLAlchemy), security (bcrypt/jwt), time (Clock), config (pydantic-settings)
├── presentation/   # http routes / schemas (Pydantic) / middlewares
└── main/           # composition root — app.py crea la FastAPI app
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main.app:app --reload --port 8000
# health: http://localhost:8000/api/v1/health  ·  docs: http://localhost:8000/docs
```

Docker:

```bash
docker compose up --build
```

## Migrations

```bash
alembic revision --autogenerate -m "init"
alembic upgrade head
```
