"""Open digital MRV research package."""

from .config import ModelConfig
from .pipeline import run_synthetic_pipeline

__all__ = ["ModelConfig", "run_synthetic_pipeline"]
__version__ = "0.1.0"
