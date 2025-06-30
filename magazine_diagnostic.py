#!/usr/bin/env python3
"""
Magazine-specific OCR diagnostic script.
Focuses on detecting large headlines, mastheads, and varied text sizes.
"""

import pytesseract
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance
from bs4 import BeautifulSoup
import webbrowser


def test_magazine_specific_configs(image_path: str):
    """Test configurations optimized for magazine layouts."""
    
    configs = [
        # Magazine-specific configurations
        ("Magazine Auto", "--psm 3 --oem 3"),
        ("Magazine Sparse", "--psm 4 --oem 3"),  # Sparse text (good for headlines)
        ("Magazine Column", "--psm 5 --oem 3"),  # Single column of text
        ("Magazine Block", "--psm 6 --oem 3"),   # Single uniform block
        ("Magazine Line", "--psm 7 --oem 3"),    # Single text line (for headlines)
        ("Magazine Word", "--psm 8 --oem 3"),    # Single word (for large text)
        ("All Text", "--psm 12 --oem 3"),        # Sparse text without OSD
        ("Raw Line", "--psm 13 --oem 3"),        # Raw line, bypass heuristics
        
        # Try with different preprocessing
        ("High Contrast Auto", "--psm 3 --oem 3", "high_contrast"),
        ("Inverted Auto", "--psm 3 --oem 3", "invert"),
        ("Large Text Mode", "--psm 4 --oem 3", "large_text"),
    ]
    
    image_name = Path(image_path).stem
    output_dir = Path("magazine_diagnostic")
    output_dir.mkdir(exist_ok=True)
    
    results = []
    
    for i, config in enumerate(configs):
        config_name = config[0]
        tesseract_config = config[1]
        preprocess = config[2] if len(config) > 2 else None
        
        print(f"\n{'='*60}")
        print(f"Testing {i+1}/{len(configs)}: {config_name}")
        print(f"Config: {tesseract_config}")
        if preprocess:
            print(f"Preprocessing: {preprocess}")
        
        try:
            # Load and preprocess image
            image = Image.open(image_path)
            processed_image = preprocess_for_magazine(image, preprocess) if preprocess else image
            
            # Generate HOCR
            hocr_output = pytesseract.image_to_pdf_or_hocr(processed_image, config=tesseract_config, extension='hocr')
            
            # Save files
            hocr_path = output_dir / f"{image_name}_{i:02d}_{config_name.replace(' ', '_')}_hocr.html"
            visual_path = output_dir / f"{image_name}_{i:02d}_{config_name.replace(' ', '_')}_visual.png"
            
            with open(hocr_path, 'wb') as f:
                f.write(hocr_output)
            
            # Create visual debugging
            word_count = create_visual_debug(processed_image, hocr_path, visual_path)
            
            # Extract text
            text = extract_text_from_hocr_simple(hocr_path)
            
            result = {
                'name': config_name,
                'config': tesseract_config,
                'preprocess': preprocess,
                'word_count': word_count,
                'text_length': len(text),
                'text': text,
                'visual_path': visual_path,
                'hocr_path': hocr_path,
                'has_private': 'PRIVATE' in text.upper(),
                'has_eye': 'EYE' in text.upper(),
                'has_andrew': 'ANDREW' in text.upper(),
                'has_1642': '1642' in text,
            }
            
            results.append(result)
            
            print(f"Words detected: {word_count}")
            print(f"Text length: {len(text)} chars")
            print(f"Has PRIVATE: {'✓' if result['has_private'] else '✗'}")
            print(f"Has EYE: {'✓' if result['has_eye'] else '✗'}")
            print(f"Has ANDREW: {'✓' if result['has_andrew'] else '✗'}")
            print(f"Has 1642: {'✓' if result['has_1642'] else '✗'}")
            print(f"Preview: {repr(text[:100])}")
            
        except Exception as e:
            print(f"Error with {config_name}: {e}")
            continue
    
    return results


def preprocess_for_magazine(image: Image.Image, method: str) -> Image.Image:
    """Apply magazine-specific preprocessing."""
    
    if method == "high_contrast":
        # Enhance contrast for better text separation
        image = ImageOps.grayscale(image)
        image = ImageEnhance.Contrast(image).enhance(2.0)
        return image
        
    elif method == "invert":
        # Try inverted colors (sometimes helps with colored backgrounds)
        image = ImageOps.grayscale(image)
        image = ImageOps.invert(image)
        return image
        
    elif method == "large_text":
        # Optimize for large text (headlines, mastheads)
        image = ImageOps.grayscale(image)
        # Slight blur to connect broken letters
        image = image.resize((image.width // 2, image.height // 2), Image.Resampling.LANCZOS)
        image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
        return image
    
    return image


def create_visual_debug(image: Image.Image, hocr_path: Path, visual_path: Path) -> int:
    """Create visual debugging image with larger, more visible boxes."""
    
    try:
        draw = ImageDraw.Draw(image)
        word_count = 0
        
        # Try to load a larger font
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            try:
                font = ImageFont.load_default()
            except:
                font = None
        
        # Parse HOCR
        with open(hocr_path, 'r', encoding='utf-8') as f:
            hocr_content = f.read()
        
        soup = BeautifulSoup(hocr_content, 'html.parser')
        
        # Draw boxes for words
        for span in soup.find_all('span', class_='ocrx_word'):
            if 'title' in span.attrs:
                title = span['title']
                bbox_part = [part for part in title.split(';') if 'bbox' in part][0]
                coords = list(map(int, bbox_part.split()[1:5]))
                text = span.get_text().strip()
                
                if text:
                    # Draw thicker, more visible box
                    draw.rectangle(coords, outline='red', width=3)
                    # Draw text with background for better visibility
                    if font:
                        text_bbox = draw.textbbox((coords[0], coords[1] - 20), text, font=font)
                        draw.rectangle(text_bbox, fill='yellow', outline='red')
                        draw.text((coords[0], coords[1] - 20), text, fill='black', font=font)
                    word_count += 1
        
        # Also try to draw line-level boxes for better visibility
        for span in soup.find_all('span', class_='ocrx_textfloat'):
            if 'title' in span.attrs:
                title = span['title']
                bbox_part = [part for part in title.split(';') if 'bbox' in part][0]
                coords = list(map(int, bbox_part.split()[1:5]))
                draw.rectangle(coords, outline='blue', width=2)
        
        image.save(visual_path)
        return word_count
        
    except Exception as e:
        print(f"Error creating visual debug: {e}")
        return 0


def extract_text_from_hocr_simple(hocr_path: Path) -> str:
    """Simple text extraction from HOCR."""
    
    try:
        with open(hocr_path, 'r', encoding='utf-8') as f:
            hocr_content = f.read()
        
        soup = BeautifulSoup(hocr_content, 'html.parser')
        
        # Extract all text, preserve some structure
        words = []
        for span in soup.find_all('span', class_='ocrx_word'):
            text = span.get_text().strip()
            if text:
                words.append(text)
        
        return ' '.join(words)
        
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""


def analyze_results(results):
    """Analyze and rank results by magazine text detection success."""
    
    print(f"\n{'='*80}")
    print("MAGAZINE TEXT DETECTION ANALYSIS")
    print(f"{'='*80}")
    
    # Score each result
    for result in results:
        score = 0
        score += result['word_count'] * 1  # Base score for words detected
        score += 100 if result['has_private'] else 0  # Key masthead text
        score += 100 if result['has_eye'] else 0      # Key masthead text
        score += 50 if result['has_andrew'] else 0    # Headline text
        score += 25 if result['has_1642'] else 0      # Issue number
        result['score'] = score
    
    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"{'Rank':<4} {'Method':<20} {'Score':<6} {'Words':<6} {'PRIV':<4} {'EYE':<4} {'AND':<4} {'1642':<4}")
    print("-" * 80)
    
    for i, result in enumerate(results[:10]):  # Show top 10
        priv = "✓" if result['has_private'] else "✗"
        eye = "✓" if result['has_eye'] else "✗"
        andrew = "✓" if result['has_andrew'] else "✗"
        num = "✓" if result['has_1642'] else "✗"
        
        print(f"{i+1:<4} {result['name']:<20} {result['score']:<6} {result['word_count']:<6} {priv:<4} {eye:<4} {andrew:<4} {num:<4}")
    
    return results


def open_best_results(results):
    """Open the best performing results."""
    
    if not results:
        return
    
    best = results[0]
    print(f"\nOpening best result: {best['name']} (Score: {best['score']})")
    
    try:
        visual_path = Path(best['visual_path']).absolute()
        if visual_path.exists():
            webbrowser.open(f"file://{visual_path}")
            print(f"Opened: {visual_path}")
    except Exception as e:
        print(f"Error opening results: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python magazine_diagnostic.py <image_path>")
        return
    
    image_path = sys.argv[1]
    if not Path(image_path).exists():
        print(f"Image not found: {image_path}")
        return
    
    print("Starting magazine-specific OCR diagnostic...")
    results = test_magazine_specific_configs(image_path)
    
    if results:
        analyzed_results = analyze_results(results)
        open_best_results(analyzed_results)
        print(f"\nAll results saved in: magazine_diagnostic/")
    else:
        print("No successful results obtained.")


if __name__ == "__main__":
    main()