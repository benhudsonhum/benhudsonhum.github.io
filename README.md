# Ben Hudson — instructional-design portfolio

This repository contains Ben Hudson's professional portfolio: a lightweight static site built with semantic HTML and CSS.

## Local preview

From the repository root, start any static file server. For example:

```powershell
python -m http.server 8000
```

Then open `http://127.0.0.1:8000/`.

## Quality checks

Run the built-in validator from the repository root:

```powershell
python scripts/check_site.py
```

The check covers expected pages, page metadata, internal links, referenced assets, evidence markup and deployment files.

## Deployment

The site is structured for GitHub Pages at `benhudsonhum.github.io`. The repository root is the document root; no build step is required.
