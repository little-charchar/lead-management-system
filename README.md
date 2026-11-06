# Legal Lead Management System

A full-stack legal lead-management and case-workspace application built for a
take-home technical assessment. It demonstrates deterministic law-firm routing,
plaintiff intake, firm review and case management, and system-wide administration
with auditable reassignment and strict firm-private notes.

The monorepo contains a FastAPI/SQLAlchemy backend, Alembic migrations, and a
Next.js interface with a built-in demo persona switcher. Docker Compose starts
PostgreSQL, migrates and seeds a new database, then starts the API and frontend.

## Quick start

Requirements: Git and Docker Desktop (or Docker Engine with the Compose plugin).
No local Python or Node installation is needed.

```bash
git clone https://github.com/little-charchar/lead-management-system.git
cd lead-management-system
docker compose up --build
```

On the first start, Compose waits for PostgreSQL's health check, the backend
applies Alembic migrations and seeds an empty database, and the frontend starts
after the API is healthy. Open:

- **Application:** <http://localhost:3000>
- **Interactive API docs:** <http://localhost:8000/docs>

The seeded demo database and uploaded PDFs persist across container restarts.
The startup seed is non-destructive when users already exist. To intentionally
remove all local database data and seed again, run:

```bash
docker compose down -v
docker compose up --build
```

`docker compose down -v` deletes the named PostgreSQL volume; use it only when
you want a fresh demo database. Uploaded files are stored separately in
`backend/uploads/` and are not removed by that command. Stop the services with
`Ctrl+C`, or run `docker compose down` in another terminal.

## Demo personas

Use the **Switch persona** controls at the top of the application to change
workspaces. These are seeded demo identities, not real user accounts.

| Name | Email | Role | Firm |
|---|---|---|---|
| Jane Doe | `jane@plaintiff.com` | Plaintiff | — |
| Sarah Attorney | `sarah@apexlegal.com` | Attorney | Apex Legal Partners |
| David Attorney | `david@beaconrights.com` | Attorney | Beacon Rights Group |
| Elena Admin | `admin@system.com` | System administrator | — |

The seed also includes Bob Smith (`bob@plaintiff.com`), Mark Paralegal
(`mark@apexlegal.com`), Crestview Counsel, several routing rules, and 12
additional plaintiff personas. The expanded dataset contains 100 leads across
unassigned, pending, accepted, and declined workflows; 40 cases across multiple
progress stages; firm-private notes; and a populated audit timeline.

## Five-minute interactive verification

This short walkthrough exercises routing, acceptance, case operations,
documents, audit history, reassignment, and firm isolation:

1. **Submit a routed lead.** Switch to Jane Doe and create a lead with category
   **Personal Injury**, region **NY**, and a short description. The matching
   routing rule assigns it to Apex Legal Partners for review.
2. **Accept it as the assigned firm.** Switch to Sarah Attorney. Find Jane's
   new item in the firm inbox, inspect it, and accept it. It becomes a case.
3. **Upload a plaintiff document.** Switch back to Jane, open the accepted case,
   and upload a small PDF. Confirm it appears in the case's shared documents.
4. **Update progress and add a private note.** Switch to Sarah, open the case,
   advance its progress, and add a clearly identifiable firm-private note such
   as “Apex-only verification note.”
5. **Reassign as an administrator.** Switch to Elena Admin, locate the case in
   the global case directory, inspect its audit history, and reassign it to
   **Beacon Rights Group**.
6. **Verify the new firm's access.** Switch to David Attorney. The case should
   appear in Beacon's workspace, and its plaintiff-uploaded PDF should still be
   available. The Apex-only note must not appear.
7. **Verify old-firm isolation and retained history.** Switch to Sarah: the
   reassigned case should no longer appear in Apex's workspace, and directly
   requesting `GET http://localhost:8000/api/cases/{case_id}` with
   `X-Demo-User-Email: sarah@apexlegal.com` should return `403`. Switch to
   Elena: the admin can still inspect the historical Apex note and the
   reassignment audit event.

The same flow can be explored in the API docs. The frontend demo switcher sends
the selected identity in the `X-Demo-User-Email` header.

## Demo routing: region and category to firm

The seed data routes leads to a firm only when both the category and region
match:

| Category | Region | Routed firm |
| --- | --- | --- |
| `PERSONAL_INJURY` | `NY` | Apex Legal Partners |
| `LABOR` | `CA` | Beacon Rights Group |
| `FAMILY` | `ON` | Crestview Counsel |

Other category and region combinations remain unassigned until an admin
reassigns them.

## Automated tests

The backend image includes the test dependencies. With the Compose services
running:

```bash
docker compose exec backend pytest
```

The test suite uses an isolated SQLite-backed test database and exercises
routing, permissions, reassignment, document handling, CORS, and pagination.

## Repository layout

```text
backend/   FastAPI application, SQLAlchemy models, migrations, seed, tests
frontend/  Next.js application and demo persona switcher
docker-compose.yml
```

Configuration templates are in `backend/.env.example` and
`frontend/.env.example`. `docker compose up --build` supplies the container
settings directly and does not require either environment file.
