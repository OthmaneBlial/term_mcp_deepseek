#!/usr/bin/env python3
"""Verify that the portable GitHub Pages site has no broken local references."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).parents[1]
SITE = ROOT / "site"
HTML_FILES = (SITE / "index.html", SITE / "docs.html")


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.references: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"] or "")
        for attribute in ("href", "src"):
            value = values.get(attribute)
            if value:
                self.references.append((attribute, value))


def page_parser(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def local_target(source: Path, reference: str) -> tuple[Path, str] | None:
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or reference.startswith(("mailto:", "tel:")):
        return None
    if parsed.path.startswith("/"):
        raise ValueError(f"root-relative reference is not project-subpath safe: {reference}")
    target = source if not parsed.path else source.parent / unquote(parsed.path)
    if parsed.path.endswith("/"):
        target /= "index.html"
    return target.resolve(), parsed.fragment


def check_pages() -> list[str]:
    errors: list[str] = []
    parsed_pages = {path.resolve(): page_parser(path) for path in HTML_FILES}
    for page, parser in parsed_pages.items():
        for attribute, reference in parser.references:
            try:
                result = local_target(page, reference)
            except ValueError as error:
                errors.append(f"{page.relative_to(ROOT)}: {error}")
                continue
            if result is None:
                continue
            target, fragment = result
            if not target.is_relative_to(SITE.resolve()):
                errors.append(f"{page.relative_to(ROOT)}: {attribute} escapes site/: {reference}")
                continue
            if not target.exists():
                errors.append(f"{page.relative_to(ROOT)}: missing {attribute}: {reference}")
                continue
            if fragment and target.suffix == ".html":
                target_parser = parsed_pages.get(target) or page_parser(target)
                if fragment not in target_parser.ids:
                    errors.append(
                        f"{page.relative_to(ROOT)}: missing fragment #{fragment} in "
                        f"{target.relative_to(ROOT)}"
                    )
    return errors


def check_css() -> list[str]:
    css = (SITE / "styles.css").read_text(encoding="utf-8")
    errors: list[str] = []
    for reference in re.findall(r"url\([\"']?([^\"')]+)", css):
        if reference.startswith(("data:", "http://", "https://", "%")):
            continue
        target = (SITE / unquote(urlsplit(reference).path)).resolve()
        if not target.is_relative_to(SITE.resolve()) or not target.exists():
            errors.append(f"site/styles.css: missing url(): {reference}")
    return errors


def check_copied_evidence() -> list[str]:
    errors: list[str] = []
    pairs = [
        (ROOT / "docs/assets/mission-control.png", SITE / "assets/mission-control.jpg"),
        (ROOT / "term_mcp_deepseek/static/favicon.svg", SITE / "assets/favicon.svg"),
    ]
    pairs.extend(
        (source, SITE / "receipts" / source.name)
        for source in sorted((ROOT / "examples/receipts").glob("*.json"))
    )
    pairs.extend(
        (source, SITE / "recipes" / source.name)
        for source in sorted((ROOT / "examples/recipes").glob("*.json"))
    )
    for source, copy in pairs:
        if not copy.exists() or source.read_bytes() != copy.read_bytes():
            errors.append(f"stale or missing evidence copy: {copy.relative_to(ROOT)}")
    return errors


def main() -> int:
    errors = check_pages() + check_css() + check_copied_evidence()
    index = (SITE / "index.html").read_text(encoding="utf-8")
    for required in (
        "Make terminal work",
        "94",
        "signed receipt",
        "v1.0.0",
        "No mandatory telemetry",
    ):
        if required.lower() not in index.lower():
            errors.append(f"site/index.html: missing factual product copy: {required}")
    try:
        ET.parse(SITE / "sitemap.xml")
    except (ET.ParseError, OSError) as error:
        errors.append(f"site/sitemap.xml: {error}")

    if errors:
        print("site check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("site check: ok (portable links, evidence copies, sitemap, product facts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
