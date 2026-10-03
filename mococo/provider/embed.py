"""Text embeddings for retrieval. One multilingual model, cached after first load."""

from __future__ import annotations

from threading import Lock

import numpy as np

from mococo import config

MODEL_NAME = "BAAI/bge-m3"
_model = None
_model_lock = Lock()


def _get():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(MODEL_NAME, device="cpu", cache_folder=str(config.models_dir()))
    return _model


def embed(texts: list[str], batch_size: int = 32) -> np.ndarray:
    """Unit-normalised float32 vectors, one row per text."""
    if not texts:
        return np.zeros((0, 1024), dtype=np.float32)
    vecs = _get().encode(
        texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=len(texts) > 64
    )
    return np.asarray(vecs, dtype=np.float32)
