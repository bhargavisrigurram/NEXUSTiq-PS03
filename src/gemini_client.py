"""Gemini API client interface for grounded inference and embeddings.

Uses current official google-genai SDK (google-genai).
Adheres strictly to security rules: never logs, prints, or exposes the API key.
Provides rock-solid fallback to deterministic answers if offline or API key is absent.
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from src.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    EMBEDDING_MODEL,
    is_gemini_configured
)
from src.prompts import SYSTEM_PROMPT, build_grounded_prompt

logger = logging.getLogger(__name__)

class GeminiClient:
    """Interface for Gemini text generation and embeddings."""

    def __init__(self):
        self._client = None
        self._available = False
        self._init_client()

    def _init_client(self):
        """Initializes the google-genai client if API key is present."""
        if not is_gemini_configured():
            logger.info("GEMINI_API_KEY not configured. Operating in deterministic offline mode.")
            self._available = False
            return

        try:
            from google import genai
            # Initialize client strictly passing the key from environment
            self._client = genai.Client(api_key=GEMINI_API_KEY)
            self._available = True
            logger.info(f"Gemini client initialized with model={GEMINI_MODEL}, embedding={EMBEDDING_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {type(e).__name__}: {str(e)}")
            self._client = None
            self._available = False

    @property
    def is_available(self) -> bool:
        """Returns True if the Gemini client is initialized and ready."""
        return self._available and (self._client is not None)

    def embed_text(self, text: str) -> Optional[np.ndarray]:
        """Generates embedding for a single string using gemini-embedding-001."""
        if not self.is_available:
            return None

        try:
            response = self._client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text
            )
            # Check embedding output structure
            embeddings_list = getattr(response, "embeddings", None)
            if embeddings_list and len(embeddings_list) > 0:
                values = embeddings_list[0].values
                return np.array(values, dtype=np.float32)
            single_embedding = getattr(response, "embedding", None)
            if single_embedding and hasattr(single_embedding, "values"):
                return np.array(single_embedding.values, dtype=np.float32)
            return None
        except Exception as e:
            logger.warning(f"Gemini embedding call failed: {type(e).__name__}: {str(e)}")
            return None

    def embed_batch(self, texts: List[str]) -> Optional[List[np.ndarray]]:
        """Generates embeddings for a batch of strings."""
        if not self.is_available or not texts:
            return None

        try:
            # Batch call or sequential call with rate-limit safety
            results = []
            for t in texts:
                vec = self.embed_text(t)
                if vec is not None:
                    results.append(vec)
                else:
                    return None
            return results
        except Exception as e:
            logger.warning(f"Batch embedding failed: {type(e).__name__}: {str(e)}")
            return None

    def generate_grounded_response(self, question: str, evidence_text: str, context_notes: str = "") -> Dict[str, Any]:
        """Generates a grounded natural language response using Gemini 3.5 Flash Lite.
        
        Falls back to deterministic template generation if Gemini is unreachable or unconfigured.
        """
        if not self.is_available:
            return self._generate_deterministic_fallback(question, evidence_text)

        prompt = build_grounded_prompt(question, evidence_text, context_notes)

        # Attempt primary model first; fallback to gemini-2.5-flash if needed
        models_to_try = [GEMINI_MODEL, "gemini-2.5-flash", "gemini-3.7-flash"]
        # Deduplicate while preserving order
        models_to_try = list(dict.fromkeys(models_to_try))

        last_error = None
        for model_id in models_to_try:
            try:
                response = self._client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config={
                        "system_instruction": SYSTEM_PROMPT,
                        "temperature": 0.1,  # Ultra-low temperature for maximum numerical fidelity
                    }
                )
                if response and response.text:
                    return {
                        "text": response.text.strip(),
                        "model": model_id,
                        "grounded": True,
                        "source": "gemini"
                    }
            except Exception as e:
                last_error = e
                logger.warning(f"Model {model_id} failed: {type(e).__name__}: {str(e)}. Trying next fallback...")

        logger.error(f"All Gemini generation attempts failed. Reason: {last_error}")
        return self._generate_deterministic_fallback(question, evidence_text, reason=str(last_error))

    def _generate_deterministic_fallback(self, question: str, evidence_text: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Provides a clean, transparent deterministic response when Gemini is offline."""
        if not evidence_text.strip():
            answer = "No matching records or evidence was found in the dataset for this question."
        else:
            answer = (
                f"**Retail Copilot (Deterministic Analysis)**\n\n"
                f"Based on the verified retail records in the store dataset:\n\n"
                f"{evidence_text}\n\n"
                f"*Note: Numerical figures above are computed directly by the deterministic analytics engine.*"
            )

        return {
            "text": answer,
            "model": "deterministic_engine",
            "grounded": True,
            "source": "deterministic_fallback",
            "offline_reason": reason or "API key not configured"
        }
