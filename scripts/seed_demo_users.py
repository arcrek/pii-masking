#!/usr/bin/env python3
"""CLI seeder script to populate demo accounts with securely hashed passwords (BE-01).

Passwords are read from environment variables or randomly generated at runtime.
No plaintext credentials are hardcoded or committed to version control.

Usage:
  python3 scripts/seed_demo_users.py [--json]
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


def generate_seed_data() -> tuple[list[dict], dict[str, str]]:
    """Generate user seed objects with hashed passwords, returning (records, plain_passwords)."""
    seeded_records = []
    plain_passwords = {}

    for spec in DEFAULT_USER_SPECS:
        # Check env or generate random secure password
        plain = os.environ.get(spec["env_var"])
        if not plain:
            plain = secrets.token_urlsafe(16)

        pw_hash = hash_password(plain)
        seeded_records.append({
            "id": spec["id"],
            "username": spec["username"],
            "password_hash": pw_hash,
            "role": spec["role"],
            "is_active": True,
        })
        plain_passwords[spec["username"]] = plain

    return seeded_records, plain_passwords


def main() -> None:
    seed_records, plain_passwords = generate_seed_data()
    if "--json" in sys.argv:
        print(json.dumps(seed_records, indent=2))
    else:
        print("Generated demo users with secure password hashes:")
        for r in seed_records:
            u = r["username"]
            print(f" - [{r['role'].upper()}] {u} (ID: {r['id']})")
            print(f"   Password (keep safe!): {plain_passwords[u]}")
            print(f"   Hash: {r['password_hash'][:24]}...")


if __name__ == "__main__":
    main()
