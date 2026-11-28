#!/usr/bin/env python3
"""CLI seeder script to populate demo accounts with securely hashed passwords (BE-01).

Usage:
  python3 scripts/seed_demo_users.py [--json]
"""

import sys
import json
import uuid
from pathlib import Path

# Add repo root to sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from app.security.auth import hash_password

DEFAULT_DEMO_USERS = [
    {
        "id": "u-admin-001",
        "username": "admin",
        "default_pass": "AdminDemo2026@Secret",
        "role": "admin",
    },
    {
        "id": "u-reviewer-001",
        "username": "reviewer",
        "default_pass": "Reviewer2026@Secret",
        "role": "reviewer",
    },
    {
        "id": "u-demo-001",
        "username": "demo_user",
        "default_pass": "DemoUser2026@Secret",
        "role": "viewer",
    },
]


def generate_seed_data() -> list[dict]:
    """Generate user seed objects with bcrypt-hashed passwords."""
    seeded = []
    for u in DEFAULT_DEMO_USERS:
        pw_hash = hash_password(u["default_pass"])
        seeded.append({
            "id": u["id"],
            "username": u["username"],
            "password_hash": pw_hash,
            "role": u["role"],
            "is_active": True,
        })
    return seeded


def main() -> None:
    seed_records = generate_seed_data()
    if "--json" in sys.argv:
        print(json.dumps(seed_records, indent=2))
    else:
        print("Successfully generated seed data for demo users:")
        for r in seed_records:
            print(f" - [{r['role'].upper()}] {r['username']} (ID: {r['id']}) -> Hash: {r['password_hash'][:16]}...")


if __name__ == "__main__":
    main()
