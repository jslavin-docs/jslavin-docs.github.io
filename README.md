# jslavin-docs.github.io

Private-ready MkDocs Material portfolio site for Jeff Slavin, Senior Technical Writer and Documentation Lead.

This repo is designed to stay **private while you build** and become a free GitHub Pages site when you are ready to make the repo public.

## What's included

```text
jslavin-docs.github.io/
├── mkdocs.yml                       # MkDocs Material configuration
├── README.md                        # Setup and publishing instructions
├── GITHUB_PROFILE_README.md         # Copy into the separate public jslavin-docs profile repo
├── requirements.txt                 # Pinned MkDocs Material dependency
├── .gitignore                       # Blocks source/private files from being committed
├── .github/workflows/pages.yml      # Builds on every push; deploys only after repo is public
└── docs/
    ├── index.md                     # Polished hero, headshot, metrics, skills, featured work
    ├── portfolio.md                 # Categorized writing-sample cards with live links
    ├── resume.md                    # Resume page with quantified impact metrics and no phone number
    └── assets/
        ├── jeff-slavin.jpg          # Professional headshot
        └── custom.css               # Hero, card grid, metrics, and resume styling
```

## Privacy check

The portfolio intentionally does **not** show a phone number. It includes only:

- Miami, FL
- jslavin.docs@gmail.com
- LinkedIn
- GitHub

Do not commit the original resume DOCX, writing-samples DOCX, PDFs, or ZIP files. The `.gitignore` is set up to help prevent that.

## Step 1 — Create the private portfolio repo

On GitHub, create a new repository named exactly:

```text
jslavin-docs.github.io
```

Use these settings:

- Visibility: **Private**
- Do not initialize with a README, .gitignore, or license

## Step 2 — Push this portfolio repo

From the folder that contains this README:

```bash
unzip jslavin-docs.github.io-recreated.zip
cd jslavin-docs.github.io
git init
git branch -M main
git add .
git commit -m "Create technical writing portfolio"
git remote add origin https://github.com/jslavin-docs/jslavin-docs.github.io.git
git push -u origin main
```

The GitHub Action will build the site while the repo is private, but the deploy job is skipped until the repo is public.

## Step 3 — Preview locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt
mkdocs serve
```

Open:

```text
http://127.0.0.1:8000
```

## Step 4 — Create your GitHub profile README

Create a separate **public** repo named exactly:

```text
jslavin-docs
```

Then copy `GITHUB_PROFILE_README.md` into that repo as:

```text
README.md
```

That public README becomes the visible overview on your GitHub profile.

## Step 5 — Publish the portfolio when ready

When you are ready for employers to see the portfolio:

1. In `jslavin-docs.github.io`, go to **Settings → General → Danger Zone → Change visibility** and make the repo **Public**.
2. Go to **Settings → Pages**.
3. Under **Build and deployment**, set **Source** to **GitHub Actions**.
4. Go to **Actions → Build and deploy MkDocs portfolio → Run workflow**.
5. Your site will publish at:

```text
https://jslavin-docs.github.io
```

## Step 6 — Pin the portfolio repo

On your GitHub profile:

1. Select **Customize your pins**.
2. Pin `jslavin-docs.github.io`.
3. Keep `jslavin-docs` public so your profile README remains visible.

## Notes

- GitHub Pages on the free plan requires the Pages repository to be public.
- Private-repo GitHub Pages requires a paid plan.
- This repo uses a GitHub Actions Pages workflow instead of a `gh-pages` branch, so you do not need to select a branch before it exists.
