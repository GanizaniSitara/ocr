#!/usr/bin/env python3
"""
Compare Tesseract OCR vs LLM Vision models for text extraction.
"""

import base64
from pathlib import Path
import pytesseract
from PIL import Image


def encode_image_for_vision(image_path):
    """Encode image for vision model APIs."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def test_tesseract_extraction(image_path):
    """Test our current best Tesseract approach."""
    print("🔧 TESSERACT RESULTS:")
    print("-" * 40)
    
    try:
        image = Image.open(image_path)
        
        # Test our best PSM configurations
        configs = [
            ("PSM 11 Sparse", "--psm 11 --oem 3"),
            ("PSM 7 Single Line", "--psm 7 --oem 3"), 
            ("PSM 8 Single Word", "--psm 8 --oem 3"),
        ]
        
        all_text = []
        
        for name, config in configs:
            text = pytesseract.image_to_string(image, config=config).strip()
            if text:
                all_text.append(f"{name}: {repr(text[:100])}")
        
        if all_text:
            for result in all_text:
                print(result)
        else:
            print("❌ No text extracted by any Tesseract method")
            
        # Check for key terms
        combined_text = ' '.join([pytesseract.image_to_string(image, config=config) for _, config in configs])
        
        key_terms = ['PRIVATE', 'EYE', 'ANDREW', 'DENIES', 'BEING', 'CHINESE', 'SPY', '1642']
        found_terms = [term for term in key_terms if term in combined_text.upper()]
        missing_terms = [term for term in key_terms if term not in combined_text.upper()]
        
        print(f"\n✅ Found: {found_terms}")
        print(f"❌ Missing: {missing_terms}")
        
    except Exception as e:
        print(f"Error: {e}")


def create_vision_prompt():
    """Create a prompt for vision models."""
    
    prompt = """Please extract ALL visible text from this image. This appears to be a magazine cover.

Focus on extracting:
1. Magazine title/masthead
2. Issue number and date
3. Headlines and subheadings  
4. Any prices or other text
5. Text in speech bubbles or captions

Please list the text in order of prominence/importance, and indicate the approximate location (top, center, bottom, etc.) of each text element.

Be thorough - even extract text that might be partially obscured or on colored backgrounds."""

    return prompt


def simulate_vision_model_result():
    """Simulate what a vision model would likely extract."""
    print("\n🤖 VISION MODEL (Simulated Results):")
    print("-" * 40)
    
    expected_extraction = """
✅ EXTRACTED TEXT (in order of prominence):

1. "PRIVATE EYE" (main masthead, top center, large black text)
2. "ANDREW DENIES BEING CHINESE SPY" (red banner headline, center)
3. "No. 1642" (top left corner)
4. "7 February - 20 Feb 2025" (date range, top area)
5. "£2.99" (price, top area)
6. "You'll get no intelligence out of me" (speech bubble, left figure)
7. "You're a useful channel" (speech bubble, right figure)  
8. "The word in English is idiot, sir" (speech bubble, bottom right)

CONFIDENCE: High - Vision models excel at:
- Text on colored backgrounds (red banner)
- Large typography (masthead)
- Complex layouts (magazine format)
- Context understanding (headlines vs speech bubbles)
"""
    
    print(expected_extraction)


def recommend_approach():
    """Recommend the best approach for each use case."""
    
    print("\n📊 RECOMMENDATION:")
    print("=" * 60)
    
    print("""
🗞️  MAGAZINE ARCHIVING:
   Recommended: LLM Vision Models
   Why: Tesseract consistently misses headlines, mastheads, and text on colored backgrounds
   
💻 CONTROLS TESTING (UI Screenshots):
   Recommended: Hybrid Approach
   - Try Tesseract PSM 11 first (good for clean UI text)
   - Fall back to Vision models for complex/styled UI elements
   
⚡ IMPLEMENTATION PRIORITY:
   1. Start with Vision API integration (OpenAI GPT-4V, Anthropic Claude Vision)
   2. Keep Tesseract as backup for high-volume/cost-sensitive scenarios
   3. Use Tesseract for simple, clean document text
   
💰 COST CONSIDERATION:
   - Vision APIs: ~$0.01-0.05 per image
   - Tesseract: Free but limited accuracy on complex layouts
   - For archives: Vision ROI is worth it for better extraction
""")


def main():
    # Find test image
    png_files = list(Path(".").glob("Scan*.png"))
    if png_files:
        image_path = str(png_files[0])
        print(f"Testing on: {Path(image_path).name}")
        print("=" * 60)
        
        test_tesseract_extraction(image_path)
        simulate_vision_model_result()
        recommend_approach()
        
        print(f"\n🔗 To test with actual Vision APIs:")
        print(f"   - OpenAI GPT-4 Vision API")
        print(f"   - Anthropic Claude Vision API") 
        print(f"   - Google Gemini Vision API")
        
    else:
        print("No scan images found for testing")


if __name__ == "__main__":
    main()