

<div align="center">

# CyGen: Advanced RAG System with Groq LLM 🚀

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg?cacheSeconds=2592000)
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.103.0-009688.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.27.0-FF4B4B.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

</div>

<p align="center">
  <img src="assets/cygen logo.png" alt="CyGen Banner" width="800"/>
</p>

CyGen is a powerful Retrieval-Augmented Generation (RAG) system built with FastAPI, MongoDB, Qdrant, and Groq LLM, featuring a Streamlit frontend for seamless interaction. This system allows you to upload PDF documents, process them intelligently, and have natural language conversations about their content.

## ✨ Features

- **📄 Advanced PDF Document Ingestion**
  - Multi-threaded PDF processing
  - Intelligent text chunking with configurable parameters
  - Background task queue for non-blocking operations
  - Progress tracking for document processing

- **🔍 Smart Vector Search**
  - Semantic similarity search using embeddings
  - Context-aware document retrieval
  - Configurable relevance thresholds
  - Metadata-enhanced document chunks

- **💬 Interactive Chat Interface**
  - Real-time chat with HTTP POST endpoint
  - Context window management
  - Conversation history with MongoDB
  - Automatic conversation titles generation

- **🧠 Groq LLM Integration**
  - Fast inference with 8k context window
  - Optimized prompting strategy
  - Balanced context retrieval
  - Temperature control for response diversity

- **🖥️ User-friendly Web UI**
  - Document upload with progress indicators
  - Conversation management
  - Responsive design
  - Real-time chat updates

## 🏗️ System Architecture

<p align="center">
  <img src="https://via.placeholder.com/800x400?text=System+Architecture" alt="System Architecture" width="800"/>
</p>

The system comprises several key components that work together:

- **FastAPI Backend**
  - RESTful API endpoints and background task processing
  - Asynchronous request handling for high concurrency
  - Dependency injection for clean service management
  - Error handling and logging

- **MongoDB**
  - Conversation history storage
  - Document metadata and status tracking
  - Asynchronous operations with Motor client
  - Indexed collections for fast retrieval

- **Qdrant Vector Database**
  - High-performance vector storage and retrieval
  - Scalable embedding storage
  - Similarity search with metadata filtering
  - Optimized for semantic retrieval

- **Groq LLM Integration**
  - Ultra-fast inference for responsive conversation
  - 8k token context window
  - Adaptive system prompts based on query context
  - Clean API integration with error handling

- **Streamlit Frontend**
  - Intuitive user interface for document uploads
  - Conversation management and history
  - Real-time chat interaction
  - Mobile-responsive design

## ⚙️ Technical Details

### PDF Processing Pipeline

Our PDF processing pipeline is designed for efficiency and accuracy:

1. **Text Extraction**: Extract raw text from PDF documents using PyPDF2
2. **Text Cleaning**: Remove artifacts and normalize text
3. **Chunking Strategy**: Implement recursive chunking with smart boundary detection
4. **Metadata Enrichment**: Add page numbers, file paths, and other metadata
5. **Vector Embedding**: Generate embeddings for each chunk
6. **Storage**: Store vectors in Qdrant and metadata in MongoDB

### RAG Implementation

The RAG system follows a sophisticated approach to content retrieval:

1. **Query Analysis**: Analyze user query for intent and keywords
2. **Context Retrieval**: Retrieve relevant document chunks from vector store
3. **Threshold Filtering**: Filter results based on similarity score threshold
4. **Context Assembly**: Combine retrieved chunks with conversation history
5. **Prompt Construction**: Build prompt with system instructions and context
6. **LLM Generation**: Generate response using Groq LLM
7. **Response Delivery**: Deliver response to user in real-time

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- uv package manager (recommended for local development)
- Groq API key
- MongoDB instance (local or Atlas)
- Qdrant instance (local or cloud)

### Environment Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/cygen.git
   cd cygen
   ```

2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

3. Update the following variables in `.env`:
   ```
   GROQ_API_KEY=your_groq_api_key
   MONGODB_URL=mongodb://username:password@host:port/db_name
   QDRANT_URL=http://qdrant_host:port
   MAX_WORKERS=4
   CHUNK_SIZE=512
   CHUNK_OVERLAP=50
   TOP_K=5
   RAG_THRESHOLD=0.75
   TEMPERATURE=0.7
   N_LAST_MESSAGE=5
   ```

### Running the Application

#### Option 1: Using the Interactive Launcher Script

```bash
chmod +x start.sh
./start.sh
```

The launcher offers the following options:
1. Start both the FastAPI backend and Streamlit frontend with Docker Compose
2. Start only the FastAPI backend
3. Start only the Streamlit frontend (with Docker or locally)

#### Option 2: Using Docker Compose

Start all services:
```bash
docker-compose up --build
```

Start only specific services:
```bash
docker-compose up --build app      # Backend only
docker-compose up --build streamlit # Frontend only
```

#### Option 3: Running Locally (Development)

1. Create and activate a virtual environment:
   ```bash
   uv venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

2. Install dependencies:
   ```bash
   uv pip install -e .
   ```

3. Start the FastAPI backend:
   ```bash
   uvicorn src.main:app --reload --port 8000
   ```

4. Start the Streamlit frontend (in a separate terminal):
   ```bash
   cd streamlit
   ./run.sh  # or `streamlit run app.py`
   ```

### Accessing the Application

- **Streamlit Frontend**: http://localhost:8501
- **FastAPI Swagger Docs**: http://localhost:8000/docs
- **API Base URL**: http://localhost:8000/api/v1

## 📋 Usage Guide

### Document Upload

1. Navigate to the Streamlit web interface
2. Click on the "Upload Documents" section in the sidebar
3. Select a PDF file (limit: 200MB per file)
4. Click "Process Document"
5. Wait for the processing to complete (progress will be displayed)

### Creating a Conversation

1. Click "New Conversation" in the sidebar
2. A new conversation will be created with a temporary title
3. The title will be automatically updated based on your first message

### Chatting with Your Documents

1. Type your question in the chat input
2. The system will:
   - Retrieve relevant context from your documents
   - Consider your conversation history
   - Generate a comprehensive answer
3. Continue the conversation with follow-up questions

### Managing Conversations

- All your conversations are saved and accessible from the sidebar
- Select any conversation to continue where you left off
- Conversation history is preserved between sessions

## 🔧 API Endpoints

The system exposes the following key API endpoints:

### Documents API

- `POST /api/v1/documents/upload`: Upload a PDF document
- `GET /api/v1/documents/task/{task_id}`: Check document processing status

### Chat API

- `PUT /api/v1/chat/conversation`: Create a new conversation
- `GET /api/v1/chat/conversations`: List all conversations
- `GET /api/v1/chat/conversations/{conversation_id}`: Get a specific conversation
- `DELETE /api/v1/chat/conversations/{conversation_id}`: Delete a conversation
- `POST /api/v1/chat/{conversation_id}`: Send a message in a conversation

## 📁 Project Structure

```
.
├── docker/                 # Docker configuration files
│   ├── app/                # Backend Docker setup
│   └── streamlit/          # Frontend Docker setup
├── logs/                   # Application logs
├── src/                    # Backend source code
│   ├── router/             # API route definitions
│   │   ├── chat.py         # Chat endpoints
│   │   └── documents.py    # Document endpoints
│   ├── utils/              # Utility modules
│   │   ├── llm.py          # LLM integration
│   │   ├── pdf_processor.py # PDF processing
│   │   ├── text_chunking.py # Text chunking
│   │   └── vector_store.py # Vector database interface
│   ├── main.py             # FastAPI application entry
│   └── settings.py         # Application settings
├── streamlit/              # Streamlit frontend
│   ├── app.py              # Main Streamlit application
│   └── utils.py            # Frontend utilities
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── uploads/                # Uploaded documents storage
├── .env.example            # Example environment variables
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile              # Backend Dockerfile
├── pyproject.toml          # Python project configuration
├── start.sh                # Interactive launcher script
└── README.md               # Project documentation
```

## 🛠️ Configuration Options

The system can be configured through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API key for LLM integration | - |
| `MONGODB_URL` | MongoDB connection string | mongodb://localhost:27017 |
| `MONGODB_DB_NAME` | MongoDB database name | rag_system |
| `QDRANT_URL` | Qdrant server URL | http://localhost:6333 |
| `MAX_WORKERS` | Maximum worker threads for PDF processing | 4 |
| `CHUNK_SIZE` | Target chunk size for document splitting | 512 |
| `CHUNK_OVERLAP` | Overlap between consecutive chunks | 50 |
| `TOP_K` | Number of chunks to retrieve per query | 5 |
| `RAG_THRESHOLD` | Similarity threshold for relevance | 0.75 |
| `TEMPERATURE` | LLM temperature setting | 0.7 |
| `N_LAST_MESSAGE` | Number of previous messages to include | 5 |

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a pull request

Please ensure your code follows our style guidelines and includes appropriate tests.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📧 Contact

Project Link: [https://github.com/NnA301023/cygen](https://github.com/NnA301023/cygen)

---

<div align="center">
  <p>Built with ❤️ by RnD Team</p>
</div>