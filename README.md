# The Unclaimed Things Network (UTN)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.14](https://img.shields.io/badge/Python-3.14-blue.svg)](https://www.python.org/)
[![React 19](https://img.shields.io/badge/React-19.2-cyan.svg)](https://react.dev/)
[![Neon Postgres](https://img.shields.io/badge/PostgreSQL-pgvector-teal.svg)](https://neon.tech/)

A privacy-conscious, multi-location campus lost-and-found recovery network connecting disparate campus facilities (Libraries, Central Security, Transit Services, Student Centers). UTN replaces fragmented social media boards and localized paper logbooks with a unified, permission-gated recovery platform.

---

## Architectural Principles & Core Features

1. **Zero-Leakage Privacy Boundary**
   - Public listings expose only generic, neutral attributes.
   - Distinctive markings, serial numbers, engraving, and confidential ownership statements reside in an isolated **Private Verification Vault** (`ReportPrivateDetail`), accessible exclusively to assigned facility staff during verification.
2. **EXIF Metadata Stripping & Image Security**
   - Uploaded photos are stripped in-memory of all EXIF metadata (camera make, device serials, and GPS coordinates) before storage.
   - Enforces a 5MB payload limit and randomized server-side file naming.
3. **NVIDIA NIM Hybrid AI with Graceful Fallback**
   - High-dimensional vector embeddings generated using `nvidia/nemotron-3-embed-1b` (2048 dimensions).
   - Candidate ranking combines Neon `pgvector` cosine distance (`<=>`), category agreement, and PostgreSQL keyword/trigram similarity.
   - If NVIDIA NIM is unreachable or disabled (`NIM_ENABLED=false`), the system gracefully falls back to full-text search with zero downtime.
4. **Immutable Multi-Location Custody Trail**
   - Custody transfer invariance: when an item is transferred between campus facilities, it remains marked at the originating location until destination staff physically acknowledges receipt.
   - Every custody handover and transfer records an immutable `CustodyEvent`.
5. **Campus Admin Governance & Telemetry**
   - Operational dashboard for campus administrators: real-time system metrics, append-only audit trail, content moderation queue (`ACTIVE`, `HIDDEN`, `REMOVED`), and user governance (account suspension).
6. **Automated Data Retention Engine**
   - Automated batch cleanup command (`enforce_retention_policy`) enforcing privacy lifecycle compliance:
     - 30-day purge of withdrawn reports.
     - 90-day anonymization and private vault scrubbing of returned items.
     - 180-day encrypted purge of claim verification statements and evidence.
7. **Production Rate Limiting & Throttling**
   - Scoped rate limiting on sensitive endpoints (sign-in, registration, claim submission, report creation, and search) with standardized JSON error envelopes.

---

## Repository Structure

```text
unclaimed-things-network/
├── backend/
│   ├── accounts/          # Custom user model, email authentication, role mappings
│   ├── locations/         # Multi-facility locations and staff membership scoping
│   ├── reports/           # Lost and found reports, private vault, EXIF image service
│   ├── matching/          # NVIDIA NIM adapter, pgvector search, feedback engine
│   ├── claims/            # Ownership claims, proof submissions, handover workflows
│   ├── custody/           # Multi-location transfers and immutable custody ledger
│   ├── audit/             # Campus admin workspace, moderation, audit event logs
│   ├── common/            # Health checks (/health/live, /health/ready), exception handling
│   ├── config/            # Django project settings, URL routing, DRF throttling
│   ├── tests/             # Automated end-to-end and security test suite
│   ├── Dockerfile         # Backend production container specification
│   ├── manage.py
│   └── requirements.txt   # Pinned backend dependencies
├── frontend/
│   ├── src/               # React 19 + TypeScript components, views, API client
│   ├── public/
│   ├── Dockerfile         # Frontend multi-stage build container specification
│   ├── nginx.conf         # Static asset serving configuration
│   └── package.json       # Frontend dependencies and build scripts
├── infra/
│   ├── docker-compose.yml # Orchestrated composition (db, backend, frontend, nginx)
│   └── nginx.conf         # Reverse proxy routing /api/v1/ and /
├── .env.example           # Environment template with documented parameters
├── .gitignore             # Strict privacy and secret exclusions
├── LICENSE                # MIT License
└── README.md              # Project documentation and developer quickstart
```

---

## Quickstart & Local Development

### Prerequisites
- Python 3.12+ (Python 3.14 recommended)
- Node.js v20+ & npm
- PostgreSQL with `pgvector` (or a free [Neon](https://neon.tech) Serverless Postgres project)

### 1. Environment Configuration
Copy `.env.example` to `.env` and fill in your database credentials:
```bash
cp .env.example .env
```

### 2. Backend Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run migrations
cd backend
python manage.py migrate

# Seed campus locations and pilot users
python manage.py seed_pilot_data

# Start development server (Port 8000)
python manage.py runserver 127.0.0.1:8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The client will be running at `http://localhost:5173/`.

---

## Containerized Deployment (Docker Compose)

To spin up the entire stack with PostgreSQL (`pgvector`), Django backend, React frontend, and Nginx reverse proxy:

```bash
docker-compose -f infra/docker-compose.yml up --build -d
```
Access the application at `http://localhost/`.

---

## Automated Testing & Verification

Run the comprehensive test suite covering health endpoints, authentication, zero-leakage privacy boundaries, EXIF stripping, E2E lost-to-handover lifecycle, custody transfer invariance, IDOR protections, admin governance, and data retention:

```bash
# Run backend test suite
cd backend
python manage.py test tests --keepdb

# Verify frontend production bundle
cd ../frontend
npm run build
```

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
