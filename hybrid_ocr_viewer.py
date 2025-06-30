#!/usr/bin/env python3
"""
Hybrid OCR viewer: OpenAI Vision for covers, analytical OCR for content pages.
Uses the UX paradigm with caching and toggleable overlays.
"""

import base64
import json
from pathlib import Path
import openai
import os
import sys
from flask import Flask, render_template, request, jsonify, send_from_directory
import re
import pytesseract
from PIL import Image
from bs4 import BeautifulSoup


app = Flask(__name__)

# Global storage for processed images
processed_images = {}


def setup_openai():
    """Setup OpenAI client with API key."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        return None
    return openai.OpenAI(api_key=api_key)


def encode_image(image_path):
    """Encode image to base64 for OpenAI API."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def extract_text_with_openai(client, image_path):
    """Extract text using OpenAI Vision with position estimation (for covers)."""
    
    try:
        base64_image = encode_image(image_path)
        
        prompt = """Analyze this magazine cover and extract ALL visible text with approximate positions.

For each piece of text you find, provide:
1. The exact text content
2. Approximate position as percentage from top-left (0-100% for both x and y)
3. Approximate size (small/medium/large)
4. Text type (masthead/headline/caption/speech_bubble/price/date/other)

Format your response as a JSON array like this:
[
  {
    "text": "PRIVATE EYE",
    "x_percent": 50,
    "y_percent": 15,
    "size": "large",
    "type": "masthead"
  }
]

Be thorough - extract ALL text including titles, headlines, speech bubbles, prices, dates."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1500
        )
        
        response_text = response.choices[0].message.content
        
        # Try to extract JSON from response
        try:
            json_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                extracted_data = json.loads(json_text)
                return extracted_data
            else:
                return json.loads(response_text)
                
        except json.JSONDecodeError:
            print("Could not parse OpenAI response as JSON, using fallback...")
            return parse_text_manually(response_text)
            
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return []


def extract_text_with_analytical_ocr(image_path):
    """Extract text using analytical OCR with bounding boxes (for content pages)."""
    
    try:
        print(f"Using analytical OCR for content page: {image_path}")
        
        # Load image
        image = Image.open(image_path)
        image_width, image_height = image.size
        
        # Use optimal PSM for content pages
        config = "--psm 3 --oem 3"  # The configuration that worked well
        
        # Get HOCR output with bounding boxes
        hocr_output = pytesseract.image_to_pdf_or_hocr(image, config=config, extension='hocr')
        
        # Parse HOCR
        soup = BeautifulSoup(hocr_output, 'html.parser')
        
        extracted_data = []
        
        # Extract words with bounding boxes and confidence
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
                        
                        # Convert absolute coordinates to percentages
                        x_percent = (coords[0] / image_width) * 100
                        y_percent = (coords[1] / image_height) * 100
                        
                        # Determine size based on bounding box dimensions
                        width = coords[2] - coords[0]
                        height = coords[3] - coords[1]
                        
                        if height > 20:
                            size = "large"
                        elif height > 12:
                            size = "medium"
                        else:
                            size = "small"
                        
                        extracted_data.append({
                            "text": text,
                            "x_percent": x_percent,
                            "y_percent": y_percent,
                            "size": size,
                            "type": "content",
                            "confidence": confidence,
                            "bbox": coords
                        })
        
        print(f"Analytical OCR extracted {len(extracted_data)} text elements")
        return extracted_data
        
    except Exception as e:
        print(f"Error in analytical OCR: {e}")
        return []


def parse_text_manually(response_text):
    """Manual parsing fallback if JSON parsing fails."""
    import re
    
    lines = response_text.split('\n')
    results = []
    
    for line in lines:
        quotes = re.findall(r'"([^"]+)"', line)
        for quote in quotes:
            if len(quote) > 2:
                results.append({
                    "text": quote,
                    "x_percent": 50,
                    "y_percent": 30 + len(results) * 15,
                    "size": "medium",
                    "type": "other"
                })
    
    return results


def is_cover_page(image_path):
    """Determine if this is a cover page or content page."""
    image_name = Path(image_path).name.lower()
    
    # Heuristics for cover pages
    cover_indicators = [
        '000',  # Often first page
        'cover',
        'front'
    ]
    
    # Check if it's the first file (sorted)
    png_files = sorted(list(Path(image_path).parent.glob("*.png")))
    if png_files and str(png_files[0]) == str(image_path):
        return True
    
    # Check filename patterns
    for indicator in cover_indicators:
        if indicator in image_name:
            return True
    
    return False


def load_cached_results():
    """Load previously processed results from cache file."""
    cache_file = Path("hybrid_ocr_cache.json")
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                processed_images.update(cached_data)
                print(f"Loaded {len(cached_data)} cached results from {cache_file}")
                return True
        except Exception as e:
            print(f"Error loading cache: {e}")
    return False


def save_cached_results():
    """Save processed results to cache file."""
    cache_file = Path("hybrid_ocr_cache.json")
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(processed_images, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(processed_images)} results to {cache_file}")
    except Exception as e:
        print(f"Error saving cache: {e}")


def process_image(image_path, force_reprocess=False):
    """Process image with appropriate OCR method and store results."""
    
    image_name = Path(image_path).name
    
    # Check if already processed (unless forced)
    if not force_reprocess and image_name in processed_images:
        print(f"Using cached result for {image_name}")
        return processed_images[image_name]
    
    # Determine processing method
    if is_cover_page(image_path):
        print(f"Detected cover page - using OpenAI Vision: {image_name}")
        client = setup_openai()
        if not client:
            print("OpenAI not available, falling back to analytical OCR")
            text_data = extract_text_with_analytical_ocr(image_path)
            method = "analytical_ocr_fallback"
        else:
            text_data = extract_text_with_openai(client, image_path)
            method = "openai_vision"
    else:
        print(f"Detected content page - using analytical OCR: {image_name}")
        text_data = extract_text_with_analytical_ocr(image_path)
        method = "analytical_ocr"
    
    # Store results
    processed_images[image_name] = {
        'image_path': image_path,
        'text_data': text_data,
        'total_texts': len(text_data),
        'method': method
    }
    
    return processed_images[image_name]


@app.route('/')
def index():
    """Main page showing available images."""
    return render_template('hybrid_viewer.html', images=list(processed_images.keys()))


@app.route('/view/<image_name>')
def view_image(image_name):
    """View specific image with text overlays."""
    
    if image_name not in processed_images:
        return "Image not processed", 404
    
    data = processed_images[image_name]
    return render_template('hybrid_image_viewer.html', 
                         image_name=image_name,
                         image_data=data)


@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve image files."""
    return send_from_directory('.', filename)


@app.route('/api/text_data/<image_name>')
def get_text_data(image_name):
    """API endpoint to get text data for an image."""
    if image_name in processed_images:
        return jsonify(processed_images[image_name]['text_data'])
    return jsonify([])


def create_templates():
    """Create HTML templates for the hybrid OCR interface."""
    
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)
    
    # Main index template
    index_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hybrid OCR Text Extractor</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        h1 { color: #333; text-align: center; }
        .subtitle { text-align: center; color: #666; margin-bottom: 30px; }
        .image-list { list-style: none; padding: 0; }
        .image-item { 
            background: #f9f9f9; 
            margin: 10px 0; 
            padding: 15px; 
            border-radius: 5px; 
            border-left: 4px solid #007bff;
        }
        .image-item.openai { border-left-color: #28a745; }
        .image-item.analytical { border-left-color: #ffc107; }
        .image-item a { text-decoration: none; color: #007bff; font-weight: bold; }
        .image-item a:hover { color: #0056b3; }
        .stats { color: #666; font-size: 0.9em; margin-top: 5px; }
        .method-tag { 
            display: inline-block; 
            padding: 2px 6px; 
            border-radius: 3px; 
            font-size: 0.8em; 
            font-weight: bold; 
        }
        .method-openai { background: #d4edda; color: #155724; }
        .method-analytical { background: #fff3cd; color: #856404; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Hybrid OCR Text Extractor</h1>
        <div class="subtitle">OpenAI Vision for covers • Analytical OCR for content pages</div>
        
        {% if images %}
        <h2>Processed Images:</h2>
        <ul class="image-list">
            {% for image in images %}
            {% set data = processed_images[image] %}
            <li class="image-item {{ data.method.replace('_', '-') }}">
                <a href="/view/{{ image }}">{{ image }}</a>
                <span class="method-tag method-{{ data.method.replace('_', '-') }}">
                    {{ data.method.replace('_', ' ').title() }}
                </span>
                <div class="stats">
                    {{ data.total_texts }} text elements • Click to view with interactive overlays
                </div>
            </li>
            {% endfor %}
        </ul>
        {% else %}
        <p>No images processed yet. Run the script to process images.</p>
        {% endif %}
    </div>
</body>
</html>'''
    
    # Update the image viewer template with method info
    viewer_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ image_name }} - Hybrid OCR Viewer</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f0f0f0; }
        .header { text-align: center; margin-bottom: 20px; }
        .method-info { 
            text-align: center; 
            margin-bottom: 15px; 
            padding: 8px; 
            border-radius: 5px; 
            font-weight: bold;
        }
        .method-openai-vision { background: #d4edda; color: #155724; }
        .method-analytical-ocr { background: #fff3cd; color: #856404; }
        .method-analytical-ocr-fallback { background: #f8d7da; color: #721c24; }
        
        .controls { text-align: center; margin-bottom: 15px; }
        .toggle-btn {
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin: 0 10px;
        }
        .toggle-btn:hover { background: #0056b3; }
        .toggle-btn.active { background: #28a745; }
        
        .image-container {
            position: relative;
            display: inline-block;
            border: 2px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
            background: white;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            margin: 0 auto;
            display: block;
            max-width: 90vw;
        }
        
        .main-image {
            max-width: 100%;
            height: auto;
            display: block;
        }
        
        .text-overlay {
            position: absolute;
            cursor: pointer;
            padding: 1px 2px;
            border-radius: 2px;
            font-weight: bold;
            text-shadow: 1px 1px 1px rgba(0,0,0,0.5);
            transition: all 0.2s ease;
            user-select: text;
            z-index: 10;
            border: 1px solid rgba(255,255,255,0.3);
        }
        
        .text-overlay.size-small { font-size: 10px; }
        .text-overlay.size-medium { font-size: 12px; }
        .text-overlay.size-large { font-size: 16px; }
        
        .text-overlay.type-masthead { color: #ffffff; background: rgba(255,0,0,0.8); }
        .text-overlay.type-headline { color: #ffffff; background: rgba(255,102,0,0.8); }
        .text-overlay.type-speech_bubble { color: #ffffff; background: rgba(0,102,255,0.8); }
        .text-overlay.type-caption { color: #ffffff; background: rgba(0,153,0,0.8); }
        .text-overlay.type-price { color: #ffffff; background: rgba(204,0,153,0.8); }
        .text-overlay.type-date { color: #ffffff; background: rgba(102,102,0,0.8); }
        .text-overlay.type-content { color: #000000; background: rgba(255,255,255,0.7); }
        .text-overlay.type-other { color: #ffffff; background: rgba(51,51,51,0.8); }
        
        .text-overlay:hover {
            background: rgba(255,255,0,0.9) !important;
            color: #000 !important;
            transform: scale(1.1);
            z-index: 20;
        }
        
        .text-overlay.hidden { display: none; }
        
        .sidebar {
            position: fixed;
            right: 20px;
            top: 100px;
            width: 300px;
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            max-height: 70vh;
            overflow-y: auto;
        }
        
        .text-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        
        .text-item {
            padding: 6px;
            margin: 3px 0;
            background: #f9f9f9;
            border-radius: 3px;
            cursor: pointer;
            border-left: 3px solid #007bff;
            font-size: 0.85em;
        }
        
        .text-item:hover { background: #e9ecef; }
        .text-item.selected { background: #d4edda; border-left-color: #28a745; }
        
        .back-link {
            display: inline-block;
            margin-bottom: 15px;
            color: #007bff;
            text-decoration: none;
        }
        
        .stats {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <a href="/" class="back-link">← Back to Image List</a>
        <h1>{{ image_name }}</h1>
        <div class="method-info method-{{ image_data.method.replace('_', '-') }}">
            Processing Method: {{ image_data.method.replace('_', ' ').title() }}
        </div>
        <div class="stats">{{ image_data.total_texts }} text elements detected</div>
    </div>
    
    <div class="controls">
        <button id="toggleOverlays" class="toggle-btn active">Hide Text Overlays</button>
        <button id="toggleSidebar" class="toggle-btn">Toggle Sidebar</button>
    </div>
    
    <div class="image-container">
        <img src="/images/{{ image_name }}" class="main-image" id="mainImage" alt="{{ image_name }}">
        <div id="textOverlays"></div>
    </div>
    
    <div class="sidebar" id="sidebar">
        <h3>Extracted Text</h3>
        <div class="stats">Click any text to copy to clipboard</div>
        <ul class="text-list" id="textList"></ul>
    </div>

    <script>
        const imageData = {{ image_data.text_data | tojson }};
        const overlaysContainer = document.getElementById('textOverlays');
        const textList = document.getElementById('textList');
        const toggleBtn = document.getElementById('toggleOverlays');
        const sidebarBtn = document.getElementById('toggleSidebar');
        const sidebar = document.getElementById('sidebar');
        const mainImage = document.getElementById('mainImage');
        
        let overlaysVisible = true;
        let sidebarVisible = true;
        
        function createOverlays() {
            overlaysContainer.innerHTML = '';
            textList.innerHTML = '';
            
            imageData.forEach((item, index) => {
                // Create overlay element
                const overlay = document.createElement('div');
                overlay.className = `text-overlay size-${item.size} type-${item.type}`;
                overlay.textContent = item.text;
                overlay.dataset.index = index;
                
                // Position based on percentages
                const x = (item.x_percent / 100) * mainImage.clientWidth;
                const y = (item.y_percent / 100) * mainImage.clientHeight;
                
                overlay.style.left = x + 'px';
                overlay.style.top = y + 'px';
                
                overlay.addEventListener('click', () => selectText(index));
                overlaysContainer.appendChild(overlay);
                
                // Create sidebar list item
                const listItem = document.createElement('li');
                listItem.className = 'text-item';
                const confText = item.confidence ? ` (${item.confidence}%)` : '';
                listItem.innerHTML = `
                    <strong>${item.text}</strong>${confText}<br>
                    <small>${item.type} • ${item.size}</small>
                `;
                listItem.dataset.index = index;
                listItem.addEventListener('click', () => selectText(index));
                textList.appendChild(listItem);
            });
        }
        
        function selectText(index) {
            // Clear previous selections
            document.querySelectorAll('.text-overlay, .text-item').forEach(el => {
                el.classList.remove('selected');
            });
            
            // Select current
            const overlay = document.querySelector(`[data-index="${index}"]`);
            if (overlay) {
                overlay.classList.add('selected');
                
                // Copy text to clipboard
                const text = imageData[index].text;
                navigator.clipboard.writeText(text).then(() => {
                    console.log('Copied to clipboard:', text);
                }).catch(err => {
                    console.log('Could not copy to clipboard');
                });
            }
        }
        
        function toggleOverlays() {
            overlaysVisible = !overlaysVisible;
            const overlays = document.querySelectorAll('.text-overlay');
            
            overlays.forEach(overlay => {
                overlay.classList.toggle('hidden', !overlaysVisible);
            });
            
            toggleBtn.textContent = overlaysVisible ? 'Hide Text Overlays' : 'Show Text Overlays';
            toggleBtn.classList.toggle('active', overlaysVisible);
        }
        
        function toggleSidebar() {
            sidebarVisible = !sidebarVisible;
            sidebar.style.display = sidebarVisible ? 'block' : 'none';
            sidebarBtn.textContent = sidebarVisible ? 'Hide Sidebar' : 'Show Sidebar';
        }
        
        // Event listeners
        toggleBtn.addEventListener('click', toggleOverlays);
        sidebarBtn.addEventListener('click', toggleSidebar);
        mainImage.addEventListener('load', createOverlays);
        window.addEventListener('resize', createOverlays);
        
        // Initial setup
        if (mainImage.complete) {
            createOverlays();
        }
    </script>
</body>
</html>'''
    
    # Write templates with UTF-8 encoding
    with open(templates_dir / "hybrid_viewer.html", "w", encoding='utf-8') as f:
        f.write(index_template)
    
    with open(templates_dir / "hybrid_image_viewer.html", "w", encoding='utf-8') as f:
        f.write(viewer_template)


def main():
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Hybrid OCR Interactive Viewer')
    parser.add_argument('--reprocess', action='store_true', help='Force reprocessing of all images')
    parser.add_argument('--cache-only', action='store_true', help='Only use cached results, no new processing')
    parser.add_argument('--content-page', help='Specific content page to process (e.g., 033)')
    args = parser.parse_args()
    
    # Create templates
    create_templates()
    
    # Load cached results first
    load_cached_results()
    
    if args.cache_only:
        print("Cache-only mode: using existing cached results")
        if not processed_images:
            print("No cached results found. Run without --cache-only to process images.")
            return
    else:
        # Get all PNG files
        png_files = sorted(list(Path(".").glob("*.png")))
        if not png_files:
            print("No PNG files found to process")
            return
        
        # Determine which images to process
        images_to_process = []
        
        if args.reprocess:
            print("Reprocessing mode: will reprocess all cached images")
            for image_name in processed_images.keys():
                matching_files = [f for f in png_files if f.name == image_name]
                if matching_files:
                    images_to_process.extend(matching_files)
        elif args.content_page:
            # Process specific content page
            content_files = [f for f in png_files if args.content_page in f.name]
            if content_files:
                images_to_process.extend(content_files)
                print(f"Selected specific content page: {[f.name for f in content_files]}")
            else:
                print(f"No files found matching '{args.content_page}'")
        else:
            # Normal mode: process cover + one content page if not cached
            
            # 1. Cover page (first file)
            first_image = png_files[0]
            if first_image.name not in processed_images:
                images_to_process.append(first_image)
                print(f"Selected cover page: {first_image.name}")
            else:
                print(f"Cover page already cached: {first_image.name}")
            
            # 2. One content page from the rest
            if len(processed_images) < 2 and len(png_files) > 1:
                import random
                remaining_files = [f for f in png_files[1:] if f.name not in processed_images]
                if remaining_files:
                    # Prefer content pages (with numbers)
                    numbered_files = [f for f in remaining_files if any(c.isdigit() for c in f.name)]
                    if numbered_files:
                        content_page = random.choice(numbered_files)
                    else:
                        content_page = random.choice(remaining_files)
                    images_to_process.append(content_page)
                    print(f"Selected content page: {content_page.name}")
        
        # Process selected images
        if images_to_process:
            print(f"\nProcessing {len(images_to_process)} images with hybrid OCR...")
            
            for image_path in images_to_process:
                print(f"\nProcessing {image_path.name}...")
                result = process_image(str(image_path), force_reprocess=args.reprocess)
                if result:
                    print(f"  Success: {result['total_texts']} text elements found using {result['method']}")
                else:
                    print(f"  Failed to process {image_path.name}")
            
            # Save updated cache
            save_cached_results()
        else:
            print("All selected images already processed (cached)")
    
    if processed_images:
        print(f"\nStarting web server...")
        print(f"Available images: {list(processed_images.keys())}")
        print(f"Open your browser to: http://localhost:5000")
        print(f"\nProcessing methods used:")
        for name, data in processed_images.items():
            print(f"  {name}: {data['method']}")
        print(f"\nCommands for next run:")
        print(f"   python hybrid_ocr_viewer.py --cache-only           (use cached results only)")
        print(f"   python hybrid_ocr_viewer.py --reprocess            (reprocess all images)")
        print(f"   python hybrid_ocr_viewer.py --content-page 033     (process specific page)")
        
        # Add processed_images to app context for templates
        app.jinja_env.globals['processed_images'] = processed_images
        
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("No images available to display")


if __name__ == "__main__":
    main()