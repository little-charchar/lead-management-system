"""Prepare the database and start the API server."""

import os
import subprocess
import sys
import time

from sqlalchemy.exc import OperationalError

from app.database import engine


def wait_for_database() -> None:
    """Wait for the configured database, failing after a bounded number of tries."""
    attempts = int(os.getenv("DB_CONNECT_ATTEMPTS", "30"))
    delay_seconds = float(os.getenv("DB_CONNECT_DELAY_SECONDS", "2"))
    last_error: OperationalError | None = None

    for attempt in range(1, attempts + 1):
        try:
            with engine.connect():
                print("Database connection established.", flush=True)
                return
        except OperationalError as error:
            last_error = error
            if attempt < attempts:
                print(
                    f"Database is unavailable (attempt {attempt}/{attempts}); "
                    f"retrying in {delay_seconds:g}s.",
                    flush=True,
                )
                time.sleep(delay_seconds)

    raise RuntimeError(
        f"Database did not become available after {attempts} attempts."
    ) from last_error


def main() -> None:
    """Apply migrations, seed an empty database, and replace this process with Uvicorn."""
    wait_for_database()
    subprocess.run(
        ["alembic", "upgrade", "head"],
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "app.seed", "--if-empty"],
        check=True,
    )
    os.execvp(
        "uvicorn",
        [
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
    )


if __name__ == "__main__":
    main()
