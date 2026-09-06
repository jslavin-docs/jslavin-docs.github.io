#!/usr/bin/env python3
"""Regenerate the shared NovaDeploy SVG from the samples' Mermaid source.

Requires Node.js. Uses mmdc from PATH, or downloads Mermaid CLI 11.17.0
through npx. CI may pass --puppeteer-config to select its installed Chrome.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = [
    ROOT / "docs/writing-samples/novadeploy-gitops-admin-guide-portfolio-cut.md",
    ROOT / "docs/writing-samples/novadeploy-gitops-admin-guide-full-version.md",
]
FENCE = re.compile(r"^```mermaid[ \t]*\n(.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)
OUTPUT = ROOT / "docs/assets/diagrams/novadeploy-architecture.svg"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puppeteer-config", type=Path)
    args = parser.parse_args()

    sources = []
    for path in SAMPLES:
        blocks = FENCE.findall(path.read_text(encoding="utf-8"))
        if len(blocks) != 1:
            raise SystemExit(f"Expected one Mermaid diagram in {path.relative_to(ROOT)}")
        sources.append(blocks[0].strip() + "\n")
    if sources[0] != sources[1]:
        raise SystemExit("The two NovaDeploy diagrams differ; update both before regenerating.")

    mmdc = shutil.which("mmdc")
    command = [mmdc] if mmdc else [
        "npx", "--yes", "--package", "@mermaid-js/mermaid-cli@11.17.0", "mmdc"
    ]
    with tempfile.TemporaryDirectory(prefix="novadeploy-diagram-") as temporary:
        source = Path(temporary) / "architecture.mmd"
        rendered = Path(temporary) / "architecture.svg"
        source.write_text(sources[0], encoding="utf-8")
        command += [
            "-i", str(source), "-o", str(rendered), "-b", "transparent",
            "-I", "novadeploy-architecture",
        ]
        if args.puppeteer_config:
            command += ["-p", str(args.puppeteer_config.resolve())]
        subprocess.run(command, check=True)
        svg = rendered.read_text(encoding="utf-8").strip() + "\n"

    # Give the static graphic the same accessible context as the prose below it.
    def describe(match: re.Match) -> str:
        attributes = re.sub(r'\s(?:role|aria-roledescription|aria-labelledby)="[^"]*"', "", match[1])
        return (
            '<svg' + attributes + ' role="img" aria-labelledby="nova-title nova-description">'
            '<title id="nova-title">NovaDeploy architecture</title>'
            '<desc id="nova-description">GitOps deployment, Terraform-owned cloud controls, '
            'and runtime secret synchronization and refresh. A detailed description follows '
            'the diagram under Accessible Diagram Summary.</desc>'
        )

    svg = re.sub(r"<svg\b([^>]*)>", describe, svg, count=1)

    element = ET.fromstring(svg)
    view_box = [float(value) for value in element.attrib["viewBox"].split()]
    metadata = {
        "source_sha256": hashlib.sha256(sources[0].encode("utf-8")).hexdigest(),
        "svg_sha256": hashlib.sha256(svg.encode("utf-8")).hexdigest(),
        "width": view_box[2],
        "height": view_box[3],
        "renderer": "@mermaid-js/mermaid-cli@11.17.0",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8")
    OUTPUT.with_suffix(".json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Updated {OUTPUT.relative_to(ROOT)} and source checksums.")


if __name__ == "__main__":
    main()
