"""MkDocs build hooks for pre-rendered diagrams and AI-retrieval artifacts.

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
4. Substitutes the checked-in NovaDeploy SVG when rendering its two
   sample pages, avoiding browser-side Mermaid rendering. The original
   Markdown and its Mermaid source remain intact in the AI exports.
5. Gives the theme's site-search dialog an accessible name on every
   page, including the 404 page. The theme marks it role="dialog" but
   ships it without a name, which fails screen readers and automated
   accessibility audits.
6. Removes the theme's GitHub statistics lookup from the repository
   link on every page, including the 404 page. The site does not show
   star, fork, or release numbers, so the lookup was an unused request
   to the GitHub API. The "GitHub" link itself is unchanged.
7. Adds accessible mobile controls and search status messages, gives the
   404 page a descriptive title, and publishes a small cached helper for
   keyboard operation, focus handling, and disabling character shortcuts.

Both exports are cleaned before they are written: presentation-only
attribute lists are removed and raw HTML layout blocks are converted
back to Markdown, so agents receive prose and not markup. Relative links are
resolved to absolute URLs so they work from any location the export is
read in.

docs/llms.txt (the curated index) is a plain static file that MkDocs
copies through on its own; no hook is needed for it.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from html import escape
from pathlib import Path
from pathlib import PurePosixPath
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from markdownify import markdownify
from mkdocs.exceptions import PluginError
from mkdocs.utils import get_relative_url

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

NOVADEPLOY_PAGES = {
    "writing-samples/novadeploy-gitops-admin-guide-portfolio-cut.md",
    "writing-samples/novadeploy-gitops-admin-guide-full-version.md",
}
MERMAID_FENCE = re.compile(
    r"^```mermaid[ \t]*\n(.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL
)
DIAGRAM_PATH = Path("assets/diagrams/novadeploy-architecture.svg")

# Trailing { .class } / { #id } attribute lists: styling only, no meaning.
ATTR_LIST = re.compile(r"[ \t]*\{[ \t]*[.#][^}\n]*\}[ \t]*$", re.MULTILINE)
# Top-level raw HTML layout blocks in the Markdown source.
HTML_BLOCK = re.compile(
    r"^<(div|figure|section)\b.*?^</\1>\s*$", re.MULTILINE | re.DOTALL
)
# Markdown links and images with a relative destination.
RELATIVE_LINK = re.compile(r"(!?\[[^\]]*\]\()(?!\w+:|#|/)([^)\s]+)(\))")


def on_page_markdown(markdown, page, config, files):
    """Use the saved diagram only when it matches this page's source."""
    if page.file.src_uri not in NOVADEPLOY_PAGES:
        return markdown

    regenerate = (
        "Keep the Mermaid blocks in both NovaDeploy samples identical, "
        "then run `python scripts/render_diagram.py`."
    )
    fences = list(MERMAID_FENCE.finditer(markdown))
    if len(fences) != 1:
        raise PluginError(
            f"{page.file.src_uri}: expected one NovaDeploy Mermaid diagram. "
            + regenerate
        )

    source = fences[0].group(1).strip() + "\n"
    svg_path = Path(config["docs_dir"]) / DIAGRAM_PATH
    try:
        svg_bytes = svg_path.read_bytes()
        svg = svg_bytes.decode("utf-8")
        metadata = json.loads(svg_path.with_suffix(".json").read_text("utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise PluginError(
            "Cannot read the pre-rendered NovaDeploy diagram or its metadata. "
            + regenerate
        ) from exc

    source_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
    svg_sha256 = hashlib.sha256(svg_bytes).hexdigest()
    if not isinstance(metadata, dict) or (
        metadata.get("source_sha256") != source_sha256
        or metadata.get("svg_sha256") != svg_sha256
    ):
        raise PluginError(
            f"{page.file.src_uri}: the pre-rendered NovaDeploy diagram is stale "
            "or has been modified. " + regenerate
        )

    replacement = '\n<div class="prerendered-diagram">\n' + svg.strip() + "\n</div>\n"
    fence = fences[0]
    return markdown[:fence.start()] + replacement + markdown[fence.end():]


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

    # Keep the helper in this hook so updating hooks.py is a complete change.
    # Its content hash prevents an older cached script accompanying new HTML.
    helper = site_dir / _ACCESSIBILITY_PATH
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text(_ACCESSIBILITY_SCRIPT, encoding="utf-8")

def on_page_content(html, page, config, files):
    """Fail the build if a page's Contents box is missing or its links drift.

    Only pages whose Markdown mentions page-contents are checked. The box
    must render as its own details block (not inside another block) and
    link to every level-2 heading below it, in order, by its real id.
    """
    if "page-contents" not in page.markdown:
        return html

    soup = BeautifulSoup(html, "html.parser")
    box = soup.find("details", class_="page-contents")
    if (
        box is None
        or box.find_parent("details") is not None
        or box.find_parent(class_="admonition") is not None
    ):
        raise PluginError(
            f"{page.file.src_uri}: the Contents box did not render as its own "
            "block. The ??? line must start at the left margin and every link "
            "line under it must be indented by exactly four spaces."
        )

    links = [a.get("href") for a in box.find_all("a")]
    headings = [
        "#" + h["id"] for h in box.find_all_next("h2") if h.has_attr("id")
    ]
    if links != headings:
        raise PluginError(
            f"{page.file.src_uri}: the Contents box links do not match the "
            f"page's section headings in order.\n  box:      {links}\n"
            f"  headings: {headings}"
        )
    return html


SEARCH_DIALOG = '<div class="md-search" data-md-component="search" role="dialog">'
SEARCH_DIALOG_NAMED = SEARCH_DIALOG[:-1] + ' aria-label="Search">'


def _name_search_dialog(html: str, source: str) -> str:
    """Add aria-label="Search" to the theme's search dialog.

    The build fails if the dialog markup is not found exactly once, so a
    theme upgrade that changes it is caught in CI instead of silently
    shipping an unnamed dialog again.
    """
    if html.count(SEARCH_DIALOG) != 1:
        raise PluginError(
            f"{source}: expected exactly one unnamed search dialog. The theme "
            "markup may have changed; update SEARCH_DIALOG in hooks.py."
        )
    return html.replace(SEARCH_DIALOG, SEARCH_DIALOG_NAMED)


SOURCE_COMPONENT = ' data-md-component="source"'


def _drop_repo_stats_lookup(html: str, source: str) -> str:
    """Remove the marker that makes the theme look up GitHub statistics.

    The theme's script requests stars, forks, and the latest release from
    the GitHub API for every link carrying this marker. This site does not
    display those numbers, and the repository publishes no releases, so the
    lookup was an unused request that logged a 404 in the browser console.
    Removing the marker leaves the "GitHub" link itself unchanged.

    The build fails if the marker is not found, so a theme upgrade that
    changes it is caught in CI instead of silently restoring the lookup.
    """
    if SOURCE_COMPONENT not in html:
        raise PluginError(
            f"{source}: expected the theme's repository link marker. The theme "
            "markup may have changed, or repo_url was removed from mkdocs.yml; "
            "update SOURCE_COMPONENT in hooks.py."
        )
    return html.replace(SOURCE_COMPONENT, "")


def _replace_once(html: str, old: str, new: str, source: str) -> str:
    """Catch theme changes rather than silently losing an accessibility fix."""
    if html.count(old) != 1:
        raise PluginError(
            f"{source}: expected exactly one {old!r}; update the accessibility "
            "markup guards in hooks.py for the current theme."
        )
    return html.replace(old, new, 1)


def _add_web_accessibility(html: str, source: str, helper_url: str) -> str:
    """Enhance the shared controls without reserializing page content or SVGs."""
    header_controls = 0
    search_back_controls = 0

    def label(match: re.Match) -> str:
        nonlocal header_controls, search_back_controls
        opening = match.group(0)
        attrs = BeautifulSoup(opening, "html.parser").label.attrs
        classes = attrs.get("class", [])
        target = attrs.get("for")
        name = ""
        close = False
        panel = ""
        if "md-header__button" in classes and target in {"__drawer", "__search"}:
            header_controls += 1
            name = "Navigation" if target == "__drawer" else "Search"
            panel = "site-navigation" if target == "__drawer" else "site-search"
        elif "md-search__icon" in classes and target == "__search":
            search_back_controls += 1
            name, panel, close = "Close search", "site-search", True
        elif target == "__toc" and 'id="__toc"' in html:
            # These labels are buttons only in the mobile navigation drawer.
            # The helper leaves the desktop table-of-contents title as text.
            closing = html.find("</label>", match.end())
            text = BeautifulSoup(html[match.end():closing], "html.parser").get_text(" ", strip=True)
            action = "back to navigation" if "md-nav__title" in classes else "table of contents"
            name = f"{text}: {action}"
        else:
            return opening

        if "role" in attrs or "tabindex" in attrs:
            raise PluginError(f"{source}: theme toggle already has semantics; review hooks.py.")
        extra = (
            f' data-a11y-toggle="{target}" data-a11y-name="{escape(name, quote=True)}"'
            f' role="button" aria-label="{escape(name, quote=True)}" tabindex="0"'
        )
        if panel:
            extra += f' aria-controls="{panel}"'
        if close:
            extra += ' data-a11y-close-search'
        else:
            extra += ' aria-expanded="false"'
        return opening[:-1] + extra + ">"

    html = re.sub(r"<label\b[^>]*>", label, html)
    if header_controls != 2 or search_back_controls != 1:
        raise PluginError(f"{source}: expected two header toggles and one search back control.")

    html = _replace_once(html, SEARCH_DIALOG_NAMED,
                         SEARCH_DIALOG_NAMED[:-1] + ' id="site-search">', source)
    pattern = r'<div\b(?=[^>]*class="md-sidebar md-sidebar--primary")[^>]*>'
    matches = list(re.finditer(pattern, html))
    if len(matches) != 1:
        raise PluginError(f"{source}: expected one primary navigation sidebar.")
    original = matches[0].group(0)
    html = _replace_once(html, original, original[:-1] + ' id="site-navigation">', source)
    html = _replace_once(
        html, '<div class="md-search-result__meta">',
        '<div class="md-search-result__meta" role="status" aria-live="polite" aria-atomic="true">', source)
    html = _replace_once(html, '<div class="md-search__output">',
                         '<div class="md-search__output" inert>', source)
    html = _replace_once(
        html, '<div class="md-search__scrollwrap" tabindex="0" data-md-scrollfix>',
        '<div class="md-search__scrollwrap" tabindex="-1" data-md-scrollfix>', source)
    return _replace_once(html, "</body>",
                         f'<script src="{escape(helper_url, quote=True)}" defer></script>\n</body>', source)


def _adjust_theme_markup(html: str, source: str, helper_url: str) -> str:
    """Apply the shared theme adjustments to one rendered page."""
    html = _drop_repo_stats_lookup(_name_search_dialog(html, source), source)
    return _add_web_accessibility(html, source, helper_url)


def on_post_page(output, page, config):
    """Adjust the theme markup on every rendered page."""
    return _adjust_theme_markup(output, page.file.src_uri,
                                get_relative_url(str(_ACCESSIBILITY_PATH), page.url))


def on_post_template(output_content, template_name, config):
    """Adjust the theme markup on the 404 page, which is not a page object."""
    if template_name != "404.html":
        return output_content
    # GitHub Pages serves this document at the missing URL, including nested
    # paths. Resolve its helper against the configured site, not that URL.
    helper_url = urljoin(config["site_url"] or "/", str(_ACCESSIBILITY_PATH))
    output_content = _adjust_theme_markup(output_content, template_name, helper_url)
    titles = list(re.finditer(r"<title>.*?</title>", output_content, re.DOTALL))
    if len(titles) != 1:
        raise PluginError("404.html: expected exactly one document title.")
    title = "Page not found - " + escape(config["site_name"])
    return output_content.replace(titles[0].group(0), f"<title>{title}</title>", 1)


# Runtime adapter for the existing theme; published as a cached asset at build time.
_ACCESSIBILITY_SCRIPT = r"""
/* Small accessibility adapter for Material's existing checkbox controls.
 * Keep the theme's search worker, arrow navigation and ordinary Tab exit. */
(() => {
  "use strict";
  const search = document.getElementById("__search");
  const drawer = document.getElementById("__drawer");
  const panel = document.getElementById("site-search");
  const sidebar = document.getElementById("site-navigation");
  const query = document.querySelector('[data-md-component="search-query"]');
  const output = document.querySelector(".md-search__output");
  const scroll = document.querySelector(".md-search__scrollwrap");
  if (!search || !drawer || !panel || !sidebar || !query || !output || !scroll) return;

  const controls = [...document.querySelectorAll("[data-a11y-toggle]")];
  const searchButton = document.querySelector('.md-header__button[data-a11y-toggle="__search"]');
  const menuButton = document.querySelector('.md-header__button[data-a11y-toggle="__drawer"]');
  const desktopSearch = window.matchMedia("(min-width: 60em)");
  const desktopNavigation = window.matchMedia("(min-width: 76.25em)");
  const characterShortcuts = new Set(["f", "s", "/", "p", ",", "n", "."]);
  const focusable = 'a[href],button,input,select,textarea,[tabindex="0"]';
  const toc = document.getElementById("__toc");
  const tocPanel = sidebar.querySelector(".md-nav--primary .md-nav--secondary");
  const tocTrigger = sidebar.querySelector('.md-nav__link[data-a11y-toggle="__toc"]');
  const tocBack = tocPanel?.querySelector('[data-a11y-toggle="__toc"]');
  const tocBackground = tocPanel ? [...sidebar.querySelectorAll(focusable)]
    .filter(element => element !== toc && !tocPanel.contains(element))
    .map(element => [element, Boolean(element.inert)]) : [];
  let searchOpener = null;

  function visible(element) {
    if (!(element instanceof HTMLElement) || !element.isConnected || element.closest("[inert]")) return false;
    const style = getComputedStyle(element);
    return style.visibility !== "hidden" && style.display !== "none" &&
      element.getClientRects().length > 0;
  }

  function sync() {
    output.inert = !search.checked;
    scroll.tabIndex = search.checked ? 0 : -1;
    panel.inert = !desktopSearch.matches && !search.checked;
    sidebar.inert = !desktopNavigation.matches && !drawer.checked;
    // Below 60em the nested TOC covers its parent menu with a sliding panel.
    // Its hidden panel and covered parent controls must not receive focus.
    const mobileToc = !desktopSearch.matches && Boolean(toc && tocPanel);
    if (tocPanel) tocPanel.inert = mobileToc && !toc.checked;
    for (const [element, originallyInert] of tocBackground) {
      element.inert = originallyInert || (mobileToc && toc.checked);
    }
    for (const control of controls) {
      const id = control.dataset.a11yToggle;
      const toggle = document.getElementById(id);
      const back = control.hasAttribute("data-a11y-close-search");
      const enabled = back ? !desktopSearch.matches :
        id !== "__toc" || (mobileToc && sidebar.contains(control));
      if (enabled) {
        control.setAttribute("role", "button");
        control.setAttribute("aria-label", control.dataset.a11yName || control.textContent.trim());
        control.setAttribute("aria-expanded", String(Boolean(toggle && toggle.checked)));
        const hiddenTocControl = id === "__toc" &&
          (tocPanel.contains(control) ? !toc.checked : toc.checked);
        control.tabIndex = (back && !search.checked) || hiddenTocControl ? -1 : 0;
      } else {
        control.removeAttribute("role");
        control.removeAttribute("aria-label");
        control.removeAttribute("aria-expanded");
        control.tabIndex = -1;
      }
      // On desktop the same search icon is decorative, not a back button.
      if (back) control.setAttribute("aria-hidden", String(!enabled));
    }
  }

  function close(toggle) {
    if (toggle.checked) toggle.click();
  }

  function returnFromSearch() {
    const candidates = [searchOpener, searchButton, menuButton,
      ...document.querySelectorAll(".md-header__inner a[href]")];
    const target = candidates.find(element => visible(element) && !panel.contains(element));
    if (target) target.focus({ preventScroll: true });
  }

  search.addEventListener("change", () => {
    sync();
    // The mobile input was inert when the theme's label listener first ran.
    if (search.checked && document.activeElement !== query) query.focus();
  });
  drawer.addEventListener("change", () => {
    sync();
    if (drawer.checked && !desktopNavigation.matches) {
      const first = [...sidebar.querySelectorAll(focusable)].find(visible);
      if (first) first.focus({ preventScroll: true });
    }
  });
  toc?.addEventListener("change", () => {
    sync();
    if (!desktopSearch.matches && drawer.checked) {
      const target = toc.checked ? tocBack || tocPanel?.querySelector("a[href]") : tocTrigger;
      if (visible(target)) target.focus({ preventScroll: true });
    }
  });

  document.addEventListener("click", event => {
    const control = event.target instanceof Element ? event.target.closest("[data-a11y-toggle]") : null;
    if (control === searchButton) searchOpener = control;
    if (control?.hasAttribute("data-a11y-close-search")) {
      queueMicrotask(() => { if (!search.checked) returnFromSearch(); });
    }
  }, true);

  document.addEventListener("focusin", event => {
    if (event.target === query && event.relatedTarget instanceof HTMLElement &&
        !panel.contains(event.relatedTarget) && event.relatedTarget.matches(focusable)) {
      searchOpener = event.relatedTarget;
    }
    // The drawer is a disclosure: leaving it closes it without trapping focus.
    if (drawer.checked && !desktopNavigation.matches && !sidebar.contains(event.target) &&
        !menuButton?.contains(event.target)) close(drawer);
  });

  document.addEventListener("keydown", event => {
    if (event.isComposing || event.ctrlKey || event.metaKey || event.altKey) return;
    const target = event.target instanceof Element ? event.target : null;
    const control = target?.closest('[data-a11y-toggle][role="button"]');
    if (control && (event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      event.stopPropagation(); // Avoid the theme's second label activation.
      control.click();
      return;
    }
    if (event.key === "Escape" && (search.checked || drawer.checked)) {
      event.preventDefault();
      event.stopPropagation();
      if (search.checked) {
        close(search);
        returnFromSearch();
      } else {
        close(drawer);
        if (visible(menuButton)) menuButton.focus({ preventScroll: true });
      }
      return;
    }
    // Let native buttons (including Clear) activate with Space before search
    // can redirect that key to its text field. Do not cancel native behavior.
    if (search.checked && event.key === " " && target?.closest("button")) {
      event.stopPropagation();
    }
    const editable = target && (target.closest("input,textarea,select") || target.isContentEditable);
    if (!search.checked && !editable && characterShortcuts.has(event.key)) event.stopPropagation();
  }, true);

  desktopSearch.addEventListener("change", sync);
  desktopNavigation.addEventListener("change", sync);
  sync();
})();
"""
_ACCESSIBILITY_PATH = Path("assets") / (
    "site-accessibility." + hashlib.sha256(_ACCESSIBILITY_SCRIPT.encode("utf-8")).hexdigest()[:12] + ".js"
)
