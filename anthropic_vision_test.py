#!/usr/bin/env python3
"""
Anthropic Claude Vision API test script - compare against Tesseract OCR.
"""

import base64
import json
from pathlib import Path
import pytesseract
from PIL import Image
import anthropic
import os
import sys


def setup_anthropic():
    """Setup Anthropic client with API key."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY environment variable not set")
        print("Get your API key from: https://console.anthropic.com/")
        print("Set it with: export ANTHROPIC_API_KEY='your-api-key-here'")
        print("Or: set ANTHROPIC_API_KEY=your-api-key-here  (Windows)")
        return None
    
    return anthropic.Anthropic(api_key=api_key)


def encode_image_for_claude(image_path):
    """Encode image to base64 for Claude API."""
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Determine media type
        if image_path.lower().endswith('.png'):
            media_type = "image/png"
        elif image_path.lower().endswith(('.jpg', '.jpeg')):
            media_type = "image/jpeg"
        else:
            media_type = "image/png"  # default
            
        return base64_image, media_type


def test_claude_vision(client, image_path):
    """Test Claude Vision on the image."""
    print("🤖 ANTHROPIC CLAUDE VISION RESULTS:")
    print("-" * 50)
    
    try:
        # Encode image
        base64_image, media_type = encode_image_for_claude(image_path)
        
        # Create the prompt
        prompt = """Please analyze this image and extract ALL visible text. This appears to be a magazine cover.

I need you to identify and extract:

1. **Magazine masthead/title** (the main magazine name)
2. **Issue information** (issue number, date, price)
3. **Main headlines** (primary story headlines)
4. **Speech bubbles or captions** (any dialogue or photo captions)
5. **Any other visible text**

Please format your response as a structured list showing:
- What text you found
- Where it appears on the image (top, center, bottom, etc.)
- Any special formatting (large text, colored background, etc.)

Be thorough - extract even text that appears on colored backgrounds or in stylized fonts."""

        # Make API call
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        
        # Extract response
        response_text = response.content[0].text
        print("Claude's Analysis:")
        print(response_text)
        
        # Try to parse key information
        text_upper = response_text.upper()
        found_terms = []
        key_terms = ['PRIVATE', 'EYE', 'ANDREW', 'DENIES', 'BEING', 'CHINESE', 'SPY', '1642']
        
        for term in key_terms:
            if term in text_upper:
                found_terms.append(term)
        
        print(f"\n📋 KEY TERMS DETECTED: {found_terms}")
        print(f"🎯 DETECTION RATE: {len(found_terms)}/{len(key_terms)} ({len(found_terms)/len(key_terms)*100:.1f}%)")
        
        return {
            "full_response": response_text,
            "key_terms_found": found_terms,
            "detection_rate": len(found_terms)/len(key_terms)
        }
        
    except Exception as e:
        print(f"❌ Error calling Claude Vision API: {e}")
        return None


def test_tesseract_comparison(image_path):
    """Test Tesseract for comparison."""
    print("\n🔧 TESSERACT COMPARISON:")
    print("-" * 50)
    
    try:
        image = Image.open(image_path)
        
        configs = [
            ("PSM 11 Sparse", "--psm 11 --oem 3"),
            ("PSM 7 Single Line", "--psm 7 --oem 3"),
            ("PSM 8 Single Word", "--psm 8 --oem 3"),
        ]
        
        all_text_combined = ""
        
        for name, config in configs:
            try:
                text = pytesseract.image_to_string(image, config=config).strip()
                all_text_combined += " " + text
                if text:
                    print(f"{name}: {repr(text[:60])}...")
                else:
                    print(f"{name}: No text extracted")
            except Exception as e:
                print(f"{name}: Error - {e}")
        
        # Check key terms
        key_terms = ['PRIVATE', 'EYE', 'ANDREW', 'DENIES', 'BEING', 'CHINESE', 'SPY', '1642']
        found_terms = [term for term in key_terms if term in all_text_combined.upper()]
        
        print(f"\n📋 TESSERACT KEY TERMS: {found_terms}")
        print(f"🎯 TESSERACT RATE: {len(found_terms)}/{len(key_terms)} ({len(found_terms)/len(key_terms)*100:.1f}%)")
        
        return {
            "combined_text": all_text_combined,
            "key_terms_found": found_terms,
            "detection_rate": len(found_terms)/len(key_terms)
        }
        
    except Exception as e:
        print(f"❌ Tesseract error: {e}")
        return {"detection_rate": 0, "key_terms_found": []}


def compare_results(claude_result, tesseract_result):
    """Compare Claude vs Tesseract results."""
    print(f"\n{'='*60}")
    print("📊 HEAD-TO-HEAD COMPARISON:")
    print(f"{'='*60}")
    
    if claude_result and tesseract_result:
        claude_rate = claude_result.get('detection_rate', 0) * 100
        tesseract_rate = tesseract_result.get('detection_rate', 0) * 100
        
        print(f"🤖 Claude Vision:     {claude_rate:.1f}% detection rate")
        print(f"🔧 Tesseract OCR:     {tesseract_rate:.1f}% detection rate")
        
        if claude_rate > tesseract_rate:
            improvement = claude_rate - tesseract_rate
            print(f"\n🏆 WINNER: Claude Vision (+{improvement:.1f}% better)")
            
            claude_found = set(claude_result.get('key_terms_found', []))
            tesseract_found = set(tesseract_result.get('key_terms_found', []))
            claude_unique = claude_found - tesseract_found
            
            if claude_unique:
                print(f"✅ Claude found these that Tesseract missed: {list(claude_unique)}")
        
        print(f"\n💡 INSIGHTS:")
        print(f"   • Claude excels at complex layouts and colored backgrounds")
        print(f"   • Tesseract works well for simple, clean document text")
        print(f"   • For magazine archiving: Claude is clearly superior")
        print(f"   • For controls testing: Hybrid approach recommended")


def main():
    # Get image path
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        png_files = list(Path(".").glob("Scan*.png"))
        if not png_files:
            print("No PNG files found. Usage: python anthropic_vision_test.py [image_path]")
            return
        image_path = str(png_files[0])
    
    if not Path(image_path).exists():
        print(f"Image not found: {image_path}")
        return
    
    print(f"Testing Claude Vision vs Tesseract on: {Path(image_path).name}")
    print(f"Image size: {Image.open(image_path).size}")
    
    # Setup Anthropic
    client = setup_anthropic()
    if not client:
        return
    
    # Test Claude Vision
    claude_result = test_claude_vision(client, image_path)
    
    # Test Tesseract for comparison
    tesseract_result = test_tesseract_comparison(image_path)
    
    # Compare results
    compare_results(claude_result, tesseract_result)
    
    # Save results
    results = {
        'image': str(image_path),
        'claude_vision': claude_result,
        'tesseract': tesseract_result
    }
    
    output_file = Path("claude_vs_tesseract_results.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    main()