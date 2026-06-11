#  C-RAG Research Assistant

A **Corrective Retrieval-Augmented Generation (CRAG)** system that intelligently answers research questions using your documents with web search fallback for enhanced accuracy.

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![LangChain](https://img.shields.io/badge/LangChain-latest-green.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

##  Features

-  Multi-Format Document Support - PDF, TXT, MD, CSV files
-  Intelligent Retrieval - Vector similarity search with relevance grading
-  Web Fallback - Automatically searches the web when local documents are insufficient
-  Hallucination Detection - Validates answers against source documents
-  Self-Correction - Retries generation if answers are not grounded
-  Source Tracking - Shows which documents/sources were used
-  Feedback System - Integrated with LangSmith for answer quality tracking
-  Real-time Processing - Interactive Streamlit interface

##  Architecture

```
┌─────────────┐
│   User      │
│  Question   │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Vector Retrieval   │
│   (ChromaDB)        │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Relevance Grading   │◄─── LLM Judge
└──────┬──────────────┘
       │
       ├──► Relevant Docs ──┐
       │                    │
       └──► Not Relevant    │
              │             │
              ▼             ▼
       ┌─────────────┐ ┌──────────┐
       │ Web Search  │ │ Generate │
       │  (Tavily)   │ │  Answer  │
       └──────┬──────┘ └─────┬────┘
              │              │
              └──────┬───────┘
                     ▼
              ┌──────────────┐
              │ Hallucination│◄─── LLM Judge
              │   Checking   │
              └──────┬───────┘
                     │
                     ├──► Grounded ──►  Return Answer
                     │
                     └──► Not Grounded ──►  Retry (max 3x)
```

##  Quick Start

### Prerequisites

- Python 3.9+
- Groq API key (for LLM)
- Tavily API key (for web search)
- LangSmith account (optional, for monitoring)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/crag-research-assistant.git
cd crag-research-assistant
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

Create a `.env` file in the project root:

```env
# Required
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# Optional (for monitoring)
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=crag-research-assistant
```

5. **Prepare your documents**
```bash
mkdir docs
# Add your PDF, TXT, MD, or CSV files to the docs/ folder
```

6. **Index your documents**
```bash
python ingest.py
```

7. **Run the application**
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

##  Usage

### Through the Web Interface

1. **Upload Documents** (Sidebar)
   - Click "Browse files" to upload PDFs, TXTs, MDs, or CSVs
   - Click "Re-index Documents" to process them

2. **Ask Questions**
   - Type your research question in the text area
   - Click "Search" to get your answer

3. **Review Results**
   - Read the generated answer
   - Expand "View Sources" to see supporting documents
   - Provide feedback with 👍/👎 buttons

### Programmatic Usage

```python
from graph import app

# Ask a question
result = app.invoke({
    "question": "What are the main findings about climate change?",
    "retry_count": 0
})

print(result["generation"])
```

##  Project Structure

```
crag-research-assistant/
│
├── app.py                  # Streamlit UI
├── graph.py                # LangGraph workflow definition
├── nodes.py                # Graph node functions (retrieve, grade, generate)
├── chains.py               # LLM chains for grading and validation
├── state.py                # Graph state schema
├── retriever.py            # Vector store retriever configuration
├── ingest.py               # Document loading and indexing
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not in repo)
│
├── docs/                   # Your research documents (PDFs, TXTs, etc.)
└── chroma_db/              # Vector database (auto-generated)
```

##  Configuration

### Retriever Settings (`retriever.py`)

```python
TOP_K = 6                    # Number of documents to retrieve
SCORE_THRESHOLD = 0.3        # Minimum similarity score (0-1)
```

### Chunking Parameters (`ingest.py`)

```python
CHUNK_SIZE = 1000            # Characters per chunk
CHUNK_OVERLAP = 200          # Overlap between chunks
```

### LLM Model (`nodes.py`, `chains.py`)

```python
llm = ChatGroq(
    model="llama-3.3-70b-versatile",  # Can change to other Groq models
    temperature=0
)
```

##  How It Works

### 1. **Document Retrieval**
- Converts your question into embeddings using `all-MiniLM-L6-v2`
- Searches ChromaDB vector store for similar chunks
- Returns top-K most relevant documents

### 2. **Relevance Grading**
- LLM evaluates each retrieved document for relevance
- Filters out irrelevant documents
- Triggers web search if no relevant docs found

### 3. **Web Search (Fallback)**
- Uses Tavily Search API to find current web information
- Combines web results with relevant local documents

### 4. **Answer Generation**
- Synthesizes information from all sources
- Generates comprehensive, research-focused answer

### 5. **Quality Control**
- **Hallucination Check**: Verifies answer is grounded in sources
- **Answer Grading**: Confirms answer addresses the question
- **Retry Logic**: Regenerates up to 3 times if quality checks fail

##  Monitoring with LangSmith

The system integrates with LangSmith for:
-  Tracing each query through the graph
-  Collecting user feedback
-  Debugging failed queries
-  Performance analytics

View your runs at: [smith.langchain.com](https://smith.langchain.com)

##  Use Cases

- **Academic Research** - Query multiple research papers
- **Technical Documentation** - Search internal knowledge bases
- **Legal Analysis** - Review case documents and contracts
- **Business Intelligence** - Analyze reports and market research
- **Personal Knowledge Management** - Your second brain for notes

##  Customization

### Add New Document Types

Edit `ingest.py`:

```python
from langchain_community.document_loaders import UnstructuredWordDocumentLoader

loaders = [
    # ... existing loaders
    DirectoryLoader(docs_dir, glob="**/*.docx", loader_cls=UnstructuredWordDocumentLoader),
]
```

### Change Embedding Model

Edit `retriever.py` and `ingest.py`:

```python
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2"  # More powerful
)
```

### Switch LLM Provider

Replace `ChatGroq` with `ChatOpenAI`, `ChatAnthropic`, etc.:

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4", temperature=0)
```

##  Known Limitations

- **Embedding Model**: `all-MiniLM-L6-v2` is fast but not state-of-the-art
- **Web Search**: Limited to 3 results per query (Tavily free tier)
- **No Streaming**: Answers appear all at once (can be improved)
- **Single User**: No authentication or multi-user support

##  Roadmap

- [ ] Add streaming responses
- [ ] Support for images in documents
- [ ] Multi-language support
- [ ] Better citation formatting
- [ ] Conversational memory
- [ ] Export answers to markdown/PDF
- [ ] Advanced search filters
- [ ] API endpoint deployment

##  Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

##  License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

##  Acknowledgments

- **LangChain** - For the RAG framework
- **LangGraph** - For the agentic workflow orchestration
- **Groq** - For blazing-fast LLM inference
- **Tavily** - For quality web search results
- **ChromaDB** - For the vector database
- **Streamlit** - For the beautiful UI

## 📧 Contact

For questions or feedback:
- Open an issue on GitHub
- Email: amitsingjyala@gmail.com

---

