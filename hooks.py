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

Both exports are cleaned before they are written: presentation-only
attribute lists are removed and raw HTML layout blocks are converted
back to Markdown, so agents receive prose and not markup. Relative links are
resolved to absolute URLs so they work from any location the export is
read in.

docs/llms.txt (the curated index) is a plain static file that MkDocs
copies through on its own; no hook is needed for it.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from pathlib import PurePosixPath
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from markdownify import markdownify

# Published pages in reading order. Any other .md file added to docs/
# later is appended alphabetically; files in EXCLUDE are never exported.
PAGE_ORDER = [
    "index.md",
    "portfolio.md",
    "resume.md",
    "case-studies/gcp-iot-core-migration.md",
    "writing-samples/novadeploy-gitops-admin-guide-portfolio-cut.md",
    "writing-samples/novadeploy-gitops-admin-guide-full-version.md",
]
EXCLUDE = set()

# Trailing { .class } / { #id } attribute lists: styling only, no meaning.
ATTR_LIST = re.compile(r"[ \t]*\{[ \t]*[.#][^}\n]*\}[ \t]*$", re.MULTILINE)
# Top-level raw HTML layout blocks in the Markdown source.
HTML_BLOCK = re.compile(
    r"^<(div|figure|section)\b.*?^</\1>\s*$", re.MULTILINE | re.DOTALL
)
# Markdown links and images with a relative destination.
RELATIVE_LINK = re.compile(r"(!?\[[^\]]*\]\()(?!\w+:|#|/)([^)\s]+)(\))")


def _unwrap_cards(html: str) -> str:
    """Move a card's link onto its heading.

    Card markup wraps a whole block in one <a>, which would otherwise
    convert into a single multi-line link. This produces a normal
    heading link followed by plain description text instead.
    """
    soup = BeautifulSoup(html, "html.parser")
    for anchor in soup.find_all("a", href=True):
        heading = anchor.find(["h2", "h3", "h4"])
        if heading is None:
            continue
        link = soup.new_tag("a", href=anchor["href"])
        link.string = heading.get_text(strip=True)
        heading.clear()
        heading.append(link)
        for span in anchor.find_all("span", class_="card-link"):
            span.decompose()
        anchor.unwrap()
    return str(soup)


def _html_to_markdown(match: re.Match) -> str:
    converted = markdownify(
        _unwrap_cards(match.group(0)), heading_style="ATX", strip=["img"]
    )
    return re.sub(r"\n{3,}", "\n\n", converted).strip() + "\n"


def _clean(text: str) -> str:
    """Strip presentation markup so the export is prose, not layout."""
    text = ATTR_LIST.sub("", text)
    text = HTML_BLOCK.sub(_html_to_markdown, text)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def _absolutize(text: str, site_url: str, rel_path: str) -> str:
    """Resolve relative links the way MkDocs does.

    Relative targets are resolved against the source file's folder, not
    the published page URL, and a .md target becomes its clean page URL.
    """
    parent = str(PurePosixPath(rel_path).parent)
    base = site_url + ("" if parent == "." else parent + "/")

    def fix(match: re.Match) -> str:
        target, _, fragment = match.group(2).partition("#")
        url = urljoin(base, target)
        if url.endswith(".md"):
            url = url[: -len(".md")] + "/"
        if fragment:
            url += "#" + fragment
        return match.group(1) + url + match.group(3)

    return RELATIVE_LINK.sub(fix, text)


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
        body = _clean(body)
        url = _page_url(site_url, rel)

        header = ["=" * 72, "Page: " + url]
        if description:
            header.append("Description: " + description)
        header.append("=" * 72)
        body = _absolutize(body, site_url, rel)
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
