#!/usr/bin/env python3
"""
Page Segmentation Mode (PSM) Guide and Tester
Educational tool to understand when to use each PSM mode.
"""

import pytesseract
from PIL import Image
from pathlib import Path


def explain_psm_modes():
    """Explain all PSM modes with use cases."""
    
    psm_modes = {
        0: {
            "name": "OSD Only",
            "description": "Orientation and Script Detection only - no OCR",
            "use_cases": ["Detecting page rotation", "Identifying text scripts/languages"],
            "magazine_fit": "❌ No - doesn't extract text",
            "controls_fit": "❌ No - doesn't extract text"
        },
        1: {
            "name": "Auto + OSD",
            "description": "Automatic page segmentation with orientation detection",
            "use_cases": ["Mixed orientation documents", "Scanned books"],
            "magazine_fit": "⚠️ Maybe - if pages are rotated",
            "controls_fit": "⚠️ Maybe - if screenshots are rotated"
        },
        2: {
            "name": "Auto No OSD",
            "description": "Automatic page segmentation (no orientation detection)",
            "use_cases": ["Standard documents", "Multi-column text"],
            "magazine_fit": "⚠️ Maybe - for text-heavy articles",
            "controls_fit": "❌ No - UI elements aren't standard text"
        },
        3: {
            "name": "Auto (Default)",
            "description": "Fully automatic page segmentation (most common default)",
            "use_cases": ["Books", "Articles", "General documents"],
            "magazine_fit": "⚠️ Sometimes - good for article text, bad for headlines",
            "controls_fit": "❌ Poor - assumes document-like layout"
        },
        4: {
            "name": "Single Column",
            "description": "Single column of text of variable sizes",
            "use_cases": ["Newspapers", "Magazine columns", "Scattered headlines"],
            "magazine_fit": "✅ Excellent - handles varied text sizes",
            "controls_fit": "⚠️ Maybe - for single-column UI lists"
        },
        5: {
            "name": "Vertical Text Block",
            "description": "Single uniform block of vertically aligned text",
            "use_cases": ["Single column articles", "Code blocks"],
            "magazine_fit": "⚠️ Maybe - for uniform article text",
            "controls_fit": "✅ Good - for code editors, logs"
        },
        6: {
            "name": "Single Block",
            "description": "Single uniform block of text",
            "use_cases": ["Paragraphs", "Single text blocks"],
            "magazine_fit": "❌ Poor - magazines aren't single blocks",
            "controls_fit": "✅ Excellent - UI dialogs, single text areas"
        },
        7: {
            "name": "Single Line",
            "description": "Single text line",
            "use_cases": ["Headlines", "Titles", "Single input fields"],
            "magazine_fit": "✅ Perfect - for mastheads like 'PRIVATE EYE'",
            "controls_fit": "✅ Perfect - buttons, labels, field names"
        },
        8: {
            "name": "Single Word",
            "description": "Single word",
            "use_cases": ["Large text", "Logos", "Single buttons"],
            "magazine_fit": "✅ Good - for large headline words",
            "controls_fit": "✅ Excellent - button text, single labels"
        },
        9: {
            "name": "Circle of Words",
            "description": "Text arranged in a circle",
            "use_cases": ["Logos", "Circular text", "Special layouts"],
            "magazine_fit": "❌ Rare - only for special logo text",
            "controls_fit": "❌ No - UI elements aren't circular"
        },
        10: {
            "name": "Single Character",
            "description": "Single character",
            "use_cases": ["Large single letters", "Captchas"],
            "magazine_fit": "❌ Too granular",
            "controls_fit": "❌ Too granular"
        },
        11: {
            "name": "Sparse Text",
            "description": "Sparse text - find as much text as possible",
            "use_cases": ["Forms", "Scattered text", "UI screenshots"],
            "magazine_fit": "✅ Excellent - finds scattered headlines",
            "controls_fit": "✅ Perfect - UI elements scattered around"
        },
        12: {
            "name": "Sparse + OSD",
            "description": "Sparse text with orientation detection",
            "use_cases": ["Rotated forms", "Mixed orientation UI"],
            "magazine_fit": "✅ Good - if magazine pages are rotated",
            "controls_fit": "✅ Good - if screenshots are rotated"
        },
        13: {
            "name": "Raw Line",
            "description": "Raw line - bypass all Tesseract heuristics",
            "use_cases": ["When other modes fail", "Custom preprocessing"],
            "magazine_fit": "⚠️ Last resort - when everything else fails",
            "controls_fit": "⚠️ Last resort - when everything else fails"
        }
    }
    
    print("=" * 100)
    print("TESSERACT PAGE SEGMENTATION MODES (PSM) GUIDE")
    print("=" * 100)
    
    for psm, info in psm_modes.items():
        print(f"\nPSM {psm}: {info['name']}")
        print(f"Description: {info['description']}")
        print(f"Use Cases: {', '.join(info['use_cases'])}")
        print(f"Magazine Archive: {info['magazine_fit']}")
        print(f"Controls Testing: {info['controls_fit']}")
        print("-" * 80)


def recommend_psm_strategies():
    """Recommend PSM strategies for your specific use cases."""
    
    print("\n" + "=" * 100)
    print("RECOMMENDED PSM STRATEGIES FOR YOUR USE CASES")
    print("=" * 100)
    
    print("\n🗞️  MAGAZINE ARCHIVING STRATEGY:")
    print("-" * 50)
    print("Primary approaches (try in order):")
    print("1. PSM 11 (Sparse) - Best for scattered headlines, dates, prices")
    print("2. PSM 4 (Single Column) - Good for varied text sizes")
    print("3. PSM 7 (Single Line) - Perfect for mastheads like 'PRIVATE EYE'")
    print("4. PSM 8 (Single Word) - For large individual words")
    print("5. PSM 3 (Auto) - Fallback for article body text")
    
    print("\nWhy these work for magazines:")
    print("• PSM 11 finds text anywhere on the page (headlines, prices, dates)")
    print("• PSM 7 perfect for large mastheads and banner headlines")
    print("• PSM 4 handles the mix of large headlines and smaller text")
    print("• PSM 8 catches large words that other modes miss")
    
    print("\n💻 CONTROLS TESTING STRATEGY:")
    print("-" * 50)
    print("Primary approaches (try in order):")
    print("1. PSM 11 (Sparse) - Perfect for UI elements scattered around")
    print("2. PSM 8 (Single Word) - Excellent for button text, labels")
    print("3. PSM 7 (Single Line) - Great for field names, titles")
    print("4. PSM 6 (Single Block) - Good for dialog boxes, text areas")
    print("5. PSM 5 (Vertical Block) - Perfect for code editors, logs")
    
    print("\nWhy these work for UI screenshots:")
    print("• PSM 11 finds all scattered UI text (buttons, labels, menus)")
    print("• PSM 8 perfect for individual button text, field labels")
    print("• PSM 7 great for window titles, toolbar text")
    print("• PSM 6 good for message boxes, single text areas")
    print("• PSM 5 excellent for code/SQL in editors")
    
    print("\n🎯 COMBINED MULTI-PSM APPROACH:")
    print("-" * 50)
    print("For maximum accuracy, run multiple PSMs and combine results:")
    print("1. Run PSM 11 (sparse) to find ALL text")
    print("2. Run PSM 7 (line) for titles/headlines")
    print("3. Run PSM 8 (word) for individual important words")
    print("4. Merge results, removing duplicates")
    print("5. This gives you comprehensive text extraction")


def create_psm_test_script():
    """Create a script to test PSMs on your specific images."""
    
    test_script = '''#!/usr/bin/env python3
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
        print(f"\\nBEST: PSM {best['psm']} with {best['length']} characters")
        print(f"Text: {repr(best['text'][:200])}...")
    
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python psm_tester.py <image_path> [magazine|controls|both]")
        sys.exit(1)
    
    image_path = sys.argv[1]
    use_case = sys.argv[2] if len(sys.argv) > 2 else "both"
    
    test_recommended_psms(image_path, use_case)
'''
    
    with open('psm_tester.py', 'w') as f:
        f.write(test_script)
    
    print(f"\n📝 Created psm_tester.py for testing your images!")
    print("Usage examples:")
    print("  python psm_tester.py magazine.png magazine")
    print("  python psm_tester.py ui_screenshot.png controls")
    print("  python psm_tester.py any_image.png both")


def main():
    explain_psm_modes()
    recommend_psm_strategies()
    create_psm_test_script()


if __name__ == "__main__":
    main()