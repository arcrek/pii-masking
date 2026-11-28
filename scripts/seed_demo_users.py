#!/usr/bin/env python3
"""CLI seeder script to populate demo accounts with securely hashed passwords (BE-01).

Passwords are read from environment variables or randomly generated at runtime.
No plaintext credentials are hardcoded or committed to version control.
Plaintext passwords are never echoed to stdout (preventing CI/Docker log leaks).

Usage:
  python3 scripts/seed_demo_users.py [--json] [--show-generated]
"""

from __future__ import annotations

import os
import sys
import json
import secrets
from pathlib import Path

# Add repo root to sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from app.security.auth import hash_password

DEFAULT_USER_SPECS = [
    {
        "id": "u-admin-001",
        "username": "admin",
        "env_var": "DEMO_ADMIN_PASSWORD",
        "role": "admin",
    },
    {
        "id": "u-reviewer-001",
        "username": "reviewer",
        "env_var": "DEMO_REVIEWER_PASSWORD",
        "role": "reviewer",
    },
    {
        "id": "u-demo-001",
        "username": "demo_user",
        "env_var": "DEMO_USER_PASSWORD",
        "role": "viewer",
    },
]


def generate_seed_data() -> tuple[list[dict], dict[str, str], dict[str, bool]]:
    """Generate user seed objects with hashed passwords.

    Returns:
        (records, plain_passwords, is_generated_flags)
    """
    seeded_records = []
    plain_passwords = {}
    is_generated = {}

    for spec in DEFAULT_USER_SPECS:
        env_val = os.environ.get(spec["env_var"])
        if env_val:
            plain = env_val
            was_gen = False
        else:
            plain = secrets.token_urlsafe(16)
            was_gen = True

        pw_hash = hash_password(plain)
        seeded_records.append({
            "id": spec["id"],
            "username": spec["username"],
            "password_hash": pw_hash,
            "role": spec["role"],
            "is_active": True,
        })
        plain_passwords[spec["username"]] = plain
        is_generated[spec["username"]] = was_gen

    return seeded_records, plain_passwords, is_generated


def main() -> None:
    seed_records, plain_passwords, is_generated = generate_seed_data()

    if "--json" in sys.argv:
        # Structured JSON containing only safe hash records
        print(json.dumps(seed_records, indent=2))
    else:
        # Safe stdout output: never print plain passwords to stdout
        print("Generated demo users with secure password hashes:")
        for r in seed_records:
            u = r["username"]
            src = "env" if not is_generated[u] else "generated"
            print(f" - [{r['role'].upper()}] {u} (ID: {r['id']}, source: {src})")
            print(f"   Hash: {r['password_hash'][:24]}...")

    # Display generated passwords only on explicit request to stderr (never stdout)
    if "--show-generated" in sys.argv:
        generated_users = [u for u, was_gen in is_generated.items() if was_gen]
        if generated_users:
            sys.stderr.write("\nGenerated random credentials (keep safe!):\n")
            for u in generated_users:
                sys.stderr.write(f" - {u}: {plain_passwords[u]}\n")


if __name__ == "__main__":
    main()
