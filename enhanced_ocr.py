#!/usr/bin/env python3
"""
Enhanced OCR script with multiple strategies for better text recognition.
Specifically designed to handle challenging text recognition cases.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse

import pytesseract
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import cv2
import numpy as np

IMG_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"}


def advanced_preprocess(img: Image.Image, strategy: str = "default") -> Image.Image:
    """Apply advanced preprocessing strategies."""
    # Convert PIL to OpenCV format
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    if strategy == "high_contrast":
        # High contrast + denoising
        img_cv = cv2.convertScaleAbs(img_cv, alpha=1.5, beta=10)
        img_cv = cv2.bilateralFilter(img_cv, 9, 75, 75)
        
    elif strategy == "morphology":
        # Morphological operations for text cleanup
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        kernel = np.ones((2,2), np.uint8)
        img_cv = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_GRAY2BGR)
        
    elif strategy == "adaptive_threshold":
        # Adaptive thresholding
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        img_cv = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 11, 2)
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_GRAY2BGR)
        
    elif strategy == "edge_enhance":
        # Edge enhancement
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        img_cv = cv2.addWeighted(gray, 0.8, edges, 0.2, 0)
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_GRAY2BGR)
    
    # Convert back to PIL
    return Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))


def multi_strategy_ocr(image_path: Path, target_text: Optional[str] = None) -> Dict:
    """Try multiple OCR strategies and return the best result."""
    img = Image.open(image_path)
    
    # Define multiple OCR strategies
    charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?;:()[]{}'-_@#$%&*+=/<>| "
    
    strategies = [
        # Strategy 1: Minimal preprocessing with different PSM modes
        {
            'name': 'minimal_psm6',
            'preprocess': lambda x: ImageOps.grayscale(x),
            'config': f'--psm 6 -c tessedit_char_whitelist={charset}'
        },
        {
            'name': 'minimal_psm8',
            'preprocess': lambda x: ImageOps.grayscale(x),
            'config': f'--psm 8 -c tessedit_char_whitelist={charset}'
        },
        {
            'name': 'minimal_psm3',
            'preprocess': lambda x: ImageOps.grayscale(x),
            'config': f'--psm 3 -c tessedit_char_whitelist={charset}'
        },
        # Strategy 2: High contrast
        {
            'name': 'high_contrast',
            'preprocess': lambda x: advanced_preprocess(x, "high_contrast"),
            'config': f'--psm 6 -c tessedit_char_whitelist={charset}'
        },
        # Strategy 3: No character whitelist - sometimes helps with special cases
        {
            'name': 'no_whitelist_psm6',
            'preprocess': lambda x: ImageOps.grayscale(x),
            'config': '--psm 6'
        },
        {
            'name': 'no_whitelist_psm3',
            'preprocess': lambda x: ImageOps.grayscale(x),
            'config': '--psm 3'
        },
        # Strategy 4: Traditional preprocessing with different settings
        {
            'name': 'traditional_high_thresh',
            'preprocess': lambda x: x.convert('L').point(lambda p: 255 if p > 180 else 0),
            'config': f'--psm 6 -c tessedit_char_whitelist={charset}'
        },
        # Strategy 5: Enhanced contrast
        {
            'name': 'enhanced_contrast',
            'preprocess': lambda x: ImageEnhance.Contrast(ImageOps.grayscale(x)).enhance(2.0),
            'config': '--psm 6'
        },
        # Strategy 6: Simple preprocessing variations
        {
            'name': 'threshold_150',
            'preprocess': lambda x: x.convert('L').point(lambda p: 255 if p > 150 else 0),
            'config': '--psm 6'
        },
        {
            'name': 'threshold_120',
            'preprocess': lambda x: x.convert('L').point(lambda p: 255 if p > 120 else 0),
            'config': '--psm 6'
        }
    ]
    
    results = []
    
    for strategy in strategies:
        try:
            processed_img = strategy['preprocess'](img.copy())
            text = pytesseract.image_to_string(processed_img, config=strategy['config'])
            
            # Calculate score based on text length and target match
            score = len(text.strip())
            if target_text:
                # Bonus for containing target words
                target_words = target_text.upper().split()
                found_words = sum(1 for word in target_words if word in text.upper())
                score += found_words * 100
            
            results.append({
                'strategy': strategy['name'],
                'text': text.strip(),
                'score': score,
                'length': len(text.strip())
            })
            
        except Exception as e:
            print(f"Error with strategy {strategy['name']}: {e}", file=sys.stderr)
    
    # Sort by score (descending)
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return {
        'source': str(image_path),
        'best_result': results[0] if results else None,
        'all_results': results
    }


def process_single_image(image_path: str, target_text: str = None) -> None:
    """Process a single image and display results."""
    path = Path(image_path)
    if not path.exists():
        print(f"Image not found: {image_path}")
        return
    
    print(f"Processing: {path.name}")
    print("=" * 50)
    
    result = multi_strategy_ocr(path, target_text)
    
    if result['best_result']:
        print(f"Best strategy: {result['best_result']['strategy']}")
        print(f"Score: {result['best_result']['score']}")
        print(f"Text length: {result['best_result']['length']}")
        print("\nExtracted text:")
        print("-" * 30)
        print(result['best_result']['text'])
        print("-" * 30)
        
        # Show all results for comparison
        print(f"\nAll results ({len(result['all_results'])} strategies):")
        for i, res in enumerate(result['all_results'][:5]):  # Show top 5
            print(f"{i+1}. {res['strategy']} (score: {res['score']}, len: {res['length']})")
            if target_text:
                # Highlight target text matches
                text_upper = res['text'].upper()
                target_upper = target_text.upper()
                if target_upper in text_upper:
                    print(f"   ✓ Contains target text!")
                else:
                    print(f"   ✗ Missing target text")
    else:
        print("No results obtained from any strategy")


def main():
    parser = argparse.ArgumentParser(description="Enhanced OCR with multiple strategies")
    parser.add_argument("image", help="Path to image file")
    parser.add_argument("--target", help="Target text to look for (improves scoring)")
    parser.add_argument("--save", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    result = multi_strategy_ocr(Path(args.image), args.target)
    
    if args.save:
        with open(args.save, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {args.save}")
    else:
        process_single_image(args.image, args.target)


if __name__ == "__main__":
    main()