#!/usr/bin/env python3
import os
import sys
import glob
import json
import re
from datetime import datetime, timezone

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WIKI_DIR = os.path.join(BASE_DIR, "wiki")
DATA_DIR = os.path.join(BASE_DIR, "data")
GRAPH_DATA_PATH = os.path.join(DATA_DIR, "graph.json")
GRAPH_ROOT_PATH = os.path.join(BASE_DIR, "graph.json")
CATEGORIES = ["Projects", "Areas", "Resources", "Archives"]

def parse_note(file_path):
    """
    Parses a markdown note into frontmatter dict and body text.
    Handles manual parsing of YAML frontmatter.
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
            if current_key and isinstance(frontmatter.get(current_key), list):
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

def derive_title(frontmatter, body, default_id, filename):
    """Derive note title from frontmatter, body header, or summary."""
    if frontmatter.get("title"):
        return str(frontmatter["title"]).strip()
    if frontmatter.get("summary"):
        summary = str(frontmatter["summary"]).strip()
        if len(summary) > 60:
            return summary[:57] + "..."
        return summary
    
    # Try finding first level-1 heading in body
    for line in body.splitlines():
        line_s = line.strip()
        if line_s.startswith("# "):
            return line_s[2:].strip()

    # Fallback to filename stem or ID
    base = os.path.splitext(filename)[0]
    return base

def extract_links(frontmatter, body):
    """Extract candidate target IDs / references from frontmatter and body."""
    targets = set()

    # 1. Frontmatter links list
    fm_links = frontmatter.get("links", [])
    if isinstance(fm_links, list):
        for item in fm_links:
            if isinstance(item, str) and item.strip():
                targets.add(item.strip())

    # 2. Wikilinks [[target]] or [[target|label]]
    wikilinks = re.findall(r'\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]', body)
    for wl in wikilinks:
        clean_wl = wl.strip()
        if clean_wl:
            targets.add(clean_wl)

    # 3. Standard Markdown links [text](path)
    md_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', body)
    for _, href in md_links:
        href_clean = href.strip()
        if href_clean.endswith(".md"):
            filename = os.path.basename(href_clean)
            targets.add(os.path.splitext(filename)[0])
        elif "/" not in href_clean and not href_clean.startswith("http"):
            targets.add(href_clean)

    return targets

def main():
    print("Building Cerebro Knowledge Graph...")

    if not os.path.exists(WIKI_DIR):
        print(f"Error: wiki directory not found at '{WIKI_DIR}'", file=sys.stderr)
        sys.exit(1)

    # Find all markdown files in wiki directory
    md_files = []
    for category in CATEGORIES:
        category_dir = os.path.join(WIKI_DIR, category)
        if os.path.exists(category_dir):
            md_files.extend(glob.glob(os.path.join(category_dir, "*.md")))

    # Also search directly in WIKI_DIR if any
    md_files.extend([f for f in glob.glob(os.path.join(WIKI_DIR, "*.md")) if f not in md_files])
    
    md_files = [f for f in md_files if not os.path.basename(f).startswith(".")]

    print(f"Found {len(md_files)} markdown notes across wiki categories.")

    nodes_map = {}
    path_to_id = {}
    filename_to_id = {}
    raw_edges = []

    # First pass: Build node catalog and lookup indexes
    for file_path in md_files:
        filename = os.path.basename(file_path)
        rel_path = os.path.relpath(file_path, BASE_DIR).replace("\\", "/")
        frontmatter, body = parse_note(file_path)

        note_id = frontmatter.get("id")
        if not note_id:
            # Fallback to filename stem
            note_id = os.path.splitext(filename)[0]

        category = frontmatter.get("category")
        if not category:
            category = os.path.basename(os.path.dirname(file_path))

        title = derive_title(frontmatter, body, note_id, filename)
        tags = frontmatter.get("tags", [])
        if not isinstance(tags, list):
            tags = [str(tags)]

        summary = frontmatter.get("summary", "")
        timestamp = frontmatter.get("timestamp", "")
        source_type = frontmatter.get("source_type", "")
        source_value = frontmatter.get("source_value", "")

        node = {
            "id": note_id,
            "title": title,
            "category": category,
            "tags": tags,
            "summary": summary,
            "timestamp": timestamp,
            "source_type": source_type,
            "source_value": source_value,
            "filepath": rel_path
        }

        nodes_map[note_id] = node
        path_to_id[rel_path] = note_id
        path_to_id[file_path] = note_id
        path_to_id[filename] = note_id
        filename_stem = os.path.splitext(filename)[0]
        filename_to_id[filename_stem] = note_id

        # Extract links for second pass resolution
        candidate_targets = extract_links(frontmatter, body)
        raw_edges.append((note_id, candidate_targets))

    # Second pass: Resolve target IDs and build edge list
    edges = []
    edge_set = set()

    for source_id, candidate_targets in raw_edges:
        for target_ref in candidate_targets:
            target_id = None
            if target_ref in nodes_map:
                target_id = target_ref
            elif target_ref in filename_to_id:
                target_id = filename_to_id[target_ref]
            elif target_ref in path_to_id:
                target_id = path_to_id[target_ref]
            else:
                # Partial ID matching
                for nid in nodes_map:
                    if nid.startswith(target_ref) or target_ref.startswith(nid):
                        target_id = nid
                        break

            if target_id and target_id != source_id:
                edge_key = (source_id, target_id)
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({
                        "source": source_id,
                        "target": target_id
                    })

    # Prepare final output structure
    nodes_list = list(nodes_map.values())

    graph_data = {
        "nodes": nodes_list,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes_list),
            "total_edges": len(edges),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    }

    # Ensure output directories exist
    os.makedirs(DATA_DIR, exist_ok=True)

    # Save to data/graph.json
    with open(GRAPH_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2)
    print(f"Graph data saved to: {GRAPH_DATA_PATH}")

    # Also save to root graph.json for standard access
    with open(GRAPH_ROOT_PATH, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2)
    print(f"Graph data saved to: {GRAPH_ROOT_PATH}")

    print(f"Summary: {len(nodes_list)} nodes and {len(edges)} edges processed successfully.")

if __name__ == "__main__":
    main()
