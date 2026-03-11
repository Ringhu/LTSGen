# ts_capv2/__init__.py
"""
ts_capv2: Rule/Stats grounded time series captioning toolkit.

This package provides:
- Wrappers: load datasets and produce windowed samples
- Core: analyze windows, build validated claims, render captions
"""

__version__ = "0.1.0"

# Optional convenience exports
from .core.sample import generate_sample  # noqa: F401

__all__ = ["generate_sample", "__version__"]
