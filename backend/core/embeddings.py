"""
EmbeddingGemma LangChain wrapper and helpers.

Provides the EmbeddingGemmaLangChain class that wraps SentenceTransformer
(google/embeddinggemma-300M) into LangChain's Embeddings interface.
Uses task-specific prompt names for asymmetric retrieval:
  - "Retrieval-document" for indexing passages
  - "Retrieval-query" for encoding user questions
"""

import os
import torch
from typing import List

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer
from huggingface_hub import login as hf_login


BATCH_SIZE = 16  # Safe default for CPU; reduce to 8 if memory-constrained


class EmbeddingGemmaLangChain(Embeddings):
    """
    LangChain-compatible wrapper around SentenceTransformer (EmbeddingGemma).
    Uses task-specific prompts for documents vs. queries, as recommended
    in the EmbeddingGemma documentation for RAG pipelines.
    """

    def __init__(self, model: SentenceTransformer, batch_size: int = BATCH_SIZE):
        self.model = model
        self.batch_size = batch_size

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Encode a list of document texts.
        Uses prompt_name="Retrieval-document" — optimized for passages/docs.
        """
        all_embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_embeddings = self.model.encode(
                batch,
                prompt_name="Retrieval-document",
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            all_embeddings.extend(batch_embeddings.tolist())
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        Encode a single query string.
        Uses prompt_name="Retrieval-query" — optimized for user questions.
        """
        embedding = self.model.encode(
            text,
            prompt_name="Retrieval-query",
            normalize_embeddings=True,
        )
        return embedding.tolist()


def build_embedding_text(obj: dict) -> str:
    """
    Build a single embedding-ready string from a knowledge object.
    Concatenates all metadata fields + content for richer semantic representation.
    """
    keywords = ", ".join(obj.get("keywords", []))
    text = f"""Unit: {obj.get('unit', '')}
Topic: {obj.get('topic', '')}
Section: {obj.get('section', '')}
Type: {obj.get('type', '')}
Keywords: {keywords}
{obj.get('content', '')}"""
    return text.strip()


def load_embedding_model() -> SentenceTransformer:
    """
    Authenticate with HuggingFace and load the EmbeddingGemma-300M model.
    This takes ~30s on first run (model download) and ~10s on subsequent runs.
    Returns the SentenceTransformer instance.
    """
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        hf_login(token=hf_token, add_to_git_credential=False)

    model_id = os.getenv("EMBEDDING_MODEL", "google/embeddinggemma-300M")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"Loading EmbeddingGemma on {device}... (this may take a minute)")
    model = SentenceTransformer(model_id).to(device)

    dim = model.get_embedding_dimension()
    print(f"EmbeddingGemma loaded -- {dim} dimensions on {device}")
    return model
