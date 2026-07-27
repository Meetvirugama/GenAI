# Tools & Integrations

The AI Agent relies on three LangChain tools. Each tool is strongly typed using Pydantic `BaseModel` schemas (`args_schema`) to ensure the LLM provides perfectly formatted inputs. All tools are wrapped in a `@safe_call` decorator (`app/tools/base.py`) which prevents Python exceptions within the tools from crashing the entire LangGraph orchestration loop.

## 1. `search_documents`
- **Location:** `tools/document.py`
- **Purpose:** Queries the local ChromaDB (or Pinecone) vector store for semantic matches to the user's question.
- **Input Schema (`SearchDocumentsInput`):**
  - `query` (str): The search phrase.
- **Dependency Injection:** This tool is dynamically constructed via `get_search_tool(document_retriever)` in `main.py` so that it uses the active vector store instance instead of relying on a global Singleton.
- **Streaming Safe:** In async streaming mode (`astream_events`), LangGraph uses the synchronous `run` method via a thread executor which historically lost `ContextVar` context. This tool explicitly defines an `_arun` coroutine (`asearch_documents`) so LangGraph correctly propagates the `session_id_var` and `image_path_var` context variables.

## 2. `describe_image`
- **Location:** `tools/vision.py` & `vision/gemini_vision.py`
- **Purpose:** Connects to the **Google Gemini Vision API** (`gemini-2.5-flash`) to answer questions about the active image.
- **Input Schema (`DescribeImageInput`):**
  - `question` (str): The specific question about the image.
- **Context Injection:** Because the image path is not provided by the LLM, the tool extracts the `current_image_path` dynamically from the `image_path_var` ContextVar (set by the FastAPI router).
- **Processing:** The image is pre-processed (`vision/utils.py`) before being uploaded to Gemini API via the native `google-generativeai` SDK.

## 3. `search_web`
- **Location:** `tools/search.py`
- **Purpose:** Connects to the live internet via DuckDuckGo.
- **Implementation:** Wraps the `DuckDuckGoSearchRun` utility from LangChain community tools. Provides a fallback to the direct `duckduckgo_search` DDGS library if LangChain integration is broken.
- **Caching:** The tool internally caches identical search queries in-memory (`@lru_cache`) to prevent redundant external API calls during the same agent loop or subsequent identical user questions.
