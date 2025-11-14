"""Embedding service using sentence-transformers (bge-m3)"""
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import logging
import torch

from src.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings"""

    def __init__(self):
        """Initialize the embedding model"""
        self.model_name = settings.EMBEDDING_MODEL
        self.device = settings.EMBEDDING_DEVICE
        self.batch_size = settings.EMBEDDING_BATCH_SIZE
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the embedding model"""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device
            )
            logger.info(f"Model loaded on device: {self.device}")
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text

        Args:
            text: Input text string

        Returns:
            Embedding vector as list of floats
        """
        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts

        Args:
            texts: List of input text strings

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        logger.info(f"Embedding batch of {len(texts)} texts")

        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=True if len(texts) > 100 else False,
            convert_to_numpy=True
        )

        return embeddings.tolist()

    def embed_chunks(self, chunks: List[str]) -> List[List[float]]:
        """
        Generate embeddings for document chunks

        This is an alias for embed_batch optimized for chunked documents.

        Args:
            chunks: List of text chunks

        Returns:
            List of embedding vectors
        """
        return self.embed_batch(chunks)

    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score between -1 and 1
        """
        embeddings = self.embed_batch([text1, text2])
        emb1 = np.array(embeddings[0])
        emb2 = np.array(embeddings[1])

        # Cosine similarity (normalized vectors)
        similarity = float(np.dot(emb1, emb2))
        return similarity

    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "dimension": settings.EMBEDDING_DIMENSION,
            "batch_size": self.batch_size,
            "is_loaded": self._model is not None
        }


# Global instance (lazy loaded)
embedding_service = EmbeddingService()
