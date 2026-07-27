"""
core/exceptions.py
===================
Centralized custom exceptions for the Multimodal Q&A Pro application.
"""

class MultiModalError(Exception):
    """Base exception for all application-specific errors."""

class ParserError(MultiModalError):
    """Raised when document parsing fails."""

class VisionError(MultiModalError):
    """Raised when an error occurs in the vision analysis pipeline."""

class RetrievalError(MultiModalError):
    """Raised when document retrieval fails."""

class LLMError(MultiModalError):
    """Raised when the language model fails to generate a response."""
