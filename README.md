<div align="center">

# 📄 PDF Assistant

### *Chat with your PDFs using AI - Just paste a link and start asking!*

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![SAP AI Core](https://img.shields.io/badge/SAP-AI_Core-0FAAFF?style=for-the-badge&logo=sap&logoColor=white)](https://www.sap.com/products/artificial-intelligence.html)

---

**Turn any PDF URL into an interactive Q&A chatbot in seconds!**

[Features](#-features) • [Demo](#-demo) • [Installation](#-installation) • [Usage](#-usage) • [Architecture](#-architecture)

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔗 **URL-based PDF Loading** | Just paste any PDF link - no downloads needed |
| 💬 **Multi-PDF Conversations** | Add multiple PDFs to the same chat session |
| 🧠 **Smart RAG Pipeline** | Vector-based semantic search for accurate answers |
| 💾 **Persistent Chat History** | All conversations saved automatically |
| 🎨 **Beautiful UI** | Clean Streamlit interface with sidebar navigation |
| ⚡ **Production Ready** | Connection pooling, error handling, scalable design |

---

## 🎬 Demo

```
┌─────────────────────────────────────────────────────────────────┐
│  📄 PDF Assistant                    │ 💬 Chat with your PDFs  │
├─────────────────────────────────────────────────────────────────┤
│                                      │                          │
│  ➕ New Conversation                 │  You: Here's a PDF about │
│  ─────────────────────               │  machine learning:       │
│                                      │  https://example.com/    │
│  📚 PDFs in this chat                │  ml-guide.pdf            │
│  ├── 📄 ml-guide.pdf                │                          │
│  └── 📄 research-paper.pdf          │  🤖 Assistant: I've      │
│                                      │  loaded the PDF! It      │
│  💬 Chat History                     │  contains 45 pages about │
│  ├── 📂 ML Discussion               │  neural networks...      │
│  ├── 📂 Research Notes              │                          │
│  └── 📂 Technical Docs              │  You: What are the main  │
│                                      │  topics covered?         │
│                                      │                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Installation

### Prerequisites

- Python 3.9+
- PostgreSQL with pgvector extension
- SAP AI Core credentials (for embeddings & LLM)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/kpcreative/pdf_reader_agent_from_pdf_link.git
cd pdf_reader_agent_from_pdf_link

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup

Create a `.env` file in the root directory:

```env
# SAP AI Core Configuration
AICORE_AUTH_URL=https://your-auth-url.authentication.sap.hana.ondemand.com
AICORE_CLIENT_ID=your-client-id
AICORE_CLIENT_SECRET=your-client-secret
AICORE_BASE_URL=https://api.ai.your-region.aws.ml.hana.ondemand.com
AICORE_RESOURCE_GROUP=your-resource-group

# Database (PostgreSQL with pgvector)
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/pdf_assistant

# Model Configuration (optional)
MODEL_NAME=gpt-4o
EMBEDDING_MODEL=text-embedding-3-small
```

### Database Setup

```bash
# Using Docker (recommended)
docker run -d \
  --name pgvector-db \
  -e POSTGRES_USER=ai \
  -e POSTGRES_PASSWORD=ai \
  -e POSTGRES_DB=ai \
  -p 5532:5432 \
  pgvector/pgvector:pg16
```

---

## 🚀 Usage

### Start the Application

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

### How to Use

1. **Start a New Chat** - Click "➕ New Conversation" in the sidebar
2. **Add a PDF** - Paste any PDF URL in the chat
3. **Ask Questions** - The AI will answer based on PDF content
4. **Add More PDFs** - Add multiple PDFs to the same conversation
5. **Switch Chats** - Access previous conversations from the sidebar

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         STREAMLIT UI                               │
│                        (app.py)                                    │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                      PDF ASSISTANT                                 │
│                    (pdf_assistant.py)                              │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────────┐    │
│  │ URL Parser  │  │ Chat Management │  │ Knowledge Base Ops  │    │
│  └─────────────┘  └─────────────────┘  └─────────────────────┘    │
└────────────────────────────┬───────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐
│  LLM Client     │  │ Custom Embedder │  │  PDF Reader             │
│ (SAP AI Core)   │  │ (SAP AI Core)   │  │  (PyPDF)                │
│ llm_client.py   │  │ custom_embedder │  │  custom_pdf_reader.py   │
└─────────────────┘  └─────────────────┘  └─────────────────────────┘
         │                   │
         └─────────┬─────────┘
                   ▼
┌────────────────────────────────────────────────────────────────────┐
│                 POSTGRESQL + PGVECTOR                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────────┐ │
│  │ Vector Store   │  │ Chat History   │  │ PDF Metadata         │ │
│  │ (Embeddings)   │  │ (Messages)     │  │ (Source tracking)    │ │
│  └────────────────┘  └────────────────┘  └──────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
pdf_assistant/
├── 📄 app.py                 # Streamlit web interface
├── 🤖 pdf_assistant.py       # Core assistant logic & RAG pipeline
├── 🔗 llm_client.py          # SAP AI Core LLM integration
├── 🧮 custom_embedder.py     # Custom embedding provider
├── 📑 custom_pdf_reader.py   # PDF parsing & text extraction
├── 🔍 debug_storage.py       # Storage debugging utilities
├── 📋 list_models.py         # List available AI models
├── 📦 requirements.txt       # Python dependencies
├── 🔒 .env                   # Environment variables (not in git)
└── 📖 README.md              # You are here!
```

---

## 🔧 Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `MODEL_NAME` | LLM model for chat | `gpt-4o` |
| `EMBEDDING_MODEL` | Embedding model | `text-embedding-3-small` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql+psycopg://ai:ai@localhost:5532/ai` |
| `VECTOR_COLLECTION` | Vector store collection name | `pdf_embeddings` |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📜 License

This project is open source and available under the [MIT License](LICENSE).

---

## 🙏 Acknowledgments

- [Phidata](https://github.com/phidatahq/phidata) - AI toolkit framework
- [Streamlit](https://streamlit.io) - Web UI framework
- [pgvector](https://github.com/pgvector/pgvector) - Vector similarity search for PostgreSQL
- [SAP AI Core](https://www.sap.com/products/artificial-intelligence.html) - Enterprise AI platform

---

<div align="center">

**Made with ❤️ by [Kartik Pandey](https://github.com/kpcreative)**

⭐ Star this repo if you found it helpful!

</div>
