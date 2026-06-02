#!/usr/bin/env python3
"""
Internal link checker for a built MkDocs site.

Usage:
  python scripts/check_internal_links.py site

Checks local HTML links in the generated site directory. External links,
mailto:, tel:, JavaScript links, and pure fragments are ignored to avoid
blocking deploys on third-party rate limits or anti-bot behavior.
"""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {k: v for k, v in attrs}
        for attr in ("id", "name"):
            value = attrs_dict.get(attr)
            if value:
                self.ids.add(value)
        if tag in {"a", "link", "script", "img", "source"}:
            for attr in ("href", "src"):
                value = attrs_dict.get(attr)
                if value:
                    self.links.append((attr, value))


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def html_target(site_dir: Path, current_file: Path, url: str) -> tuple[Path, str]:
    parsed = urlparse(url)
    path = unquote(parsed.path)
    fragment = unquote(parsed.fragment or "")

    if path.startswith("/"):
        target = site_dir / path.lstrip("/")
    else:
        target = (current_file.parent / path).resolve()

    if path.endswith("/") or not target.suffix:
        target = target / "index.html"
    elif target.is_dir():
        target = target / "index.html"

    return target, fragment


def should_skip(url: str) -> bool:
    stripped = url.strip()
    if not stripped or stripped.startswith("#"):
        return True
    parsed = urlparse(stripped)
    return parsed.scheme in {"http", "https", "mailto", "tel", "javascript", "data"}


def main() -> int:
    site_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "site").resolve()
    if not site_dir.exists():
        print(f"ERROR: site directory not found: {site_dir}", file=sys.stderr)
        return 2

    html_files = sorted(site_dir.rglob("*.html"))
    ids_by_file: dict[Path, set[str]] = {}
    links_by_file: dict[Path, list[str]] = {}

    for html_file in html_files:
        parser = LinkParser()
        parser.feed(html_file.read_text(encoding="utf-8", errors="ignore"))
        ids_by_file[html_file.resolve()] = parser.ids
        links_by_file[html_file.resolve()] = [url for _, url in parser.links]

    failures: list[str] = []

    for html_file, links in links_by_file.items():
        for url in links:
            if should_skip(url):
                continue

            target, fragment = html_target(site_dir, html_file, url)

            if not target.exists():
                target_display = target.relative_to(site_dir) if is_relative_to(target, site_dir) else target
                failures.append(f"{html_file.relative_to(site_dir)} -> missing {url} ({target_display})")
                continue

            if fragment and fragment not in ids_by_file.get(target.resolve(), set()):
                failures.append(f"{html_file.relative_to(site_dir)} -> missing anchor {url}")

    if failures:
        print("Internal link check failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(f"Internal link check passed for {len(html_files)} HTML files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
