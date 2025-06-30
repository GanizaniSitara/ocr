#!/usr/bin/env python3
"""
PSM Visual Tester with Bounding Box Overlays
Tests PSM modes and creates visual debugging images like the earlier working example.
"""

import pytesseract
from PIL import Image, ImageDraw, ImageFont
import sys
from pathlib import Path
from bs4 import BeautifulSoup
import webbrowser


def test_psm_with_visual_overlay(image_path: str, use_case: str = "both"):
    """Test PSMs and create visual overlays showing detected text."""
    
    # Define PSM sets based on use case
    if use_case == "magazine":
        psms_to_test = [
            (11, "Sparse - Find all scattered text"),
            (7, "Single Line - Perfect for mastheads"),
            (8, "Single Word - Large individual words"),
            (4, "Single Column - Varied text sizes"),
            (3, "Auto - Fallback for articles")
        ]
        print("🗞️  Testing MAGAZINE ARCHIVING PSMs")
    elif use_case == "controls":
        psms_to_test = [
            (11, "Sparse - All UI elements"),
            (8, "Single Word - Button text/labels"),
            (7, "Single Line - Field names/titles"),
            (6, "Single Block - Dialog boxes"),
            (5, "Vertical Block - Code/SQL editors")
        ]
        print("💻 Testing CONTROLS TESTING PSMs")
    else:  # both
        psms_to_test = [
            (11, "Sparse - Find everything"),
            (7, "Single Line - Headlines/titles"),
            (8, "Single Word - Individual words"),
            (4, "Single Column - Varied sizes"),
            (6, "Single Block - Text areas"),
            (5, "Vertical Block - Code blocks")
        ]
        print("🎯 Testing COMBINED APPROACH PSMs")
    
    image_name = Path(image_path).stem
    output_dir = Path("psm_visual_results")
    output_dir.mkdir(exist_ok=True)
    
    print(f"Image: {Path(image_path).name}")
    print(f"Output directory: {output_dir}")
    print("=" * 80)
    
    results = []
    
    for psm, description in psms_to_test:
        try:
            print(f"\nTesting PSM {psm}: {description}")
            
            # Generate HOCR output
            image = Image.open(image_path)
            config = f"--psm {psm} --oem 3"
            hocr_output = pytesseract.image_to_pdf_or_hocr(image, config=config, extension='hocr')
            
            # Save HOCR file
            hocr_path = output_dir / f"{image_name}_psm{psm:02d}_hocr.html"
            with open(hocr_path, 'wb') as f:
                f.write(hocr_output)
            
            # Create visual overlay
            visual_path = output_dir / f"{image_name}_psm{psm:02d}_visual.png"
            word_count, extracted_text = create_visual_overlay(image_path, hocr_path, visual_path, psm)
            
            # Also get plain text for comparison
            plain_text = pytesseract.image_to_string(image, config=config).strip()
            
            result = {
                'psm': psm,
                'description': description,
                'word_count': word_count,
                'text_length': len(extracted_text),
                'text': extracted_text,
                'plain_text': plain_text,
                'visual_path': visual_path,
                'hocr_path': hocr_path,
                # Check for key magazine terms
                'has_private': 'PRIVATE' in extracted_text.upper(),
                'has_eye': 'EYE' in extracted_text.upper(),
                'has_andrew': 'ANDREW' in extracted_text.upper(),
                'has_1642': '1642' in extracted_text,
                'has_chinese': 'CHINESE' in extracted_text.upper(),
                'has_spy': 'SPY' in extracted_text.upper(),
            }
            
            results.append(result)
            
            # Print results
            print(f"  Words detected: {word_count}")
            print(f"  Text length: {len(extracted_text)} chars")
            print(f"  Key terms: PRIVATE:{'✓' if result['has_private'] else '✗'} "
                  f"EYE:{'✓' if result['has_eye'] else '✗'} "
                  f"ANDREW:{'✓' if result['has_andrew'] else '✗'} "
                  f"1642:{'✓' if result['has_1642'] else '✗'}")
            print(f"  Preview: {repr(extracted_text[:80])}...")
            print(f"  Visual saved: {visual_path.name}")
            
        except Exception as e:
            print(f"  ERROR with PSM {psm}: {e}")
            continue
    
    return results


def create_visual_overlay(image_path: str, hocr_path: Path, visual_path: Path, psm: int):
    """Create visual debugging image with bounding boxes and text overlays."""
    
    try:
        # Load image
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)
        
        # Try to load a good font
        try:
            font = ImageFont.truetype("arial.ttf", 14)
            small_font = ImageFont.truetype("arial.ttf", 10)
        except:
            try:
                font = ImageFont.load_default()
                small_font = font
            except:
                font = None
                small_font = None
        
        # Parse HOCR file
        with open(hocr_path, 'r', encoding='utf-8') as f:
            hocr_content = f.read()
        
        soup = BeautifulSoup(hocr_content, 'html.parser')
        
        words = []
        word_count = 0
        
        # Extract words with bounding boxes
        for span in soup.find_all('span', class_='ocrx_word'):
            if 'title' in span.attrs:
                title = span['title']
                # Extract bounding box coordinates
                bbox_part = [part for part in title.split(';') if 'bbox' in part]
                if bbox_part:
                    coords = list(map(int, bbox_part[0].split()[1:5]))
                    text = span.get_text().strip()
                    
                    # Extract confidence if available
                    conf_part = [part for part in title.split(';') if 'x_wconf' in part]
                    confidence = int(conf_part[0].split()[-1]) if conf_part else 0
                    
                    if text and len(text) > 0:
                        words.append({
                            'text': text,
                            'bbox': coords,
                            'confidence': confidence
                        })
                        word_count += 1
        
        # Draw bounding boxes and text
        for word in words:
            bbox = word['bbox']
            text = word['text']
            conf = word['confidence']
            
            # Choose color based on confidence
            if conf >= 80:
                box_color = 'green'
                text_bg_color = 'lightgreen'
            elif conf >= 60:
                box_color = 'orange'
                text_bg_color = 'lightyellow'
            else:
                box_color = 'red'
                text_bg_color = 'lightcoral'
            
            # Draw bounding box
            draw.rectangle(bbox, outline=box_color, width=2)
            
            # Draw text label above the box
            if font:
                # Calculate text position
                text_x = bbox[0]
                text_y = max(0, bbox[1] - 20)
                
                # Draw background for text
                text_bbox = draw.textbbox((text_x, text_y), f"{text} ({conf}%)", font=small_font)
                draw.rectangle(text_bbox, fill=text_bg_color, outline=box_color)
                
                # Draw text
                draw.text((text_x, text_y), f"{text} ({conf}%)", fill='black', font=small_font)
        
        # Add PSM info to image
        if font:
            psm_text = f"PSM {psm} - {word_count} words detected"
            draw.rectangle((10, 10, 300, 40), fill='white', outline='black')
            draw.text((15, 15), psm_text, fill='black', font=font)
        
        # Save the visual debugging image
        image.save(visual_path)
        
        # Extract text in reading order
        words.sort(key=lambda w: (w['bbox'][1], w['bbox'][0]))  # Sort by top, then left
        extracted_text = ' '.join([w['text'] for w in words])
        
        return word_count, extracted_text
        
    except Exception as e:
        print(f"Error creating visual overlay: {e}")
        return 0, ""


def analyze_and_rank_results(results):
    """Analyze results and rank by effectiveness."""
    
    print(f"\n{'='*100}")
    print("RESULTS ANALYSIS - RANKED BY EFFECTIVENESS")
    print(f"{'='*100}")
    
    # Calculate scores
    for result in results:
        score = 0
        score += result['word_count'] * 2  # Base score for words found
        score += result['text_length']     # Length bonus
        
        # Key term bonuses (magazine specific)
        score += 100 if result['has_private'] else 0
        score += 100 if result['has_eye'] else 0
        score += 50 if result['has_andrew'] else 0
        score += 25 if result['has_1642'] else 0
        score += 25 if result['has_chinese'] else 0
        score += 25 if result['has_spy'] else 0
        
        result['score'] = score
    
    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Print ranking table
    print(f"{'Rank':<4} {'PSM':<4} {'Description':<25} {'Score':<6} {'Words':<6} {'Chars':<6} {'Key Terms':<20}")
    print("-" * 100)
    
    for i, result in enumerate(results):
        key_terms = []
        if result['has_private']: key_terms.append('PRIV')
        if result['has_eye']: key_terms.append('EYE')
        if result['has_andrew']: key_terms.append('AND')
        if result['has_1642']: key_terms.append('1642')
        if result['has_chinese']: key_terms.append('CHI')
        if result['has_spy']: key_terms.append('SPY')
        
        key_terms_str = ','.join(key_terms) if key_terms else 'none'
        
        print(f"{i+1:<4} {result['psm']:<4} {result['description'][:24]:<25} "
              f"{result['score']:<6} {result['word_count']:<6} {result['text_length']:<6} {key_terms_str:<20}")
    
    return results


def open_best_results(results, num_to_open=3):
    """Open the top performing visual results."""
    
    if not results:
        print("No results to display")
        return
    
    print(f"\n🎯 Opening top {num_to_open} visual results...")
    
    for i, result in enumerate(results[:num_to_open]):
        try:
            visual_path = Path(result['visual_path']).absolute()
            if visual_path.exists():
                webbrowser.open(f"file://{visual_path}")
                print(f"Opened PSM {result['psm']}: {visual_path.name}")
            else:
                print(f"File not found: {visual_path}")
        except Exception as e:
            print(f"Error opening PSM {result['psm']} visual: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python psm_visual_tester.py <image_path> [magazine|controls|both]")
        print("\nExamples:")
        print("  python psm_visual_tester.py magazine.png magazine")
        print("  python psm_visual_tester.py ui_screenshot.png controls")
        print("  python psm_visual_tester.py any_image.png both")
        return
    
    image_path = sys.argv[1]
    use_case = sys.argv[2] if len(sys.argv) > 2 else "both"
    
    if not Path(image_path).exists():
        print(f"Image not found: {image_path}")
        return
    
    # Test PSMs with visual overlays
    results = test_psm_with_visual_overlay(image_path, use_case)
    
    if results:
        # Analyze and rank results
        ranked_results = analyze_and_rank_results(results)
        
        # Open best results
        open_best_results(ranked_results)
        
        print(f"\n📁 All visual results saved in: psm_visual_results/")
        print(f"🏆 Best PSM: {ranked_results[0]['psm']} - {ranked_results[0]['description']}")
        
    else:
        print("❌ No successful results obtained.")


if __name__ == "__main__":
    main()