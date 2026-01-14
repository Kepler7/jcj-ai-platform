# JCJ AI Platform

Educational platform with AI-assisted insights to support teachers and families, starting with a **Pre-K 2 (ages 5–8) pilot focused on neurodiversity**.

This repository contains a **monorepo** with:

* **Backend**: FastAPI (Python)
* **Frontend**: React (Vite)
* **Infrastructure**: Docker Compose (local development)

The system is designed as a **modular monolith**, intentionally structured to allow an easy future migration to microservices and Kubernetes.

---

## 🎯 Project Goals

* Help teachers create structured educational reports quickly.
* Use AI to generate **educational support strategies** (not diagnoses).
* Deliver clear, practical guidance to families.
* Keep humans in control: AI assists, teachers approve.

> ⚠️ This platform **does not diagnose**, **does not use clinical labels**, and **does not make autonomous decisions**. It is an educational support tool.

---

## 🧱 Tech Stack

### Backend

* **FastAPI** – API and application core
* **Python 3.11**
* **PostgreSQL** – structured data (students, reports, users)
* **Redis** – background jobs and caching
* **ChromaDB** – vector store for educational playbooks and context
* **Agno** – AI agent orchestration (reasoning with guardrails)

### Frontend

* **React + TypeScript** (Vite)
* Web UI for teachers and administrators
* Parent view via secure link (no login required)

### Infrastructure

* **Docker & Docker Compose** – local development and reproducibility

---

## 📁 Repository Structure

```
jcj-ai-platform/
  backend/          # FastAPI backend
  frontend/         # React frontend
  infra/            # Infra-related docs/scripts
  docker-compose.yml
  .env.example
  README.md
```

---

## 🚀 Getting Started (Local Development)

### Prerequisites

* **Docker Desktop** installed and running
* **Git**

> You do NOT need Python or Node installed locally. Docker handles everything.

---

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/YOUR_ORG_OR_USER/jcj-ai-platform.git
cd jcj-ai-platform
```

---

### 2️⃣ Environment Variables

Create a local `.env` file from the example:

```bash
cp .env.example .env
```

You normally do not need to change values for local development.

> ⚠️ Never commit `.env` to GitHub.

---

### 3️⃣ Build and Run with Docker

From the project root:

```bash
docker compose up --build
```

This will start:

* Backend (FastAPI)
* Frontend (React)
* PostgreSQL
* Redis
* ChromaDB

---

## 🌍 Environment Configuration

This project is configured **entirely through environment variables**.  
You should be able to switch between `dev`, `staging`, and `prod` **without changing code**.

### ENV Modes

Set `ENV` in your `.env` file:

- `ENV=dev` → Local development (default)
- `ENV=staging` → Pre-production testing (future)
- `ENV=prod` → Production (future)

### Required Variables

These variables are required for the backend:

- `ENV`  
  Controls runtime mode (`dev | staging | prod`)

- `LOG_LEVEL`  
  Logging verbosity (recommended: `INFO` for dev, `WARNING` for prod)

- `DATABASE_URL`  
  PostgreSQL connection string

- `REDIS_URL`  
  Redis connection string (queues/background jobs)

- `CHROMA_URL`  
  ChromaDB endpoint URL

Example (local dev):
```env
ENV=dev
LOG_LEVEL=INFO
DATABASE_URL=postgresql+psycopg://jcj:jcjpassword@postgres:5432/jcjdb
REDIS_URL=redis://redis:6379/0
CHROMA_URL=http://chroma:8000


### 4️⃣ Verify Services

#### Backend healthcheck

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok"}
```

#### Backend dependencies healthcheck

```bash
curl http://localhost:8000/health/deps
```

Expected response:

```json
{
  "status": "ok",
  "deps": {
    "postgres": {"ok": true, "error": null},
    "redis": {"ok": true, "error": null}
  }
}
```

#### Frontend

Open in browser:

```
http://localhost:5173
```

---

## 🔐 Security & Ethics

* No clinical diagnoses
* No medical recommendations
* No autonomous decisions
* Teachers always review and approve content
* Parents access reports via **secure, expiring links**

This design protects:

* children
* families
* educators
* the organization

---

### To run script inside the container

```bash
docker compose exec backend sh -lc "PYTHONPATH=/app python
```

## 🧪 Development Notes

* The backend is a **modular monolith** (auth, students, reports, AI, messaging).
* Internal boundaries are defined using contracts and events.
* This allows future extraction into microservices with minimal refactoring.

---

## 📦 What Is NOT Tracked in Git

The following are intentionally ignored:

* Python virtual environments (`.venv`, `jcj-ai/`)
* `node_modules/`
* `.env`
* OS and editor files

See `.gitignore` for details.

---

## 🛣️ Roadmap (High Level)

* ✅ Local dev environment (Docker)
* 🔄 Teacher authentication
* 🔄 Student and report management
* 🔄 AI-generated educational support
* 🔄 Secure parent sharing (WhatsApp link)
* ⏭️ Pilot deployment (DigitalOcean)
* ⏭️ Feedback loop and iteration

---

## 🌿 Git Workflow (IMPORTANT)

To keep the codebase stable and avoid breaking the main branch, **direct pushes to `main` are not allowed**.

### Rules

* ❌ **Never push directly to `main`**
* ✅ Always create a new branch for your work
* ✅ Push your branch to GitHub
* ✅ Open a **Pull Request (PR)** into `main`
* ✅ A PR **must be approved by the CTO** (for now) before merging

### Recommended Branch Naming

```
feature/<short-description>
fix/<short-description>
chore/<short-description>
```

Example:

```
feature/auth-login
```

### Basic Workflow

```bash
# Create a new branch
git checkout -b feature/your-feature-name

# Work and commit
git add .
git commit -m "feat: short clear description"

# Push branch
git push origin feature/your-feature-name
```

Then open a Pull Request on GitHub and request approval from the **CTO**.

---

## 👥 Contributors

* **Kepler Hiram Velasco Guzmán** – CTO
* **Jefte Velasco Solano** – Software Developer
* JCJ Neuroeducativo Team

---

## 📄 License

Private – JCJ Neuroeducativo Team

---

## 📄 License

Private – JCJ Neuroeducativo

