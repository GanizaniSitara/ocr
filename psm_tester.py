#!/usr/bin/env python3
"""
PSM Testing Script for Your Use Cases
Tests the recommended PSM modes on your images.
"""

import pytesseract
from PIL import Image
import sys
from pathlib import Path

def test_recommended_psms(image_path: str, use_case: str = "both"):
    """Test recommended PSMs for magazine or controls testing."""
    
    if use_case == "magazine":
        psms_to_test = [11, 4, 7, 8, 3]  # Recommended for magazines
        print("Testing MAGAZINE ARCHIVING PSMs")
    elif use_case == "controls":
        psms_to_test = [11, 8, 7, 6, 5]  # Recommended for UI controls
        print("Testing CONTROLS TESTING PSMs")
    else:  # both
        psms_to_test = [11, 7, 8, 4, 6, 5, 3]  # Combined approach
        print("Testing COMBINED APPROACH PSMs")
    
    image = Image.open(image_path)
    print(f"Image: {Path(image_path).name}")
    print(f"Size: {image.size}")
    print("=" * 60)
    
    results = []
    
    for psm in psms_to_test:
        try:
            config = f"--psm {psm} --oem 3"
            text = pytesseract.image_to_string(image, config=config)
            text_clean = text.strip()
            
            print(f"PSM {psm:2d}: {len(text_clean):4d} chars | {repr(text_clean[:60])}...")
            
            results.append({
                'psm': psm,
                'text': text_clean,
                'length': len(text_clean)
            })
            
        except Exception as e:
            print(f"PSM {psm:2d}: ERROR - {e}")
    
    # Find best result
    if results:
        best = max(results, key=lambda x: x['length'])
        print(f"\nBEST: PSM {best['psm']} with {best['length']} characters")
        print(f"Text: {repr(best['text'][:200])}...")
    
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python psm_tester.py <image_path> [magazine|controls|both]")
        sys.exit(1)
    
    image_path = sys.argv[1]
    use_case = sys.argv[2] if len(sys.argv) > 2 else "both"
    
    test_recommended_psms(image_path, use_case)
