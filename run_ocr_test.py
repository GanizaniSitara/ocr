#!/usr/bin/env python3
"""
One-click OCR test script - tests your image with optimal PSM modes and opens results.
"""

import pytesseract
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from bs4 import BeautifulSoup
import webbrowser
import sys


def main():
    # Use the first PNG file found, or the provided argument
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # Auto-find first PNG file
        png_files = list(Path(".").glob("*.png"))
        if not png_files:
            print("No PNG files found. Usage: python run_ocr_test.py [image_path]")
            return
        image_path = str(png_files[0])
    
    if not Path(image_path).exists():
        print(f"Image not found: {image_path}")
        return
    
    print(f"Testing OCR on: {Path(image_path).name}")
    
    # Test the optimal PSM modes
    psms_to_test = [
        (11, "Sparse - Finds scattered text (magazines/UI)"),
        (7, "Single Line - Perfect for headlines"),
        (8, "Single Word - Large individual words"),
        (3, "Auto - Current default (for comparison)")
    ]
    
    output_dir = Path("ocr_test_results")
    output_dir.mkdir(exist_ok=True)
    image_name = Path(image_path).stem
    
    best_result = None
    best_score = 0
    
    for psm, description in psms_to_test:
        try:
            print(f"\nTesting PSM {psm}: {description}")
            
            # Run OCR with HOCR output
            image = Image.open(image_path)
            config = f"--psm {psm} --oem 3"
            hocr_output = pytesseract.image_to_pdf_or_hocr(image, config=config, extension='hocr')
            
            # Save and parse HOCR
            hocr_path = output_dir / f"{image_name}_psm{psm}.html"
            with open(hocr_path, 'wb') as f:
                f.write(hocr_output)
            
            # Create visual with bounding boxes
            visual_path = output_dir / f"{image_name}_psm{psm}_visual.png"
            word_count, text = create_visual_overlay(image_path, hocr_path, visual_path, psm, description)
            
            # Score this result
            score = word_count * 2 + len(text)
            key_terms = ['PRIVATE', 'EYE', 'ANDREW', '1642', 'CHINESE', 'SPY']
            score += sum(100 for term in key_terms if term in text.upper())
            
            print(f"  Words: {word_count}, Text length: {len(text)}, Score: {score}")
            print(f"  Preview: {repr(text[:60])}...")
            
            if score > best_score:
                best_score = score
                best_result = {
                    'psm': psm,
                    'description': description,
                    'visual_path': visual_path,
                    'text': text,
                    'word_count': word_count,
                    'score': score
                }
            
        except Exception as e:
            print(f"  ERROR: {e}")
    
    # Open the best result
    if best_result:
        print(f"\n🏆 BEST RESULT: PSM {best_result['psm']} - {best_result['description']}")
        print(f"Score: {best_result['score']}, Words: {best_result['word_count']}")
        print(f"Text: {repr(best_result['text'][:100])}...")
        
        try:
            visual_path = Path(best_result['visual_path']).absolute()
            webbrowser.open(f"file://{visual_path}")
            print(f"\n✓ Opened visual result: {visual_path.name}")
        except Exception as e:
            print(f"Error opening result: {e}")
    else:
        print("❌ No successful results")


def create_visual_overlay(image_path: str, hocr_path: Path, visual_path: Path, psm: int, description: str):
    """Create visual debugging image with bounding boxes."""
    
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)
    
    # Load font
    try:
        font = ImageFont.truetype("arial.ttf", 12)
    except:
        font = ImageFont.load_default()
    
    # Parse HOCR
    with open(hocr_path, 'r', encoding='utf-8') as f:
        hocr_content = f.read()
    
    soup = BeautifulSoup(hocr_content, 'html.parser')
    words = []
    
    # Extract words and coordinates with confidence filtering
    for span in soup.find_all('span', class_='ocrx_word'):
        if 'title' in span.attrs:
            title = span['title']
            bbox_part = [part for part in title.split(';') if 'bbox' in part]
            conf_part = [part for part in title.split(';') if 'x_wconf' in part]
            
            if bbox_part:
                coords = list(map(int, bbox_part[0].split()[1:5]))
                text = span.get_text().strip()
                confidence = int(conf_part[0].split()[-1]) if conf_part else 0
                
                # Filter out low confidence and likely false positives
                if (text and 
                    confidence >= 70 and  # Minimum 70% confidence
                    len(text) >= 2 and    # At least 2 characters
                    not all(c in '!@#$%^&*()_+-=[]{}|\\:";\'<>?,./' for c in text) and  # Not all symbols
                    any(c.isalnum() for c in text)):  # Contains at least one letter/number
                    words.append({'text': text, 'bbox': coords, 'confidence': confidence})
    
    # Draw bounding boxes and text with confidence-based colors
    for word in words:
        bbox = word['bbox']
        text = word['text']
        confidence = word.get('confidence', 0)
        
        # Color-code by confidence
        if confidence >= 90:
            box_color = 'green'
            bg_color = 'lightgreen'
        elif confidence >= 80:
            box_color = 'blue'
            bg_color = 'lightblue'
        else:
            box_color = 'orange'
            bg_color = 'lightyellow'
        
        # Draw box around detected text
        draw.rectangle(bbox, outline=box_color, width=2)
        
        # Draw text with confidence above box
        text_with_conf = f"{text} ({confidence}%)"
        text_y = max(0, bbox[1] - 15)
        text_bbox = draw.textbbox((bbox[0], text_y), text_with_conf, font=font)
        draw.rectangle(text_bbox, fill=bg_color, outline=box_color)
        draw.text((bbox[0], text_y), text_with_conf, fill='black', font=font)
    
    # Add header with PSM info
    header_text = f"PSM {psm}: {description} | {len(words)} words detected"
    draw.rectangle((5, 5, 600, 30), fill='white', outline='black', width=2)
    draw.text((10, 10), header_text, fill='black', font=font)
    
    image.save(visual_path)
    
    # Return word count and extracted text
    words.sort(key=lambda w: (w['bbox'][1], w['bbox'][0]))  # Reading order
    extracted_text = ' '.join([w['text'] for w in words])
    
    return len(words), extracted_text


if __name__ == "__main__":
    main()