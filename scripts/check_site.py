#!/usr/bin/env python3
"""Static quality checks for the Ben Hudson portfolio."""

from __future__ import annotations

import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
SITE_DOMAIN = "benhudsonhum.github.io"
SOCIAL_IMAGE_URL = (
    "https://benhudsonhum.github.io/assets/images/common/social-preview.png"
)
WALKTHROUGH_URL = "https://www.youtube.com/watch?v=nUyF6JenkFE"
WALKTHROUGH_THUMBNAIL = (
    "/assets/images/healthcare/evidence/adhd-interactive-video-menu.png"
)
EXPECTED_HTML = [
    Path("index.html"),
    Path("about.html"),
    Path("404.html"),
    Path("work/healthcare-simulation.html"),
    Path("work/life-skills-curriculum.html"),
    Path("work/refugee-sponsorship.html"),
]
REQUIRED_FILES = [
    Path(".nojekyll"),
    Path("favicon.svg"),
    Path("site.webmanifest"),
    Path("robots.txt"),
    Path("sitemap.xml"),
    Path("assets/css/site.css"),
    Path("assets/js/site.js"),
    Path("assets/documents/ben-hudson-instructional-designer-resume.pdf"),
    Path("assets/images/common/social-preview.png"),
    Path("assets/images/common/ben-hudson-portrait-desktop-520x650.jpg"),
    Path("assets/images/common/ben-hudson-portrait-desktop-696x870.jpg"),
    Path("assets/images/common/ben-hudson-portrait-mobile-800x533.jpg"),
    Path("assets/images/common/ben-hudson-portrait-mobile-1400x933.jpg"),
]
REQUIRED_EVIDENCE = [
    Path("assets/images/healthcare/evidence/adhd-course-overview-safe.png"),
    Path("assets/images/healthcare/evidence/adhd-chaptered-lecture-video.png"),
    Path("assets/images/healthcare/evidence/adhd-interactive-timeline.png"),
    Path("assets/images/healthcare/evidence/adhd-interactive-video-menu.png"),
    Path("assets/images/curriculum/evidence/tfac-life-skills-manual-spread.png"),
    Path("assets/images/curriculum/evidence/tfac-equity-handout.png"),
    Path("assets/images/curriculum/evidence/tfac-child-protection-flow-chart.png"),
    Path("assets/images/curriculum/curriculum-architecture.svg"),
    Path("assets/images/curriculum/tfac-eswatini-facilitation-cycle.svg"),
    Path("assets/images/refugee/evidence/refugee-online-learning-overview.png"),
    Path("assets/images/refugee/evidence/refugee-education-scenario.png"),
    Path("assets/images/refugee/evidence/refugee-confidentiality-check.png"),
    Path("assets/images/refugee/evidence/refugee-workshop-structure.png"),
    Path("assets/images/refugee/evidence/refugee-facilitator-guidance.png"),
]
PRIVATE_DIRS = {"private", "working", "source-materials", "raw-assets"}
FORBIDDEN_VISIBLE = ("TODO", "FIXME", "LOREM IPSUM", "PLACEHOLDER")
FORBIDDEN_PUBLIC_TEXT = (
    "Approved project artefact",
    "Approved course screenshot",
    "Support-network learning handout",
    "SIB-P",
)
OBSOLETE_EVIDENCE_REFERENCES = (
    "adhd-course-overview.png",
    "adhd-interactive-content.png",
    "adhd-interview-simulation.png",
    "tfac-support-network-handout.png",
    "tfac-eswatini-facilitation.jpg",
)
INTERNAL_PUBLIC_LINKS = (
    "PORTFOLIO_SPEC.md",
    "CONTENT_REGISTER.md",
    "APPROVED_EVIDENCE_MANIFEST.md",
    "CODEX_FIRST_BUILD.md",
    "LAUNCH_CHECKLIST.md",
)
FORBIDDEN_EVIDENCE_PATTERNS = (
    "digital literacies",
    "launch_story",
    "storyline",
    "story_content",
    "ben_hudson_portfolio_build_pack",
)
FORBIDDEN_PUBLIC_SUFFIXES = {".exe", ".zip", ".rar", ".7z"}
ASSET_WARNING_BYTES = 1_000_000
RASTER_SUFFIXES = {".jpg", ".jpeg", ".png"}
HOMEPAGE_PREVIEWS = {
    Path("assets/images/home/healthcare-searchable-video.jpg"),
    Path("assets/images/home/healthcare-interactive-reference.jpg"),
    Path("assets/images/home/healthcare-decision-practice.jpg"),
    Path("assets/images/home/curriculum-90-activity-manual.jpg"),
    Path("assets/images/home/curriculum-visual-learning-resource.jpg"),
    Path("assets/images/home/curriculum-safeguarding-pathway.jpg"),
    Path("assets/images/home/refugee-online-pathway.jpg"),
    Path("assets/images/home/refugee-scenario-practice.jpg"),
    Path("assets/images/home/refugee-workshop-design.jpg"),
}
OBSOLETE_HOMEPAGE_PREVIEWS = {
    "adhd-course-overview-safe-preview.png",
    "tfac-equity-card-16x10.png",
    "refugee-online-learning-card-16x10.png",
    "tfac-equity-handout-preview.png",
    "refugee-online-learning-preview.png",
}
JUSTIFIED_UNREFERENCED_IMAGES: set[Path] = set()
OBSOLETE_PORTRAITS = (
    "ben-hudson-portrait-520x650.jpg",
    "ben-hudson-portrait-696x870.jpg",
    "ben-hudson-portrait-hero-800.jpg",
    "ben-hudson-portrait-hero-1400.jpg",
)
PROHIBITED_CASE_HEADINGS = (
    "The Brief",
    "What I Designed and Delivered",
    "What the Work Produced",
    "What I Learned",
)
EXPECTED_WORK_EXAMPLES = {
    Path("work/healthcare-simulation.html"): {"examples": 2, "flipbooks": [4], "singles": 1},
    Path("work/life-skills-curriculum.html"): {"examples": 3, "flipbooks": [3], "singles": 2},
    Path("work/refugee-sponsorship.html"): {"examples": 2, "flipbooks": [3, 2], "singles": 0},
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.in_title = False
        self.meta_description = ""
        self.meta: dict[str, str] = {}
        self.canonical = ""
        self.h1_count = 0
        self.ids: list[str] = []
        self.links: list[str] = []
        self.assets: list[str] = []
        self.images: list[dict[str, str]] = []
        self.images_without_alt = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "h1":
            self.h1_count += 1
        if values.get("id"):
            self.ids.append(values["id"] or "")
        if tag == "meta" and values.get("name", "").lower() == "description":
            self.meta_description = (values.get("content") or "").strip()
        if tag == "meta":
            meta_key = (values.get("property") or values.get("name") or "").lower()
            if meta_key:
                self.meta[meta_key] = (values.get("content") or "").strip()
        if tag == "link" and "canonical" in (values.get("rel") or "").lower():
            self.canonical = (values.get("href") or "").strip()
        if tag == "a" and values.get("href"):
            self.links.append(values["href"] or "")
        if tag in {"img", "script", "source"} and values.get("src"):
            self.assets.append(values["src"] or "")
        if tag in {"img", "source"} and values.get("srcset"):
            for candidate in (values.get("srcset") or "").split(","):
                url = candidate.strip().split()[0] if candidate.strip() else ""
                if url:
                    self.assets.append(url)
        if tag == "link" and values.get("href") and "canonical" not in (values.get("rel") or "").lower():
            self.assets.append(values["href"] or "")
        if tag == "img" and "alt" not in values:
            self.images_without_alt += 1
        if tag == "img":
            self.images.append({key: value or "" for key, value in values.items()})

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return "".join(self.title_parts).strip()


def local_target(source_page: Path, raw_url: str) -> tuple[Path | None, str]:
    parsed = urlparse(raw_url)
    if parsed.scheme in {"http", "https", "mailto", "tel", "data"} or raw_url.startswith("//"):
        return None, ""
    path_text = unquote(parsed.path)
    if not path_text:
        target = source_page
    elif path_text.startswith("/"):
        relative = path_text.lstrip("/")
        target = ROOT / (relative or "index.html")
    else:
        target = (source_page.parent / path_text).resolve()
    if target.is_dir():
        target = target / "index.html"
    return target, parsed.fragment


def visible_text(html: str) -> str:
    cleaned = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html, flags=re.I | re.S)
    cleaned = re.sub(r"<!--.*?-->", " ", cleaned, flags=re.S)
    return re.sub(r"<[^>]+>", " ", cleaned)


def check_social_png(errors: list[str], warnings: list[str]) -> None:
    png_path = ROOT / "assets/images/common/social-preview.png"
    if not png_path.is_file():
        return
    header = png_path.read_bytes()[:26]
    if len(header) < 26 or header[:8] != b"\x89PNG\r\n\x1a\n":
        errors.append("social-preview.png is not a valid PNG file")
        return
    width, height = struct.unpack(">II", header[16:24])
    colour_type = header[25]
    if (width, height) != (1200, 630):
        errors.append(
            f"social-preview.png has invalid dimensions: {width}x{height}"
        )
    if colour_type not in {2, 6}:
        errors.append("social-preview.png must use RGB or RGBA colour")
    if png_path.stat().st_size >= 1_000_000:
        warnings.append("social-preview.png is 1 MB or larger")


def raster_dimensions(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as handle:
        header = handle.read(24)
        if len(header) >= 24 and header[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", header[16:24])
        if len(header) < 2 or header[:2] != b"\xff\xd8":
            return None
        handle.seek(2)
        while True:
            marker_start = handle.read(1)
            if not marker_start:
                return None
            if marker_start != b"\xff":
                continue
            marker = handle.read(1)
            while marker == b"\xff":
                marker = handle.read(1)
            if not marker or marker in {b"\xd8", b"\xd9"}:
                continue
            length_bytes = handle.read(2)
            if len(length_bytes) != 2:
                return None
            segment_length = struct.unpack(">H", length_bytes)[0]
            if marker[0] in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                data = handle.read(5)
                if len(data) != 5:
                    return None
                height, width = struct.unpack(">HH", data[1:5])
                return width, height
            handle.seek(segment_length - 2, 1)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    parsed_pages: dict[Path, PageParser] = {}
    referenced_images: set[Path] = set()

    for relative in EXPECTED_HTML:
        page = ROOT / relative
        if not page.is_file():
            errors.append(f"missing HTML page: {relative.as_posix()}")
            continue
        html = page.read_text(encoding="utf-8")
        for match in re.findall(r"/assets/images/[A-Za-z0-9._/-]+", html):
            referenced_images.add(Path(match.lstrip("/")))
        parser = PageParser()
        parser.feed(html)
        parsed_pages[page.resolve()] = parser
        if not parser.title:
            errors.append(f"missing title: {relative.as_posix()}")
        if not parser.meta_description:
            errors.append(f"missing meta description: {relative.as_posix()}")
        if parser.h1_count != 1:
            errors.append(f"expected one H1, found {parser.h1_count}: {relative.as_posix()}")
        if parser.images_without_alt:
            errors.append(f"{parser.images_without_alt} image(s) missing alt: {relative.as_posix()}")
        duplicate_ids = sorted({item for item in parser.ids if parser.ids.count(item) > 1})
        if duplicate_ids:
            errors.append(f"duplicate IDs {duplicate_ids}: {relative.as_posix()}")
        if urlparse(parser.canonical).netloc != SITE_DOMAIN:
            errors.append(f"invalid canonical domain: {relative.as_posix()}")
        expected_social_metadata = {
            "og:image": SOCIAL_IMAGE_URL,
            "twitter:image": SOCIAL_IMAGE_URL,
            "og:image:type": "image/png",
            "og:image:width": "1200",
            "og:image:height": "630",
            "twitter:card": "summary_large_image",
        }
        for meta_key, expected_value in expected_social_metadata.items():
            actual_value = parser.meta.get(meta_key, "")
            if actual_value != expected_value:
                errors.append(
                    f"invalid social metadata {meta_key}: {relative.as_posix()}"
                )
        if not parser.meta.get("og:image:alt", "").strip():
            errors.append(f"missing social metadata og:image:alt: {relative.as_posix()}")
        if not parser.meta.get("twitter:image:alt", "").strip():
            errors.append(f"missing social metadata twitter:image:alt: {relative.as_posix()}")
        if parser.meta.get("theme-color", "").lower() != "#0b0f14":
            errors.append(f"missing or invalid dark theme-color: {relative.as_posix()}")
        for image in parser.images:
            source = image.get("src", "")
            suffix = Path(urlparse(source).path).suffix.lower()
            if suffix in RASTER_SUFFIXES:
                if not image.get("width", "").isdigit() or not image.get("height", "").isdigit():
                    errors.append(f"raster image missing intrinsic dimensions in {relative.as_posix()}: {source}")
                else:
                    target, _ = local_target(page, source)
                    actual = raster_dimensions(target) if target and target.is_file() else None
                    declared = (int(image["width"]), int(image["height"]))
                    if actual and actual != declared:
                        errors.append(
                            f"raster image dimensions do not match the file in {relative.as_posix()}: {source}"
                        )
            if "/evidence/" in source:
                if not image.get("alt", "").strip():
                    errors.append(f"evidence image missing meaningful alt text in {relative.as_posix()}: {source}")
        if re.search(r"[A-Za-z]:[\\/]Users[\\/]", html, flags=re.I):
            errors.append(f"source-folder absolute path in HTML: {relative.as_posix()}")
        artifact_blocks = re.findall(
            r'<figure\b[^>]*class="[^"]*artifact-frame[^"]*"[^>]*>.*?</figure>',
            html,
            flags=re.I | re.S,
        )
        for block in artifact_blocks:
            match = re.search(r'<img\b[^>]*src="([^"]*/evidence/[^"]+)"', block, flags=re.I)
            if match and not re.search(r'<a\b[^>]*class="[^"]*artifact-fullsize[^"]*"', block, flags=re.I):
                errors.append(f"detailed evidence missing full-size link in {relative.as_posix()}: {match.group(1)}")
        bootstrap_position = html.find('class="theme-bootstrap"')
        stylesheet_position = html.find('href="/assets/css/site.css"')
        if (
            bootstrap_position < 0
            or stylesheet_position < 0
            or bootstrap_position > stylesheet_position
            or "document.documentElement.dataset.theme" not in html
        ):
            errors.append(f"theme bootstrap is missing or follows the stylesheet: {relative.as_posix()}")
        if len(re.findall(r'<button\b[^>]*data-theme-toggle', html, flags=re.I)) != 1:
            errors.append(f"expected one theme toggle: {relative.as_posix()}")
        if not re.search(r'<script\b[^>]*src="/assets/js/site\.js"[^>]*\bdefer\b', html, flags=re.I):
            errors.append(f"shared site JavaScript is not loaded with defer: {relative.as_posix()}")

        if relative.parent == Path("work"):
            expected = EXPECTED_WORK_EXAMPLES[relative]
            if 'data-role-summary' not in html or 'class="role-summary"' not in html:
                errors.append(f"role summary is missing: {relative.as_posix()}")
            case_visible = " ".join(visible_text(html).split())
            for heading in PROHIBITED_CASE_HEADINGS:
                if heading.casefold() in case_visible.casefold():
                    errors.append(f"prohibited generic heading remains ({heading}): {relative.as_posix()}")
            if "case-toc" in html:
                errors.append(f"case-study table of contents remains: {relative.as_posix()}")
            if "About the evidence" in case_visible:
                errors.append(f"public About the evidence copy remains: {relative.as_posix()}")

            example_blocks = re.findall(
                r'<article\b[^>]*class="[^"]*\bwork-example\b[^"]*"[^>]*>.*?</article>',
                html,
                flags=re.I | re.S,
            )
            if len(example_blocks) != expected["examples"]:
                errors.append(
                    f"expected {expected['examples']} work examples, found {len(example_blocks)}: {relative.as_posix()}"
                )
            flipbook_blocks = [block for block in example_blocks if "work-example--flipbook" in block]
            single_blocks = [block for block in example_blocks if "work-example--single" in block]
            if len(flipbook_blocks) != len(expected["flipbooks"]):
                errors.append(f"unexpected flipbook count: {relative.as_posix()}")
            if len(single_blocks) != expected["singles"]:
                errors.append(f"unexpected single-artefact count: {relative.as_posix()}")

            all_caption_texts: list[str] = []
            for book_position, (block, expected_slides) in enumerate(
                zip(flipbook_blocks, expected["flipbooks"]), start=1
            ):
                slides = re.findall(
                    r'<figure\b[^>]*class="[^"]*flipbook__slide[^"]*"[^>]*>.*?</figure>',
                    block,
                    flags=re.I | re.S,
                )
                if len(slides) != expected_slides:
                    errors.append(
                        f"flipbook {book_position} expected {expected_slides} slides, found {len(slides)}: {relative.as_posix()}"
                    )
                for control in ("data-flipbook-previous", "data-flipbook-next", "data-flipbook-status"):
                    if block.count(control) != 1:
                        errors.append(
                            f"flipbook {book_position} missing unique {control}: {relative.as_posix()}"
                        )
                for slide_position, figure in enumerate(slides, start=1):
                    image_match = re.search(r'<img\b([^>]*)>', figure, flags=re.I | re.S)
                    if not image_match:
                        errors.append(
                            f"flipbook {book_position} slide {slide_position} has no image: {relative.as_posix()}"
                        )
                    else:
                        image_tag = image_match.group(1)
                        for attribute in ("src", "alt", "width", "height"):
                            match = re.search(rf'\b{attribute}="([^"]*)"', image_tag, flags=re.I)
                            if not match or not match.group(1).strip():
                                errors.append(
                                    f"flipbook {book_position} slide {slide_position} image missing {attribute}: {relative.as_posix()}"
                                )
                    caption_match = re.search(
                        r'<figcaption\b[^>]*>(.*?)</figcaption>', figure, flags=re.I | re.S
                    )
                    if not caption_match:
                        errors.append(
                            f"flipbook {book_position} slide {slide_position} has no caption: {relative.as_posix()}"
                        )
                        continue
                    caption_html = caption_match.group(1)
                    caption_text = " ".join(visible_text(caption_html).split()).casefold()
                    all_caption_texts.append(caption_text)
                    if not all(
                        token in caption_html
                        for token in ("artifact-label", "<strong", "artifact-fullsize")
                    ):
                        errors.append(
                            f"flipbook {book_position} slide {slide_position} lacks label, title or full-size link: {relative.as_posix()}"
                        )
                    explanation_match = re.search(
                        r'</strong>\s*<span>(.*?)</span>', caption_html, flags=re.I | re.S
                    )
                    explanation = (
                        " ".join(visible_text(explanation_match.group(1)).split())
                        if explanation_match
                        else ""
                    )
                    explanation_words = re.findall(r"[\w’'-]+", explanation, flags=re.UNICODE)
                    if not 18 <= len(explanation_words) <= 35:
                        errors.append(
                            f"flipbook {book_position} slide {slide_position} explanation is not 18-35 words ({len(explanation_words)}): {relative.as_posix()}"
                        )

            for single_position, block in enumerate(single_blocks, start=1):
                figures = re.findall(
                    r'<figure\b[^>]*class="[^"]*work-example__figure[^"]*"[^>]*>.*?</figure>',
                    block,
                    flags=re.I | re.S,
                )
                if len(figures) != 1:
                    errors.append(
                        f"single example {single_position} must contain one figure: {relative.as_posix()}"
                    )
                    continue
                figure = figures[0]
                image_match = re.search(r'<img\b([^>]*)>', figure, flags=re.I | re.S)
                if not image_match:
                    errors.append(f"single example {single_position} has no image: {relative.as_posix()}")
                else:
                    for attribute in ("src", "alt", "width", "height"):
                        match = re.search(rf'\b{attribute}="([^"]*)"', image_match.group(1), flags=re.I)
                        if not match or not match.group(1).strip():
                            errors.append(
                                f"single example {single_position} image missing {attribute}: {relative.as_posix()}"
                            )
                caption_match = re.search(
                    r'<figcaption\b[^>]*>(.*?)</figcaption>', figure, flags=re.I | re.S
                )
                if not caption_match:
                    errors.append(f"single example {single_position} has no caption: {relative.as_posix()}")
                else:
                    caption_html = caption_match.group(1)
                    all_caption_texts.append(" ".join(visible_text(caption_html).split()).casefold())
                    if not all(
                        token in caption_html
                        for token in ("artifact-label", "<strong", "artifact-fullsize")
                    ):
                        errors.append(
                            f"single example {single_position} lacks label, title or full-size link: {relative.as_posix()}"
                        )
                    explanation_match = re.search(
                        r'</strong>\s*<span>(.*?)</span>', caption_html, flags=re.I | re.S
                    )
                    explanation = (
                        " ".join(visible_text(explanation_match.group(1)).split())
                        if explanation_match
                        else ""
                    )
                    explanation_words = re.findall(r"[\w’'-]+", explanation, flags=re.UNICODE)
                    if not 18 <= len(explanation_words) <= 35:
                        errors.append(
                            f"single example {single_position} explanation is not 18-35 words ({len(explanation_words)}): {relative.as_posix()}"
                        )
            if len(all_caption_texts) != len(set(all_caption_texts)):
                errors.append(f"work-example captions are not unique: {relative.as_posix()}")
        upper_visible = visible_text(html).upper()
        for marker in FORBIDDEN_VISIBLE:
            if marker in upper_visible:
                errors.append(f"visible {marker}: {relative.as_posix()}")
        visible = visible_text(html)
        for marker in FORBIDDEN_PUBLIC_TEXT:
            if marker.casefold() in visible.casefold():
                errors.append(f"visible prohibited evidence text {marker}: {relative.as_posix()}")
        for obsolete in OBSOLETE_EVIDENCE_REFERENCES:
            if obsolete.casefold() in html.casefold():
                errors.append(f"obsolete evidence reference {obsolete}: {relative.as_posix()}")
        for obsolete in OBSOLETE_PORTRAITS:
            if obsolete.casefold() in html.casefold():
                errors.append(f"obsolete portrait reference {obsolete}: {relative.as_posix()}")
        for internal in INTERNAL_PUBLIC_LINKS:
            if internal.casefold() in html.casefold():
                errors.append(f"internal file linked from public HTML {internal}: {relative.as_posix()}")

    for required in REQUIRED_FILES:
        if not (ROOT / required).is_file():
            errors.append(f"missing required file: {required.as_posix()}")

    missing_evidence = 0
    for evidence in REQUIRED_EVIDENCE:
        if not (ROOT / evidence).is_file():
            missing_evidence += 1
            errors.append(f"missing selected evidence file: {evidence.as_posix()}")

    check_social_png(errors, warnings)

    index_html = (ROOT / "index.html").read_text(encoding="utf-8")
    healthcare_html = (ROOT / "work/healthcare-simulation.html").read_text(
        encoding="utf-8"
    )
    css = (ROOT / "assets/css/site.css").read_text(encoding="utf-8")
    walkthrough_occurrences = sum(
        (ROOT / relative).read_text(encoding="utf-8").count(WALKTHROUGH_URL)
        for relative in EXPECTED_HTML
        if (ROOT / relative).is_file()
    )
    if walkthrough_occurrences != 1:
        errors.append(
            "approved YouTube walkthrough must appear exactly once in public HTML"
        )
    walkthrough_link = re.search(
        rf'<a\b[^>]*href="{re.escape(WALKTHROUGH_URL)}"[^>]*>'
        rf'.*?<img\b[^>]*src="{re.escape(WALKTHROUGH_THUMBNAIL)}"[^>]*>'
        r'.*?</a>',
        healthcare_html,
        flags=re.I | re.S,
    )
    if not walkthrough_link:
        errors.append(
            "approved YouTube walkthrough is missing its public-safe linked thumbnail"
        )
    hero_match = re.search(
        r'<section\b[^>]*class="[^"]*hero[^"]*"[^>]*>.*?</section>',
        index_html,
        flags=re.I | re.S,
    )
    hero = hero_match.group(0) if hero_match else ""
    if not hero:
        errors.append("homepage hero section not found")
    else:
        portrait_names = (
            "ben-hudson-portrait-desktop-520x650.jpg",
            "ben-hudson-portrait-desktop-696x870.jpg",
            "ben-hudson-portrait-mobile-800x533.jpg",
            "ben-hudson-portrait-mobile-1400x933.jpg",
        )
        if "<picture" not in hero or any(name not in hero for name in portrait_names):
            errors.append("homepage hero does not use all four responsive portrait derivatives")
        if not re.search(r'<source\b[^>]*media="\(min-width: 72rem\)"[^>]*portrait-desktop', hero, flags=re.I):
            errors.append("homepage portrait lacks the desktop 4:5 art-direction source")
        if not re.search(r'<img\b[^>]*portrait-mobile[^>]*width="800"[^>]*height="533"', hero, flags=re.I):
            errors.append("homepage portrait lacks the mobile 3:2 fallback and intrinsic dimensions")
        if "system-map.svg" in hero:
            errors.append("system map remains in the homepage hero")
        if 'fetchpriority="high"' not in hero or 'decoding="async"' not in hero:
            errors.append("homepage portrait is missing fetch priority or async decoding")
        if re.search(r'<img\b[^>]*ben-hudson-portrait[^>]*loading="lazy"', hero, flags=re.I):
            errors.append("homepage portrait must not be lazy-loaded")

    approach_match = re.search(
        r'<section\b[^>]*aria-labelledby="approach-title"[^>]*>.*?</section>',
        index_html,
        flags=re.I | re.S,
    )
    if not approach_match or "assets/images/common/system-map.svg" not in approach_match.group(0):
        errors.append("system map is not used in the homepage Approach section")

    project_blocks = re.findall(
        r'<figure\b[^>]*class="[^"]*project-card__visual[^"]*"[^>]*>.*?</figure>',
        index_html,
        flags=re.I | re.S,
    )
    project_sources: set[Path] = set()
    for block in project_blocks:
        matches = re.findall(r'<img\b[^>]*src="([^"]+)"[^>]*>', block, flags=re.I)
        labels = re.findall(r'class="[^"]*mini-collage__label[^"]*"', block, flags=re.I)
        if len(matches) != 3 or len(labels) != 3 or "mini-collage" not in block:
            errors.append("homepage project card must use a labelled three-image mini-collage")
        for raw_source in matches:
            source = Path(urlparse(raw_source).path.lstrip("/"))
            project_sources.add(source)
            target = ROOT / source
            if not target.is_file() or raster_dimensions(target) is None:
                errors.append(f"invalid homepage collage image: {source.as_posix()}")
    if project_sources != HOMEPAGE_PREVIEWS:
        errors.append("homepage mini-collage set does not match the optimized project assets")
    homepage_transfer = sum((ROOT / source).stat().st_size for source in project_sources if (ROOT / source).is_file())
    homepage_transfer += sum(
        (ROOT / portrait).stat().st_size
        for portrait in (
            Path("assets/images/common/ben-hudson-portrait-desktop-520x650.jpg"),
            Path("assets/images/common/ben-hudson-portrait-desktop-696x870.jpg"),
            Path("assets/images/common/ben-hudson-portrait-mobile-800x533.jpg"),
            Path("assets/images/common/ben-hudson-portrait-mobile-1400x933.jpg"),
        )
        if (ROOT / portrait).is_file()
    )
    if homepage_transfer >= 1_500_000:
        errors.append(f"homepage image transfer exceeds 1.5 MB: {homepage_transfer:,} bytes")

    metric_count = len(re.findall(r'class="metric"', index_html))
    if metric_count != 4:
        errors.append(f"homepage must contain four metrics, found {metric_count}")
    if "tag-list" in index_html:
        errors.append("homepage project tag list remains")
    if re.search(r'id="capabilit', index_html, flags=re.I) or "Capabilities" in visible_text(index_html):
        errors.append("homepage Capabilities section remains")

    project_css = re.search(r"\.project-card__visual img\s*\{([^}]*)\}", css, flags=re.I | re.S)
    if not project_css or "object-fit: cover" not in project_css.group(1).lower() or "object-fit: contain" in project_css.group(1).lower():
        errors.append("homepage project-card images are not configured for full-bleed cover")
    if re.search(r"\.artifact-grid[^{}]*\{[^}]*aspect-ratio\s*:\s*4\s*/\s*3", css, flags=re.I | re.S):
        errors.append("evidence-gallery images are still forced into 4:3")
    if re.search(r"\.artifact-grid[^{}]*\{[^}]*object-fit\s*:\s*contain", css, flags=re.I | re.S):
        errors.append("evidence-gallery images are still forced to object-fit contain")
    for obsolete in OBSOLETE_HOMEPAGE_PREVIEWS:
        if obsolete in index_html:
            errors.append(f"old homepage preview remains referenced: {obsolete}")

    expected_portraits = {
        Path("assets/images/common/ben-hudson-portrait-desktop-520x650.jpg"): (520, 650),
        Path("assets/images/common/ben-hudson-portrait-desktop-696x870.jpg"): (696, 870),
        Path("assets/images/common/ben-hudson-portrait-mobile-800x533.jpg"): (800, 533),
        Path("assets/images/common/ben-hudson-portrait-mobile-1400x933.jpg"): (1400, 933),
    }
    for relative, expected_dimensions in expected_portraits.items():
        target = ROOT / relative
        if target.is_file():
            actual_dimensions = raster_dimensions(target)
            if actual_dimensions != expected_dimensions:
                errors.append(f"portrait derivative has invalid dimensions: {relative.as_posix()}")
            if target.stat().st_size > 350_000:
                errors.append(f"portrait derivative exceeds 350 KB: {relative.as_posix()}")

    for xml_path in [ROOT / "sitemap.xml", *sorted(ROOT.rglob("*.svg"))]:
        try:
            ET.parse(xml_path)
        except ET.ParseError as exc:
            errors.append(f"invalid XML {xml_path.relative_to(ROOT).as_posix()}: {exc}")
    try:
        json.loads((ROOT / "site.webmanifest").read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        errors.append(f"invalid site.webmanifest JSON: {exc}")

    for directory in PRIVATE_DIRS:
        if (ROOT / directory).exists():
            errors.append(f"private/raw directory present: {directory}/")

    prohibited_files = []
    for candidate in ROOT.rglob("*"):
        if not candidate.is_file() or ".git" in candidate.parts:
            continue
        relative_text = candidate.relative_to(ROOT).as_posix().lower()
        if candidate.suffix.lower() in FORBIDDEN_PUBLIC_SUFFIXES or any(
            pattern in relative_text for pattern in FORBIDDEN_EVIDENCE_PATTERNS
        ):
            prohibited_files.append(candidate.relative_to(ROOT).as_posix())
    for prohibited in prohibited_files:
        errors.append(f"prohibited source/runtime file in site: {prohibited}")

    for image_path in sorted((ROOT / "assets/images").rglob("*")):
        if not image_path.is_file() or image_path.suffix.lower() not in RASTER_SUFFIXES | {".svg"}:
            continue
        relative = image_path.relative_to(ROOT)
        if relative not in referenced_images and relative not in JUSTIFIED_UNREFERENCED_IMAGES:
            errors.append(f"unreferenced image asset: {relative.as_posix()}")

    broken_links = 0
    missing_assets = 0
    for page, parser in parsed_pages.items():
        for raw_url in parser.links:
            target, fragment = local_target(page, raw_url)
            if target is None:
                continue
            if not target.exists():
                broken_links += 1
                errors.append(f"broken link in {page.relative_to(ROOT)}: {raw_url}")
                continue
            if fragment and target.suffix.lower() == ".html":
                target_parser = parsed_pages.get(target.resolve())
                if target_parser is None:
                    html = target.read_text(encoding="utf-8")
                    target_parser = PageParser()
                    target_parser.feed(html)
                    parsed_pages[target.resolve()] = target_parser
                if fragment not in target_parser.ids:
                    broken_links += 1
                    errors.append(f"missing fragment in {page.relative_to(ROOT)}: {raw_url}")
        for raw_url in parser.assets:
            target, _ = local_target(page, raw_url)
            if target is not None and not target.exists():
                missing_assets += 1
                errors.append(f"missing asset in {page.relative_to(ROOT)}: {raw_url}")

    public_roots = [ROOT / "assets", ROOT / "favicon.svg"]
    for public_root in public_roots:
        candidates = [public_root] if public_root.is_file() else list(public_root.rglob("*")) if public_root.exists() else []
        for asset in candidates:
            if asset.is_file() and asset.stat().st_size > ASSET_WARNING_BYTES:
                warnings.append(f"asset over 1 MB: {asset.relative_to(ROOT)} ({asset.stat().st_size:,} bytes)")

    print(f"PASS {len(parsed_pages)} HTML pages checked" if len(parsed_pages) == len(EXPECTED_HTML) else f"FAIL {len(parsed_pages)}/{len(EXPECTED_HTML)} HTML pages checked")
    print(f"PASS {broken_links} broken internal links" if broken_links == 0 else f"FAIL {broken_links} broken internal links")
    print(f"PASS {missing_assets} missing assets" if missing_assets == 0 else f"FAIL {missing_assets} missing assets")
    metadata_ok = not any(any(word in error for word in ("title", "description", "H1", "alt", "duplicate", "canonical")) for error in errors)
    print("PASS titles, descriptions, H1 counts, alt attributes and canonical URLs" if metadata_ok else "FAIL page structure or metadata")
    social_metadata_ok = not any("social metadata" in error for error in errors)
    print("PASS social-preview PNG metadata on every page" if social_metadata_ok else "FAIL social-preview metadata")
    evidence_errors = [error for error in errors if "evidence" in error or "source-folder" in error or "prohibited" in error]
    print(
        f"PASS {len(REQUIRED_EVIDENCE)} selected evidence assets checked"
        if missing_evidence == 0
        else f"FAIL {missing_evidence} selected evidence assets missing"
    )
    print(
        "PASS evidence dimensions, alt text, full-size links and source-file boundaries"
        if not evidence_errors
        else "FAIL evidence markup or source-file boundaries"
    )
    deployment_ok = not any("required file" in error for error in errors)
    print("PASS required deployment files" if deployment_ok else "FAIL required deployment files")
    walkthrough_ok = not any("YouTube walkthrough" in error for error in errors)
    print(
        "PASS approved YouTube walkthrough thumbnail link"
        if walkthrough_ok
        else "FAIL approved YouTube walkthrough thumbnail link"
    )
    for warning in warnings:
        print(f"WARN {warning}")
    for error in errors:
        print(f"ERROR {error}")
    if errors:
        print(f"FAIL {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"PASS 0 errors, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
