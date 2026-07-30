# Implementation Plan: Cerebro

This document outlines the step-by-step, phase-wise implementation plan to build **Cerebro**, from project initialization to live public deployment.

---

## Plan Overview

- **Phase 0:** Setup & Scaffolding
- **Phase 1-5:** Core Component Development (Ingestion, Classification, Linking, Graph Building, RAG Engine)
- **Phase 6-7:** UI & Integration (Local Testing)
- **Phase 8-9:** Deployment & Final Validation

---

## Detailed Phases

### Phase 0: Setup & Scaffolding
Initialize the workspace, set up dependency management, and verify environment keys.

- [x] Create the project directory structure:
  ```text
  cerebro/
  ├── raw/
  ├── wiki/
  │   ├── Projects/
  │   ├── Areas/
  │   ├── Resources/
  │   └── Archives/
  └── docs/
  ```
- [x] Initialize Python virtual environment.
- [x] Create `requirements.txt` with required libraries:
  - `groq` (LLM client)
  - `sentence-transformers` (local embeddings)
  - `numpy` / `scikit-learn` (vector calculations)
  - `streamlit` (UI application)
  - `beautifulsoup4` / `requests` / `markdownify` (link scraping)
- [x] Create `.env` template and verify access to the Groq API Key.

---

### Phase 1: Ingestion Pipeline (`capture.py`)
Implement the command-line tool to capture text, URLs, and local files directly into the raw directory.

- [x] Build command-line interface to accept text notes, links, or file paths.
- [x] Implement URL parsing and scraping (convert HTML body to clean markdown or text).
- [x] Implement file readers to handle basic text/markdown files.
- [x] Generate metadata: ISO 8601 timestamp and unique UUID.
- [x] Save raw contents as `{timestamp}_{uuid}.json` inside `raw/`.
- [x] **Verification:** Manually capture 10+ real pieces of personal notes, links, and documents.

---

### Phase 2: LLM PARA Classification (`classify.py`)
Automate organization of raw captures using an LLM.

- [x] Write logic to read unprocessed files in `raw/`.
- [x] Draft system prompt for Llama 3 (via Groq API) to enforce JSON-only output with:
  - Category (strictly limited to: `Projects`, `Areas`, `Resources`, `Archives`)
  - Tags (array of lowercase keywords)
  - One-line Summary
- [x] Parse JSON output from the LLM.
- [x] Format note content: YAML frontmatter containing metadata + raw body text.
- [x] Write the structured note to `wiki/{category}/{filename}.md`.
- [x] **Verification:** Run classification across the 10+ captured files and check if they are correctly stored in corresponding PARA directories.

---

### Phase 3: Semantic Linking Engine (`link.py`)
Connect related notes automatically using local vector embeddings.

- [x] Implement local embedding generator using `sentence-transformers` (`all-MiniLM-L6-v2`).
- [x] Compute embeddings for each markdown file in the `wiki/` directory.
- [x] Store embeddings in a lightweight local index (e.g. pickle or JSON dict mapping note IDs to vector lists).
- [x] Compute pairwise cosine similarities between new notes and existing notes.
- [x] Set similarity threshold (e.g., `0.6`).
- [x] For items exceeding the threshold, auto-insert bidirectional markdown links (`[[Note Title]]` or relative file links) at the end of both notes.
- [x] **Verification:** Add related notes and verify they automatically link to each other.

---

### Phase 4: Graph Data Model (`build_graph.py`)
Build the data adapter that maps markdown pages and internal links to a structured network graph.

- [x] Traverse all markdown files in the `wiki/` directory.
- [x] Extract YAML frontmatter metadata (node details: ID, title, category, tags).
- [x] Extract markdown links (edges: source -> target relationships).
- [x] Construct the nodes and edges lists.
- [x] Save the resulting graph as `graph.json`.
- [x] **Verification:** Validate `graph.json` contains valid arrays of nodes and edges matching the notes directory.

---

### Phase 5: Search & Q&A (`ask.py`)
Build the Retrieval-Augmented Generation (RAG) backend to answer user questions using accumulated knowledge.

- [x] Convert user search query to vector embeddings.
- [x] Compare query embedding against the local vector database of notes.
- [x] Retrieve top-$K$ (e.g., $K=3$) matching notes.
- [x] Load corresponding note contents.
- [x] Create LLM prompt containing query + context chunks.
- [x] Call Groq Llama 3 to synthesize an answer.
- [x] **Verification:** Run `python ask.py "your question"` and inspect the output and citations.

---

### Phase 6: UI Dashboard - Graph Visualizer (`app.py`)
Build the visual graph explorer component of the frontend application.

- [x] Set up Streamlit page config and layout.
- [x] Load node and edge data from `graph.json`.
- [x] Implement interactive network visualization using a JavaScript library (`vis-network` or `Cytoscape.js`) loaded inside a Streamlit HTML component or using `streamlit-agraph`.
- [x] Apply custom CSS and styling options (pulsing nodes, color coding by PARA category, tooltips/popups showing summaries on hover, and mouse drag/zoom).

---

### Phase 7: UI Dashboard - Search Integration & Local Test (`app.py`)
Integrate components and run end-to-end system testing locally.

- [x] Build search/query text box in Streamlit.
- [x] Connect the input box to the `ask()` RAG function.
- [x] Render synthesized responses with sources/citations.
- [x] Populate with 15+ real captures to perform exhaustive testing.
- [x] Verify that new captures immediately update the graph and search index.

---

### Phase 8: Deployment Preparation
Package the application dependencies and configure environment variables for deployment.

- [x] Finalize `requirements.txt` ensuring compatibility with cloud environments.
- [x] Create a Streamlit configuration directory (`.streamlit/config.toml`) to set themes and colors.
- [x] Draft instructions for setting up Groq API Key secrets on the deployment host.
- [x] Push the clean, structured repository to a public GitHub repository.

---

### Phase 9: Public Deployment & Final Validation
Publish the application online and verify live system behavior.

- [ ] Deploy the app on Streamlit Cloud or Hugging Face Spaces.
- [ ] Configure environment secret keys on the platform.
- [ ] Validate end-to-end flow using the live deployment URL:
  - Add a note/link.
  - Verify graph updates.
  - Run search queries and check response accuracy.
