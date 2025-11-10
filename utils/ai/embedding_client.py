"""
Unified Embedding Client using LangChain OpenAIEmbeddings

Provides simplified text vectorization services with async support.
Uses LangChain's OpenAIEmbeddings for better maintainability.
"""

import os
import asyncio
from typing import List, Optional, Union

from langchain_openai import OpenAIEmbeddings

from ..core.logging import get_project_logger
from ..core.exceptions import LLMError

logger = get_project_logger(__name__)

# Global semaphore for controlling async concurrency
_semaphore: Optional[asyncio.Semaphore] = None
MAX_CONCURRENT_REQUESTS = 10


# Global singleton instance
_embedding_model: Optional[OpenAIEmbeddings] = None


def get_embedding_model() -> OpenAIEmbeddings:
    """
    Get global OpenAIEmbeddings model singleton
    
    Returns:
        OpenAIEmbeddings instance
    """
    global _embedding_model
    if _embedding_model is None:
        api_key = os.getenv("EMBEDDING_API_KEY")
        api_base = os.getenv("EMBEDDING_API_BASE")
        model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        
        if not api_key or not api_base:
            raise LLMError(
                "Missing required embedding API configuration", 
                error_code="MISSING_EMBEDDING_CONFIG"
            )
        
        _embedding_model = OpenAIEmbeddings(
            openai_api_key=api_key,
            openai_api_base=api_base,
            model=model,
            chunk_size=32,  # Process 32 texts per API call
        )
        logger.info(f"Initialized OpenAIEmbeddings with model: {model}, chunk_size: 32")
    
    return _embedding_model


def get_embedding(text: Union[str, List[str]]) -> List[float]:
    """
    Get text embedding vector (one text at a time)
    
    Args:
        text: Input text or list of texts (will be joined)
        
    Returns:
        Embedding vector
    """
    model = get_embedding_model()
    
    if isinstance(text, list):
        text = " ".join(text)
    
    if not text or text.strip() == "":
        return [0.0] * 1024  # Return zero vector
    
    try:
        result = model.embed_query(text)
        return result
    except Exception as e:
        logger.error(f"Failed to get embedding: {e}")
        return [0.0] * 1024


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Get embeddings for multiple texts in batch (uses LangChain's automatic batching)
    
    LangChain automatically splits the texts into chunks of chunk_size (32) 
    and makes multiple API calls efficiently.
    
    Args:
        texts: List of input texts
        
    Returns:
        List of embedding vectors
    """
    model = get_embedding_model()
    
    if not texts:
        return []
    
    # Filter out empty texts and track indices
    valid_texts = []
    valid_indices = []
    for idx, text in enumerate(texts):
        if isinstance(text, list):
            text = " ".join(text)
        if text and str(text).strip():
            valid_texts.append(str(text))
            valid_indices.append(idx)
    
    if not valid_texts:
        return [[0.0] * 1024] * len(texts)
    
    try:
        # LangChain automatically batches by chunk_size (32)
        embeddings = model.embed_documents(valid_texts)
        
        # Reconstruct result with zero vectors for empty texts
        result = [[0.0] * 1024] * len(texts)
        for idx, emb in zip(valid_indices, embeddings):
            result[idx] = emb
        
        return result
    except Exception as e:
        logger.error(f"Failed to get batch embeddings: {e}")
        # Fallback: return zero vectors
        return [[0.0] * 1024] * len(texts)


async def get_embeddings_batch_async(texts: List[str]) -> List[List[float]]:
    """
    Get embeddings for multiple texts in batch using async (MUCH faster with concurrency!)
    
    Uses asyncio with Semaphore to control concurrent requests (default: 10).
    LangChain's aembed_documents + concurrency = maximum throughput!
    
    Args:
        texts: List of input texts
        
    Returns:
        List of embedding vectors
    """
    global _semaphore
    
    model = get_embedding_model()
    
    if not texts:
        return []
    
    # Initialize semaphore if needed
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    # Filter out empty texts and track indices
    valid_texts = []
    valid_indices = []
    for idx, text in enumerate(texts):
        if isinstance(text, list):
            text = " ".join(text)
        if text and str(text).strip():
            valid_texts.append(str(text))
            valid_indices.append(idx)
    
    if not valid_texts:
        return [[0.0] * 1024] * len(texts)
    
    try:
        # Split into chunks and process with controlled concurrency
        chunk_size = 32  # Same as model's chunk_size
        chunks = [valid_texts[i:i+chunk_size] for i in range(0, len(valid_texts), chunk_size)]
        
        async def process_chunk(chunk: List[str]) -> List[List[float]]:
            """Process one chunk with semaphore control"""
            async with _semaphore:
                # Use LangChain's async method
                return await model.aembed_documents(chunk)
        
        # Process all chunks concurrently (up to MAX_CONCURRENT_REQUESTS at once)
        tasks = [process_chunk(chunk) for chunk in chunks]
        chunk_results = await asyncio.gather(*tasks)
        
        # Flatten results
        embeddings = []
        for chunk_result in chunk_results:
            embeddings.extend(chunk_result)
        
        # Reconstruct result with zero vectors for empty texts
        result = [[0.0] * 1024] * len(texts)
        for idx, emb in zip(valid_indices, embeddings):
            result[idx] = emb
        
        return result
    except Exception as e:
        logger.error(f"Failed to get batch embeddings (async): {e}")
        # Fallback: return zero vectors
        return [[0.0] * 1024] * len(texts)


# Legacy compatibility
def get_embedding_client():
    """
    Legacy function for backward compatibility
    Returns the embedding model
    """
    return get_embedding_model()