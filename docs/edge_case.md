# Edge Cases & Corner Scenarios: Cerebro

This document catalogues the technical edge cases, error conditions, and corner scenarios identified for the **Cerebro** personal AI second brain project, along with proposed mitigation strategies for each.

---

## 1. Ingestion & Capture Pipeline (`capture.py`)

### 1.1 Scraping Failures & Web Paywalls
- **Scenario:** The user captures a URL that requires authentication (e.g., paywalled articles, private dashboards) or returns a client/server error (404, 403, 500).
- **Impact:** Scraping fails, writing empty text or error HTML (like a Cloudflare challenge page) into the raw capture.
- **Mitigation:**
  - Implement basic error handling in the scraper. If requests return non-200 status codes, fall back to saving just the URL and title rather than blank pages.
  - Implement a configurable request timeout (e.g., 10 seconds) to prevent the capture command from hanging.

### 1.2 Multi-Gigabyte & Binary Files
- **Scenario:** The user attempts to capture a large PDF, audio/video file, or zip archive.
- **Impact:** Memory exhaustion, slow processing times, or disk space exhaustion in `raw/` and embedding stages.
- **Mitigation:**
  - Define a strict file size limit (e.g., 20MB) in `capture.py`. If a file exceeds this, reject capture and show an warning.
  - Check file extensions. For binary formats that cannot be read as text, extract only file metadata (filename, path, size, date) rather than trying to parse raw bytes as text.

### 1.3 Character Encoding & Unicode
- **Scenario:** Input files or web pages contain exotic Unicode characters, emojis, or non-UTF-8 encodings.
- **Impact:** Python throws `UnicodeDecodeError` or writes corrupted data to the JSON output.
- **Mitigation:**
  - Always enforce `encoding="utf-8"` explicitly when opening and writing files.
  - Use resilient decoding strategies like `errors="replace"` or `errors="ignore"` when reading external files.

---

## 2. LLM PARA Classification (`classify.py`)

### 2.1 Malformed JSON from LLM
- **Scenario:** The LLM client returns text that contains conversational prefixes (e.g., *"Here is the classification JSON:"*) or fails to output syntactically valid JSON.
- **Impact:** Python's `json.loads()` throws a JSONDecodeError, breaking the classification step.
- **Mitigation:**
  - Use Groq API's structured JSON output mode if available.
  - Use regex to extract JSON blocks between outer brackets `{ ... }`.
  - Fall back to standard defaults (category: `Resources`, tags: `[]`) if parsing fails.

### 2.2 Invalid Categories
- **Scenario:** The LLM categorizes a note as "Inbox", "General", or "Personal" instead of the strict PARA set (`Projects`, `Areas`, `Resources`, `Archives`).
- **Impact:** Notes get saved to incorrect directories, breaking the system's folder hierarchy.
- **Mitigation:**
  - Use strict prompt engineering with few-shot examples showing the allowed categories.
  - In code, validate the category string: if not in the PARA set, default to `Resources`.

### 2.3 Groq API Key & Rate Limits
- **Scenario:** The user has not configured the `GROQ_API_KEY`, or they hit API rate limits when processing multiple raw captures.
- **Impact:** Classification script halts with an exception.
- **Mitigation:**
  - Perform environment variable checks during startup; print a user-friendly configuration instruction if missing.
  - Implement automatic retries with exponential backoff on API rate limit codes (HTTP 429).

---

## 3. Semantic Linking Engine (`link.py`)

### 3.1 N-Squared Scaling Bottleneck
- **Scenario:** The user accumulates hundreds or thousands of notes. Pairwise cosine similarity checks grow at an $O(N^2)$ rate.
- **Impact:** Generating embeddings and comparing files slows down significantly, freezing CPU cycles.
- **Mitigation:**
  - Cache calculated embeddings in a local vector registry (`wiki_embeddings.pkl` or local index) alongside note hashes.
  - Only compute embeddings and run comparisons for *newly added or modified* notes, matching them against cached vectors.

### 3.2 Duplicate and Loop Links
- **Scenario:** The linking engine runs multiple times, adding the same Markdown links repeatedly, or linking a document to itself.
- **Impact:** Notes get bloated with redundant links; visual graph shows self-loops.
- **Mitigation:**
  - Filter out self-comparisons in `link.py`.
  - Parse existing links before appending; only write new cross-links if they do not already exist in the file.

---

## 4. Graph Projection & Visualizer (`build_graph.py` & `app.py`)

### 4.1 Broken Links (Dead References)
- **Scenario:** A note is deleted or renamed, but other notes still contain Markdown links pointing to its old ID/path.
- **Impact:** Graph displays broken paths; clicking node link leads to a file not found.
- **Mitigation:**
  - During `build_graph.py` traversal, validate target exists before creating an edge in `graph.json`. Discard edges pointing to non-existent node IDs.

### 4.2 Single Isolated Nodes
- **Scenario:** Many notes have zero semantic similarity to other notes.
- **Impact:** The force-directed graph is populated with isolated nodes floating off-screen.
- **Mitigation:**
  - Support clustering or visual filtering in the UI to toggle display of isolated nodes.

### 4.3 Graph UI Performance Degradation
- **Scenario:** High number of nodes (500+) rendered dynamically in `vis-network`.
- **Impact:** Rendering freezes the Streamlit web browser or uses excessive GPU/CPU.
- **Mitigation:**
  - Enable physics stabilization on initial load and turn off active physics animations once the graph is settled.
  - Cap the max node count or filter by category/tags inside the UI.

---

## 5. Retrieval-Augmented Generation (`ask.py` / RAG)

### 5.1 Context Window Overflow
- **Scenario:** Top-$K$ retrieved notes contain long text blocks, and their combined length exceeds Llama 3's context window.
- **Impact:** Groq API call fails with a token count error.
- **Mitigation:**
  - Chunk long documents before indexing, rather than passing entire file contents.
  - Limit top-$K$ retrieval to a safe context token threshold (e.g. max 4,000 tokens for context).

### 5.2 Hallucinations & False Grounding
- **Scenario:** The user asks a question not answered in the notes, and the LLM hallucinates an answer.
- **Impact:** Undermines the system's validity as a personal "Second Brain".
- **Mitigation:**
  - Adjust LLM system prompt: *"Only answer the question based on the provided context notes. If the context does not contain enough information to answer, state clearly that the answer is not in the knowledge base."*
  - Set LLM temperature parameter low (e.g., `temperature=0.0` or `0.2`) for high-fidelity responses.
