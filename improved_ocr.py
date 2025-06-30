#!/usr/bin/env python3
"""
Improved OCR script using your existing setup with better preprocessing.
"""

import sys
from pathlib import Path
import argparse
import pytesseract
from PIL import Image, ImageOps, ImageFilter, ImageEnhance


def preprocess_for_text_clarity(img: Image.Image, strategy: str = "default") -> Image.Image:
    """Apply preprocessing specifically to improve text clarity."""
    
    if strategy == "high_contrast_threshold":
        # Convert to grayscale
        img = ImageOps.grayscale(img)
        # Increase contrast significantly
        img = ImageEnhance.Contrast(img).enhance(2.5)
        # Apply binary threshold
        img = img.point(lambda p: 255 if p > 140 else 0)
        
    elif strategy == "gentle_enhancement":
        img = ImageOps.grayscale(img)
        img = ImageEnhance.Contrast(img).enhance(1.3)
        img = img.point(lambda p: 255 if p > 160 else 0)
        
    elif strategy == "sharp_threshold":
        img = ImageOps.grayscale(img)
        img = img.filter(ImageFilter.SHARPEN)
        img = img.point(lambda p: 255 if p > 130 else 0)
        
    elif strategy == "denoise_threshold":
        img = ImageOps.grayscale(img)
        # Apply a slight blur to reduce noise
        img = img.filter(ImageFilter.MedianFilter(size=3))
        img = ImageEnhance.Contrast(img).enhance(1.8)
        img = img.point(lambda p: 255 if p > 150 else 0)
        
    elif strategy == "minimal":
        # Just grayscale conversion
        img = ImageOps.grayscale(img)
        
    else:  # default
        img = ImageOps.grayscale(img)
        img = ImageEnhance.Contrast(img).enhance(1.5)
        img = img.point(lambda p: 255 if p > 150 else 0)
    
    return img


def extract_text_multiple_ways(image_path: Path, target_text: str = None) -> dict:
    """Try multiple preprocessing and OCR configurations."""
    
    img = Image.open(image_path)
    
    # Define different approaches
    approaches = [
        {"name": "minimal", "psm": 6},
        {"name": "minimal", "psm": 3},
        {"name": "minimal", "psm": 8},
        {"name": "default", "psm": 6},
        {"name": "default", "psm": 3},
        {"name": "high_contrast_threshold", "psm": 6},
        {"name": "high_contrast_threshold", "psm": 3},
        {"name": "gentle_enhancement", "psm": 6},
        {"name": "sharp_threshold", "psm": 6},
        {"name": "denoise_threshold", "psm": 6},
    ]
    
    results = []
    
    for approach in approaches:
        try:
            # Preprocess image
            processed_img = preprocess_for_text_clarity(img.copy(), approach["name"])
            
            # Try OCR with this configuration
            config = f"--psm {approach['psm']}"
            text = pytesseract.image_to_string(processed_img, config=config)
            
            # Score the result
            text_clean = text.strip()
            score = len(text_clean)
            
            # Bonus for target text presence
            if target_text and target_text.upper() in text_clean.upper():
                score += 1000
                
            # Check for partial matches
            if target_text:
                target_words = target_text.upper().split()
                found_words = sum(1 for word in target_words if word in text_clean.upper())
                score += found_words * 50
            
            results.append({
                "strategy": f"{approach['name']}_psm{approach['psm']}",
                "text": text_clean,
                "score": score,
                "length": len(text_clean),
                "has_target": target_text.upper() in text_clean.upper() if target_text else False
            })
            
        except Exception as e:
            print(f"Error with {approach['name']}_psm{approach['psm']}: {e}", file=sys.stderr)
    
    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "source": str(image_path),
        "results": results
    }


def main():
    parser = argparse.ArgumentParser(description="Improved OCR with better preprocessing")
    parser.add_argument("image", help="Path to image file")
    parser.add_argument("--target", help="Target text to look for")
    parser.add_argument("--all", action="store_true", help="Show all results, not just the best")
    
    args = parser.parse_args()
    
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Image not found: {args.image}")
        return
    
    print(f"Processing: {image_path.name}")
    print("=" * 60)
    
    result = extract_text_multiple_ways(image_path, args.target)
    
    if not result["results"]:
        print("No text extracted by any method.")
        return
    
    # Show best result
    best = result["results"][0]
    print(f"Best result: {best['strategy']} (score: {best['score']})")
    if args.target:
        print(f"Contains target: {'✓' if best['has_target'] else '✗'}")
    print(f"Text length: {best['length']}")
    print("\nExtracted text:")
    print("-" * 40)
    print(best["text"])
    print("-" * 40)
    
    # Show comparison
    if args.all:
        print(f"\nAll results ({len(result['results'])}):")
        for i, res in enumerate(result["results"]):
            target_indicator = "✓" if res["has_target"] else "✗" if args.target else ""
            print(f"{i+1:2d}. {res['strategy']:<25} score:{res['score']:4d} len:{res['length']:3d} {target_indicator}")
    else:
        print(f"\nTop 5 results:")
        for i, res in enumerate(result["results"][:5]):
            target_indicator = "✓" if res["has_target"] else "✗" if args.target else ""
            print(f"{i+1}. {res['strategy']:<25} score:{res['score']:4d} len:{res['length']:3d} {target_indicator}")


if __name__ == "__main__":
    main()