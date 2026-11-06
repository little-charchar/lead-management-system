# Backend API and database layer

## Setup

Use Python 3.11 or newer. From this directory, install the database dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Set `DATABASE_URL` to a PostgreSQL connection URL when not using the default
`postgresql://postgres:postgres@localhost:5432/lead_management`. Plain
`postgresql://` URLs are configured to use psycopg 3.

## Migrations

From `backend/`, create a revision with
`alembic revision --autogenerate -m "describe change"` and apply migrations with
`alembic upgrade head`. The Alembic environment imports all models and uses the
same dynamically configured database URL as the application.

## Seed data

Run `python -m app.seed` from `backend/` to clear application rows and load a
larger demo dataset: 3 firms, 19 personas, 100 leads, 40 cases, private notes,
and audit history. The reset preserves the schema and Alembic-managed indexes,
but is destructive to application data; do not point it at a database containing
records you need to keep. The container startup uses
`python -m app.seed --if-empty`, which preserves existing records and seeds only
an empty database.

## Run the API

From `backend/`, apply migrations and launch the development server:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

Authenticated demo requests use `X-Demo-User-Email` with a seeded user's email.
Public lead intake accepts the same header optionally; existing plaintiff
accounts must submit with their own header. Uploaded PDFs are stored below
`backend/uploads/` by default. Set `UPLOAD_DIRECTORY` to change the storage root.
Intake PDFs are stored as lead attachments before acceptance and remain linked
to the lead after it becomes a case; the `0002_lead_attachments` migration
creates their metadata table. The `0003_lead_title` migration adds a short
summary title to new and existing leads.
The `0004_scale_indexes` migration adds write-friendly B-tree indexes for
tenant-scoped pagination and PostgreSQL `pg_trgm` indexes for substring search.
It builds the indexes concurrently to reduce write blocking; the migration
database role must be allowed to create the trusted `pg_trgm` extension.

## Run tests

Install the test dependencies and run the isolated SQLite-backed suite from
`backend/`:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```
