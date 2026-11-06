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
(`mark@apexlegal.com`), Crestview Counsel, several routing rules, an unmatched
lead, a pending lead, and an accepted sample case.

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

## Architecture and system design

### Monorepo instead of microservices

The application is a modular monolith: the frontend and backend are separate
deployable containers, while the domain logic and transactional database remain
in one API service. Accepting a lead and creating its case are a single
transactional workflow, so a service boundary would add network and distributed
failure modes without improving this assessment's scale target of approximately
1,000 leads per day. The monorepo and Compose setup also make the complete
application straightforward to review and run.

### Relational schema and tenant isolation

PostgreSQL stores the transactional domain data; SQLAlchemy 2.0 models and
typed relationships express constraints and provide a maintainable unit-of-work
layer. Alembic migrations are the schema source of truth. This keeps routing,
assignment, case creation, and audit updates transactionally consistent while
retaining the ability to issue explicit SQL for reporting and indexing.

Each case's `assigned_firm_id` determines which firm currently has access.
Reassignment updates the case and its lead, so the former firm loses access
immediately and the new firm receives the case and its documents. Notes carry
their own `author_firm_id`; firm reads filter notes to the current firm's ID,
not the case's current owner. Therefore a reassigned firm does not inherit
another firm's private notes, while authorized administrators can inspect the
historical record. Plaintiff responses do not include private notes.

Indexes support tenant-scoped filters, ordering, related-record lookup, and
audit history. A PostgreSQL `pg_trgm` migration accelerates substring search.
Directory APIs use pagination and compact case summaries so list pages do not
load hundreds of related documents and notes for every row.

### Document storage

PDF bytes are stored on disk under `backend/uploads/`; PostgreSQL stores
case-linked metadata such as filename, MIME type, size, uploader, and file path.
This keeps large binary payloads out of transactional rows and lets documents
remain associated with a case through reassignment. Compose bind-mounts the
upload directory so files survive container replacement. A production
deployment should replace local disk with durable object storage and configure
backups and retention policies.

### Demo authentication boundary

This assessment build uses `X-Demo-User-Email` to switch among seeded personas.
It is a convenient workflow demonstration, **not production authentication or
authorization at the network boundary**. A public deployment must replace it
with a verified identity provider/session mechanism and harden secrets,
transport security, upload scanning, and operational policies.

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
