# 🧠 Cerebro: AI-Powered Second Brain & Knowledge Graph

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io)

**Cerebro** is an automated, AI-powered personal knowledge management system ("Second Brain"). It ingests raw text notes, web URLs, and documents, automatically organizes them according to Tiago Forte's **PARA Method** (Projects, Areas, Resources, Archives), computes semantic vector links between related items, and provides an interactive visual network graph explorer alongside a hybrid RAG search engine.

---

## 🌟 Features & Highlights

- 📥 **Multi-Format Resource Ingestion**:
  - **Quick Text Notes**: Ingest thoughts and snippets directly via UI or CLI.
  - **Web Link Scraping**: Automatically scrapes HTML content from URLs and transforms it into clean Markdown (powered by `BeautifulSoup` & `markdownify`).
  - **File Uploader**: Upload `.txt`, `.md`, or `.markdown` files directly into your second brain.
- 🏷️ **Automated LLM PARA Classification**:
  - Automatically classifies every note into **Projects**, **Areas**, **Resources**, or **Archives** using Llama 3 on Groq API (`classify.py`).
- 🔗 **Semantic Linking Engine**:
  - Computes vector embeddings using local models (`sentence-transformers/all-MiniLM-L6-v2`) to detect conceptual relationships and insert bidirectional Wikilinks (`[[Note Title]]`) between notes (`link.py`).
- 🕸️ **Interactive Network Graph Explorer**:
  - Custom JavaScript `vis-network` Streamlit component with PARA color-coding, dynamic node sizes, summary tooltips, physics layout toggles, keyword node search, click-to-inspect metadata panel, and tab-switch auto-canvas fitting (`graph_component/index.html`).
- 🤖 **Ask Cerebro (RAG Search Engine)**:
  - Vector similarity retrieval engine paired with Gemini 2.5 Flash / Groq LLMs to answer questions from your notes with exact source citations and similarity scores (`ask.py`).
- 📁 **Note Vault Browser**:
  - Dedicated browser tab to inspect all categorized notes in your vault, view summary tags, source paths, and read full note content.
- 🔄 **Real-Time Data Persistence & GitHub Auto-Sync**:
  - Automatic Git commit & push pipeline (`git_sync.py`) that commits new notes and graph updates back to GitHub, preserving your second brain data even across Streamlit Cloud redeployments and container sleep after inactivity.

---

## 📁 Repository Structure

```text
cerebro/
├── app.py                   # Main Streamlit application dashboard
├── capture.py               # Resource capture & web scraping module
├── classify.py              # LLM PARA classification engine
├── link.py                  # Semantic vector similarity linking script
├── build_graph.py           # Network graph builder (nodes & edges)
├── ask.py                   # RAG search engine & terminal Q&A
├── git_sync.py              # Automated Git sync & push module
├── requirements.txt         # Python dependencies
├── graph.json               # Knowledge graph data structure
├── .streamlit/
│   └── config.toml          # Streamlit dark theme & configuration
├── graph_component/         # Custom vis-network Streamlit HTML component
│   └── index.html
├── raw/                     # Raw JSON capture payloads
├── data/                    # Vector embeddings cache & graph data
└── wiki/                    # Organised PARA markdown files
    ├── Projects/
    ├── Areas/
    ├── Resources/
    └── Archives/
```

---

## 🧹 How to Clear Sample Data & Build Your Own Brain

If you just cloned this repository and want to start fresh with your own notes and knowledge graph, follow these steps to reset the sample data:

### Step 1: Delete Sample Notes & Cache Files

#### On Windows (PowerShell):
```powershell
# Remove sample raw capture files
Get-ChildItem -Path "raw" -Exclude ".gitkeep" | Remove-Item -Force -Recurse

# Remove sample markdown notes from PARA directories
Get-ChildItem -Path "wiki\Projects", "wiki\Areas", "wiki\Resources", "wiki\Archives" -Exclude ".gitkeep" | Remove-Item -Force -Recurse

# Remove cached graph and embeddings
Remove-Item -Path "graph.json", "data\graph.json", "data\wiki_embeddings.pkl" -Force -ErrorAction SilentlyContinue
```

#### On macOS / Linux (Bash):
```bash
# Remove sample raw captures and markdown notes (keeping directory structure)
rm -f raw/*.json
rm -f wiki/Projects/*.md wiki/Areas/*.md wiki/Resources/*.md wiki/Archives/*.md

# Remove cached graph and embeddings
rm -f graph.json data/graph.json data/wiki_embeddings.pkl
```

### Step 2: Initialize a Clean Empty Graph
Run the graph builder script to generate a fresh, empty `graph.json` file:
```bash
python build_graph.py
```

Now your vault is completely clean and ready for your personal notes!

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
- Python 3.9+
- A Groq API Key ([Get one here](https://console.groq.com/))
- A Google Gemini API Key ([Get one here](https://aistudio.google.com/))

### 2. Installation
```bash
# Clone repository
git clone https://github.com/Niklaus2003/cerebro.git
cd cerebro

# Create and activate virtual environment
python -m venv venv

# On Windows (PowerShell):
.\venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables Setup
Create a `.env` file in the root directory:
```env
# Required for note classification
GROQ_API_KEY=gsk_your_groq_api_key_here

# Required for high-token RAG Q&A synthesis
GEMINI_API_KEY=your_gemini_api_key_here

# (Optional) GitHub Token for automatic persistence if deploying to Streamlit Cloud
GITHUB_TOKEN=ghp_your_github_personal_access_token_here
```

### 4. Running the Dashboard
Launch the interactive Streamlit dashboard:
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser to start adding your own knowledge!

---

## 🛠️ Command Line Usage

You can also interact with Cerebro directly from your terminal:

```bash
# 1. Capture raw text note
python capture.py --text "Key insights on transformer self-attention mechanisms..."

# 2. Capture & scrape web link
python capture.py --link "https://en.wikipedia.org/wiki/Knowledge_graph"

# 3. Classify raw notes into PARA architecture
python classify.py

# 4. Compute vector embeddings & build semantic graph
python link.py
python build_graph.py

# 5. Ask RAG questions in terminal
python ask.py "What notes do I have on knowledge graphs?"
```

---

## ☁️ Streamlit Community Cloud Deployment

To host your Cerebro instance online with full data persistence:

1. Push your repository to GitHub (`https://github.com/Niklaus2003/cerebro.git`).
2. Log in to [share.streamlit.io](https://share.streamlit.io/) and create a **New app**.
3. Set **Main file path** to `app.py`.
4. Under **Advanced Settings -> Secrets**, paste your environment secrets:
   ```toml
   GROQ_API_KEY = "gsk_your_groq_api_key_here"
   GEMINI_API_KEY = "your_gemini_api_key_here"
   GITHUB_TOKEN = "ghp_your_github_personal_access_token_here"
   ```
5. Click **Deploy**.
   *Note: Providing `GITHUB_TOKEN` enables real-time auto-commit & push so newly ingested notes persist even if the Cloud container sleeps or redeploys!*

---

## 📄 License

MIT License. Built for the July Cohort Second Brain Project.
