# Jeff Slavin | Technical Writing Portfolio

[![Deploy to GitHub Pages](https://github.com/jslavin-docs/jslavin-docs.github.io/actions/workflows/pages.yml/badge.svg)](https://github.com/jslavin-docs/jslavin-docs.github.io/actions/workflows/pages.yml)

**Senior Technical Writer & Documentation Lead**  
API • Cloud • Edge • IoT • GitOps • DevSecOps • Docs as Code

This repository contains the source for my technical writing portfolio, built with MkDocs Material and published with GitHub Pages. It demonstrates the same Docs as Code practices I use professionally: Markdown authoring, YAML configuration, Git version control, local build checks, and GitHub Actions automation.

**Live portfolio:** https://jslavin-docs.github.io  
**Resume:** [View PDF](https://jslavin-docs.github.io/assets/Jeff-Slavin-Resume.pdf)  
**LinkedIn:** [jeff-slavin](https://www.linkedin.com/in/jeff-slavin)  
**Email:** [jslavin.docs@gmail.com](mailto:jslavin.docs@gmail.com)  

## Focus areas

API documentation · OpenAPI 3.0 · SDK documentation · Information architecture · Docs as Code · Cloud and edge computing · IoT · Kubernetes · GitOps · Argo CD · DevSecOps · Prometheus

## What this repo demonstrates

- **MkDocs Material** — custom theme configuration, navigation tabs, admonitions, code copy, and permalink anchors
- **Custom CSS** — hero layout, metric cards, portfolio grid, and skill cards layered on top of the Material theme
- **GitHub Actions CI/CD** — automated site build workflow on pushes to `main`
- **GitHub Pages** — static-site publishing for a public technical writing portfolio
- **Docs as Code workflow** — content authored in Markdown, configuration managed in YAML, and version-controlled in Git
- **Documentation QA** — local preview and strict build checks before publishing

## Built with

- MkDocs Material
- Markdown
- HTML/CSS
- GitHub Actions
- GitHub Pages
- Docs as Code workflow

## Repository structure

```text
jslavin-docs.github.io/
├── .github/workflows/pages.yml   # GitHub Actions workflow for build/deploy
├── docs/                         # Markdown source files and assets
│   ├── index.md                  # Portfolio homepage
│   ├── portfolio.md              # Writing samples overview
│   ├── resume.md                 # Resume page
│   ├── writing-samples/          # Markdown portfolio samples
│   └── assets/                   # Custom CSS, PDFs, and images
├── mkdocs.yml                    # MkDocs Material configuration
├── requirements.txt              # Python dependencies
├── .gitignore                    # Local/private file exclusions
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
