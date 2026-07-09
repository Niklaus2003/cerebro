#!/usr/bin/env python3
import os
import sys
import uuid
import json
import argparse
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# Directory where raw captures are stored
RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")

def ensure_raw_dir():
    """Ensure the raw/ directory exists."""
    if not os.path.exists(RAW_DIR):
        os.makedirs(RAW_DIR)

def scrape_url(url):
    """Scrape a URL and convert its HTML content to Markdown."""
    print(f"Scraping URL: {url} ...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Try to detect encoding
        if response.encoding is None or response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding
            
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract title
        title = soup.title.string.strip() if soup.title else url
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Convert body html to markdown
        body_content = soup.body if soup.body else soup
        markdown_text = md(str(body_content), heading_style="ATX")
        
        # Format content nicely
        full_content = f"# {title}\n\nSource: {url}\n\n{markdown_text.strip()}"
        return full_content
        
    except Exception as e:
        print(f"Error scraping URL: {e}", file=sys.stderr)
        # Fallback to saving just the URL and error description
        return f"# Scraping Failed: {url}\n\nError: {str(e)}\n\nCould not fetch full page content."

def read_local_file(file_path):
    """Read contents of a local file."""
    print(f"Reading file: {file_path} ...")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    # Get absolute path
    abs_path = os.path.abspath(file_path)
    
    # Try reading as text
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return content
    except Exception as e:
        raise IOError(f"Could not read file {file_path}: {e}")

def save_capture(source_type, source_value, content):
    """Save the captured content to the raw/ directory as JSON."""
    ensure_raw_dir()
    
    # Generate metadata
    capture_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    payload = {
        "id": capture_id,
        "timestamp": timestamp,
        "source_type": source_type,
        "source_value": source_value,
        "raw_content": content
    }
    
    # Generate file name: {timestamp_safe}_{uuid}.json
    # Replace colon and dot to make it safe for file systems
    timestamp_safe = timestamp.replace(":", "-").replace(".", "-")
    file_name = f"{timestamp_safe}_{capture_id}.json"
    file_path = os.path.join(RAW_DIR, file_name)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully captured {source_type}!")
    print(f"Saved to: {file_path}")
    return file_path

def main():
    parser = argparse.ArgumentParser(description="Cerebro Command-Line Ingestion Tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", type=str, help="Raw text note to capture")
    group.add_argument("--link", type=str, help="URL/Link to scrape and capture")
    group.add_argument("--file", type=str, help="Path to local file to capture")
    
    args = parser.parse_args()
    
    try:
        if args.text:
            save_capture(source_type="text", source_value="cli", content=args.text)
        elif args.link:
            content = scrape_url(args.link)
            save_capture(source_type="link", source_value=args.link, content=content)
        elif args.file:
            content = read_local_file(args.file)
            save_capture(source_type="file", source_value=args.file, content=content)
            
    except Exception as e:
        print(f"Capture failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
