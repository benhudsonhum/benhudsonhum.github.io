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
DOMAIN = "benhudsonhum.github.io"
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
]
REQUIRED_EVIDENCE = [
    Path("assets/images/healthcare/evidence/adhd-course-guide-navigation.png"),
    Path("assets/images/healthcare/evidence/adhd-searchable-rating-reference.png"),
    Path("assets/images/healthcare/evidence/adhd-interactive-timeline.png"),
    *[Path(f"assets/images/healthcare/storyboard/adhd-interviewer-error-0{index}-{name}.jpg") for index, name in (
        (1, "set-the-context"),
        (2, "observe-the-interview"),
        (3, "identify-the-first-error"),
        (4, "choose-a-better-probe"),
        (5, "review-the-reasoning"),
        (6, "continue-to-feedback"),
    )],
    Path("assets/images/healthcare/applied-instructional-design-process.svg"),
    Path("assets/images/healthcare/video/adhd-question-choice-poster.jpg"),
    Path("assets/images/healthcare/video/adhd-systematic-reporter-bias-poster.jpg"),
    Path("assets/video/healthcare/adhd-question-choice-highlight.mp4"),
    Path("assets/video/healthcare/adhd-question-choice-highlight.webm"),
    Path("assets/video/healthcare/adhd-systematic-reporter-bias-highlight.mp4"),
    Path("assets/video/healthcare/adhd-systematic-reporter-bias-highlight.webm"),
    Path("assets/images/curriculum/evidence/tfac-life-skills-manual-spread.png"),
    *[Path(f"assets/images/curriculum/manual/life-skills-pages-{pages}.png") for pages in (
        "002-003", "042-043", "047-048", "052-053", "059-060",
    )],
    Path("assets/images/curriculum/evidence/tfac-equity-handout.png"),
    Path("assets/images/curriculum/evidence/tfac-child-protection-flow-chart.png"),
    Path("assets/images/curriculum/evidence/tfac-child-protection-network-display.png"),
    *[Path(f"assets/images/curriculum/evidence/team-girl-{name}.png") for name in (
        "cover-contents", "condoms-assertive-communication", "menstruation-bullying", "rights-srhr-behaviours",
    )],
    Path("assets/images/curriculum/evidence/tfac-workshop-journey.png"),
    Path("assets/images/curriculum/evidence/tfac-mphatso-journey-1.png"),
    Path("assets/images/curriculum/evidence/tfac-mphatso-journey-2.png"),
    Path("assets/images/curriculum/evidence/tfac-eswatini-facilitation-public.jpg"),
    Path("assets/images/curriculum/evidence/tfac-observation-assessment.jpg"),
    Path("assets/images/curriculum/tfac-eswatini-facilitation-cycle.svg"),
    Path("assets/images/curriculum/participatory-learning-methodology.svg"),
    Path("assets/images/refugee/evidence/refugee-online-resource-overview.png"),
    Path("assets/images/refugee/evidence/refugee-learning-identity-safe.png"),
    Path("assets/images/refugee/evidence/refugee-sponsorship-agreement-check.png"),
    Path("assets/images/refugee/evidence/refugee-considering-culture.png"),
    Path("assets/images/refugee/evidence/refugee-housing-scenario-reflection.png"),
    Path("assets/images/refugee/evidence/refugee-workshop-outcomes-doing-with.png"),
    Path("assets/images/refugee/evidence/refugee-workshop-training-principles.png"),
    Path("assets/images/refugee/evidence/refugee-workshop-reflective-practice.png"),
    *[Path(f"assets/images/refugee/manual/sponsorship-manual-page-{name}.png") for name in (
        "09-outcomes-structure", "14-workshop-notes", "15-roles-practice",
        "16-organization-communication", "17-communication-scenario", "28-facilitator-reflection",
    )],
]
HOMEPAGE_PREVIEWS = {
    Path("assets/images/healthcare/video/adhd-question-choice-poster.jpg"),
    Path("assets/images/curriculum/evidence/tfac-eswatini-facilitation-public.jpg"),
    Path("assets/images/refugee/evidence/refugee-online-resource-overview.webp"),
}
OBSOLETE_PATHS = (
    "system-map.svg", "healthcare-course-overview.jpg",
    "healthcare-searchable-video.jpg", "healthcare-interactive-reference.jpg", "curriculum-facilitation-circle.jpg",
    "curriculum-90-activity-manual.jpg", "curriculum-visual-learning-resource.jpg", "refugee-online-pathway.jpg",
    "refugee-workshop-design.jpg", "adhd-course-overview-safe.png", "adhd-course-overview-framed.png",
    "adhd-chaptered-lecture-video.png", "adhd-chaptered-lecture-framed.png", "adhd-interactive-timeline-framed.png",
    "adhd-decision-practice-framed.png", "adhd-interactive-video-menu.png", "refugee-online-pathway-framed.png",
    "refugee-education-scenario.png", "refugee-education-scenario-framed.png", "refugee-confidentiality-check.png",
    "refugee-confidentiality-check-framed.png",
)
FORBIDDEN_SUFFIXES = {".rar", ".zip", ".7z", ".ppt", ".pptx", ".doc", ".docx", ".psd", ".exe"}
FORBIDDEN_TEXT = ("C:\\Users\\", "C:/Users/", "BEGIN PRIVATE KEY", "password=", "api_key=")
NEW_RASTERS = {path for path in [*REQUIRED_EVIDENCE, *HOMEPAGE_PREVIEWS] if path.suffix.lower() in {".png", ".jpg", ".jpeg"}}
PAGE_WORD_TARGETS = {
    Path("index.html"): (0, 300),
    Path("work/healthcare-simulation.html"): (350, 500),
    Path("work/life-skills-curriculum.html"): (450, 625),
    Path("work/refugee-sponsorship.html"): (350, 525),
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self.meta: dict[str, str] = {}
        self.canonical = ""
        self.h1_count = 0
        self.ids: list[str] = []
        self.links: list[str] = []
        self.assets: list[str] = []
        self.images: list[dict[str, str]] = []
        self.videos: list[dict[str, str]] = []
        self.sources: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "title": self._in_title = True
        if tag == "h1": self.h1_count += 1
        if values.get("id"): self.ids.append(values["id"])
        if tag == "meta":
            key = (values.get("name") or values.get("property") or "").lower()
            if key: self.meta[key] = values.get("content", "").strip()
        if tag == "link" and "canonical" in values.get("rel", "").lower(): self.canonical = values.get("href", "").strip()
        if tag == "a" and values.get("href"): self.links.append(values["href"])
        if tag in {"img", "script", "source", "video"}:
            for attribute in ("src", "srcset", "poster"):
                if values.get(attribute): self.assets.extend(part.strip().split()[0] for part in values[attribute].split(","))
        if tag == "img": self.images.append(values)
        if tag == "video": self.videos.append(values)
        if tag == "source": self.sources.append(values)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title": self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title: self.title += data


def visible_text(html: str) -> str:
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    return " ".join(html.replace("&nbsp;", " ").split())


def main_visible_text(html: str) -> str:
    match = re.search(r"<main\b[^>]*>(.*?)</main>", html, flags=re.I | re.S)
    main_html = match.group(1) if match else html
    main_html = re.sub(
        r"<details\b[^>]*>\s*(<summary\b[^>]*>.*?</summary>).*?</details>",
        r"\1",
        main_html,
        flags=re.I | re.S,
    )
    return visible_text(main_html)


def local_target(page: Path, raw_url: str) -> tuple[Path | None, str]:
    parsed = urlparse(raw_url)
    if parsed.scheme in {"http", "https", "mailto", "tel", "data"} or raw_url.startswith("//"): return None, ""
    path_text = unquote(parsed.path)
    if not path_text: return page, parsed.fragment
    target = ROOT / path_text.lstrip("/") if path_text.startswith("/") else page.parent / path_text
    if path_text.endswith("/"): target = target / "index.html"
    return target.resolve(), parsed.fragment


def raster_dimensions(path: Path) -> tuple[int, int] | None:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24: return struct.unpack(">II", data[16:24])
    if data.startswith(b"\xff\xd8"):
        index = 2
        while index + 9 < len(data):
            if data[index] != 0xFF:
                index += 1
                continue
            marker = data[index + 1]
            index += 2
            if marker in {0xD8, 0xD9}: continue
            if index + 2 > len(data): break
            length = struct.unpack(">H", data[index:index + 2])[0]
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                height, width = struct.unpack(">HH", data[index + 3:index + 7])
                return width, height
            index += length
    return None


def metadata_markers(path: Path) -> list[str]:
    data = path.read_bytes()
    markers = {"EXIF": b"Exif\x00\x00", "XMP": b"http://ns.adobe.com/xap/1.0/", "Photoshop": b"Photoshop 3.0", "GPS": b"GPSInfo"}
    return [name for name, marker in markers.items() if marker in data]


def parse_pages(errors: list[str]) -> tuple[dict[Path, PageParser], dict[Path, str]]:
    pages, source = {}, {}
    for relative in EXPECTED_HTML:
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"missing HTML page: {relative.as_posix()}")
            continue
        html = path.read_text(encoding="utf-8")
        parser = PageParser(); parser.feed(html)
        pages[path.resolve()] = parser; source[relative] = html
        if not parser.title.strip() or not parser.meta.get("description"): errors.append(f"missing title or description: {relative.as_posix()}")
        if parser.h1_count != 1: errors.append(f"expected one H1 in {relative.as_posix()}, found {parser.h1_count}")
        if len(parser.ids) != len(set(parser.ids)): errors.append(f"duplicate IDs: {relative.as_posix()}")
        if relative != Path("404.html") and DOMAIN not in parser.canonical: errors.append(f"missing canonical URL: {relative.as_posix()}")
        for image in parser.images:
            for attr in ("src", "alt", "width", "height"):
                if not image.get(attr, "").strip(): errors.append(f"image missing {attr}: {relative.as_posix()} {image.get('src', '')}")
    return pages, source


def main() -> int:
    errors, warnings = [], []
    for required in [*REQUIRED_FILES, *REQUIRED_EVIDENCE, *HOMEPAGE_PREVIEWS]:
        if not (ROOT / required).is_file(): errors.append(f"missing required file: {required.as_posix()}")
    pages, html_source = parse_pages(errors)
    for page, parser in pages.items():
        for raw_url in parser.links:
            target, fragment = local_target(page, raw_url)
            if target is None: continue
            if not target.exists(): errors.append(f"broken link in {page.relative_to(ROOT)}: {raw_url}")
            elif fragment and target.suffix.lower() == ".html":
                target_parser = pages.get(target)
                if target_parser and fragment not in target_parser.ids: errors.append(f"missing fragment in {page.relative_to(ROOT)}: {raw_url}")
        for raw_url in parser.assets:
            target, _ = local_target(page, raw_url)
            if target is not None and not target.exists(): errors.append(f"missing asset in {page.relative_to(ROOT)}: {raw_url}")

    index = html_source.get(Path("index.html"), "")
    if re.search(r"aria-labelledby=\"approach-title\"|system-map\.svg", index, flags=re.I): errors.append("homepage Approach section or system map remains")
    if 'class="hero__credentials"' not in index or 'aria-label="Practice summary"' not in index: errors.append("homepage compact credentials are missing")
    if re.search(r"<dt>\s*(48|90)\s*</dt>", index): errors.append("homepage practice summary still uses 48 or 90 as a headline")
    home_figures = re.findall(r'<figure class="project-card__visual".*?</figure>', index, flags=re.S)
    home_sources = {Path(urlparse(value).path.lstrip("/")) for value in re.findall(r'<img\b[^>]*src="([^"]+)"', "".join(home_figures), flags=re.I)}
    if home_sources != HOMEPAGE_PREVIEWS: errors.append("homepage lead images do not match selected project evidence")
    if len(home_figures) != 3 or any(figure.count('<img ') != 1 or '<figcaption' not in figure for figure in home_figures): errors.append("each homepage project needs one image and a caption")
    homepage_bytes = sum((ROOT / item).stat().st_size for item in HOMEPAGE_PREVIEWS if (ROOT / item).is_file()) + (ROOT / 'index.html').stat().st_size + (ROOT / 'assets/css/site.css').stat().st_size + (ROOT / 'assets/js/site.js').stat().st_size + (ROOT / 'assets/images/common/ben-hudson-portrait-desktop-696x870.jpg').stat().st_size
    if homepage_bytes >= 1_500_000: errors.append(f"homepage preview transfer exceeds 1.5 MB: {homepage_bytes:,} bytes")

    exact_home_strings = (
        "I turn complex expertise into practical, performance-based learning.",
        "ADHD diagnostic-interview training",
        "Participatory curricula and facilitator training",
        "Training for refugee sponsorship groups",
    )
    for required in exact_home_strings:
        if required not in re.sub(r'<[^>]+>', '', index): errors.append(f"missing exact homepage text: {required}")
    if "professional audiences" in index.casefold(): errors.append("homepage proposition still contains professional audiences")
    if re.search(r"artifact-fullsize|View full-size", "\n".join(html_source.values()), flags=re.I): errors.append("visible View full-size link or obsolete artifact-fullsize markup remains")

    role_expectations = {
        Path("work/healthcare-simulation.html"): (2, 1), Path("work/life-skills-curriculum.html"): (3, 3), Path("work/refugee-sponsorship.html"): (2, 1),
    }
    for relative, (example_count, flipbook_count) in role_expectations.items():
        html = html_source.get(relative, "")
        actual_examples = len(re.findall(r'<article\b[^>]*class="[^"]*work-example(?:\s|\")', html, flags=re.I))
        actual_flipbooks = len(re.findall(r'\bdata-flipbook(?:\s|=)', html, flags=re.I))
        if actual_examples != example_count: errors.append(f"{relative.as_posix()} has {actual_examples}/{example_count} work examples")
        if actual_flipbooks != flipbook_count: errors.append(f"{relative.as_posix()} has {actual_flipbooks}/{flipbook_count} flipbooks")
    if sum(len(re.findall(r'\bdata-flipbook(?:\s|=)', html, flags=re.I)) for html in html_source.values()) != 5: errors.append("site must contain exactly five final flipbooks")

    healthcare = html_source.get(Path("work/healthcare-simulation.html"), "")
    if "<h1>ADHD diagnostic-interview training for healthcare professionals</h1>" not in healthcare: errors.append("missing exact CHEO project H1")
    for title in ("A self-directed ADHD diagnostic-interview course", "Interactive interview practice"):
        if f"<h2>{title}</h2>" not in healthcare: errors.append(f"missing CHEO example title: {title}")
    if healthcare.count('class="media-card"') != 2 or healthcare.count("<video ") != 2: errors.append("CHEO must contain two video cards")
    for required in (
        "Questioning and Rating Practice",
        "Interactive video in which learners practise choosing effective questions and assigning ratings from interview evidence.",
        "Informant Problem Solving",
        "Interactive video focused on responding to challenges that arise while interviewing an informant.",
        "Interviewer Error Analysis",
        "Six-screen flipbook showing how learners identify an interviewer error, choose a better approach and review the reasoning.",
    ):
        if required not in healthcare: errors.append(f"missing exact CHEO interaction text: {required}")
    expected_storyboard = ["Set the context", "Observe the interview", "Identify the first error", "Choose a better probe", "Review the reasoning", "Continue to feedback"]
    storyboard = re.search(r'data-flipbook-id="interviewer-error-analysis".*?</section>', healthcare, flags=re.S)
    if not storyboard or re.findall(r'<figcaption class="artifact-caption"><strong>([^<]+)</strong>', storyboard.group())[0:6] != expected_storyboard: errors.append("CHEO storyboard labels or order are incorrect")
    if healthcare.count('class="flipbook__slide"') != 6: errors.append("Interviewer Error Analysis flipbook must contain six slides")
    if "applied-instructional-design-process.svg" in healthcare: errors.append("retrospective CHEO process diagram remains visible")
    healthcare_parser = pages.get((ROOT / "work/healthcare-simulation.html").resolve())
    if healthcare_parser:
        if len(healthcare_parser.videos) != 2: errors.append("CHEO video element count is not two")
        for video in healthcare_parser.videos:
            if any(attribute not in video for attribute in ("controls", "playsinline", "preload", "width", "height", "poster")) or video.get("preload") != "metadata": errors.append("video is missing native-control or dimension attributes")
            if "autoplay" in video or "loop" in video: errors.append("video must not autoplay or loop")
        video_sources = [source for source in healthcare_parser.sources if source.get("type", "").startswith("video/")]
        if len(video_sources) != 4 or {source.get("type") for source in video_sources} != {"video/mp4", "video/webm"}: errors.append("video cards require WebM and MP4 sources")

    tfac = html_source.get(Path("work/life-skills-curriculum.html"), "")
    if "<h1>Participatory curricula and facilitator training</h1>" not in tfac: errors.append("missing exact Theatre for a Change project H1")
    for title in ("A 90-activity life-skills manual", "Learner resources and narrative activities", "Participatory methodology and facilitator tools"):
        if f"<h2>{title}</h2>" not in tfac: errors.append(f"missing TfaC example title: {title}")
    if "20 youth peer educators" in tfac: errors.append("unsupported youth peer educator wording remains")
    if tfac.count('class="flipbook__slide"') != 17: errors.append("TfaC flipbooks must contain 5, 6 and 6 slides")
    if tfac.count("life-skills-pages-") != 10: errors.append("Life Skills manual must use five full-resolution spread targets")
    if tfac.count('class="facilitation-anchor"') != 1: errors.append("Eswatini facilitation photograph must remain one standalone anchor image")

    refugee = html_source.get(Path("work/refugee-sponsorship.html"), "")
    if "<h1>Training for refugee sponsorship groups</h1>" not in refugee: errors.append("missing exact Refugee Hub project H1")
    for title in ("A Training In Four Parts", "An in-person sponsorship training manual"):
        if f"<h2>{title}</h2>" not in refugee: errors.append(f"missing Refugee Hub example title: {title}")
    if "evidence-collage--four" not in refugee: errors.append("Refugee Hub online-training collage is incomplete")
    if refugee.count('class="flipbook__slide"') != 6: errors.append("sponsorship-manual flipbook must contain six authenticated full manual pages")

    project_html = "\n".join(html_source.get(path, "") for path in role_expectations)
    triggers = re.findall(r'<a\b[^>]*class="[^"]*evidence-trigger[^"]*"[^>]*>', project_html, flags=re.I)
    if len(triggers) != 37: errors.append(f"expected 37 modal-enabled evidence images, found {len(triggers)}")
    for trigger in triggers:
        for attribute in ("href", "aria-label", "data-evidence-title", "data-evidence-caption"):
            if not re.search(rf'\b{attribute}="[^"]+"', trigger, flags=re.I): errors.append(f"evidence trigger missing {attribute}: {trigger[:120]}")
    script = (ROOT / "assets/js/site.js").read_text(encoding="utf-8")
    for marker in ('createElement("dialog")', 'Full-resolution evidence viewer', "history.pushState", "history.replaceState", 'addEventListener("popstate"', "showModal()", "touchstart", "focus({ preventScroll: true })"):
        if marker not in script: errors.append(f"modal implementation marker missing: {marker}")

    for relative, (minimum, maximum) in PAGE_WORD_TARGETS.items():
        count = len(re.findall(r"[\w’'-]+", main_visible_text(html_source.get(relative, "")), flags=re.UNICODE))
        print(f"INFO visible main words {relative.as_posix()}: {count}")
        if not minimum <= count <= maximum: errors.append(f"visible main word count outside {minimum}-{maximum}: {relative.as_posix()} ({count})")

    public_text = "\n".join(html_source.values()) + "\n" + (ROOT / "assets/css/site.css").read_text(encoding="utf-8") + "\n" + (ROOT / "assets/js/site.js").read_text(encoding="utf-8")
    for marker in FORBIDDEN_TEXT:
        if marker.casefold() in public_text.casefold(): errors.append(f"private path or credential marker in public text: {marker}")
    for obsolete in OBSOLETE_PATHS:
        if obsolete.casefold() in public_text.casefold(): errors.append(f"obsolete asset reference remains: {obsolete}")
    for item in ROOT.rglob("*"):
        if not item.is_file() or ".git" in item.parts: continue
        if item.suffix.lower() in FORBIDDEN_SUFFIXES: errors.append(f"prohibited source/archive file in public tree: {item.relative_to(ROOT).as_posix()}")
        if item.suffix.lower() == ".pdf" and item.relative_to(ROOT) != Path("assets/documents/ben-hudson-instructional-designer-resume.pdf"):
            errors.append(f"unexpected PDF in public tree: {item.relative_to(ROOT).as_posix()}")
        if item.name in {"Interactive Video Example #1.mp4", "Interactive Video Example #2.mp4"}: errors.append(f"full source video in public tree: {item.relative_to(ROOT).as_posix()}")
    for relative in NEW_RASTERS:
        path = ROOT / relative
        if not path.is_file(): continue
        if not raster_dimensions(path): errors.append(f"unreadable raster dimensions: {relative.as_posix()}")
        markers = metadata_markers(path)
        if markers: errors.append(f"nonessential metadata in {relative.as_posix()}: {', '.join(markers)}")
    for relative in REQUIRED_EVIDENCE:
        path = ROOT / relative
        if path.suffix.lower() in {".mp4", ".webm"} and path.is_file() and not 1_000_000 <= path.stat().st_size <= 5_500_000:
            warnings.append(f"video outside approximate 1-5.5 MB budget: {relative.as_posix()} ({path.stat().st_size:,} bytes)")
    for xml_path in [ROOT / "sitemap.xml", *sorted(ROOT.rglob("*.svg"))]:
        try: ET.parse(xml_path)
        except (ET.ParseError, OSError) as exc: errors.append(f"invalid XML {xml_path.relative_to(ROOT).as_posix()}: {exc}")
    try: json.loads((ROOT / "site.webmanifest").read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc: errors.append(f"invalid site.webmanifest JSON: {exc}")

    print(f"PASS {len(pages)}/{len(EXPECTED_HTML)} HTML pages checked")
    print("PASS internal links and local assets" if not any("link" in error or "asset" in error for error in errors) else "FAIL internal links or assets")
    print("PASS intended 2/3/2 project-page structure and five final flipbooks" if not any("work examples" in error or "flipbook" in error for error in errors) else "FAIL project-page structure")
    print("PASS two accessible video cards and six storyboard steps" if not any("video" in error.lower() or "storyboard" in error.lower() for error in errors) else "FAIL video or storyboard checks")
    print(f"PASS {len(REQUIRED_EVIDENCE)} required evidence derivatives checked" if not any("required file" in error for error in errors) else "FAIL required evidence")
    print("PASS source, privacy and metadata boundaries" if not any(word in error for error in errors for word in ("metadata", "source", "private", "prohibited")) else "FAIL source or privacy boundaries")
    for warning in warnings: print(f"WARN {warning}")
    for error in errors: print(f"ERROR {error}")
    if errors:
        print(f"FAIL {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"PASS 0 errors, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
