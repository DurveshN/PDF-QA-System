"""
PDF-to-knowledge pipeline using Gemini 2.5 Flash.

Provides:
  - extract_knowledge_objects() — sends PDF to Gemini, gets structured JSON
  - build_langchain_documents() — converts knowledge objects to LangChain Documents
  - process_pdf() — orchestrates the full pipeline with progress tracking

The pipeline flow:
  1. Upload PDF bytes → Gemini 2.5 Flash API for extraction
  2. Parse JSON → knowledge_objects list
  3. Build LangChain Documents with metadata
  4. Index into session-specific ChromaDB via vectorstore module
"""

import os
import json
import asyncio
import uuid
from datetime import datetime, timezone

from google import genai
from google.genai import types
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from core.embeddings import build_embedding_text
from core.vectorstore import create_session_vectorstore
from dotenv import load_dotenv
load_dotenv()

def _get_gemini_client():
    """Create a Gemini API client."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment variables.")
    return genai.Client(api_key=api_key)


async def extract_knowledge_objects(
    pdf_bytes: bytes,
    filename: str,
) -> dict:
    """
    Send a PDF to Gemini 2.5 Flash and extract structured knowledge objects.

    Args:
        pdf_bytes: Raw bytes of the PDF file.
        filename: Original filename for logging.

    Returns:
        Dict with {"markdown": str, "knowledge_objects": list[dict]}
    """
    client = _get_gemini_client()

    prompt = """
Role:
You are an expert Academic Transcription Assistant specializing in Software Project Management (SPM).

Objective:
Transcribe the attached handwritten PDF into structured Markdown AND structured JSON knowledge objects optimized for semantic retrieval and RAG systems.

Critical Rules:
- Do NOT summarize.
- Do NOT omit any content.
- Preserve full informational completeness.
- Correct obvious spelling errors while preserving original meaning.
- If handwriting is unclear, write: [Unclear Text: possible interpretation].
- Do NOT invent missing information.

Markdown Formatting:

# Headings
# Unit titles
## major sections
### sub-sections

Paragraph Structure:
- Keep related concepts together
- Maximum 6–8 lines
- Use bullet points where useful

Terminology:
Write full technical terms at least once.

Example:
Critical Path Method (CPM)
Program Evaluation and Review Technique (PERT)
Activity-on-Node (AON)
Precedence Network Diagram

Diagrams:
Create section:

### [Diagram Analysis]

Include:
- Components
- Logical flow
- Dependencies

Tables:
Recreate as Markdown tables.

Charts:
Explain axes and trends.

Concept Markers:
**Definition:**
**Process Steps:**
**Advantages:**
**Disadvantages:**

JSON Knowledge Extraction:

Each object format:

{
"id": "...",
"unit": "...",
"topic": "...",
"section": "...",
"type": "definition | process | explanation | diagram | table | advantages | disadvantages",
"keywords": [],
"content": "..."
}

Return ONLY JSON:

{
"markdown": "...",
"knowledge_objects": []
}
"""

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(
                    data=pdf_bytes,
                    mime_type="application/pdf",
                ),
                prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )

        data = json.loads(response.text)

        if "knowledge_objects" not in data:
            raise ValueError("Gemini response missing 'knowledge_objects' key.")

        return data

    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Gemini response as JSON: {e}")
    except Exception as e:
        raise RuntimeError(f"Gemini extraction failed for '{filename}': {e}")


def build_langchain_documents(knowledge_objects: list[dict]) -> list[Document]:
    """
    Convert knowledge objects to LangChain Document objects.

    Each document gets:
      - page_content: The full embedding text (unit + topic + section + type + keywords + content)
      - metadata: {id, unit, topic, section, type} for filtering in ChromaDB

    Args:
        knowledge_objects: List of knowledge object dicts from Gemini extraction.

    Returns:
        List of LangChain Document objects.
    """
    documents = []
    for obj in knowledge_objects:
        text = build_embedding_text(obj)
        metadata = {
            "id": obj.get("id", ""),
            "unit": obj.get("unit", ""),
            "topic": obj.get("topic", ""),
            "section": obj.get("section", ""),
            "type": obj.get("type", ""),
        }
        doc = Document(page_content=text, metadata=metadata)
        documents.append(doc)

    return documents


async def process_pdf(
    pdf_bytes: bytes,
    filename: str,
    session_id: str,
    embedding_fn: Embeddings,
    progress_callback=None,
) -> dict:
    """
    Full PDF processing pipeline:
      1. Extract knowledge objects via Gemini (0-40%)
      2. Build LangChain documents (40-60%)
      3. Create/update session vector store (60-100%)

    Args:
        pdf_bytes: Raw PDF file bytes.
        filename: Original filename.
        session_id: The chat session to index into.
        embedding_fn: EmbeddingGemmaLangChain instance.
        progress_callback: Optional async callable(stage, progress, message).

    Returns:
        Dict with {note_id, filename, topic_count, chunk_count, created_at}
    """
    note_id = str(uuid.uuid4())

    # ── Stage 1: Extract with Gemini ─────────────────────────────────────
    if progress_callback:
        await progress_callback("extracting", 10, "Extracting with Gemini...")

    data = await extract_knowledge_objects(pdf_bytes, filename)
    knowledge_objects = data.get("knowledge_objects", [])
    markdown_text = data.get("markdown", "")

    if progress_callback:
        await progress_callback("extracting", 40, f"Extracted {len(knowledge_objects)} knowledge objects")

    # ── Stage 2: Build LangChain Documents ───────────────────────────────
    if progress_callback:
        await progress_callback("embedding", 50, "Building embeddings...")

    documents = build_langchain_documents(knowledge_objects)

    if progress_callback:
        await progress_callback("embedding", 60, f"Built {len(documents)} documents")

    # ── Stage 3: Index to ChromaDB ───────────────────────────────────────
    if progress_callback:
        await progress_callback("indexing", 70, "Indexing to ChromaDB...")

    # Run the indexing in a thread since it's CPU-bound (embedding computation)
    vector_store = await asyncio.to_thread(
        create_session_vectorstore,
        session_id,
        documents,
        embedding_fn,
    )

    chunk_count = vector_store._collection.count()

    if progress_callback:
        await progress_callback("done", 100, "Done!")

    # Extract unique topics for metadata
    topics = list(set(obj.get("topic", "") for obj in knowledge_objects if obj.get("topic")))

    # Save extracted data alongside the vector store
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "vector_stores",
        session_id,
    )
    os.makedirs(data_dir, exist_ok=True)

    # Save the knowledge objects JSON for reference
    with open(os.path.join(data_dir, "knowledge_objects.json"), "w", encoding="utf-8") as f:
        json.dump(knowledge_objects, f, indent=2, ensure_ascii=False)

    # Save the markdown for reference
    with open(os.path.join(data_dir, "notes.md"), "w", encoding="utf-8") as f:
        f.write(markdown_text)

    return {
        "note_id": note_id,
        "filename": filename,
        "topic_count": len(topics),
        "chunk_count": chunk_count,
        "topics": topics,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
