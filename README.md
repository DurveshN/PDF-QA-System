# PDF-QA System

An AI-powered Question-Answering system for PDF documents. The application leverages State-of-the-Art Language Models (Gemma) via Ollama, local vector stores for retrieval-augmented generation (RAG), and Exa for supplementary web searches. 

## Features
- **Local RAG Workflow**: Ingests, processes, and chunk PDF documents using local Embedding models (e.g., `google/embeddinggemma-300M`) and ChromaDB vector store.
- **FastAPI Backend**: A robust asynchronous backend to handle chat sessions, document uploads, user notes, and memory mapping.
- **Ollama Integration**: Seamless integration with local Ollama service to serve LLMs like Gemma for high-quality, local, and private chat responses.
- **Web Search Fallback**: Automatically integrates Exa API to perform web searches when the LLM requires more up-to-date context.

## Project Structure

- `frontend/`: React single-page application built with Vite, Tailwind CSS, and Zustand.
- `backend/`: The FastAPI backend containing routing, core AI modules, and RAG implementations.
- `jupyter/`: Jupyter notebooks used for data exploration, rapid prototyping, and workflow validation.
- `docs/`: Reference documentation regarding specific integration components like LangChain, Exa, and Gemma.

## Prerequisites
- **Python**: version >= 3.9
- **Ollama**: Installed and running locally. Ensure the intended model (e.g., `gemma4:e2b`) is pulled via `ollama run <model-name>`.
- **Node.js**: If running a separate front-end client (expected at `http://localhost:5173`).

## Setup and Installation

### Backend Setup

1. **Clone the repository**:
   ```bash
   git clone <your-repo-link>
   cd "PDF-QA system"
   ```

2. **Set up the backend virtual environment**:
   ```bash
   cd backend
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**:
   Create a `.env` file inside the `backend/` directory with the required variables:
   ```env
   # LLM Configs
   OLLAMA_MODEL="gemma4:e2b"
   EMBEDDING_MODEL="google/embeddinggemma-300M"
   
   # External APIs
   EXA_API_KEY="your-exa-api-key"   # Optional, for web search functionality
   
   # App Configs
   BACKEND_PORT=8000
   ```

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install Node modules**:
   ```bash
   npm install
   ```

3. **Environment Variables**:
   Create a `.env` file in the `frontend/` directory (if required). By default, Vite will connect to the backend running at `http://localhost:8000`.

## Running the Application

Ensure Ollama is running in the background.

**1. Start the Backend**:
```bash
cd backend
python main.py
```
The API will be accessible over `http://localhost:8000`. You can interact with the Swagger docs at `http://localhost:8000/docs`.

**2. Start the Frontend**:
In a separate terminal session:
```bash
cd frontend
npm run dev
```
The user interface will be accessible at `http://localhost:5173`.
