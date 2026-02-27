from typing import List, Tuple, Optional
from phi.embedder.base import Embedder
from phi.utils.log import logger

from llm_client import get_llm_client, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS


class SAPAICoreEmbedder(Embedder):
    """
    Custom embedder that uses SAP AI Core for embeddings.
    """
    
    model: str = EMBEDDING_MODEL
    dimensions: int = EMBEDDING_DIMENSIONS
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text."""
        client = get_llm_client()
        try:
            response = client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            error_msg = str(e)
            if "No deployment found" in error_msg:
                raise RuntimeError(
                    f"Embedding model '{self.model}' is not deployed in SAP AI Core. "
                    f"Please deploy it or set EMBEDDING_MODEL env var to an available model. "
                    f"Original error: {e}"
                )
            logger.error(f"Error getting embedding: {e}")
            raise RuntimeError(f"Failed to get embedding: {e}")
    
    def get_embedding_and_usage(self, text: str) -> Tuple[List[float], Optional[dict]]:
        """Get embedding and usage info for a single text."""
        client = get_llm_client()
        try:
            response = client.embeddings.create(
                model=self.model,
                input=text
            )
            embedding = response.data[0].embedding
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "total_tokens": response.usage.total_tokens
            }
            return embedding, usage
        except Exception as e:
            error_msg = str(e)
            if "No deployment found" in error_msg:
                raise RuntimeError(
                    f"Embedding model '{self.model}' is not deployed in SAP AI Core. "
                    f"Please deploy it or set EMBEDDING_MODEL env var to an available model. "
                    f"Original error: {e}"
                )
            logger.error(f"Error getting embedding: {e}")
            raise RuntimeError(f"Failed to get embedding: {e}")