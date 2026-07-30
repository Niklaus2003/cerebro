#!/usr/bin/env python3
import os
import sys
import glob
import json
import pickle
import hashlib
import argparse
import numpy as np

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WIKI_DIR = os.path.join(BASE_DIR, "wiki")
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_FILE = os.path.join(DATA_DIR, "wiki_embeddings.pkl")
CATEGORIES = ["Projects", "Areas", "Resources", "Archives"]

def parse_note(file_path):
    """
    Parses a markdown note into frontmatter dict and body text.
    Handles manual parsing of YAML frontmatter to avoid external PyYAML dependencies.
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    lines = content.splitlines()
    if not lines or lines[0] != "---":
        return {}, content

    frontmatter_lines = []
    body_start_idx = -1
    for idx in range(1, len(lines)):
        if lines[idx] == "---":
            body_start_idx = idx + 1
            break
        frontmatter_lines.append(lines[idx])

    if body_start_idx == -1:
        return {}, content

    frontmatter = {}
    current_key = None
    for line in frontmatter_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            # It's a list item
            if current_key and isinstance(frontmatter.get(current_key), list):
                # Check for list item syntax
                val = stripped[2:].strip()
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                frontmatter[current_key].append(val)
        elif ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip()
            val = parts[1].strip()
            if val == "[]" or val == "":
                frontmatter[key] = []
            elif (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                frontmatter[key] = val[1:-1]
            else:
                frontmatter[key] = val
            current_key = key

    body = "\n".join(lines[body_start_idx:])
    return frontmatter, body

def serialize_note(frontmatter, body):
    """
    Serializes frontmatter dict and body text back to markdown string.
    Maintains clean layout order.
    """
    ordered_keys = ["id", "timestamp", "source_type", "source_value", "category", "tags", "summary", "links"]
    lines = ["---"]
    seen_keys = set()

    for k in ordered_keys:
        if k in frontmatter:
            v = frontmatter[k]
            seen_keys.add(k)
            if isinstance(v, list):
                if not v:
                    lines.append(f"{k}: []")
                else:
                    lines.append(f"{k}:")
                    for item in v:
                        lines.append(f"  - {item}")
            else:
                if isinstance(v, str) and ('"' in v or ":" in v or "#" in v or "-" in v or "\\" in v):
                    safe_val = v.replace('"', '\\"')
                    lines.append(f'{k}: "{safe_val}"')
                else:
                    lines.append(f"{k}: {v}")

    for k, v in frontmatter.items():
        if k not in seen_keys:
            if isinstance(v, list):
                if not v:
                    lines.append(f"{k}: []")
                else:
                    lines.append(f"{k}:")
                    for item in v:
                        lines.append(f"  - {item}")
            else:
                if isinstance(v, str) and ('"' in v or ":" in v or "#" in v or "-" in v or "\\" in v):
                    safe_val = v.replace('"', '\\"')
                    lines.append(f'{k}: "{safe_val}"')
                else:
                    lines.append(f"{k}: {v}")

    lines.append("---")
    lines.append("")
    lines.append(body.lstrip())
    return "\n".join(lines)

def get_semantic_text(frontmatter, body):
    """
    Strips links and Related Notes section to isolate semantic note content.
    Enriches with summary and tags to ensure better vector embedding.
    """
    # Strip Related Notes section
    cleaned_body = body
    if "## Related Notes" in cleaned_body:
        cleaned_body = cleaned_body.split("## Related Notes")[0]
    cleaned_body = cleaned_body.strip()

    # Prepend summary and tags
    enrichments = []
    if frontmatter.get("summary"):
        enrichments.append(frontmatter["summary"])
    if frontmatter.get("tags"):
        enrichments.append("Tags: " + ", ".join(frontmatter["tags"]))

    if enrichments:
        return "\n".join(enrichments) + "\n\n" + cleaned_body
    return cleaned_body

def compute_md5(text):
    """Calculates MD5 hash of text."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()

def cosine_similarity(v1, v2):
    """Calculates cosine similarity between two vectors."""
    dot_prod = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(dot_prod / (norm1 * norm2))

def update_body_links(body, new_links):
    """
    Adds new links to '## Related Notes' section in the body text.
    Maintains existing links and avoids duplicates.
    """
    normalized_body = body.rstrip()
    section_header = "## Related Notes"

    if section_header in normalized_body:
        parts = normalized_body.split(section_header, 1)
        before_section = parts[0].rstrip()
        section_content = parts[1]

        # Parse existing link IDs
        import re
        uuid_pattern = re.compile(r"\[\[([0-9a-fA-F\-]{36})\]\]")
        existing_ids = set(uuid_pattern.findall(section_content))

        # Filter out links that are already present
        added_lines = []
        for target_id, target_category in new_links:
            if target_id not in existing_ids:
                added_lines.append(f"- [[{target_id}]] (Category: {target_category})")
                existing_ids.add(target_id)

        if added_lines:
            new_section_content = section_content.rstrip()
            if not new_section_content.endswith("\n"):
                new_section_content += "\n"
            for line in added_lines:
                new_section_content += line + "\n"
            return before_section + "\n\n" + section_header + "\n" + new_section_content
        else:
            return normalized_body
    else:
        # Create section at the end
        lines = ["", "", section_header]
        for target_id, target_category in new_links:
            lines.append(f"- [[{target_id}]] (Category: {target_category})")
        return normalized_body + "\n".join(lines) + "\n"

def main():
    parser = argparse.ArgumentParser(description="Semantic Linking Engine for Cerebro Wiki")
    parser.path = WIKI_DIR
    parser.add_argument("--threshold", type=float, default=0.6, help="Cosine similarity threshold (default: 0.6)")
    args = parser.parse_args()

    # Ensure data directory exists
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # 1. Load Embeddings Model
    print("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as e:
        print(f"Error loading model: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Load Embedding Cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "rb") as f:
                cache = pickle.load(f)
            print(f"Loaded embedding cache from '{CACHE_FILE}' with {len(cache)} entries.")
        except Exception as e:
            print(f"Warning: Could not read cache file: {e}. Starting with empty cache.")

    # 3. Find and Parse Markdown files
    if not os.path.exists(WIKI_DIR):
        print(f"Error: wiki directory not found at '{WIKI_DIR}'", file=sys.stderr)
        sys.exit(1)

    # Search for markdown files in wiki subdirectories
    md_files = []
    for category in CATEGORIES:
        category_dir = os.path.join(WIKI_DIR, category)
        if os.path.exists(category_dir):
            md_files.extend(glob.glob(os.path.join(category_dir, "*.md")))

    print(f"Found {len(md_files)} notes in wiki.")
    notes_data = []
    cache_hits = 0

    for file_path in md_files:
        # Skip system or metadata files if any
        if os.path.basename(file_path).startswith("."):
            continue

        frontmatter, body = parse_note(file_path)
        note_id = frontmatter.get("id")
        if not note_id:
            print(f"Warning: Skipping {os.path.basename(file_path)} (missing 'id' in frontmatter).")
            continue

        category = frontmatter.get("category")
        if not category:
            # Fallback to subdirectory name
            category = os.path.basename(os.path.dirname(file_path))
            frontmatter["category"] = category

        semantic_text = get_semantic_text(frontmatter, body)
        text_hash = compute_md5(semantic_text)

        # Check cache
        rel_path = os.path.relpath(file_path, BASE_DIR)
        embedding = None
        if rel_path in cache and cache[rel_path].get("hash") == text_hash:
            embedding = cache[rel_path].get("embedding")
            cache_hits += 1
        
        if embedding is None:
            # Generate embedding
            embedding = model.encode(semantic_text)
            # Save to cache
            cache[rel_path] = {
                "id": note_id,
                "hash": text_hash,
                "embedding": embedding
            }

        notes_data.append({
            "path": file_path,
            "rel_path": rel_path,
            "id": note_id,
            "category": category,
            "frontmatter": frontmatter,
            "body": body,
            "embedding": embedding,
            "modified": False,
            "new_links": [] # list of (target_id, target_category)
        })

    print(f"Embedding computation complete. Cache hits: {cache_hits}/{len(notes_data)}")

    # 4. Compute Pairwise Similarities and Identify Matches
    print(f"Computing pairwise similarities (threshold: {args.threshold})...")
    num_notes = len(notes_data)
    for i in range(num_notes):
        for j in range(i + 1, num_notes):
            n1 = notes_data[i]
            n2 = notes_data[j]
            
            # Compute cosine similarity
            sim = cosine_similarity(n1["embedding"], n2["embedding"])
            if sim >= args.threshold:
                print(f"  Match: [{n1['id'][:8]}] and [{n2['id'][:8]}] (Sim: {sim:.3f})")
                n1["new_links"].append((n2["id"], n2["category"]))
                n2["new_links"].append((n1["id"], n1["category"]))

    # 5. Apply Links and Save Files
    updated_files_count = 0
    for note in notes_data:
        if not note["new_links"]:
            continue

        frontmatter = note["frontmatter"]
        body = note["body"]
        original_frontmatter_links = list(frontmatter.get("links", []))
        
        # Update frontmatter links
        if "links" not in frontmatter or not isinstance(frontmatter["links"], list):
            frontmatter["links"] = []

        for target_id, _ in note["new_links"]:
            if target_id not in frontmatter["links"]:
                frontmatter["links"].append(target_id)

        # Update body Related Notes section
        new_body = update_body_links(body, note["new_links"])

        # Check if anything changed
        frontmatter_changed = (list(frontmatter.get("links", [])) != original_frontmatter_links)
        body_changed = (new_body != body)

        if frontmatter_changed or body_changed:
            note["frontmatter"] = frontmatter
            note["body"] = new_body
            note["modified"] = True
            
            # Serialize and write
            serialized = serialize_note(frontmatter, new_body)
            with open(note["path"], "w", encoding="utf-8") as f:
                f.write(serialized)
            updated_files_count += 1

    print(f"Links updated. Total files modified: {updated_files_count}")

    # 6. Save Embedding Cache
    try:
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(cache, f)
        print(f"Saved embedding cache to '{CACHE_FILE}'.")
    except Exception as e:
        print(f"Error saving cache file: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
