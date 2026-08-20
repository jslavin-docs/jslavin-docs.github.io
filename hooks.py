"""MkDocs build hooks for AI-retrieval artifacts.

Runs automatically during `mkdocs build` (including --strict CI builds):

1. Copies skill.md from the repository root into the built site so it is
   served as a raw Markdown file at /skill.md instead of being rendered
   as an HTML page.
2. Generates llms-full.txt in the built site by concatenating the
   Markdown source of every published page, so the full-content export
   is rebuilt on every deploy and cannot drift from the site.
3. Publishes a clean Markdown copy of every page at its own URL plus
   index.md (e.g. /portfolio/index.md), per the llms.txt v2 spec, so
   llms.txt links can point agents at LLM-friendly page versions.

docs/llms.txt (the curated index) is a plain static file that MkDocs
copies through on its own; no hook is needed for it.
"""

from __future__ import annotations

import shutil
from pathlib import Path

# Published pages in reading order. Any other .md file added to docs/
# later is appended alphabetically; files in EXCLUDE are never exported.
PAGE_ORDER = [
    "index.md",
    "portfolio.md",
    "resume.md",
    "writing-samples/novadeploy-gitops-admin-guide-portfolio-cut.md",
    "writing-samples/novadeploy-gitops-admin-guide-full-version.md",
]
EXCLUDE = {"404.md"}


def _page_url(site_url: str, rel_path: str) -> str:
    if rel_path == "index.md":
        return site_url
    return site_url + rel_path[: -len(".md")] + "/"


def _split_front_matter(text: str) -> tuple[str, str]:
    """Return (description, body) with any YAML front matter removed."""
    description = ""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            for line in text[4:end].splitlines():
                if line.startswith("description:"):
                    description = line.split(":", 1)[1].strip().strip('"')
            text = text[end + len("\n---\n"):]
    return description, text.lstrip("\n")


def on_post_build(config) -> None:
    repo_root = Path(config["config_file_path"]).parent
    docs_dir = Path(config["docs_dir"])
    site_dir = Path(config["site_dir"])
    site_url = config["site_url"] or "/"

    # 1. Serve skill.md as a raw file at the site root.
    skill = repo_root / "skill.md"
    if skill.is_file():
        shutil.copyfile(skill, site_dir / "skill.md")

    # 2. Generate llms-full.txt and per-page Markdown exports.
    ordered = [p for p in PAGE_ORDER if (docs_dir / p).is_file()]
    known = set(ordered) | EXCLUDE
    extras = sorted(
        str(p.relative_to(docs_dir)).replace("\\", "/")
        for p in docs_dir.rglob("*.md")
        if str(p.relative_to(docs_dir)).replace("\\", "/") not in known
    )

    sections = [
        "# Jeff Slavin | Lead Technical Writer - full site content\n\n"
        "Generated at build time from the Markdown sources of "
        + site_url
        + " - see llms.txt for the curated index.\n"
        "(c) Jeff Slavin. Portfolio content is all rights reserved.\n"
    ]
    for rel in ordered + extras:
        description, body = _split_front_matter(
            (docs_dir / rel).read_text(encoding="utf-8")
        )
        header = ["=" * 72, "Page: " + _page_url(site_url, rel)]
        if description:
            header.append("Description: " + description)
        header.append("=" * 72)
        sections.append("\n".join(header) + "\n\n" + body.rstrip() + "\n")
        if rel == "index.md":
            md_out = site_dir / "index.md"
        else:
            md_out = site_dir / rel[: -len(".md")] / "index.md"
        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text(body, encoding="utf-8")

    (site_dir / "llms-full.txt").write_text(
        "\n".join(sections), encoding="utf-8"
    )
