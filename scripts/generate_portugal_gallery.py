#!/usr/bin/env python3
"""Generate the Portugal gallery figures from its optimized JPG files."""

from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GALLERY_DIR = ROOT / "images" / "Portugal"
HTML_FILE = GALLERY_DIR / "portugal.html"
START_MARKER = "            <!-- GALLERY_IMAGES_START -->"
END_MARKER = "            <!-- GALLERY_IMAGES_END -->"
FEATURED_IMAGE = "R0000463-web.jpg"


def main() -> None:
    images = sorted(GALLERY_DIR.glob("*-web.jpg"))
    if not images:
        raise SystemExit(f"No optimized JPGs found in {GALLERY_DIR}")

    featured = [image for image in images if image.name == FEATURED_IMAGE]
    ordered_images = featured + [image for image in images if image.name != FEATURED_IMAGE]

    figures = []
    for index, image in enumerate(ordered_images):
        filename = escape(image.name, quote=True)
        if index == 0:
            figures.append(
                f'            <figure><img src="{filename}" alt="Jeep in Portugal" '
                'fetchpriority="high"></figure>'
            )
        else:
            description = escape(image.stem.removesuffix("-web"), quote=True)
            figures.append(
                f'            <figure><img src="{filename}" '
                f'alt="Portugal photograph {description}" loading="lazy" '
                'decoding="async"></figure>'
            )

    html = HTML_FILE.read_text(encoding="utf-8")
    if html.count(START_MARKER) != 1 or html.count(END_MARKER) != 1:
        raise SystemExit("Expected exactly one gallery start marker and one end marker")

    start = html.index(START_MARKER) + len(START_MARKER)
    end = html.index(END_MARKER, start)
    html = html[:start] + "\n" + "\n".join(figures) + "\n            " + html[end:]
    HTML_FILE.write_text(html, encoding="utf-8")
    print(f"Generated {len(ordered_images)} Portugal gallery entries in {HTML_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
