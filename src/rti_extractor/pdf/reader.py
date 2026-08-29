import hashlib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import pymupdf


class TextLayer(StrEnum):
    NATIVE = "native"
    OCR = "ocr"
    NONE = "none"


@dataclass(frozen=True)
class PdfInfo:
    path: Path
    page_count: int
    text_layer: TextLayer
    text_by_page: list[str]
    rotation_by_page: list[int]

    @property
    def needs_images(self) -> bool:
        return self.text_layer is not TextLayer.NATIVE


def sha256_file(path: Path) -> str:
    """Fingerprint a file, reading it in chunks so large scans don't fill memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _has_full_page_image(page: Any) -> bool:
    """True when a single image covers most of the page - the fingerprint of a scan."""
    page_area = abs(page.rect.width * page.rect.height)
    if page_area == 0:
        return False
    return any(
        abs(pymupdf.Rect(image["bbox"]).get_area()) > 0.6 * page_area
        for image in page.get_image_info()
    )


def inspect(path: Path) -> PdfInfo:
    """Read a PDF's structure without changing it."""
    with pymupdf.open(path) as doc:
        page_count = doc.page_count
        text_by_page = [page.get_text().strip() for page in doc]
        rotation_by_page = [page.rotation for page in doc]
        scanned_pages = [_has_full_page_image(page) for page in doc]

    chars = sum(len(text) for text in text_by_page)
    if chars <= 100 * page_count:
        text_layer = TextLayer.NONE
    elif any(scanned_pages):
        text_layer = TextLayer.OCR
    else:
        text_layer = TextLayer.NATIVE

    return PdfInfo(
        path=path,
        page_count=page_count,
        text_layer=text_layer,
        text_by_page=text_by_page,
        rotation_by_page=rotation_by_page,
    )


def render_pages(path: Path, out_dir: Path, dpi: int = 200) -> list[Path]:
    """Turn every page into a PNG. Returns the files written, in page order."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with pymupdf.open(path) as doc:
        for number, page in enumerate(doc, start=1):
            pixmap = page.get_pixmap(dpi=dpi)
            destination = out_dir / f"page_{number:03d}.png"
            pixmap.save(destination)
            written.append(destination)
    return written
