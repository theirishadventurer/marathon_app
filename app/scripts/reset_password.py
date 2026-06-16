"""One-off CLI to reset an athlete's login password.

The seed (``app.seed.load_plan``) only sets ``password_hash`` when *creating* a
new athlete — it never rotates an existing row. So changing ``SEED_PASSWORD``
on a deployment where the athlete already exists does NOT update the live
password. Use this script for that one-off rotation.

Usage (run in the api container so deps + DATABASE_URL match prod):

    docker compose exec -T api python -m app.scripts.reset_password \
        --email you@example.com --password 'new-strong-password'

    # or read the password from the SEED_PASSWORD env var instead of --password:
    docker compose exec -T api python -m app.scripts.reset_password \
        --email you@example.com --from-seed-env

Exits non-zero (and writes nothing) if the athlete is not found.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from sqlalchemy import select

from app.auth import hash_password
from app.db import async_session_factory
from app.models.athlete import Athlete

MIN_PASSWORD_LEN = 8


async def reset_password(email: str, new_password: str) -> None:
    async with async_session_factory() as db:
        athlete = (
            await db.execute(select(Athlete).where(Athlete.email == email))
        ).scalar_one_or_none()
        if athlete is None:
            print(f"ERROR: no athlete with email {email!r}", file=sys.stderr)
            raise SystemExit(1)

        athlete.password_hash = hash_password(new_password)
        await db.commit()
        print(f"OK: password reset for {email} (athlete {athlete.id})")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset an athlete's login password.")
    parser.add_argument("--email", required=True, help="Athlete email (login identifier).")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--password", help="New password (provide directly).")
    group.add_argument(
        "--from-seed-env",
        action="store_true",
        help="Read the new password from the SEED_PASSWORD env var.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.from_seed_env:
        new_password = os.environ.get("SEED_PASSWORD", "")
        if not new_password:
            print("ERROR: --from-seed-env set but SEED_PASSWORD is empty", file=sys.stderr)
            raise SystemExit(2)
    else:
        new_password = args.password

    if len(new_password) < MIN_PASSWORD_LEN:
        print(
            f"ERROR: password must be at least {MIN_PASSWORD_LEN} characters",
            file=sys.stderr,
        )
        raise SystemExit(2)

    asyncio.run(reset_password(args.email, new_password))


if __name__ == "__main__":
    main()
