"""
core/exceptions.py
===================
Centralized custom exceptions for the Multimodal Q&A Pro application.
"""

class MultiModalError(Exception):
    """Base exception for all application-specific errors."""
    pass

class ParserError(MultiModalError):
    """Raised when document parsing fails."""
    pass

class VisionError(MultiModalError):
    """Raised when an error occurs in the vision analysis pipeline."""
    pass

class RetrievalError(MultiModalError):
    """Raised when document retrieval fails."""
    pass

class LLMError(MultiModalError):
    """Raised when the language model fails to generate a response."""
    pass
