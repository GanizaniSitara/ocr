#!/usr/bin/env python3
"""
Enhanced diagnostic script using HOCR format and visual debugging.
Based on the working approach with visual rendering and reading order.
"""

import pytesseract
import sys
import webbrowser
import subprocess
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup


def check_tesseract_info():
    """Check Tesseract version and available languages."""
    print("=== TESSERACT DIAGNOSTIC INFO ===")
    
    try:
        version = pytesseract.get_tesseract_version()
        print(f"Tesseract version: {version}")
        langs = pytesseract.get_languages()
        print(f"Available languages: {langs}")
        cmd = pytesseract.pytesseract.tesseract_cmd
        print(f"Tesseract executable: {cmd}")
    except Exception as e:
        print(f"Error getting Tesseract info: {e}")


def test_hocr_approach(image_path: str, config: str = "--psm 3 --oem 3"):
    """Test OCR using HOCR format with visual debugging."""
    
    image_name = Path(image_path).stem
    output_dir = Path("diagnostic_output")
    output_dir.mkdir(exist_ok=True)
    
    hocr_path = output_dir / f"{image_name}_hocr.html"
    visual_path = output_dir / f"{image_name}_visual.png"
    text_path = output_dir / f"{image_name}_text.txt"
    
    try:
        print(f"\n=== TESTING HOCR APPROACH ===")
        print(f"Config: {config}")
        
        # Open the image
        image = Image.open(image_path)
        print(f"Image size: {image.size}")
        
        # Generate HOCR output
        print("Generating HOCR...")
        hocr_output = pytesseract.image_to_pdf_or_hocr(image, config=config, extension='hocr')
        
        # Save HOCR to file
        with open(hocr_path, 'wb') as f:
            f.write(hocr_output)
        print(f"HOCR saved to: {hocr_path}")
        
        # Parse HOCR and create visual debugging image
        print("Creating visual debugging image...")
        visual_image = render_hocr_boxes(image_path, hocr_path, visual_path)
        
        # Extract text in reading order
        print("Extracting text in reading order...")
        extracted_text = extract_text_from_hocr(hocr_path, text_path)
        
        print(f"Text length: {len(extracted_text)} characters")
        print(f"Text preview: {repr(extracted_text[:200])}")
        
        return {
            'hocr_path': hocr_path,
            'visual_path': visual_path,
            'text_path': text_path,
            'text': extracted_text,
            'success': True
        }
        
    except Exception as e:
        print(f"Error in HOCR approach: {e}")
        return {'success': False, 'error': str(e)}


def render_hocr_boxes(image_path: str, hocr_path: Path, output_path: Path):
    """Render bounding boxes on image for visual debugging."""
    
    try:
        # Open the image
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)
        
        # Try to load a font (fallback to default if not available)
        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except:
            font = ImageFont.load_default()
        
        # Parse HOCR file
        with open(hocr_path, 'r', encoding='utf-8') as f:
            hocr_content = f.read()
        
        soup = BeautifulSoup(hocr_content, 'html.parser')
        word_count = 0
        
        # Draw bounding boxes for each word
        for span in soup.find_all('span', class_='ocrx_word'):
            if 'title' in span.attrs:
                title = span['title']
                # Extract coordinates from title
                bbox_part = [part for part in title.split(';') if 'bbox' in part][0]
                coords = list(map(int, bbox_part.split()[1:5]))
                text = span.get_text().strip()
                
                if text:  # Only draw if there's actual text
                    # Draw bounding box
                    draw.rectangle(coords, outline='red', width=2)
                    # Draw text above the box
                    draw.text((coords[0], coords[1] - 15), text, fill='blue', font=font)
                    word_count += 1
        
        # Save the visual debugging image
        image.save(output_path)
        print(f"Visual debugging image saved: {output_path} ({word_count} words)")
        
        return output_path
        
    except Exception as e:
        print(f"Error creating visual debugging image: {e}")
        return None


def extract_text_from_hocr(hocr_path: Path, text_path: Path):
    """Extract text from HOCR in proper reading order."""
    
    try:
        with open(hocr_path, 'r', encoding='utf-8') as f:
            hocr_content = f.read()
        
        soup = BeautifulSoup(hocr_content, 'html.parser')
        
        # Extract words with their positions
        words = []
        for span in soup.find_all('span', class_='ocrx_word'):
            if 'title' in span.attrs:
                title = span['title']
                bbox_part = [part for part in title.split(';') if 'bbox' in part][0]
                coords = list(map(int, bbox_part.split()[1:5]))
                text = span.get_text().strip()
                
                if text:
                    # Store (top, left, text) for sorting
                    words.append((coords[1], coords[0], text))  # (top, left, text)
        
        # Sort by reading order: top to bottom, then left to right
        words.sort(key=lambda w: (w[0], w[1]))
        
        # Extract sorted text
        extracted_text = ' '.join([word[2] for word in words])
        
        # Save to text file
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        
        print(f"Text extracted to: {text_path}")
        return extracted_text
        
    except Exception as e:
        print(f"Error extracting text from HOCR: {e}")
        return ""


def compare_configurations(image_path: str):
    """Compare different Tesseract configurations using HOCR."""
    
    configs = [
        ("Optimal", "--psm 3 --oem 3"),
        ("Legacy", "--psm 3 --oem 0"),
        ("Hybrid", "--psm 3 --oem 1"),
        ("Single Block", "--psm 6 --oem 3"),
        ("High DPI", "--psm 3 --oem 3 --dpi 300"),
    ]
    
    results = []
    
    for name, config in configs:
        print(f"\n{'='*50}")
        print(f"Testing: {name}")
        print(f"Config: {config}")
        
        result = test_hocr_approach(image_path, config)
        if result['success']:
            results.append({
                'name': name,
                'config': config,
                'text_length': len(result['text']),
                'text_preview': result['text'][:100],
                'files': {
                    'hocr': result['hocr_path'],
                    'visual': result['visual_path'],
                    'text': result['text_path']
                }
            })
    
    return results


def open_results(results):
    """Open the best results in browser/external viewers."""
    
    if not results:
        print("No results to display")
        return
    
    # Sort by text length (more text usually means better OCR)
    best_result = max(results, key=lambda x: x['text_length'])
    
    print(f"\n=== OPENING BEST RESULT: {best_result['name']} ===")
    print(f"Text length: {best_result['text_length']} characters")
    
    try:
        # Convert to absolute paths for opening
        visual_path = Path(best_result['files']['visual']).absolute()
        text_path = Path(best_result['files']['text']).absolute()
        hocr_path = Path(best_result['files']['hocr']).absolute()
        
        # Open visual debugging image in default viewer
        if visual_path.exists():
            webbrowser.open(f"file://{visual_path}")
            print(f"Opened visual image: {visual_path}")
        
        # Open text file in default text editor
        if text_path.exists():
            webbrowser.open(f"file://{text_path}")
            print(f"Opened text file: {text_path}")
            
        # Open HOCR file in browser
        if hocr_path.exists():
            webbrowser.open(f"file://{hocr_path}")
            print(f"Opened HOCR file: {hocr_path}")
            
    except Exception as e:
        print(f"Error opening files: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python enhanced_diagnostic.py <image_path>")
        return
    
    image_path = sys.argv[1]
    if not Path(image_path).exists():
        print(f"Image not found: {image_path}")
        return
    
    # Check Tesseract setup
    check_tesseract_info()
    
    # Compare different configurations
    results = compare_configurations(image_path)
    
    # Show summary
    print(f"\n{'='*60}")
    print("SUMMARY OF RESULTS:")
    print(f"{'='*60}")
    
    for result in sorted(results, key=lambda x: x['text_length'], reverse=True):
        print(f"{result['name']:<15} | {result['text_length']:4d} chars | {result['text_preview'][:50]}...")
    
    # Open best results
    if results:
        open_results(results)
    
    print(f"\nAll files saved in: diagnostic_output/")


if __name__ == "__main__":
    main()