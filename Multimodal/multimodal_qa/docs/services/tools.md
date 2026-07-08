# Tools & Integrations

The AI Agent relies on three LangChain tools. Each tool is strongly typed using Pydantic `BaseModel` schemas (`args_schema`) to ensure the LLM provides perfectly formatted inputs. All tools are wrapped in a `@safe_call` decorator which prevents Python exceptions within the tools from crashing the entire LangGraph orchestration loop.

## 1. `search_documents`
- **Location:** `tools/document.py`
- **Purpose:** Queries the Pinecone/ChromaDB vector store for semantic matches to the user's question.
- **Input Schema (`SearchDocumentsInput`):**
  - `query` (str): The search phrase.
- **Dependency Injection:** This tool is dynamically constructed via `get_search_tool(document_retriever)` in `main.py` so that it uses the active vector store instance instead of relying on a global Singleton.

## 2. `describe_image`
- **Location:** `tools/vision.py` & `vision/groq_vision.py`
- **Purpose:** Connects to the Groq Llama-3.2 Vision model to answer questions about the active image.
- **Input Schema (`DescribeImageInput`):**
  - `question` (str): The specific question about the image.
- **Context Injection:** Because the image path is not provided by the LLM, the tool extracts the `current_image_path` dynamically from the `image_path_var` ContextVar (set by the Gradio UI).
- **Security:** The image is aggressively downscaled (max 800x800) and forced into an RGB JPEG format before transmission to Groq to prevent Image Bombs and Alpha-Channel transparency exploits.

## 3. `search_web`
- **Location:** `tools/search.py`
- **Purpose:** Connects to the live internet via DuckDuckGo.
- **Implementation:** Wraps the `DuckDuckGoSearchRun` utility from LangChain community tools. Provides fallback to live news if local documents are insufficient.
