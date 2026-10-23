# PayArc

PayArc is a private, local-first personal finance command centre. It combines expense management, budgeting, goal tracking, recurring-bill awareness, and an on-device rule-based financial coach in one responsive React application.

## Highlights

- Rich transaction records: merchant, category, payment method, account, tags, notes, receipt reference, privacy level, and reimbursable/shared status
- Dashboard with cash-flow snapshots, category analytics, trend visuals, budget health, recent activity, and smart alerts
- Flexible budgets and savings goals with progress tracking
- Recurring-bill tracking and upcoming-payment visibility
- A personal PayArc Coach that turns live financial data into practical, explainable actions
- Local SQLite storage—no account, cloud sync, or third-party AI key required
- Responsive React UI designed for desktop, tablet, and phone

## Run locally

Open two terminals from this folder.

### 1. Start the API

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API docs are available at `http://127.0.0.1:8000/docs`.

### 2. Start the frontend

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL Vite prints (normally `http://127.0.0.1:5173`). The development frontend connects to `http://127.0.0.1:8000/api` by default. Set `VITE_API_URL` if you host the API elsewhere.

## Privacy note

The included assistant is deterministic and uses your locally stored financial data only. It does not call an external AI provider. It is an organizational aid, not financial, tax, or investment advice.
