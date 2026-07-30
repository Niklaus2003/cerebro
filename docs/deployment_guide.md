# Deployment Guide & Environment Secrets Setup: Cerebro

This document provides step-by-step instructions for deploying **Cerebro** to cloud hosting platforms (such as Streamlit Community Cloud, Hugging Face Spaces, or Docker containers) and configuring required LLM API keys.

---

## 1. Required Environment Variables

Cerebro requires the following environment variables for automatic PARA classification and RAG question answering:

| Variable Name | Required | Purpose | Provider |
|---|---|---|---|
| `GROQ_API_KEY` | **Yes** (Primary) | Powers Llama-3 PARA classification and RAG response synthesis | [Groq Console](https://console.groq.com/) |
| `GEMINI_API_KEY` | Optional (Fallback) | Powers Google Gemini 2.5 Flash / 1.5 Flash fallback response synthesis | [Google AI Studio](https://aistudio.google.com/) |

---

## 2. Option A: Streamlit Community Cloud (Recommended)

Streamlit Community Cloud provides seamless 1-click hosting for Streamlit applications directly from GitHub.

### Step 1: Push Repository to GitHub
Ensure all code and configuration files are committed and pushed to your public/private GitHub repository.

### Step 2: Create a New App on Streamlit Cloud
1. Log in to [share.streamlit.io](https://share.streamlit.io/).
2. Click **"New app"**.
3. Select your repository, branch (`main`), and set **Main file path** to `app.py`.

### Step 3: Configure Secret Keys in Streamlit Cloud
1. Click **"Advanced settings..."** before deploying (or navigate to **Settings -> Secrets** on your deployed app dashboard).
2. Paste your API keys into the secrets editor in TOML format:
```toml
# Streamlit Cloud Secrets Configuration
GROQ_API_KEY = "gsk_your_groq_api_key_here"
GEMINI_API_KEY = "AIzaSy_your_gemini_api_key_here"
```
3. Click **Save**.

*Note: `app.py` automatically injects keys from `st.secrets` into the Python environment at runtime.*

### Step 4: Deploy
Click **"Deploy!"**. Streamlit Cloud will automatically build dependencies from `requirements.txt` and launch the application.

---

## 3. Option B: Hugging Face Spaces

1. Create a new Space on [Hugging Face](https://huggingface.co/new-space).
2. Select **Streamlit** as the Space SDK.
3. In **Settings -> Repository secrets**, add:
   - Name: `GROQ_API_KEY`, Value: `gsk_...`
   - Name: `GEMINI_API_KEY`, Value: `AIzaSy...`
4. Upload or connect your repository files.

---

## 4. Option C: Docker / VPS Container Deployment

To run Cerebro inside a Docker container on AWS, GCP, Azure, or DigitalOcean:

### Dockerfile
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Run Command
```bash
docker build -t cerebro-app .
docker run -d -p 8501:8501 \
  -e GROQ_API_KEY="gsk_your_groq_key" \
  -e GEMINI_API_KEY="AIzaSy_your_gemini_key" \
  --name cerebro cerebro-app
```

---

## 5. Local Pre-deployment Verification Checklist

Before pushing to production:
1. Verify `requirements.txt` contains all top-level dependencies.
2. Confirm `.streamlit/config.toml` is included.
3. Test locally using:
   ```bash
   streamlit run app.py
   ```
4. Confirm `.env` and `.streamlit/secrets.toml` are in `.gitignore` so secret keys are never committed to public repositories.
