"""
Tool implementation functions for the PDF-QA agent.

Defines 5 tool functions:
  1. retrieve_chunks — semantic search in session's ChromaDB
  2. list_topics — enumerate available knowledge metadata
  3. web_search — Exa API fallback for external info
  4. generate_diagram — retrieves chunks + returns instruction for Mermaid generation
  5. save_memory — persists user preferences/facts

These are the raw implementation functions. They accept dependencies
(vector_store, exa_client) as explicit parameters.

In Phase 2, routers/chat.py defines make_tools(vector_store, exa_client)
which wraps these into closures with proper LangChain-compatible signatures
for bind_tools().

Note: load_memory is NOT a tool — called at session start, injected into
system prompt. summarize_session is NOT a tool — triggered only via REST.
"""

import json
from typing import Optional

from langchain_chroma import Chroma


# ── Tool 1: retrieve_chunks ──────────────────────────────────────────────────


def retrieve_chunks_impl(
    query: str,
    vector_store: Chroma | None,
    top_k: int = 4,
    filter_type: Optional[str] = None,
    filter_unit: Optional[str] = None,
) -> str:
    """
    Search the session's PDF knowledge base (ChromaDB) for relevant chunks.

    Args:
        query: The search query.
        vector_store: Session's Chroma instance, or None if no notes uploaded.
        top_k: Number of chunks to retrieve.
        filter_type: Optional filter by knowledge type
                     (definition|process|explanation|diagram|table|advantages|disadvantages).
        filter_unit: Optional filter by unit name (e.g. "Unit-III").

    Returns:
        JSON string with status + chunks.
    """
    if vector_store is None:
        return json.dumps({
            "status": "no_notes",
            "message": "No PDF notes uploaded for this session. Use web_search instead.",
            "chunks": [],
        })

    # Build Chroma metadata filter
    where_filter = None
    if filter_type and filter_unit:
        where_filter = {
            "$and": [
                {"type": {"$eq": filter_type}},
                {"unit": {"$eq": filter_unit}},
            ]
        }
    elif filter_type:
        where_filter = {"type": {"$eq": filter_type}}
    elif filter_unit:
        where_filter = {"unit": {"$eq": filter_unit}}

    # Run similarity search
    results = vector_store.similarity_search_with_score(
        query,
        k=top_k,
        filter=where_filter,
    )

    if not results:
        return json.dumps({
            "status": "no_results",
            "query": query,
            "num_results": 0,
            "chunks": [],
        })

    chunks = []
    for doc, score in results:
        chunks.append({
            "similarity_score": round(float(score), 4),
            "topic": doc.metadata.get("topic", ""),
            "section": doc.metadata.get("section", ""),
            "type": doc.metadata.get("type", ""),
            "unit": doc.metadata.get("unit", ""),
            "content": doc.page_content,
        })

    return json.dumps({
        "status": "success",
        "query": query,
        "num_results": len(chunks),
        "chunks": chunks,
    }, ensure_ascii=False, indent=2)


# ── Tool 2: list_topics ─────────────────────────────────────────────────────


def list_topics_impl(vector_store: Chroma | None) -> str:
    """
    List all topics, sections, units, and knowledge types in the knowledge base.

    Args:
        vector_store: Session's Chroma instance, or None.

    Returns:
        JSON string with metadata summary.
    """
    if vector_store is None:
        return json.dumps({
            "status": "no_notes",
            "message": "No PDF notes uploaded for this session.",
        })

    collection = vector_store._collection
    results = collection.get(include=["metadatas"])
    metadatas = results.get("metadatas", [])

    topics = sorted(set(m.get("topic", "") for m in metadatas if m.get("topic")))
    sections = sorted(set(m.get("section", "") for m in metadatas if m.get("section")))
    units = sorted(set(m.get("unit", "") for m in metadatas if m.get("unit")))
    types = sorted(set(m.get("type", "") for m in metadatas if m.get("type")))

    return json.dumps({
        "status": "success",
        "total_chunks": len(metadatas),
        "units": units,
        "topics": topics,
        "sections": sections,
        "types": types,
    }, ensure_ascii=False, indent=2)


# ── Tool 3: web_search ───────────────────────────────────────────────────────


def web_search_impl(
    query: str,
    exa_client,
    num_results: int = 3,
) -> str:
    """
    Search the web using Exa for information not found in the knowledge base.

    Args:
        query: A clear, descriptive search query.
        exa_client: The Exa client instance.
        num_results: Number of web results (default 3, max 5).

    Returns:
        JSON string with search results.
    """
    num_results = min(num_results, 5)

    try:
        response = exa_client.search_and_contents(
            query,
            type="auto",
            num_results=num_results,
            contents={
                "highlights": {
                    "max_characters": 3000,
                }
            },
        )

        results = []
        for r in response.results:
            results.append({
                "title": r.title,
                "url": r.url,
                "highlights": r.highlights if r.highlights else [],
                "published": r.published_date,
            })

        return json.dumps({
            "status": "success",
            "query": query,
            "num_results": len(results),
            "results": results,
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e),
        })


# ── Tool 4: generate_diagram ────────────────────────────────────────────────


def generate_diagram_impl(
    topic: str,
    vector_store: Chroma | None,
    diagram_type: str = "flowchart",
) -> str:
    """
    Retrieve relevant chunks for a topic to generate a diagram.

    Does NOT make a nested LLM call. Returns raw chunks plus an instruction
    string. The outer agentic loop's Gemma response generates the Mermaid
    syntax from these chunks.

    Args:
        topic: The topic to visualize.
        vector_store: Session's Chroma instance.
        diagram_type: Type of diagram (flowchart|sequence|mindmap|graph).

    Returns:
        JSON string with chunks + Mermaid generation instruction.
    """
    # Retrieve relevant chunks using the same logic as retrieve_chunks
    chunks_json = retrieve_chunks_impl(
        query=topic,
        vector_store=vector_store,
        top_k=6,  # Get more chunks for diagram context
    )
    chunks_data = json.loads(chunks_json)

    if chunks_data.get("status") != "success":
        return json.dumps({
            "status": chunks_data.get("status", "error"),
            "message": chunks_data.get("message", "Failed to retrieve chunks for diagram."),
            "topic": topic,
            "diagram_type": diagram_type,
        })

    return json.dumps({
        "status": "success",
        "topic": topic,
        "diagram_type": diagram_type,
        "instruction": (
            f"Generate a valid Mermaid.js {diagram_type} diagram based on the chunks below. "
            f"IMPORTANT RULES for valid Mermaid syntax:\n"
            f"- Start with the diagram type keyword on the first line (e.g. 'flowchart TD', 'graph LR', 'sequenceDiagram', 'mindmap')\n"
            f"- Use simple alphanumeric node IDs (A, B, C or node1, node2) — NO spaces in IDs\n"
            f"- Put labels in square brackets: A[My Label] --> B[Other Label]\n"
            f"- Use --> for arrows, --- for lines\n"
            f"- Do NOT use special characters like parentheses, colons, or quotes inside node IDs\n"
            f"- Wrap the diagram in ```mermaid``` code fences\n"
        ),
        "chunks": chunks_data.get("chunks", []),
    }, ensure_ascii=False, indent=2)


# ── Tool 5: save_memory ─────────────────────────────────────────────────────

# save_memory_impl is in core/memory.py — imported in make_tools() below.


# ── make_tools() — closure factory ───────────────────────────────────────────


def make_tools(
    vector_store: Chroma | None,
    exa_client,
    session_id: str = "",
    enable_web_search: bool = True,
) -> list:
    """
    Create session-scoped tool functions using closures.

    Each closure captures the session's vector_store and exa_client independently.
    Returns a list of LangChain @tool-decorated functions ready for bind_tools().

    Args:
        vector_store: Session's Chroma instance, or None if no notes uploaded.
        exa_client: The Exa client instance for web search.
        session_id: Current session ID (used by save_memory).
        enable_web_search: Whether to include the web_search tool.

    Returns:
        List of @tool decorated functions.
    """
    from langchain_core.tools import tool
    from core.memory import save_memory_impl

    tools = []
    print(f"[TOOLS] Building tools: vs={'yes' if vector_store else 'no'}, "
          f"exa={'yes' if exa_client else 'no'}, web_search={enable_web_search}")

    # ── retrieve_chunks ──────────────────────────────────────────────────

    @tool
    def retrieve_chunks(
        query: str,
        top_k: int = 4,
        filter_type: Optional[str] = None,
        filter_unit: Optional[str] = None,
    ) -> str:
        """Search the session's PDF knowledge base for relevant chunks.
        Use this to find information from uploaded notes. Call this FIRST
        for any academic question before trying web_search.

        Args:
            query: The search query describing what you're looking for.
            top_k: Number of results to return (default 4).
            filter_type: Optional filter: definition|process|explanation|diagram|table|advantages|disadvantages.
            filter_unit: Optional filter by unit name (e.g. "Unit-III").
        """
        return retrieve_chunks_impl(
            query=query,
            vector_store=vector_store,
            top_k=top_k,
            filter_type=filter_type,
            filter_unit=filter_unit,
        )

    tools.append(retrieve_chunks)

    # ── list_topics ──────────────────────────────────────────────────────

    @tool
    def list_topics() -> str:
        """List all topics, sections, units, and knowledge types available
        in the uploaded notes. Call this when the user asks what topics
        are covered or what's available in the knowledge base."""
        return list_topics_impl(vector_store=vector_store)

    tools.append(list_topics)

    # ── web_search (conditional) ─────────────────────────────────────────

    if enable_web_search:
        @tool
        def web_search(query: str, num_results: int = 3) -> str:
            """Search the web for information not found in the knowledge base.
            Use this when retrieve_chunks returns no useful results, or when
            the user asks for external/recent information.

            Args:
                query: A clear, descriptive search query.
                num_results: Number of web results (default 3, max 5).
            """
            return web_search_impl(
                query=query,
                exa_client=exa_client,
                num_results=num_results,
            )

        tools.append(web_search)

    # ── generate_diagram ─────────────────────────────────────────────────

    @tool
    def generate_diagram(topic: str, diagram_type: str = "flowchart") -> str:
        """Retrieve relevant chunks for a topic to generate a diagram.
        After receiving the result, generate valid Mermaid.js syntax
        wrapped in ```mermaid``` code fences based on the chunks.

        Args:
            topic: The topic to visualize.
            diagram_type: Type of diagram: flowchart|sequence|mindmap|graph.
        """
        return generate_diagram_impl(
            topic=topic,
            vector_store=vector_store,
            diagram_type=diagram_type,
        )

    tools.append(generate_diagram)

    # ── save_memory ──────────────────────────────────────────────────────

    @tool
    def save_memory(key: str, value: str) -> str:
        """Save an important user preference or fact to persistent memory.
        Call this when the user states something they want you to remember
        across sessions. Examples: preferred answer style, important dates, etc.

        Args:
            key: Short identifier (e.g. "preferred_style", "exam_date").
            value: The value to remember (e.g. "use bullet points").
        """
        return save_memory_impl(
            key=key,
            value=value,
            session_id=session_id,
        )

    tools.append(save_memory)

    return tools