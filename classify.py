#!/usr/bin/env python3
import os
import sys
import glob
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env file
load_dotenv()

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "raw")
WIKI_DIR = os.path.join(BASE_DIR, "wiki")

# Valid PARA categories
CATEGORIES = ["Projects", "Areas", "Resources", "Archives"]

# LLM Prompt Setup
SYSTEM_PROMPT = """You are an AI assistant designed to classify raw notes and captures into a PARA-based personal knowledge management system.

The PARA method organizes information into four categories:
1. Projects: Active endeavors with a specific goal and a deadline. (e.g. building a specific tool, preparing a presentation, writing a report, organizing an event)
2. Areas: Ongoing spheres of activity/responsibility without an end date. (e.g. Health, Finance, Writing, Coding, DevOps, Personal Development, Parenting)
3. Resources: Topics of ongoing interest, reference materials, research, web links, docs, or information that is useful for multiple areas/projects. (e.g. programming language cheat sheets, recipes, general tutorials, Wikipedia articles on note-taking)
4. Archives: Inactive items from the other three categories (e.g. completed/put-on-hold projects, areas of responsibility no longer active).

You must analyze the note content, source type, and source value to determine:
1. The most appropriate category (strictly one of: "Projects", "Areas", "Resources", "Archives").
2. A list of tags (array of lowercase string keywords representing key themes).
3. A concise one-sentence/one-line summary of the content.

You MUST respond ONLY with a JSON object containing exactly the following keys:
{
  "category": "Projects" | "Areas" | "Resources" | "Archives",
  "tags": ["tag1", "tag2", ...],
  "summary": "One-line summary here"
}

Do not include any pre-text, post-text, markdown block wrapping, or explanations. Respond with a raw JSON object only.
"""

def ensure_wiki_dirs():
    """Ensure that all PARA category directories exist inside wiki/."""
    for category in CATEGORIES:
        category_dir = os.path.join(WIKI_DIR, category)
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)

def get_unprocessed_files():
    """Scan raw/ and return a list of paths to unprocessed JSON files."""
    if not os.path.exists(RAW_DIR):
        print(f"Error: Raw directory '{RAW_DIR}' does not exist.", file=sys.stderr)
        return []

    json_files = glob.glob(os.path.join(RAW_DIR, "*.json"))
    unprocessed = []

    for file_path in json_files:
        filename = os.path.basename(file_path)
        # Skip gitkeep or any hidden files
        if filename.startswith(".") or filename == "package.json":
            continue

        base_name, _ = os.path.splitext(filename)
        md_filename = f"{base_name}.md"

        # Check if the markdown file exists in any category
        processed = False
        for category in CATEGORIES:
            target_path = os.path.join(WIKI_DIR, category, md_filename)
            if os.path.exists(target_path):
                processed = True
                break

        if not processed:
            unprocessed.append(file_path)

    return sorted(unprocessed)

def classify_content(client, content, source_type, source_value):
    """Call Groq API to classify the capture content."""
    # Truncate content to avoid exceeding token rate limits (e.g. 8,000 TPM limit)
    max_chars = 3500
    if len(content) > max_chars:
        truncated_content = content[:max_chars] + "\n\n... [CONTENT TRUNCATED FOR LLM CLASSIFICATION] ..."
    else:
        truncated_content = content

    user_message = f"Source Type: {source_type}\nSource Value: {source_value}\n\nContent:\n{truncated_content}"
    
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                model=model,
                response_format={"type": "json_object"},
                temperature=0.2
            )
            response_text = response.choices[0].message.content
            try:
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                print(f"Failed to parse LLM response as JSON: {e}", file=sys.stderr)
                print(f"Raw response: {response_text}", file=sys.stderr)
                raise
        except Exception as e:
            error_str = str(e)
            is_rate_limit = any(term in error_str.lower() for term in ["rate_limit", "413", "rate limit", "limit exceeded", "tpm"])
            if is_rate_limit and attempt < max_retries - 1:
                print(f"  -> Rate limit hit or request too large. Retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                raise


def normalize_category(category_str):
    """Normalize the category string to match the exact PARA case."""
    normalized = category_str.strip().capitalize()
    if normalized in CATEGORIES:
        return normalized
    # Loose fallback matching
    if normalized.startswith("Proj"):
        return "Projects"
    if normalized.startswith("Area"):
        return "Areas"
    if normalized.startswith("Res"):
        return "Resources"
    if normalized.startswith("Arch"):
        return "Archives"
    return "Resources"  # Default fallback

def process_file(client, file_path):
    """Read a raw capture, classify it, and write the markdown note."""
    print(f"Processing: {os.path.basename(file_path)} ...")
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    capture_id = data.get("id")
    timestamp = data.get("timestamp")
    source_type = data.get("source_type")
    source_value = data.get("source_value")
    raw_content = data.get("raw_content", "")

    # Perform LLM Classification
    classification = classify_content(client, raw_content, source_type, source_value)
    
    category = normalize_category(classification.get("category", "Resources"))
    tags = [tag.strip().lower() for tag in classification.get("tags", []) if isinstance(tag, str)]
    summary = classification.get("summary", "No summary provided.")

    # Format YAML frontmatter manually (keeps format clean without PyYAML dependency)
    if tags:
        tags_list_str = "\n".join([f"  - {tag}" for tag in tags])
        tags_section = f"tags:\n{tags_list_str}"
    else:
        tags_section = "tags: []"

    safe_summary = summary.replace('"', '\\"')
    
    frontmatter = f"""---
id: {capture_id}
timestamp: {timestamp}
source_type: {source_type}
source_value: {source_value}
category: {category}
{tags_section}
summary: "{safe_summary}"
---

"""
    
    # Save the structured note to wiki/{category}/{filename}.md
    ensure_wiki_dirs()
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    md_filename = f"{base_name}.md"
    target_path = os.path.join(WIKI_DIR, category, md_filename)
    
    # Write file
    with open(target_path, "w", encoding="utf-8") as f_out:
        f_out.write(frontmatter + raw_content)
        
    print(f"  -> Category: {category}")
    print(f"  -> Saved to: wiki/{category}/{md_filename}\n")

def main():
    # Verify API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY environment variable not found in .env file.", file=sys.stderr)
        sys.exit(1)
        
    client = Groq(api_key=api_key)
    ensure_wiki_dirs()
    
    unprocessed = get_unprocessed_files()
    if not unprocessed:
        print("All raw captures are already processed. Nothing to classify.")
        return

    print(f"Found {len(unprocessed)} unprocessed raw captures. Starting classification...\n")
    
    success_count = 0
    error_count = 0
    
    for file_path in unprocessed:
        try:
            process_file(client, file_path)
            success_count += 1
        except Exception as e:
            print(f"Error processing {os.path.basename(file_path)}: {e}", file=sys.stderr)
            error_count += 1
            
    print(f"Classification run completed.")
    print(f"Successfully processed: {success_count}")
    print(f"Errors encountered: {error_count}")

if __name__ == "__main__":
    main()
