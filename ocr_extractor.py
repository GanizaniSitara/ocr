#!/usr/bin/env python3
"""
OCR extractor with bounding box coordinates for PrivateEye magazine archiving.
Extracts text and creates clickable regions for web interface.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pytesseract
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import pandas as pd

IMG_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}


def preprocess_image(
    img: Image.Image,
    grayscale: bool = True,
    threshold: int = 150,
    sharpen: bool = False,
    contrast: float = 1.5,
    denoise: bool = True,
) -> Image.Image:
    """Preprocess image for better OCR results."""
    # Convert to grayscale first for consistent processing
    if grayscale:
        img = ImageOps.grayscale(img)
    
    # Enhance contrast before other operations
    if contrast is not None:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    
    # Apply noise reduction
    if denoise:
        img = img.filter(ImageFilter.MedianFilter(size=3))
    
    # Apply threshold for better text separation
    if threshold is not None:
        img = img.point(lambda p: 255 if p > threshold else 0)
    
    # Optional sharpening (can sometimes hurt OCR)
    if sharpen:
        img = img.filter(ImageFilter.SHARPEN)
    
    return img


def extract_text_with_boxes(
    image_path: Path,
    lang: str = "eng",
    psm: int = 3,
    preprocess: bool = True
) -> Dict:
    """Extract text with bounding box coordinates from image."""
    img = Image.open(image_path)
    original_img = img.copy()
    
    # Try multiple preprocessing approaches
    preprocessing_configs = [
        # Minimal preprocessing - often best for clean scans
        {'grayscale': True, 'threshold': None, 'contrast': 1.0, 'denoise': False, 'sharpen': False},
        # High contrast with threshold
        {'grayscale': True, 'threshold': 150, 'contrast': 1.5, 'denoise': True, 'sharpen': False},
        # Conservative approach
        {'grayscale': True, 'threshold': 180, 'contrast': 1.2, 'denoise': True, 'sharpen': False},
    ]
    
    best_result = None
    best_word_count = 0
    
    for config in preprocessing_configs:
        try:
            processed_img = preprocess_image(original_img.copy(), **config) if preprocess else original_img
            
            # Use better OCR configuration
            whitelist_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?;:()[]{}\"'-_@#$%&*+=/<>| "
            ocr_config = f"--psm {psm} -c tessedit_char_whitelist={whitelist_chars}"
            
            # Get detailed OCR data with bounding boxes
            data = pytesseract.image_to_data(
                processed_img, 
                lang=lang, 
                config=ocr_config,
                output_type=pytesseract.Output.DICT
            )
            
            # Filter out empty text and low confidence results
            words = []
            for i in range(len(data['text'])):
                text = data['text'][i].strip()
                conf = int(data['conf'][i])
                
                # More strict filtering
                if text and len(text) > 0 and conf > 50:
                    # Filter out likely OCR errors
                    if not all(c in '!@#$%^&*()_+=[]{}|\\:";\'<>?,./' for c in text):
                        words.append({
                            'text': text,
                            'confidence': conf,
                            'left': data['left'][i],
                            'top': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i],
                            'level': data['level'][i],
                            'page_num': data['page_num'][i],
                            'block_num': data['block_num'][i],
                            'par_num': data['par_num'][i],
                            'line_num': data['line_num'][i],
                            'word_num': data['word_num'][i]
                        })
            
            # Get full text for search/indexing
            full_text = pytesseract.image_to_string(processed_img, lang=lang, config=ocr_config)
            
            result = {
                'source': str(image_path),
                'image_width': original_img.width,
                'image_height': original_img.height,
                'full_text': full_text.strip(),
                'words': words,
                'word_count': len(words),
                'preprocessing_config': config
            }
            
            # Use the result with the most detected words
            if len(words) > best_word_count:
                best_result = result
                best_word_count = len(words)
                
        except Exception as e:
            print(f"Error with preprocessing config {config}: {e}", file=sys.stderr)
            continue
    
    return best_result if best_result else {
        'source': str(image_path),
        'image_width': original_img.width,
        'image_height': original_img.height,
        'full_text': '',
        'words': [],
        'word_count': 0,
        'error': 'All preprocessing approaches failed'
    }


def process_magazine_pages(input_dir: Path = None) -> List[Dict]:
    """Process all PNG files in directory and extract OCR data."""
    if input_dir is None:
        input_dir = Path(".")
    
    png_files = list(input_dir.glob("*.png"))
    results = []
    
    for png_file in sorted(png_files):
        try:
            print(f"Processing {png_file.name}...", file=sys.stderr)
            ocr_data = extract_text_with_boxes(png_file)
            results.append(ocr_data)
        except Exception as e:
            print(f"Error processing {png_file}: {e}", file=sys.stderr)
    
    return results


def save_ocr_data(ocr_results: List[Dict], output_file: Path = Path("magazine_ocr.json")):
    """Save OCR results to JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(ocr_results, f, indent=2, ensure_ascii=False)
    print(f"Saved OCR data to {output_file}")


if __name__ == "__main__":
    # Process all PNG files in current directory
    ocr_results = process_magazine_pages()
    save_ocr_data(ocr_results)