# ◈ CoinCoach — AI Personal Finance Tracker

A full-stack personal finance app with AI-powered chat, Neon PostgreSQL storage, JWT authentication, and real-time budget tracking across Day → Week → Month → Year.

---

## 🏗 Architecture

```
coincoach/
├── backend/
│   ├── server.js              # Express app entry
│   ├── routes/
│   │   ├── auth.js            # Register, login, logout, /me
│   │   ├── entries.js         # CRUD + UPSERT for financial entries
│   │   └── chat.js            # Groq AI proxy (auth-gated, rate-limited)
│   ├── middleware/
│   │   └── auth.js            # JWT verification middleware
│   ├── db/
│   │   ├── pool.js            # Neon PostgreSQL connection pool
│   │   ├── migrate.js         # CLI migration runner
│   │   └── migrate_inline.js  # Auto-runs on server start
│   ├── .env                   # Secrets (never commit)
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── tabs/          # Overview, Expenses, History, Plan
│   │   │   ├── AuthPage.jsx   # Login + Register
│   │   │   ├── ChatArea.jsx
│   │   │   ├── Header.jsx
│   │   │   ├── InputBox.jsx   # Quick + Story modes, autocomplete
│   │   │   ├── LandingPage.jsx
│   │   │   ├── MessageBubble.jsx
│   │   │   └── Sidebar.jsx
│   │   ├── hooks/
│   │   │   ├── useAuth.js     # Auth state + token management
│   │   │   └── useChat.js     # AI chat + entry persistence
│   │   ├── utils/
│   │   │   ├── api.js         # Central API client with auth headers
│   │   │   ├── constants.js
│   │   │   ├── dateUtils.js
│   │   │   └── format.js
│   │   └── styles/            # CSS Modules per component
│   └── vite.config.js
└── package.json               # Root dev runner
```

---

## ⚡ Quick Start

### 1. Install
```bash
unzip coincoach-production.zip && cd coincoach
npm run install:all
```

### 2. Configure backend
```bash
cp backend/.env.example backend/.env
# Edit backend/.env — DATABASE_URL and JWT_SECRET already set
```

### 3. Run (both servers together)
```bash
npm run dev
# Frontend → http://localhost:5173
# Backend  → http://localhost:3001
```

---

## 🚀 Deploy

### Backend → Railway
1. Push to GitHub
2. Railway → New Project → backend folder
3. Add env vars from `.env`
4. Get your Railway URL

### Frontend → Vercel
1. Vercel → New Project → frontend folder
2. Add env: `VITE_API_BASE=https://your-railway-url.railway.app/api`
3. Update `frontend/src/utils/api.js`: `const BASE = import.meta.env.VITE_API_BASE || '/api'`

---

## 🔒 Security

| Layer | Implementation |
|---|---|
| Passwords | bcrypt with 12 rounds |
| Sessions | JWT (7d) + httpOnly cookie |
| API key | Server-side only, never exposed to browser |
| Rate limiting | 60 AI calls per user per 15 min |
| SQL injection | pg parameterised queries everywhere |
| CORS | Locked to known origins |
| Request size | 40kb max body |

---

## 🗄 Database Schema (Neon PostgreSQL)

```sql
users (id uuid, name, email unique, password hash, created_at)
entries (id uuid, user_id →users, entry_date date, income numeric,
         expenses jsonb, note text, corrected bool, UNIQUE(user_id,entry_date))
```

One row per user per calendar date. Same-day entries **merge** (add). Corrections **replace** entirely.

---

## ✨ Features

- **AI Chat** — Groq LLaMA 3.3 70B, bullet-point responses
- **Story Mode** — type naturally, AI extracts all amounts
- **Smart Corrections** — "I made a mistake, petrol was ₹300" → replaces, never double-counts
- **Day → Week → Month → Year** — full history breakdown in History tab
- **Negative balance** — shown as -₹X in red, never errors
- **Donut chart** — live spending breakdown
- **50/30/20 plan** — with actual vs target tracking
- **Cloud storage** — Neon PostgreSQL, multi-device
- **JWT Auth** — secure login/register, stays logged in 7 days
