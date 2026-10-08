"""Production entry point used by Amvera.

The platform executes this file with Python.  It prepares the persistent
SQLite database and static assets, then replaces itself with Gunicorn.
"""

import os
import subprocess
import sys


def run_managepy(*arguments: str) -> None:
    subprocess.check_call([sys.executable, "manage.py", *arguments])


def main() -> None:
    os.environ.setdefault("SQLITE_PATH", "/data/db.sqlite3")
    run_managepy("migrate", "--noinput")
    run_managepy("collectstatic", "--noinput")

    port = os.environ.get("PORT", "80")
    os.execvp(
        "gunicorn",
        [
            "gunicorn",
            "sensor_site.wsgi:application",
            "--bind",
            f"0.0.0.0:{port}",
            "--workers",
            "2",
        ],
    )


if __name__ == "__main__":
    main()
