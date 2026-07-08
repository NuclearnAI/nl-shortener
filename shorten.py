#!/usr/bin/env python3
"""shorten.py — Nuclearn-owned URL shortener.

Two modes:
  github-pages   — write a redirect HTML file to a public Pages repo, commit + push (default)
  offline        — generate code + preview redirect HTML, no push (dry-run)

Third-party shorteners (da.gd, tinyurl, bit.ly, etc.) are NOT supported by design.
URL contents (calendar templates, SharePoint links, deal IDs, session tokens) must
not be leaked to outside services. See SKILL.md for the threat-model rationale.

The core "trick" of URL shortening is a compact identifier (base62, 5-7 chars)
mapped to a redirect. This tool writes a static HTML file per code that browsers
land on and follow via <meta refresh> + JS location.href.

Usage:
  shorten.py [--mode {github-pages,offline}] [--repo PATH]
             --pages-host HOST [--code CODE] [--code-length N] [--salt STR] URL

Exit codes:
  0  success (short URL printed to stdout)
  1  usage error
  3  git failure (Mode github-pages)
"""
import argparse
import hashlib
import html
import os
import random
import string
import subprocess
import sys
import urllib.parse

from typing import Optional


BASE62 = string.ascii_letters + string.digits  # [A-Za-z0-9]


def generate_code(url: str, length: int = 6, salt: Optional[str] = None) -> str:
    """Generate a base62 short code from the URL.

    Deterministic when salt is None (same URL → same code). Random suffix when
    salt is passed (avoids collisions on re-shortening the same URL).
    """
    material = url if salt is None else f"{url}#{salt}"
    digest = hashlib.sha256(material.encode()).digest()
    # Interpret first 8 bytes as an unsigned int, encode in base62
    n = int.from_bytes(digest[:8], "big")
    out = []
    while n > 0 and len(out) < length:
        n, r = divmod(n, 62)
        out.append(BASE62[r])
    # Pad if the URL hashed to a very small integer (unlikely but possible)
    while len(out) < length:
        out.append(random.choice(BASE62))
    return "".join(out[:length])


def redirect_html(target_url: str) -> str:
    """Static HTML that redirects to target_url via three layered mechanisms.

    1. HTTP-equiv meta refresh (works even with JS disabled)
    2. JavaScript location.replace (fastest when JS runs)
    3. Anchor tag fallback (visible link if both above fail)
    """
    safe = html.escape(target_url, quote=True)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Redirecting…</title>
<meta http-equiv="refresh" content="0; url={safe}">
<meta name="robots" content="noindex">
<link rel="canonical" href="{safe}">
<script>window.location.replace({target_url!r});</script>
</head>
<body>
<p>Redirecting to <a href="{safe}">{safe}</a>.</p>
</body>
</html>
"""


# --------------------------------------------------------------------------
# Mode A — GitHub Pages self-hosted redirect
# --------------------------------------------------------------------------

def shorten_github_pages(url: str, repo: str, pages_host: str, code: str) -> str:
    """Write a redirect HTML file to a Pages repo, commit + push."""
    if not os.path.isdir(repo):
        print(f"Repo path does not exist: {repo}", file=sys.stderr)
        sys.exit(3)
    if not os.path.isdir(os.path.join(repo, ".git")):
        print(f"Not a git repo: {repo}", file=sys.stderr)
        sys.exit(3)

    file_path = os.path.join(repo, f"{code}.html")
    if os.path.exists(file_path):
        print(f"Collision — {code}.html already exists in {repo}", file=sys.stderr)
        print("Retry with --salt <anything> for a different code", file=sys.stderr)
        sys.exit(3)

    with open(file_path, "w", encoding="utf-8") as fh:
        fh.write(redirect_html(url))

    def run(*cmd):
        r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"git {' '.join(cmd[1:])} failed: {r.stderr}", file=sys.stderr)
            sys.exit(3)
        return r.stdout

    run("git", "add", f"{code}.html")
    run("git", "commit", "-m", f"Add redirect {code} -> {url[:80]}")
    run("git", "push")

    return f"https://{pages_host}/{code}"


# --------------------------------------------------------------------------
# Mode B — Offline (generate + preview only)
# --------------------------------------------------------------------------

def shorten_offline(url: str, pages_host: str, code: str) -> str:
    """Print the redirect HTML that WOULD be written, return the URL that WOULD result."""
    print("--- redirect HTML that would be written ---", file=sys.stderr)
    print(redirect_html(url), file=sys.stderr)
    print("--- end HTML ---", file=sys.stderr)
    return f"https://{pages_host}/{code}"


# --------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(
        description="Nuclearn-owned URL shortener (self-hosted only, no third-party services)",
    )
    p.add_argument("url", help="Long URL to shorten")
    p.add_argument("--mode", choices=("github-pages", "offline"),
                   default="github-pages", help="Shortening backend (default: github-pages)")
    p.add_argument("--repo", help="Path to the public Pages repo (github-pages mode)")
    p.add_argument("--pages-host", required=True,
                   help="Pages hostname, e.g. go.nuclearn.ai")
    p.add_argument("--code", help="Override the generated short code")
    p.add_argument("--code-length", type=int, default=6,
                   help="Base62 code length (default: 6, ~56B unique codes)")
    p.add_argument("--salt", help="Add a salt so the same URL generates a different code")
    args = p.parse_args()

    code = args.code or generate_code(args.url, length=args.code_length, salt=args.salt)

    if args.mode == "github-pages":
        if not args.repo:
            print("--repo is required for github-pages mode", file=sys.stderr)
            sys.exit(1)
        print(shorten_github_pages(args.url, args.repo, args.pages_host, code))
    else:  # offline
        print(shorten_offline(args.url, args.pages_host, code))


if __name__ == "__main__":
    main()
