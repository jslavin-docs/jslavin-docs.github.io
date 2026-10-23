# Jeff Slavin | Technical Writing Portfolio

[![Deploy to GitHub Pages](https://github.com/jslavin-docs/jslavin-docs.github.io/actions/workflows/pages.yml/badge.svg)](https://github.com/jslavin-docs/jslavin-docs.github.io/actions/workflows/pages.yml)

**Lead Technical Writer**  
API · Cloud · Edge · IoT · GitOps · DevSecOps · Docs as Code

This repository is the source for my technical writing portfolio, built with MkDocs Material and published to GitHub Pages with the Docs as Code workflow I use professionally: Markdown, YAML, Git, and GitHub Actions.

- **Live portfolio:** https://jslavin-docs.github.io/
- **Resume:** https://jslavin-docs.github.io/resume/
- **LinkedIn:** https://www.linkedin.com/in/jeff-slavin/
- **Email:** jslavin.docs@gmail.com  

## Focus areas

API documentation · OpenAPI · SDK documentation · Information architecture · Docs as Code · AI-ready documentation (llms.txt, skill.md) · Cloud and edge computing · IoT · Kubernetes · GitOps · Argo CD · DevSecOps · Prometheus

## What this repo demonstrates

- **MkDocs Material** — custom theme configuration, navigation tabs, admonitions, code copy, and permalink anchors.
- **Custom CSS** — hero layout, metric cards, portfolio grid, and skill cards.
- **CI/CD and documentation QA** — on every push to `main` and every pull request, GitHub Actions runs `mkdocs build --strict`, an internal link check, and the pinned Nu HTML Checker. Any failure blocks the deploy. A Lighthouse audit also runs but never blocks. Pull requests aren't deployed.
- **AI-retrieval artifacts** — files that let AI tools read the site. `llms.txt` is a hand-written index. On every build, `hooks.py` adds `llms-full.txt` (all page text in one file) and a Markdown copy of every page, and copies `skill.md`, the agent skill file, unchanged.
- **Accessibility** — on every build, `hooks.py` also improves screen-reader labels and keyboard access, and fixes theme HTML errors.

## Repository structure

```text
jslavin-docs.github.io/
├── .github/workflows/pages.yml   # Build, checks, advisory audit, and deploy workflow
├── .github/dependabot.yml        # Monthly grouped dependency updates
├── docs/                         # Markdown source files and assets
│   ├── index.md                  # Portfolio homepage
│   ├── portfolio.md              # Writing samples overview
│   ├── resume.md                 # Resume page
│   ├── writing-samples/          # Markdown portfolio samples
│   ├── case-studies/             # Case study pages
│   ├── assets/                   # Custom CSS, images, and resume PDF
│   ├── llms.txt                  # Curated content index for LLM tools
│   └── robots.txt                # Crawler directives
├── scripts/                      # Utility scripts
│   ├── check_internal_links.py   # Internal link checker run in CI
│   └── render_diagram.py         # Regenerate the shared NovaDeploy SVG
├── mkdocs.yml                    # MkDocs Material configuration
├── hooks.py                      # Diagram, AI export, and accessibility build hooks
├── skill.md                      # Agent skill file, served raw at /skill.md
├── requirements.txt              # Python dependencies
├── .lighthouserc.json            # Lighthouse CI audit thresholds
├── .gitignore                    # Local/private file exclusions
├── LICENSE                       # MIT for source; content all rights reserved
└── README.md                     # Repository overview and setup
```

## Run locally

**Prerequisite:** Python must be installed on your computer. Python 3.12 is recommended to match this repository's automated build environment.

The social plugin, which draws the link-preview images, also needs the Cairo graphics library. On Debian or Ubuntu: `sudo apt-get install libcairo2-dev libfreetype6-dev libffi-dev libjpeg-dev libpng-dev libz-dev`. On macOS: `brew install cairo freetype libffi libjpeg libpng zlib`. Windows steps are on the [Material for MkDocs image processing page](https://squidfunk.github.io/mkdocs-material/plugins/requirements/image-processing/).

Clone the repository:

```bash
git clone https://github.com/jslavin-docs/jslavin-docs.github.io.git
cd jslavin-docs.github.io
```

Create and activate a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Preview the site locally:

```bash
mkdocs serve
```

Open `http://127.0.0.1:8000` in your browser.

Check the site before publishing:

```bash
mkdocs build --strict
python scripts/check_internal_links.py site
```

## Update the NovaDeploy diagram

Both NovaDeploy samples share one SVG generated from their Mermaid blocks, so visitors' browsers don't have to draw it. AI exports keep the Mermaid source.

Edit the Mermaid block in both samples so the two stay identical, then regenerate the SVG and its metadata:

```bash
python scripts/render_diagram.py
```

This requires Node.js and uses Mermaid CLI 11.17.0. Normal builds use the checked-in SVG and don't need Node.js. Commit both Markdown files, the SVG, and its JSON metadata together. The build fails if the diagram no longer matches its source.
