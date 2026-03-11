# tscap/wrappers/__init__.py
from .base import BaseWrapper, WrapperConfig
from .registry import get_wrapper
from .windowing import iter_windows

__all__ = [
    "BaseWrapper",
    "WrapperConfig",
    "get_wrapper",
    "iter_windows",
]
