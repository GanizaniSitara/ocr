#!/usr/bin/env python3
"""
Web viewer for PrivateEye magazine archive with clickable OCR text overlays.
"""

import json
import os
from pathlib import Path
from flask import Flask, render_template, jsonify, send_from_directory

app = Flask(__name__)

@app.template_filter('basename')
def basename_filter(path):
    """Custom filter to get basename of a path."""
    return Path(path).name

@app.template_filter('tojsonfilter')
def to_json_filter(obj):
    """Custom filter to convert object to JSON."""
    return json.dumps(obj)

# Global storage for OCR data
ocr_data = []
image_dir = Path(".")


def load_ocr_data(json_file: Path = Path("magazine_ocr.json")):
    """Load OCR data from JSON file."""
    global ocr_data
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            ocr_data = json.load(f)
        print(f"Loaded OCR data for {len(ocr_data)} pages")
    except FileNotFoundError:
        print(f"OCR data file {json_file} not found. Run ocr_extractor.py first.")
        ocr_data = []


@app.route('/')
def index():
    """Main page showing magazine page list."""
    pages = [{'index': i, 'filename': Path(page['source']).name} 
             for i, page in enumerate(ocr_data)]
    return render_template('index.html', pages=pages)


@app.route('/page/<int:page_index>')
def view_page(page_index):
    """View specific magazine page with OCR overlay."""
    if page_index >= len(ocr_data):
        return "Page not found", 404
    
    page_data = ocr_data[page_index]
    return render_template('page_viewer.html', 
                         page_data=page_data, 
                         page_index=page_index)


@app.route('/api/page/<int:page_index>')
def api_page_data(page_index):
    """API endpoint to get page OCR data."""
    if page_index >= len(ocr_data):
        return jsonify({'error': 'Page not found'}), 404
    
    return jsonify(ocr_data[page_index])


@app.route('/images/<filename>')
def serve_image(filename):
    """Serve PNG images."""
    return send_from_directory(image_dir, filename)


@app.route('/search/<query>')
def search_pages(query):
    """Search through OCR text across all pages."""
    results = []
    query_lower = query.lower()
    
    for i, page in enumerate(ocr_data):
        if query_lower in page['full_text'].lower():
            # Find specific words that match
            matching_words = [
                word for word in page['words'] 
                if query_lower in word['text'].lower()
            ]
            results.append({
                'page_index': i,
                'filename': Path(page['source']).name,
                'matches': len(matching_words),
                'words': matching_words[:10]  # Limit to first 10 matches
            })
    
    return jsonify(results)


def create_templates():
    """Create HTML templates for the web interface."""
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)
    
    # Main index template
    index_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PrivateEye Magazine Archive</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .page-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }
        .page-card { border: 1px solid #ddd; padding: 15px; border-radius: 5px; text-align: center; }
        .page-card:hover { background-color: #f5f5f5; }
        .page-card a { text-decoration: none; color: #333; }
        .search-box { margin-bottom: 20px; }
        .search-box input { padding: 10px; width: 300px; margin-right: 10px; }
        .search-box button { padding: 10px 20px; }
    </style>
</head>
<body>
    <h1>PrivateEye Magazine Archive</h1>
    
    <div class="search-box">
        <input type="text" id="searchQuery" placeholder="Search through magazine pages...">
        <button onclick="searchPages()">Search</button>
    </div>
    
    <div id="searchResults" style="display: none;">
        <h3>Search Results</h3>
        <div id="resultsContainer"></div>
    </div>
    
    <h2>Magazine Pages ({{ pages|length }} total)</h2>
    <div class="page-list">
        {% for page in pages %}
        <div class="page-card">
            <a href="/page/{{ page.index }}">
                <div>Page {{ page.index + 1 }}</div>
                <div>{{ page.filename }}</div>
            </a>
        </div>
        {% endfor %}
    </div>

    <script>
        function searchPages() {
            const query = document.getElementById('searchQuery').value;
            if (!query) return;
            
            fetch(`/search/${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(results => {
                    const container = document.getElementById('resultsContainer');
                    const resultsDiv = document.getElementById('searchResults');
                    
                    if (results.length === 0) {
                        container.innerHTML = '<p>No results found.</p>';
                    } else {
                        container.innerHTML = results.map(result => 
                            `<div style="border: 1px solid #ddd; padding: 10px; margin: 10px 0;">
                                <a href="/page/${result.page_index}">
                                    <strong>Page ${result.page_index + 1}</strong> (${result.filename})
                                </a>
                                <br>Found ${result.matches} matches
                            </div>`
                        ).join('');
                    }
                    resultsDiv.style.display = 'block';
                });
        }
        
        document.getElementById('searchQuery').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchPages();
            }
        });
    </script>
</body>
</html>'''
    
    # Page viewer template
    page_viewer_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Page {{ page_index + 1 }} - PrivateEye Archive</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        .viewer-container { display: flex; gap: 20px; }
        .image-container { 
            position: relative; 
            border: 1px solid #ddd; 
        }
        .page-image { 
            max-width: 800px; 
            height: auto; 
            display: block; 
        }
        .text-overlay {
            position: absolute;
            cursor: pointer;
            background-color: rgba(255, 255, 0, 0.1);
            border: 1px solid rgba(255, 255, 0, 0.3);
            transition: background-color 0.2s;
        }
        .text-overlay:hover {
            background-color: rgba(255, 255, 0, 0.3);
        }
        .sidebar {
            width: 300px;
            max-height: 600px;
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 15px;
        }
        .navigation {
            margin-bottom: 20px;
        }
        .navigation a {
            margin-right: 15px;
            text-decoration: none;
            color: #007bff;
        }
        .word-info {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 3px;
        }
        .full-text {
            font-size: 12px;
            line-height: 1.4;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="navigation">
        <a href="/">&larr; Back to Archive</a>
        {% if page_index > 0 %}
        <a href="/page/{{ page_index - 1 }}">&larr; Previous Page</a>
        {% endif %}
        <span>Page {{ page_index + 1 }}</span>
        <a href="/page/{{ page_index + 1 }}">Next Page &rarr;</a>
    </div>

    <h1>{{ page_data.source | basename }} (Page {{ page_index + 1 }})</h1>
    
    <div class="viewer-container">
        <div class="image-container">
            <img src="/images/{{ page_data.source | basename }}" 
                 class="page-image" 
                 id="pageImage"
                 alt="Magazine page">
            <div id="textOverlays"></div>
        </div>
        
        <div class="sidebar">
            <h3>Page Information</h3>
            <p><strong>Words detected:</strong> {{ page_data.word_count }}</p>
            <p><strong>Image size:</strong> {{ page_data.image_width }} × {{ page_data.image_height }}</p>
            
            <div id="selectedWordInfo" style="display: none;">
                <h4>Selected Text</h4>
                <div id="wordDetails"></div>
            </div>
            
            <h4>Full Text</h4>
            <div class="full-text">{{ page_data.full_text }}</div>
        </div>
    </div>

    <script>
        const pageData = {{ page_data | tojsonfilter }};
        const imageElement = document.getElementById('pageImage');
        const overlaysContainer = document.getElementById('textOverlays');
        
        function createOverlays() {
            const img = imageElement;
            const containerRect = img.getBoundingClientRect();
            const scaleX = img.clientWidth / pageData.image_width;
            const scaleY = img.clientHeight / pageData.image_height;
            
            overlaysContainer.innerHTML = '';
            
            pageData.words.forEach((word, index) => {
                const overlay = document.createElement('div');
                overlay.className = 'text-overlay';
                overlay.style.left = (word.left * scaleX) + 'px';
                overlay.style.top = (word.top * scaleY) + 'px';
                overlay.style.width = (word.width * scaleX) + 'px';
                overlay.style.height = (word.height * scaleY) + 'px';
                overlay.title = word.text;
                
                overlay.addEventListener('click', () => {
                    showWordInfo(word);
                });
                
                overlaysContainer.appendChild(overlay);
            });
        }
        
        function showWordInfo(word) {
            const infoDiv = document.getElementById('selectedWordInfo');
            const detailsDiv = document.getElementById('wordDetails');
            
            detailsDiv.innerHTML = `
                <div class="word-info">
                    <strong>Text:</strong> "${word.text}"<br>
                    <strong>Confidence:</strong> ${word.confidence}%<br>
                    <strong>Position:</strong> (${word.left}, ${word.top})<br>
                    <strong>Size:</strong> ${word.width} × ${word.height}<br>
                    <strong>Block:</strong> ${word.block_num}, 
                    <strong>Line:</strong> ${word.line_num}
                </div>
            `;
            
            infoDiv.style.display = 'block';
        }
        
        imageElement.addEventListener('load', createOverlays);
        window.addEventListener('resize', createOverlays);
        
        if (imageElement.complete) {
            createOverlays();
        }
    </script>
</body>
</html>'''
    
    with open(templates_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(index_html)
    
    with open(templates_dir / "page_viewer.html", "w", encoding="utf-8") as f:
        f.write(page_viewer_html)


if __name__ == "__main__":
    # Create templates
    create_templates()
    
    # Load OCR data
    load_ocr_data()
    
    if not ocr_data:
        print("No OCR data found. Run: python ocr_extractor.py")
        exit(1)
    
    print(f"Starting web server with {len(ocr_data)} magazine pages...")
    print("Visit http://localhost:5000 to view the archive")
    
    app.run(debug=True, host='0.0.0.0', port=5000)