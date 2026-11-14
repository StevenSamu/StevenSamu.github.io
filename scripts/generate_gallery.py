#!/usr/bin/env python3
"""Optimize camera JPGs and generate a static HTML photo gallery."""

import argparse
from html import escape
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
START_MARKER = "<!-- GALLERY_IMAGES_START -->"
END_MARKER = "<!-- GALLERY_IMAGES_END -->"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Resize camera JPGs to 2000px web copies, remove originals after "
            "successful conversion, and update the gallery HTML."
        )
    )
    parser.add_argument(
        "image_dir",
        type=Path,
        help="Directory containing camera JPGs and its gallery HTML file",
    )
    parser.add_argument(
        "--html",
        type=Path,
        help="HTML file to update (defaults to <image_dir>/<directory-name>.html)",
    )
    parser.add_argument(
        "--featured",
        help="Optional image filename to place first and load eagerly",
    )
    parser.add_argument(
        "--featured-alt",
        help="Alt text for the featured image (defaults to generated alt text)",
    )
    parser.add_argument(
        "--keep-originals",
        action="store_true",
        help="Keep camera JPGs after creating their optimized web copies",
    )
    return parser.parse_args()


def camera_jpgs(image_dir: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in image_dir.iterdir()
            if path.is_file()
            and path.suffix.lower() in {".jpg", ".jpeg"}
            and not path.stem.lower().endswith("-web")
        ),
        key=lambda path: path.name.lower(),
    )


def web_jpgs(image_dir: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in image_dir.iterdir()
            if path.is_file()
            and path.suffix.lower() == ".jpg"
            and path.stem.lower().endswith("-web")
        ),
        key=lambda path: path.name.lower(),
    )


def optimize_image(source: Path) -> Path:
    output = source.with_name(f"{source.stem}-web.jpg")
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{source.stem}-", suffix="-web.jpg", dir=source.parent, delete=False
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

        subprocess.run(
            [
                "sips",
                "-s",
                "format",
                "jpeg",
                "-s",
                "formatOptions",
                "82",
                "-Z",
                "2000",
                str(source),
                "--out",
                str(temporary_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
            raise RuntimeError(f"Image conversion produced an empty file for {source.name}")
        temporary_path.replace(output)
        return output
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def main() -> None:
    args = parse_args()
    image_dir = args.image_dir if args.image_dir.is_absolute() else ROOT / args.image_dir
    image_dir = image_dir.resolve()
    html_file = args.html or (image_dir / f"{image_dir.name.lower()}.html")
    if not html_file.is_absolute():
        html_file = ROOT / html_file
    html_file = html_file.resolve()

    if not image_dir.is_dir():
        raise SystemExit(f"Image directory does not exist: {image_dir}")
    if not html_file.is_file():
        raise SystemExit(f"Gallery HTML file does not exist: {html_file}")

    html = html_file.read_text(encoding="utf-8")
    if html.count(START_MARKER) != 1 or html.count(END_MARKER) != 1:
        raise SystemExit(
            f"Expected exactly one {START_MARKER} and one {END_MARKER} in {html_file}"
        )

    originals = camera_jpgs(image_dir)
    for original in originals:
        try:
            optimize_image(original)
        except (OSError, subprocess.CalledProcessError, RuntimeError) as error:
            raise SystemExit(f"Could not optimize {original.name}: {error}") from error

    images = web_jpgs(image_dir)
    if not images:
        raise SystemExit(f"No camera JPGs or *-web.jpg images found in {image_dir}")
    featured = [image for image in images if image.name == args.featured]
    if args.featured and not featured:
        raise SystemExit(f"Featured image not found in {image_dir}: {args.featured}")
    ordered_images = featured + [image for image in images if image not in featured]
    gallery_name = image_dir.name

    figures = []
    for index, image in enumerate(ordered_images):
        filename = escape(image.name, quote=True)
        description = escape(image.stem.removesuffix("-web"), quote=True)
        alt = escape(args.featured_alt, quote=True) if index == 0 and args.featured_alt else (
            f"{escape(gallery_name)} photograph {description}"
        )
        if index == 0 and args.featured:
            figures.append(
                f'            <figure><img src="{filename}" alt="{alt}" '
                'fetchpriority="high"></figure>'
            )
        else:
            figures.append(
                f'            <figure><img src="{filename}" alt="{alt}" '
                'loading="lazy" decoding="async"></figure>'
            )

    start = html.index(START_MARKER) + len(START_MARKER)
    end = html.index(END_MARKER, start)
    html = html[:start] + "\n" + "\n".join(figures) + "\n            " + html[end:]

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=html_file.parent, delete=False
    ) as temporary_html:
        temporary_html.write(html)
        temporary_html_path = Path(temporary_html.name)
    temporary_html_path.replace(html_file)

    if not args.keep_originals:
        for original in originals:
            original.unlink()

    print(f"Optimized {len(originals)} camera JPGs")
    if not args.keep_originals:
        print("Removed the camera JPG originals after successful conversion")
    try:
        display_path = html_file.relative_to(ROOT)
    except ValueError:
        display_path = html_file
    print(f"Generated {len(ordered_images)} gallery entries in {display_path}")


if __name__ == "__main__":
    main()