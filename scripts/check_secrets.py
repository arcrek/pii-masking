#!/usr/bin/env python3
"""Secret scanning and hygiene validation script for PII Detection & Redaction MVP.

Prevents committing credentials, private keys, environment tokens, or sensitive data
to git repository or CI/CD logs, fulfilling OPS-01 requirements.
Supports whole-tree scanning, git staged scanning, and git pre-commit hook installation.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# Files that should NEVER be tracked by git
FORBIDDEN_FILE_PATTERNS = [
    re.compile(r"^\.env(\.[a-zA-Z0-9_\-]+)?$"),
    re.compile(r"^.*\.(pem|key|pkcs12|pfx|p12)$"),
    re.compile(r"^id_rsa.*$"),
    re.compile(r"^.*_rsa$"),
    re.compile(r"^credentials\.json$"),
    re.compile(r"^service-account.*\.json$"),
]

# Allowed files that may mention template variables, examples, or test fixtures
ALLOWED_TEMPLATE_FILES = {
    ".env.example",
    "scripts/check_secrets.py",
    "tests/test_ops01_environment.py",
    "config/system_config.py",
    "config/logger.py",
    ".gitignore",
    ".dockerignore",
}

# Regex patterns for detecting hardcoded secrets
SECRET_REGEXES = [
    # Private Key blocks
    ("Private Key Block", re.compile(r"-----BEGIN (?:[A-Z0-9_-]+ )?PRIVATE KEY-----")),
    # AWS Access Key ID
    ("AWS Access Key", re.compile(r"\b(AKIA[0-9A-Z]{16})\b")),
    # GitHub Personal Access Token
    ("GitHub Token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{36,})\b")),
    # Slack Token
    ("Slack Token", re.compile(r"\b(xox[baprs]-[0-9A-Za-z]{10,})\b")),
    # Generic API Key / Secret assignments with high entropy string
    (
        "Hardcoded Secret / Password",
        re.compile(
            r"""(?i)(?:api_key|apikey|secret_key|secret|password|passwd|auth_token)\s*[:=]\s*['"]([A-Za-z0-9_\-+/]{20,})['"]"""
        ),
    ),
]

# Patterns that indicate false positives in generic secret matches
FALSE_POSITIVE_INDICATORS = [
    "change-this",
    "placeholder",
    "your-secret",
    "dummy",
    "example",
    "test",
    "sample",
    "0000000000000000",
    "1234567890123456",
    "[REDACTED",
]


def is_false_positive(matched_str: str) -> bool:
    """Check if the matched secret text is an obvious placeholder or false positive."""
    lower = matched_str.lower()
    return any(indicator in lower for indicator in FALSE_POSITIVE_INDICATORS)


def scan_file(file_path: Path, repo_root: Path) -> List[Tuple[int, str, str]]:
    """Scan an individual file for forbidden secret patterns."""
    try:
        rel_path = file_path.relative_to(repo_root).as_posix()
    except ValueError:
        rel_path = file_path.as_posix()

    # Skip allowed template files
    if rel_path in ALLOWED_TEMPLATE_FILES or file_path.name in ALLOWED_TEMPLATE_FILES:
        return []

    # Skip git objects, binary files, checkpoints weights, and venv
    if any(part in file_path.parts for part in (".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache")):
        return []

    if not file_path.is_file():
        return []

    # Skip files over 2MB
    try:
        if file_path.stat().st_size > 2 * 1024 * 1024:
            return []
    except OSError:
        return []

    findings = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, start=1):
                for rule_name, pattern in SECRET_REGEXES:
                    match = pattern.search(line)
                    if match:
                        matched_text = match.group(0)
                        if not is_false_positive(matched_text):
                            findings.append((line_no, rule_name, matched_text[:20] + "..."))
    except Exception:
        pass

    return findings


def scan_directory(scan_path: Path) -> int:
    """Scan directory recursively in a single pass for secret violations and forbidden files."""
    repo_root = scan_path.resolve()
    violations: List[str] = []
    scanned_count = 0

    print(f"Scanning for credentials and secrets in: {repo_root}")

    for root, dirs, files in os.walk(repo_root):
        # Prune ignored directories in-place for performance
        dirs[:] = [d for d in dirs if d not in (".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache")]
        for file_name in files:
            file_path = Path(root) / file_name
            try:
                rel_path = file_path.relative_to(repo_root).as_posix()
            except ValueError:
                rel_path = file_path.as_posix()

            if rel_path in ALLOWED_TEMPLATE_FILES:
                continue

            # 1. Check for forbidden file names
            for pattern in FORBIDDEN_FILE_PATTERNS:
                if pattern.match(file_name):
                    violations.append(f"[FORBIDDEN FILE] {rel_path} matches restricted pattern '{pattern.pattern}'")

            # 2. Check file contents
            scanned_count += 1
            file_findings = scan_file(file_path, repo_root)
            for line_no, rule_name, snippet in file_findings:
                violations.append(f"[LEAK DETECTED] {rel_path}:{line_no} matches '{rule_name}' ({snippet})")

    print(f"Scanned {scanned_count} files.")

    if violations:
        print(f"\nFAILURE: Found {len(violations)} security violation(s):")
        for v in violations:
            print(f"  * {v}")
        return 1

    print("\nSUCCESS: No uncommitted secrets, credentials, or forbidden files found.")
    return 0


def scan_git_staged(repo_root: Path) -> int:
    """Scan only files staged in git index (fast pre-commit check)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        staged_files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception as e:
        print(f"Warning: git command failed: {e}. Falling back to full scan.")
        return scan_directory(repo_root)

    if not staged_files:
        print("No staged files to scan.")
        return 0

    print(f"Scanning {len(staged_files)} git staged file(s)...")
    violations: List[str] = []

    for rel_path in staged_files:
        file_path = repo_root / rel_path
        if rel_path in ALLOWED_TEMPLATE_FILES or not file_path.exists():
            continue

        for pattern in FORBIDDEN_FILE_PATTERNS:
            if pattern.match(file_path.name):
                violations.append(f"[FORBIDDEN STAGED FILE] {rel_path} matches restricted pattern '{pattern.pattern}'")

        file_findings = scan_file(file_path, repo_root)
        for line_no, rule_name, snippet in file_findings:
            violations.append(f"[STAGED LEAK DETECTED] {rel_path}:{line_no} matches '{rule_name}' ({snippet})")

    if violations:
        print(f"\nCOMMIT BLOCKED: Found {len(violations)} secret violation(s) in staged files:")
        for v in violations:
            print(f"  * {v}")
        return 1

    print("SUCCESS: All staged files are clean of secrets.")
    return 0


def install_pre_commit_hook(repo_root: Path) -> int:
    """Install git pre-commit hook that automatically runs check_secrets.py."""
    git_dir = repo_root / ".git"
    if not git_dir.is_dir():
        print(f"Error: .git directory not found at {repo_root}")
        return 1

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file = hooks_dir / "pre-commit"

    hook_content = (
        "#!/usr/bin/env bash\n"
        "# Auto-generated pre-commit hook by scripts/check_secrets.py\n"
        "python3 scripts/check_secrets.py --staged\n"
    )
    hook_file.write_text(hook_content, encoding="utf-8")
    hook_file.chmod(0o755)
    print(f"Pre-commit secret scanning hook installed successfully at: {hook_file}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Check repository for hardcoded secrets and forbidden files.")
    parser.add_argument("--path", type=str, default=".", help="Root directory path to scan (default: current directory)")
    parser.add_argument("--staged", action="store_true", help="Scan only git staged files")
    parser.add_argument("--install-hook", action="store_true", help="Install git pre-commit hook")
    args = parser.parse_args()

    repo_path = Path(args.path).resolve()

    if args.install_hook:
        sys.exit(install_pre_commit_hook(repo_path))

    if args.staged:
        sys.exit(scan_git_staged(repo_path))

    sys.exit(scan_directory(repo_path))


if __name__ == "__main__":
    main()
