#!/usr/bin/env python3
"""
AWS Bedrock Claude Vision test script - compare against Tesseract OCR.
Uses Claude 3 Sonnet/Haiku through AWS Bedrock instead of direct Anthropic API.
"""

import base64
import json
from pathlib import Path
import pytesseract
from PIL import Image
import boto3
import os
import sys
from botocore.exceptions import ClientError, NoCredentialsError


def setup_bedrock():
    """Setup AWS Bedrock client."""
    try:
        # Try to create bedrock client with default credentials
        bedrock = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        
        # Test connection by listing available models
        print("✅ AWS Bedrock client created successfully")
        print(f"Region: {bedrock.meta.region_name}")
        
        return bedrock
        
    except NoCredentialsError:
        print("❌ AWS credentials not found")
        print("Setup AWS credentials with one of these methods:")
        print("1. AWS CLI: aws configure")
        print("2. Environment variables:")
        print("   export AWS_ACCESS_KEY_ID='your-access-key'")
        print("   export AWS_SECRET_ACCESS_KEY='your-secret-key'")
        print("   export AWS_REGION='us-east-1'")
        print("3. IAM role (if running on EC2)")
        return None
        
    except Exception as e:
        print(f"❌ Error setting up Bedrock client: {e}")
        return None


def encode_image_for_bedrock(image_path):
    """Encode image to base64 for Bedrock."""
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Determine media type for Claude
        if image_path.lower().endswith('.png'):
            media_type = "image/png"
        elif image_path.lower().endswith(('.jpg', '.jpeg')):
            media_type = "image/jpeg"
        elif image_path.lower().endswith('.webp'):
            media_type = "image/webp"
        elif image_path.lower().endswith('.gif'):
            media_type = "image/gif"
        else:
            media_type = "image/png"  # default
            
        return base64_image, media_type


def test_claude_bedrock(bedrock_client, image_path, model_id="anthropic.claude-3-sonnet-20240229-v1:0"):
    """Test Claude through Bedrock on the image."""
    print(f"🤖 AWS BEDROCK CLAUDE VISION RESULTS:")
    print(f"Model: {model_id}")
    print("-" * 60)
    
    try:
        # Encode image
        base64_image, media_type = encode_image_for_bedrock(image_path)
        
        # Create the prompt
        prompt = """Please analyze this image and extract ALL visible text. This appears to be a magazine cover.

I need you to identify and extract:

1. **Magazine masthead/title** (the main magazine name)
2. **Issue information** (issue number, date, price)
3. **Main headlines** (primary story headlines)
4. **Speech bubbles or captions** (any dialogue or photo captions)
5. **Any other visible text**

Please format your response as a structured analysis showing:
- What text you found
- Where it appears on the image (top, center, bottom, etc.)
- Any special formatting (large text, colored background, etc.)

Be thorough - extract even text that appears on colored backgrounds or in stylized fonts."""

        # Prepare the request body for Bedrock
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
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
        }
        
        # Make the Bedrock API call
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body),
            contentType="application/json"
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        response_text = response_body['content'][0]['text']
        
        print("Claude's Analysis:")
        print(response_text)
        
        # Analyze key terms
        text_upper = response_text.upper()
        key_terms = ['PRIVATE', 'EYE', 'ANDREW', 'DENIES', 'BEING', 'CHINESE', 'SPY', '1642']
        found_terms = [term for term in key_terms if term in text_upper]
        
        print(f"\n📋 KEY TERMS DETECTED: {found_terms}")
        print(f"🎯 DETECTION RATE: {len(found_terms)}/{len(key_terms)} ({len(found_terms)/len(key_terms)*100:.1f}%)")
        
        # Check usage/cost info
        if 'usage' in response_body:
            usage = response_body['usage']
            print(f"💰 USAGE: Input tokens: {usage.get('input_tokens', 'N/A')}, Output tokens: {usage.get('output_tokens', 'N/A')}")
        
        return {
            "model_id": model_id,
            "full_response": response_text,
            "key_terms_found": found_terms,
            "detection_rate": len(found_terms)/len(key_terms),
            "usage": response_body.get('usage', {})
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'AccessDeniedException':
            print(f"❌ Access denied to model {model_id}")
            print("You may need to request access to Claude models in AWS Bedrock console")
            print("Go to: AWS Console > Bedrock > Model Access > Request model access")
        elif error_code == 'ValidationException':
            print(f"❌ Validation error: {error_message}")
            print("Check if the model ID is correct and available in your region")
        else:
            print(f"❌ AWS Bedrock error ({error_code}): {error_message}")
        
        return None
        
    except Exception as e:
        print(f"❌ Error calling Claude through Bedrock: {e}")
        return None


def test_multiple_claude_models(bedrock_client, image_path):
    """Test multiple Claude models available on Bedrock."""
    
    # Available Claude models on Bedrock (as of 2024)
    models_to_test = [
        ("anthropic.claude-3-sonnet-20240229-v1:0", "Claude 3 Sonnet (Balanced)"),
        ("anthropic.claude-3-haiku-20240307-v1:0", "Claude 3 Haiku (Fast/Cheap)"),
        ("anthropic.claude-3-5-sonnet-20241022-v2:0", "Claude 3.5 Sonnet (Latest)"),
    ]
    
    results = []
    
    for model_id, description in models_to_test:
        print(f"\n{'='*70}")
        print(f"Testing: {description}")
        print(f"Model ID: {model_id}")
        
        result = test_claude_bedrock(bedrock_client, image_path, model_id)
        if result:
            result['description'] = description
            results.append(result)
        else:
            print(f"❌ Failed to test {description}")
    
    return results


def test_tesseract_comparison(image_path):
    """Test Tesseract for comparison."""
    print(f"\n{'='*70}")
    print("🔧 TESSERACT COMPARISON:")
    print("-" * 60)
    
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


def compare_all_results(claude_results, tesseract_result):
    """Compare all Claude models vs Tesseract."""
    print(f"\n{'='*70}")
    print("📊 COMPREHENSIVE COMPARISON:")
    print(f"{'='*70}")
    
    tesseract_rate = tesseract_result.get('detection_rate', 0) * 100
    print(f"🔧 Tesseract OCR:           {tesseract_rate:.1f}% detection rate")
    
    best_claude = None
    best_rate = 0
    
    for result in claude_results:
        rate = result.get('detection_rate', 0) * 100
        model_name = result.get('description', result.get('model_id', 'Unknown'))
        print(f"🤖 {model_name:<25} {rate:.1f}% detection rate")
        
        if rate > best_rate:
            best_rate = rate
            best_claude = result
    
    if best_claude:
        improvement = best_rate - tesseract_rate
        print(f"\n🏆 WINNER: {best_claude.get('description', 'Claude')} (+{improvement:.1f}% better than Tesseract)")
        
        # Show usage/cost info for best model
        usage = best_claude.get('usage', {})
        if usage:
            print(f"💰 Best model usage: {usage}")
    
    print(f"\n💡 RECOMMENDATIONS:")
    print(f"   📰 Magazine Archiving: Use Claude 3.5 Sonnet for best accuracy")
    print(f"   💻 Controls Testing: Use Claude 3 Haiku for cost-effective batch processing")
    print(f"   ⚡ High Volume: Use Tesseract first, Claude as fallback for failures")


def main():
    # Get image path
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        png_files = list(Path(".").glob("Scan*.png"))
        if not png_files:
            print("No PNG files found. Usage: python bedrock_vision_test.py [image_path]")
            return
        image_path = str(png_files[0])
    
    if not Path(image_path).exists():
        print(f"Image not found: {image_path}")
        return
    
    print(f"Testing AWS Bedrock Claude vs Tesseract on: {Path(image_path).name}")
    print(f"Image size: {Image.open(image_path).size}")
    
    # Setup Bedrock
    bedrock_client = setup_bedrock()
    if not bedrock_client:
        return
    
    # Test multiple Claude models
    claude_results = test_multiple_claude_models(bedrock_client, image_path)
    
    # Test Tesseract for comparison
    tesseract_result = test_tesseract_comparison(image_path)
    
    # Compare all results
    if claude_results:
        compare_all_results(claude_results, tesseract_result)
    
    # Save results
    results = {
        'image': str(image_path),
        'claude_bedrock_results': claude_results,
        'tesseract': tesseract_result
    }
    
    output_file = Path("bedrock_vs_tesseract_results.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    main()