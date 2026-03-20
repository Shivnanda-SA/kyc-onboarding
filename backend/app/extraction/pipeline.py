from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from PIL import Image, ImageEnhance, ImageOps
from docx import Document as DocxDocument
import re

logger = logging.getLogger(__name__)

# Resolve Tesseract OCR executable in a robust way.
# We try:
# - env var (TESSERACT_CMD / TESSERACT_PATH)
# - PATH via `shutil.which`
# - common Windows install locations
TESSERACT_AVAILABLE = False
pytesseract = None  # type: ignore[assignment]
try:
    import pytesseract as _pytesseract  # type: ignore
    pytesseract = _pytesseract  # type: ignore
except Exception:
    pytesseract = None

if pytesseract is not None:
    candidates: list[str] = []
    env_cmd = os.environ.get("TESSERACT_CMD") or os.environ.get("TESSERACT_PATH")
    if env_cmd:
        candidates.append(env_cmd)

    which_cmd = shutil.which("tesseract")
    if which_cmd:
        candidates.append(which_cmd)

    # Common default install folders on Windows
    candidates.extend(
        [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Tesseract-OCR\tesseract.exe",
        ]
    )

    for cmd in candidates:
        try:
            if cmd and Path(cmd).exists():
                pytesseract.pytesseract.tesseract_cmd = str(cmd)
                # Validate it actually works
                _ = pytesseract.get_tesseract_version()
                TESSERACT_AVAILABLE = True
                break
        except Exception:
            continue

if not TESSERACT_AVAILABLE:
    logger.warning("Tesseract OCR not found. OCR functionality will be disabled.")


@dataclass(frozen=True)
class ExtractedText:
    text: str
    method: str  # pdf_text | ocr | docx | txt


def _extract_pdf_text(path: Path) -> str:
    parts: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            if t.strip():
                parts.append(t)
    return "\n\n".join(parts).strip()


def _ocr_pdf(path: Path) -> str:
    if not TESSERACT_AVAILABLE:
        logger.warning("OCR requested but Tesseract not available for PDF: %s", path)
        return ""
    parts: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            # Higher resolution improves OCR accuracy for small text (e.g., PAN).
            img = page.to_image(resolution=400).original
            if not isinstance(img, Image.Image):
                img = Image.fromarray(img)
            img = _preprocess_for_ocr(img)
            parts.append(pytesseract.image_to_string(img))
    return "\n\n".join(parts).strip()


def _ocr_image(path: Path) -> str:
    if not TESSERACT_AVAILABLE:
        logger.warning("OCR requested but Tesseract not available for image: %s", path)
        return ""
    img = Image.open(str(path))
    img = _preprocess_for_ocr(img)
    return pytesseract.image_to_string(img).strip()


def _preprocess_for_ocr(img: Image.Image) -> Image.Image:
    # Common preprocessing for scanned docs:
    # - grayscale
    # - upsample (helps OCR for small labels)
    # - increase contrast
    # - simple threshold to reduce background noise
    g = ImageOps.grayscale(img)
    # Upscale 2x using bicubic; keeps edges sharper than nearest.
    w, h = g.size
    g = g.resize((w * 2, h * 2), resample=Image.BICUBIC)
    g = ImageEnhance.Contrast(g).enhance(2.0)
    g = ImageEnhance.Sharpness(g).enhance(1.5)
    # Threshold at mid-point; helps with blue/gray scanned backgrounds.
    g = g.point(lambda p: 255 if p > 170 else 0)
    return g


def _extract_docx(path: Path) -> str:
    doc = DocxDocument(str(path))
    parts: list[str] = []
    
    # Extract from paragraphs
    for p in doc.paragraphs:
        if p.text and p.text.strip():
            parts.append(p.text.strip())
    
    # Extract from tables (important for directors lists)
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
            if row_text:
                parts.append(row_text)
    
    return "\n".join(parts).strip()


def extract_text_from_file(path: Path) -> ExtractedText:
    ext = path.suffix.lower()
    if ext == ".txt":
        return ExtractedText(text=path.read_text(encoding="utf-8", errors="ignore"), method="txt")
    if ext == ".docx":
        return ExtractedText(text=_extract_docx(path), method="docx")
    if ext in {".png", ".jpg", ".jpeg"}:
        return ExtractedText(text=_ocr_image(path), method="ocr")
    if ext == ".pdf":
        embedded = _extract_pdf_text(path)
        embedded_clean = "".join(ch for ch in embedded.upper() if ch.isalnum())
        pan_like = re.search(r"[A-Z]{5}\d{4}[A-Z]", embedded_clean) is not None

        # If embedded text already contains a PAN-like token, trust it.
        # Otherwise, the PDF is likely scanned/image-based; OCR it.
        if len(embedded) >= 50 and pan_like:
            return ExtractedText(text=embedded, method="pdf_text")

        if TESSERACT_AVAILABLE:
            ocr_text = _ocr_pdf(path)
            if ocr_text.strip():
                return ExtractedText(text=ocr_text, method="ocr")

        logger.warning(f"PDF {path.name} did not yield PAN-like embedded text; OCR returned empty/insufficient.")
        return ExtractedText(text=embedded, method="pdf_text")
    raise ValueError(f"Unsupported file extension: {ext}")

