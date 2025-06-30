#!/usr/bin/env python3
"""
pytesseract_harness.py
CLI harness for batch OCR preprocessing.

Dependencies:
    pip install pillow pytesseract

Example:
    python pytesseract_harness.py slides/ img1.png -o ocr.jsonl --lang eng --psm 6 --grayscale --threshold 140 --sharpen
"""

import argparse
import json
import sys
from pathlib import Path

import pytesseract
from PIL import Image, ImageOps, ImageFilter, ImageEnhance

IMG_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}


def preprocess_image(
    img: Image.Image,
    grayscale: bool,
    threshold: int | None,
    sharpen: bool,
    contrast: float | None,
) -> Image.Image:
    if grayscale:
        img = ImageOps.grayscale(img)
    if threshold is not None:
        img = img.point(lambda p: 255 if p > threshold else 0)
    if sharpen:
        img = img.filter(ImageFilter.SHARPEN)
    if contrast is not None:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    return img


def ocr_file(
    path: Path,
    lang: str,
    psm: int,
    grayscale: bool,
    threshold: int | None,
    sharpen: bool,
    contrast: float | None,
) -> str:
    img = Image.open(path)
    img = preprocess_image(img, grayscale, threshold, sharpen, contrast)
    return pytesseract.image_to_string(img, lang=lang, config=f"--psm {psm}")


def gather_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            files.extend(f for f in p.rglob("*") if f.suffix.lower() in IMG_EXTS)
        elif p.is_file() and p.suffix.lower() in IMG_EXTS:
            files.append(p)
    return files


def main(argv: list[str]) -> None:
    ap = argparse.ArgumentParser(description="Batch OCR harness using pytesseract.")
    ap.add_argument("inputs", nargs="+", help="Image files or directories")
    ap.add_argument("-o", "--output", default="ocr.jsonl", help="Output JSONL file")
    ap.add_argument("--lang", default="eng", help="Tesseract language code(s)")
    ap.add_argument("--psm", type=int, default=3, help="Tesseract page segmentation mode")
    ap.add_argument("--grayscale", action="store_true", help="Convert to grayscale first")
    ap.add_argument("--threshold", type=int, help="Global threshold (0-255)")
    ap.add_argument("--sharpen", action="store_true", help="Sharpen image")
    ap.add_argument("--contrast", type=float, help="Contrast factor, e.g. 1.4")
    args = ap.parse_args(argv)

    files = gather_files(args.inputs)
    with open(args.output, "w", encoding="utf-8") as out:
        for f in files:
            try:
                text = ocr_file(
                    f,
                    args.lang,
                    args.psm,
                    args.grayscale,
                    args.threshold,
                    args.sharpen,
                    args.contrast,
                )
                out.write(json.dumps({"source": str(f), "text": text.strip()}) + "\n")
            except Exception as e:
                print(f"Error processing {f}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
