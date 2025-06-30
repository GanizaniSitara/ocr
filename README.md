# Magazine Archive

OCR-powered archiving solution for PrivateEye magazines with clickable text overlays.

## Features

- OCR text extraction with bounding box coordinates
- Web interface with clickable text areas over magazine images
- Full-text search across all pages
- Interactive word-level text selection and information display

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure Tesseract is installed on your system:
   - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
   - macOS: `brew install tesseract`
   - Linux: `sudo apt-get install tesseract-ocr`

3. Extract OCR data from PNG files:
   ```bash
   python ocr_extractor.py
   ```

4. Start the web viewer:
   ```bash
   python web_viewer.py
   ```

5. Open http://localhost:5000 in your browser

## Usage

### OCR Extraction
The `ocr_extractor.py` script processes all PNG files in the current directory and extracts:
- Full text content
- Individual word bounding boxes
- Confidence scores
- Text structure information

### Web Interface
The web viewer provides:
- Grid view of all magazine pages
- Clickable overlays on each word/text region
- Detailed word information (confidence, position, etc.)
- Full-text search across all pages
- Navigation between pages

### Files

- `ocr_extractor.py` - OCR processing with bounding boxes
- `web_viewer.py` - Flask web interface
- `tesseract.py` - Original basic OCR script
- `requirements.txt` - Python dependencies
- `magazine_ocr.json` - Generated OCR data (created after running extractor)

## Technical Details

The solution uses:
- **pytesseract** for OCR with coordinate extraction
- **Flask** for the web interface
- **PIL/Pillow** for image preprocessing
- **JavaScript** for interactive overlays that scale with image size
