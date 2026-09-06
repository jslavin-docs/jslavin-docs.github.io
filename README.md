# Jeff Slavin | Technical Writing Portfolio

[![Deploy to GitHub Pages](https://github.com/jslavin-docs/jslavin-docs.github.io/actions/workflows/pages.yml/badge.svg)](https://github.com/jslavin-docs/jslavin-docs.github.io/actions/workflows/pages.yml)

**Lead Technical Writer**  
API · Cloud · Edge · IoT · GitOps · DevSecOps · Docs as Code

This repository contains the source for my technical writing portfolio, built with MkDocs Material and published with GitHub Pages. It demonstrates the same Docs as Code practices I use professionally: Markdown authoring, YAML configuration, Git version control, strict build checks and link validation in CI, and GitHub Actions automation.

- **Live portfolio:** https://jslavin-docs.github.io/
- **Resume:** https://jslavin-docs.github.io/resume/
- **LinkedIn:** https://www.linkedin.com/in/jeff-slavin/
- **Email:** jslavin.docs@gmail.com  

## Focus areas

API documentation · OpenAPI · SDK documentation · Information architecture · Docs as Code · Cloud and edge computing · IoT · Kubernetes · GitOps · Argo CD · DevSecOps · Prometheus

## What this repo demonstrates

- **MkDocs Material** — custom theme configuration, navigation tabs, admonitions, code copy, and permalink anchors
- **Custom CSS** — hero layout, metric cards, portfolio grid, and skill cards layered on top of the Material theme
- **GitHub Actions CI/CD** — build, quality, and audit jobs on every push to `main` and every pull request, with deploy gated on the first two and skipped for pull requests
- **GitHub Pages** — static-site publishing for a public technical writing portfolio
- **Docs as Code workflow** — content authored in Markdown, configuration managed in YAML, and version-controlled in Git
- **AI-retrieval artifacts** — `llms.txt`, a build-generated `llms-full.txt`, Markdown versions of every page, and an agent instruction file (`skill.md`) expose the site content to LLM-based tools via the MkDocs hook in `hooks.py`
- **Documentation QA** — `mkdocs build --strict` and an internal link check run in CI; a broken link or build warning blocks the deploy

## Repository structure

```text
jslavin-docs.github.io/
├── .github/workflows/pages.yml   # Build, quality, audit, and deploy workflow
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
├── hooks.py                      # Pre-rendered diagram and AI export build hooks
├── skill.md                      # Agent skill file, served raw at /skill.md
├── requirements.txt              # Python dependencies
├── .lighthouserc.json            # Lighthouse CI audit thresholds
├── .gitignore                    # Local/private file exclusions
├── LICENSE                       # MIT for source; content all rights reserved
└── README.md                     # Repository overview and setup
```

## Run locally

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
```

## Update the NovaDeploy diagram

Both NovaDeploy samples use a shared SVG generated from their Mermaid blocks, so visitors' browsers do not need to generate the diagram. The original Mermaid source remains in the Markdown files and AI exports.

After updating the Mermaid block in both samples, keep the blocks identical and regenerate the SVG and its metadata:

```bash
python scripts/render_diagram.py
```

Regeneration requires Node.js and uses Mermaid CLI 11.17.0. Normal site builds use the checked-in SVG and do not require Node.js. Commit the updated Markdown, SVG, and JSON metadata together; the build rejects a diagram that no longer matches its source.
