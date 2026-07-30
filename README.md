# Cerebro: AI-Powered Second Brain & Knowledge Graph

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io)

**Cerebro** is an automated, AI-powered personal knowledge management system ("Second Brain") that ingests notes, web links, and documents, automatically organizes them according to Tiago Forte's **PARA Method** (Projects, Areas, Resources, Archives), computes semantic vector links between related items, and provides an interactive visual network graph explorer alongside a hybrid RAG search interface.

---

## 🌟 Key Features

- 📥 **Capture Engine (`capture.py`)**: Ingest raw text notes, web URLs, or text documents into structured JSON payloads with metadata.
- 🏷️ **LLM PARA Classifier (`classify.py`)**: Automatically categorizes captures into Projects, Areas, Resources, or Archives using Llama 3 on Groq API.
- 🔗 **Semantic Linker (`link.py`)**: Uses local vector embeddings (`sentence-transformers/all-MiniLM-L6-v2`) to find conceptual similarities and insert bidirectional wiki links (`[[Note Title]]`).
- 🕸️ **Interactive Graph Visualizer (`app.py`)**: Renders custom JavaScript (`vis-network`) interactive node-edge network graphs with category color-coding, physics layout, node popups, search, and filtering.
- 💬 **RAG Q&A Engine (`ask.py`)**: Perform natural language semantic searches across your accumulated personal knowledge with synthesis provided by Llama-3 / Gemini.

---

## 📁 Repository Structure

```text
cerebro/
├── app.py                   # Main Streamlit web application & graph visualizer
├── capture.py               # Ingestion script for notes, URLs, and files
├── classify.py              # LLM PARA classification script
├── link.py                  # Semantic vector similarity linking script
├── build_graph.py           # Network graph builder (nodes & edges)
├── ask.py                   # Semantic RAG search & Q&A CLI
├── requirements.txt         # Python dependency specifications
├── graph.json               # Generated network graph data
├── .streamlit/
│   └── config.toml          # Streamlit theme & server configuration
├── docs/
│   ├── implementation_plan.md  # Detailed implementation roadmap
│   ├── deployment_guide.md     # Deployment & secrets setup instructions
│   ├── architecture.md         # System architecture documentation
│   └── problem_statement.md    # Problem statement & specifications
├── raw/                     # Unprocessed captured raw JSON files
└── wiki/                    # Organised PARA markdown files
    ├── Projects/
    ├── Areas/
    ├── Resources/
    └── Archives/
```

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
- Python 3.9+
- A Groq API Key ([Get one here](https://console.groq.com/))
- (Optional) A Google Gemini API Key ([Get one here](https://aistudio.google.com/))

### 2. Installation
```bash
# Clone repository
git clone https://github.com/your-username/cerebro.git
cd cerebro

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the project root:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
GEMINI_API_KEY=AIzaSy_your_gemini_api_key_here
```

### 4. Running the Dashboard
Launch the interactive dashboard locally:
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your web browser.

---

## 🛠️ Command Line Usage

### Capture New Knowledge
```bash
# Capture raw text note
python capture.py --text "Key takeaways from quantum computing lecture..."

# Capture web link
python capture.py --url "https://en.wikipedia.org/wiki/Graph_theory"
```

### Classify Raw Captures
```bash
python classify.py
```

### Compute Semantic Links & Re-build Graph
```bash
python link.py
python build_graph.py
```

### Ask RAG Questions via Terminal
```bash
python ask.py "What notes do I have on graph theory?"
```

---

## ☁️ Deployment Instructions

Detailed instructions for deploying Cerebro to **Streamlit Community Cloud**, **Hugging Face Spaces**, or **Docker** can be found in the [Deployment Guide](file:///docs/deployment_guide.md).

### Quick Streamlit Cloud Deployment:
1. Push repository to GitHub.
2. Connect repository on [share.streamlit.io](https://share.streamlit.io/).
3. Add API Keys under **Advanced Settings -> Secrets**:
   ```toml
   GROQ_API_KEY = "gsk_..."
   ```
4. Click **Deploy**.

---

## 📄 License

MIT License. Built for the July Cohort Second Brain project.
