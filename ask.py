#!/usr/bin/env python3
import os
import sys
import glob
import json
import pickle
import hashlib
import argparse
import requests
import numpy as np
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WIKI_DIR = os.path.join(BASE_DIR, "wiki")
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_FILE = os.path.join(DATA_DIR, "wiki_embeddings.pkl")
CATEGORIES = ["Projects", "Areas", "Resources", "Archives"]

try:
    import streamlit as st
    @st.cache_resource
    def get_embedding_model():
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("all-MiniLM-L6-v2")
except Exception:
    _MODEL_CACHE = None
    def get_embedding_model():
        global _MODEL_CACHE
        if _MODEL_CACHE is None:
            from sentence_transformers import SentenceTransformer
            _MODEL_CACHE = SentenceTransformer("all-MiniLM-L6-v2")
        return _MODEL_CACHE

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

def derive_title(frontmatter, body, note_id, filename):
    """Derives a human-readable title for a note."""
    if frontmatter.get("title"):
        return str(frontmatter["title"]).strip()
    if frontmatter.get("summary"):
        summary = str(frontmatter["summary"]).strip()
        if len(summary) > 60:
            return summary[:57] + "..."
        return summary
    
    for line in body.splitlines():
        line_s = line.strip()
        if line_s.startswith("# "):
            return line_s[2:].strip()

    return os.path.splitext(filename)[0]

def get_semantic_text(frontmatter, body):
    """
    Strips links and Related Notes section to isolate semantic note content.
    Enriches with summary and tags to ensure better vector embedding.
    """
    cleaned_body = body
    if "## Related Notes" in cleaned_body:
        cleaned_body = cleaned_body.split("## Related Notes")[0]
    cleaned_body = cleaned_body.strip()

    enrichments = []
    if frontmatter.get("summary"):
        enrichments.append(f"Summary: {frontmatter['summary']}")
    if frontmatter.get("tags"):
        tags_val = frontmatter["tags"]
        if isinstance(tags_val, list):
            enrichments.append("Tags: " + ", ".join(tags_val))
        else:
            enrichments.append(f"Tags: {tags_val}")

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

SYSTEM_PROMPT = """You are Cerebro AI, an intelligent personal knowledge assistant representing Aaron Francis's personal Second Brain.

User Identity Context:
- The owner and user of this personal Second Brain is Aaron Francis.
- Whenever the user refers to 'me', 'my', 'I', 'myself', or 'Aaron' / 'Aaron Francis', they are asking about Aaron Francis, the system owner.
- Synthesize all available personal notes, profile details, LinkedIn links, contact details, background details, and preferences regarding Aaron Francis when answering questions about the user.

Instructions:
1. Base your answer on the provided context notes from Aaron Francis's Second Brain.
2. Synthesize information clearly in a well-structured response (using markdown formatting if helpful).
3. Always cite your source notes explicitly at the end of your response or inline using their Titles and Category/ID (e.g. Source: [Note Title] (Category: Resources)).
4. If the provided notes do not contain sufficient information to answer the question, clearly state what information is available and mention that no further context was found in the wiki.
"""

def load_wiki_notes(model=None):
    """
    Scans WIKI_DIR, parses notes, and ensures vector embeddings exist for all notes.
    Uses cache data/wiki_embeddings.pkl where possible.
    """
    if not os.path.exists(WIKI_DIR):
        return []

    md_files = []
    for category in CATEGORIES:
        category_dir = os.path.join(WIKI_DIR, category)
        if os.path.exists(category_dir):
            md_files.extend(glob.glob(os.path.join(category_dir, "*.md")))

    md_files = [f for f in md_files if not os.path.basename(f).startswith(".")]

    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "rb") as f:
                cache = pickle.load(f)
        except Exception:
            cache = {}

    notes_list = []
    cache_updated = False

    for file_path in md_files:
        filename = os.path.basename(file_path)
        frontmatter, body = parse_note(file_path)

        note_id = frontmatter.get("id", os.path.splitext(filename)[0])
        category = frontmatter.get("category", os.path.basename(os.path.dirname(file_path)))
        title = derive_title(frontmatter, body, note_id, filename)
        summary = frontmatter.get("summary", "")
        semantic_text = get_semantic_text(frontmatter, body)
        text_hash = compute_md5(semantic_text)
        rel_path = os.path.relpath(file_path, BASE_DIR)

        embedding = None
        if rel_path in cache and cache[rel_path].get("hash") == text_hash:
            embedding = cache[rel_path].get("embedding")

        if embedding is None:
            if model is None:
                model = get_embedding_model()
            embedding = model.encode(semantic_text)
            cache[rel_path] = {
                "id": note_id,
                "hash": text_hash,
                "embedding": embedding
            }
            cache_updated = True

        notes_list.append({
            "id": note_id,
            "title": title,
            "category": category,
            "summary": summary,
            "path": file_path,
            "rel_path": rel_path,
            "frontmatter": frontmatter,
            "body": body,
            "semantic_text": semantic_text,
            "embedding": embedding
        })

    if cache_updated:
        os.makedirs(DATA_DIR, exist_ok=True)
        try:
            with open(CACHE_FILE, "wb") as f:
                pickle.dump(cache, f)
        except Exception:
            pass

    return notes_list

def retrieve_top_k(query, notes_list, model=None, top_k=3):
    """
    Encodes query and computes similarity scores against notes_list.
    Returns top_k matching notes sorted by similarity descending.
    Enhanced with personal identity boosting for 'Aaron Francis' / 'me' / 'my' queries.
    """
    if not notes_list:
        return []

    if model is None:
        model = get_embedding_model()

    query_lower = query.lower()
    personal_keywords = ["me", "my", "i", "aaron", "francis", "myself", "who am i", "linkedin", "profile", "identity", "owner", "contact"]
    is_personal_query = any(w in query_lower.split() or w in query_lower for w in personal_keywords)

    search_query = query
    if is_personal_query:
        search_query = f"{query} Aaron Francis user profile personal background identity linkedin"

    query_embedding = model.encode(search_query)

    scored_notes = []
    for note in notes_list:
        sim = cosine_similarity(query_embedding, note["embedding"])
        
        note_text_lower = (str(note.get("title", "")) + " " + str(note.get("summary", "")) + " " + str(note.get("semantic_text", ""))).lower()
        if is_personal_query and ("aaron" in note_text_lower or "francis" in note_text_lower or "linkedin" in note_text_lower or "profile" in note_text_lower):
            sim += 0.30

        note_copy = dict(note)
        note_copy["score"] = sim
        scored_notes.append(note_copy)

    scored_notes.sort(key=lambda x: x["score"], reverse=True)
    return scored_notes[:top_k]

def generate_answer_gemini(system_prompt, user_message, api_key, model_name="gemini-2.5-flash"):
    """
    Calls Google Gemini REST API to synthesize an answer with higher token limits.
    """
    # Clean model name if user provided prefixes
    clean_model = model_name.replace("models/", "")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={api_key}"
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_prompt}\n\n{user_message}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.3
        }
    }

    res = requests.post(url, headers=headers, json=payload, timeout=30)
    if res.status_code != 200:
        # If gemini-2.5-flash endpoint is unavailable, try gemini-1.5-flash fallback
        if "2.5" in clean_model:
            fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            res = requests.post(fallback_url, headers=headers, json=payload, timeout=30)
        
        if res.status_code != 200:
            raise RuntimeError(f"Gemini API Call Failed ({res.status_code}): {res.text}")

    data = res.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"Gemini returned empty response candidates: {data}")

    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise RuntimeError("No text parts in Gemini response.")

    return parts[0].get("text", "")

def generate_answer_groq(system_prompt, user_message, groq_client=None):
    """
    Calls Groq API as a lightweight LLM alternative.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not found.")

    if groq_client is None:
        groq_client = Groq(api_key=api_key)

    llm_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    response = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        model=llm_model,
        temperature=0.3
    )

    return response.choices[0].message.content

def ask(query, top_k=3, model_obj=None, groq_client=None):
    """
    RAG Pipeline:
    1. Retrieve top-k notes using sentence-transformer embeddings.
    2. Format context for Google Gemini or Groq LLM.
    3. Synthesize answer with source citations.
    """
    if model_obj is None:
        model_obj = get_embedding_model()

    notes_list = load_wiki_notes(model=model_obj)
    top_notes = retrieve_top_k(query, notes_list, model=model_obj, top_k=top_k)

    # Build context string
    context_blocks = []
    for idx, note in enumerate(top_notes, start=1):
        block = f"--- Context Chunk {idx} ---\n"
        block += f"Title: {note['title']}\n"
        block += f"Category: {note['category']}\n"
        block += f"Note ID: {note['id']}\n"
        if note['summary']:
            block += f"Summary: {note['summary']}\n"
        block += f"Content:\n{note['body'].strip()}\n"
        context_blocks.append(block)

    context_str = "\n\n".join(context_blocks)
    user_message = f"User Question: {query}\n\nRetrieved Knowledge Context:\n{context_str}"

    # Check for Gemini API key (supports GEMINI_API_KEY or GOOGLE_API_KEY)
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key and gemini_key.strip() and not gemini_key.startswith("your_"):
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        try:
            answer_text = generate_answer_gemini(SYSTEM_PROMPT, user_message, gemini_key, model_name=gemini_model)
        except Exception as gemini_err:
            print(f"Warning: Gemini API call failed ({gemini_err}). Falling back to Groq...", file=sys.stderr)
            answer_text = generate_answer_groq(SYSTEM_PROMPT, user_message, groq_client=groq_client)
    else:
        answer_text = generate_answer_groq(SYSTEM_PROMPT, user_message, groq_client=groq_client)

    return {
        "query": query,
        "answer": answer_text,
        "sources": top_notes
    }

def main():
    parser = argparse.ArgumentParser(description="Cerebro Search & Q&A Engine (RAG)")
    parser.add_argument("query", type=str, nargs="?", help="The search query or question to answer")
    parser.add_argument("--query", "-q", dest="opt_query", type=str, help="Alternative flag for query")
    parser.add_argument("--top-k", "-k", type=int, default=3, help="Number of top context notes to retrieve (default: 3)")
    args = parser.parse_args()

    query_text = args.query or args.opt_query
    if not query_text:
        parser.print_help()
        sys.exit(1)

    print(f"\n[Cerebro Search & Q&A]")
    print(f"Query: \"{query_text}\"")
    print(f"Retrieving top {args.top_k} matching notes...\n")

    try:
        result = ask(query_text, top_k=args.top_k)
        
        print("=" * 60)
        print("RETRIEVED SOURCES:")
        print("=" * 60)
        for idx, src in enumerate(result["sources"], start=1):
            print(f"{idx}. [{src['category']}] {src['title']} (ID: {src['id'][:8]}..., Score: {src['score']:.4f})")
            if src["summary"]:
                print(f"   Summary: {src['summary']}")
            print(f"   File: {src['rel_path']}")
            print()

        print("=" * 60)
        print("SYNTHESIZED ANSWER:")
        print("=" * 60)
        print(result["answer"])
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"Error during search: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
