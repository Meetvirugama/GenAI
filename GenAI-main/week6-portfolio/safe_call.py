import functools
import gradio as gr
# pyrefly: ignore [missing-import]
from langgraph.errors import GraphRecursionError
import groq

def safe_call(func):
    """Decorator: catches all exceptions and returns a friendly error string.
    Apply to any Gradio handler that calls an LLM or external API."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except GraphRecursionError:
            raise gr.Error("⚠️ The agent ran out of steps. Try rephrasing your question or breaking it into smaller parts.")
        except groq.RateLimitError:
            raise gr.Error("⏱️ Rate limit hit. Please wait a few seconds and try again.")
        except groq.APIConnectionError:
            raise gr.Error("🔌 Could not reach Groq. Check your internet connection.")
        except ValueError as e:
            raise gr.Error(f"⚠️ Input error: {e}")
        except Exception as e:
            raise gr.Error(f"❌ Something went wrong: {e}")
    return wrapper
