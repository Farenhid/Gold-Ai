"""
Adapter Layer for Accounting System Integration

This package provides an abstract interface for connecting to various
accounting systems using the Adapter design pattern.
"""

from .base import AccountingAdapter
from .mock_adapter import MockAccountingAdapter

__all__ = ["AccountingAdapter", "MockAccountingAdapter"]
