# PayArc backend

The API is a local FastAPI + SQLite service. It seeds friendly demo data on its first run and keeps all finance data in `backend/payarc.db` (which is deliberately ignored by source control if the project adds a standard `.gitignore`).

## Run it

From the project root:

```powershell
py -m pip install -r backend/requirements.txt
py -m uvicorn backend.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation. The Vite development ports (`5173`, `4173`, and `3000`) plus other localhost ports are allowed by CORS.

## Main routes

- `GET /api/health`
- `GET /api/dashboard`
- `GET, POST, PATCH, DELETE /api/transactions`
- `GET, POST, PATCH, DELETE /api/expenses` (richer transaction representation)
- `GET, POST, PATCH, DELETE /api/budgets`
- `GET, POST, PATCH, DELETE /api/goals`
- `POST /api/goals/{id}/contributions`
- `GET, POST, PATCH, DELETE /api/recurring-bills`
- `GET /api/assistant/recommendations` and `POST /api/assistant/chat`

The personal assistant is intentionally local and rule-based. It derives explainable recommendations from data already stored in PayArc; it does not transmit private financial details to an external AI provider.

