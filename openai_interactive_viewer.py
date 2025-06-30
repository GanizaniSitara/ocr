#!/usr/bin/env python3
"""
Interactive OpenAI Vision viewer with overlay text that can be toggled and copy/pasted.
"""

import base64
import json
from pathlib import Path
import openai
import os
import sys
from flask import Flask, render_template, request, jsonify, send_from_directory
import re


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
    """Extract text using OpenAI Vision with position estimation."""
    
    try:
        base64_image = encode_image(image_path)
        
        prompt = """Analyze this image and extract ALL visible text with approximate positions.

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
  },
  {
    "text": "ANDREW DENIES BEING CHINESE SPY",
    "x_percent": 50,
    "y_percent": 35,
    "size": "large", 
    "type": "headline"
  }
]

Be very thorough - extract ALL text including:
- Magazine title and issue info
- Headlines and subheadings
- Speech bubbles and captions
- Prices, dates, and other small text

Estimate positions as accurately as possible by looking at where the text appears relative to the image boundaries."""

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
            # Look for JSON array in the response
            json_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                extracted_data = json.loads(json_text)
                return extracted_data
            else:
                # Fallback: try to parse the whole response as JSON
                return json.loads(response_text)
                
        except json.JSONDecodeError:
            print("Could not parse as JSON, trying to extract manually...")
            # Manual fallback - look for text patterns
            return parse_text_manually(response_text)
            
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return []


def parse_text_manually(response_text):
    """Manual parsing fallback if JSON parsing fails."""
    # Simple fallback - extract quoted text and make rough position estimates
    import re
    
    lines = response_text.split('\n')
    results = []
    
    for line in lines:
        # Look for quoted text
        quotes = re.findall(r'"([^"]+)"', line)
        for quote in quotes:
            if len(quote) > 2:  # Skip very short matches
                results.append({
                    "text": quote,
                    "x_percent": 50,  # Default to center
                    "y_percent": 30 + len(results) * 15,  # Spread vertically
                    "size": "medium",
                    "type": "other"
                })
    
    return results


def load_cached_results():
    """Load previously processed results from cache file."""
    cache_file = Path("openai_cache.json")
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
    cache_file = Path("openai_cache.json")
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(processed_images, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(processed_images)} results to {cache_file}")
    except Exception as e:
        print(f"Error saving cache: {e}")


def process_image(image_path, force_reprocess=False):
    """Process image with OpenAI and store results."""
    
    image_name = Path(image_path).name
    
    # Check if already processed (unless forced)
    if not force_reprocess and image_name in processed_images:
        print(f"Using cached result for {image_name}")
        return processed_images[image_name]
    
    client = setup_openai()
    if not client:
        return None
    
    print(f"Processing {image_path} with OpenAI Vision...")
    
    # Extract text with positions
    text_data = extract_text_with_openai(client, image_path)
    
    # Store results
    processed_images[image_name] = {
        'image_path': image_path,
        'text_data': text_data,
        'total_texts': len(text_data)
    }
    
    return processed_images[image_name]


@app.route('/')
def index():
    """Main page showing available images."""
    return render_template('openai_viewer.html', images=list(processed_images.keys()))


@app.route('/view/<image_name>')
def view_image(image_name):
    """View specific image with text overlays."""
    
    if image_name not in processed_images:
        return "Image not processed", 404
    
    data = processed_images[image_name]
    return render_template('image_viewer.html', 
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
    """Create HTML templates for the web interface."""
    
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)
    
    # Main index template
    index_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenAI Vision Text Extractor</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        h1 { color: #333; text-align: center; }
        .image-list { list-style: none; padding: 0; }
        .image-item { 
            background: #f9f9f9; 
            margin: 10px 0; 
            padding: 15px; 
            border-radius: 5px; 
            border-left: 4px solid #007bff;
        }
        .image-item a { text-decoration: none; color: #007bff; font-weight: bold; }
        .image-item a:hover { color: #0056b3; }
        .stats { color: #666; font-size: 0.9em; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>OpenAI Vision Text Extractor</h1>
        <p>Interactive viewer for text extracted from images using OpenAI GPT-4V</p>
        
        {% if images %}
        <h2>Processed Images:</h2>
        <ul class="image-list">
            {% for image in images %}
            <li class="image-item">
                <a href="/view/{{ image }}">{{ image }}</a>
                <div class="stats">Click to view with interactive text overlays</div>
            </li>
            {% endfor %}
        </ul>
        {% else %}
        <p>No images processed yet. Run the script to process images.</p>
        {% endif %}
    </div>
</body>
</html>'''
    
    # Image viewer template
    viewer_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ image_name }} - OpenAI Vision Viewer</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f0f0f0; }
        .header { text-align: center; margin-bottom: 20px; }
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
            padding: 2px 4px;
            border-radius: 3px;
            font-weight: bold;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.7);
            transition: all 0.2s ease;
            user-select: text;
            z-index: 10;
        }
        
        .text-overlay.size-small { font-size: 12px; }
        .text-overlay.size-medium { font-size: 14px; }
        .text-overlay.size-large { font-size: 18px; }
        
        .text-overlay.type-masthead { color: #ff0000; background: rgba(255,255,255,0.9); }
        .text-overlay.type-headline { color: #ff6600; background: rgba(255,255,255,0.8); }
        .text-overlay.type-speech_bubble { color: #0066ff; background: rgba(255,255,255,0.8); }
        .text-overlay.type-caption { color: #009900; background: rgba(255,255,255,0.7); }
        .text-overlay.type-price { color: #cc0099; background: rgba(255,255,255,0.7); }
        .text-overlay.type-date { color: #666600; background: rgba(255,255,255,0.7); }
        .text-overlay.type-other { color: #333333; background: rgba(255,255,255,0.6); }
        
        .text-overlay:hover {
            background: rgba(255,255,0,0.9) !important;
            color: #000 !important;
            transform: scale(1.05);
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
            padding: 8px;
            margin: 5px 0;
            background: #f9f9f9;
            border-radius: 4px;
            cursor: pointer;
            border-left: 3px solid #007bff;
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
        <div class="stats">{{ image_data.total_texts }} text elements detected by OpenAI GPT-4V</div>
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
        <div class="stats">Click any text to highlight on image</div>
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
            
            const imageRect = mainImage.getBoundingClientRect();
            const containerRect = overlaysContainer.parentElement.getBoundingClientRect();
            
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
                listItem.innerHTML = `
                    <strong>${item.text}</strong><br>
                    <small>${item.type} (${item.size})</small>
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
    with open(templates_dir / "openai_viewer.html", "w", encoding='utf-8') as f:
        f.write(index_template)
    
    with open(templates_dir / "image_viewer.html", "w", encoding='utf-8') as f:
        f.write(viewer_template)


def main():
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='OpenAI Vision Interactive Viewer')
    parser.add_argument('--reprocess', action='store_true', help='Force reprocessing of all images')
    parser.add_argument('--cache-only', action='store_true', help='Only use cached results, no new processing')
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
        # Get all PNG files and select images to process
        png_files = sorted(list(Path(".").glob("*.png")))
        if not png_files:
            print("No PNG files found to process")
            return
        
        # Determine which images to process
        images_to_process = []
        
        if args.reprocess:
            print("Reprocessing mode: will reprocess all cached images")
            # Reprocess all previously cached images
            for image_name in processed_images.keys():
                matching_files = [f for f in png_files if f.name == image_name]
                if matching_files:
                    images_to_process.extend(matching_files)
        else:
            # Normal mode: process first + random if not already cached
            
            # 1. First image (cover page)
            first_image = png_files[0]
            if first_image.name not in processed_images:
                images_to_process.append(first_image)
                print(f"Selected cover page: {first_image.name}")
            else:
                print(f"Cover page already cached: {first_image.name}")
            
            # 2. One random image from the rest (if not enough cached)
            if len(processed_images) < 2 and len(png_files) > 1:
                import random
                remaining_files = [f for f in png_files[1:] if f.name not in processed_images]
                if remaining_files:
                    random_image = random.choice(remaining_files)
                    images_to_process.append(random_image)
                    print(f"Selected random page: {random_image.name}")
        
        # Process selected images
        if images_to_process:
            print(f"\nProcessing {len(images_to_process)} images with OpenAI Vision...")
            
            for image_path in images_to_process:
                print(f"\nProcessing {image_path.name}...")
                result = process_image(str(image_path), force_reprocess=args.reprocess)
                if result:
                    print(f"  Success: {result['total_texts']} text elements found")
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
        print(f"\nFeatures:")
        print(f"   - Click text to copy to clipboard")
        print(f"   - Toggle text overlays on/off") 
        print(f"   - Color-coded by text type")
        print(f"   - Sidebar with all extracted text")
        print(f"\nCommands for next run:")
        print(f"   python openai_interactive_viewer.py --cache-only    (use cached results only)")
        print(f"   python openai_interactive_viewer.py --reprocess     (reprocess all images)")
        
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("No images available to display")


if __name__ == "__main__":
    main()