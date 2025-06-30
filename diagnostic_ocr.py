#!/usr/bin/env python3
"""
Diagnostic script to check Tesseract version, configuration, and test different approaches.
"""

import pytesseract
import sys
from PIL import Image
from pathlib import Path


def check_tesseract_info():
    """Check Tesseract version and available languages."""
    print("=== TESSERACT DIAGNOSTIC INFO ===")
    
    try:
        version = pytesseract.get_tesseract_version()
        print(f"Tesseract version: {version}")
    except Exception as e:
        print(f"Error getting version: {e}")
    
    try:
        langs = pytesseract.get_languages()
        print(f"Available languages: {langs}")
    except Exception as e:
        print(f"Error getting languages: {e}")
    
    # Check if we can find tesseract executable
    try:
        cmd = pytesseract.pytesseract.tesseract_cmd
        print(f"Tesseract executable path: {cmd}")
    except Exception as e:
        print(f"Error getting executable path: {e}")


def test_simple_ocr(image_path: str):
    """Test basic OCR without any preprocessing."""
    print(f"\n=== TESTING SIMPLE OCR ON {image_path} ===")
    
    try:
        img = Image.open(image_path)
        print(f"Image size: {img.size}")
        print(f"Image mode: {img.mode}")
        
        # Most basic OCR - no config
        text1 = pytesseract.image_to_string(img)
        print(f"\nBasic OCR (no config):")
        print(f"Length: {len(text1.strip())}")
        print(f"Text preview: {repr(text1[:200])}")
        
        # Try with PSM 3 (default page segmentation)
        text2 = pytesseract.image_to_string(img, config='--psm 3')
        print(f"\nPSM 3 (fully automatic):")
        print(f"Length: {len(text2.strip())}")
        print(f"Text preview: {repr(text2[:200])}")
        
        # Try with PSM 6 (single uniform text block)
        text3 = pytesseract.image_to_string(img, config='--psm 6')
        print(f"\nPSM 6 (single block):")
        print(f"Length: {len(text3.strip())}")
        print(f"Text preview: {repr(text3[:200])}")
        
        # Show basic comparison
        print(f"\nComparison of text lengths:")
        for i, text in enumerate([text1, text2, text3], 1):
            print(f"Method {i}: {len(text.strip())} characters")
        
    except Exception as e:
        print(f"Error in simple OCR test: {e}")


def test_with_preprocessing(image_path: str):
    """Test with minimal preprocessing."""
    print(f"\n=== TESTING WITH PREPROCESSING ===")
    
    try:
        img = Image.open(image_path)
        
        # Convert to grayscale
        gray_img = img.convert('L')
        text = pytesseract.image_to_string(gray_img, config='--psm 6')
        print(f"Grayscale conversion:")
        print(f"Length: {len(text.strip())}")
        print(f"Text preview: {repr(text[:200])}")
        
        # Try different DPI settings
        # Some scans might need DPI specification
        configs = [
            '--psm 3 --oem 3',  # OPTIMAL: Use LSTM OCR Engine only with auto page segmentation
            '--psm 6 --oem 3',  # LSTM with single block
            '--psm 3 --oem 1',  # Auto segmentation with LSTM + Legacy
            '--psm 6 --oem 1',  # Single block with LSTM + Legacy
            '--psm 3',          # Auto segmentation, default OEM
            '--psm 6',          # Single block, default OEM
            '--psm 3 --oem 3 --dpi 300',  # Optimal + DPI
            '--psm 3 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?;:()[]{}\'\\"-_@#$%&*+=/<>| ',
        ]
        
        for config in configs:
            try:
                result = pytesseract.image_to_string(gray_img, config=config)
                print(f"\nConfig '{config}':")
                print(f"Length: {len(result.strip())}")
                print(f"Sample: {repr(result[:100])}")
            except Exception as e:
                print(f"Config '{config}' failed: {e}")
                
    except Exception as e:
        print(f"Error in preprocessing test: {e}")


def main():
    check_tesseract_info()
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        if Path(image_path).exists():
            test_simple_ocr(image_path)
            test_with_preprocessing(image_path)
        else:
            print(f"Image not found: {image_path}")
    else:
        print("\nUsage: python diagnostic_ocr.py <image_path>")
        print("This will test various OCR approaches on your image")


if __name__ == "__main__":
    main()