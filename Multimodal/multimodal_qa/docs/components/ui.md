# User Interface (Gradio Components)

## Overview
The application uses **Gradio** (`gr.Blocks`) to render the web interface. Gradio allows for rapid development of machine learning web applications directly in Python. 

Because Gradio handles its own WebSockets, routing, and React components under the hood, there is no traditional "Frontend" (HTML/JS) or "Backend" (Flask/FastAPI) code in this repository.

## Layout & Tabs
The interface is split into three main tabs located in `ui/app.py`:

### 1. Hybrid Chat (`#chat`)
- **Purpose:** The primary interface for interacting with the LangGraph Agent.
- **Components:** 
  - `gr.Chatbot`: Displays the conversational history.
  - `gr.Textbox`: The input field for user queries.
  - `gr.Markdown` (Trace Output): A dropdown accordion that displays the agent's internal thought process and tool usage (`trace_output`).
- **Handlers:** `chat()`, `clear_chat()`

### 2. Document Q&A (`#docs`)
- **Purpose:** Allows users to upload and index PDF files.
- **Components:**
  - `gr.File`: Configured with `file_types=[".pdf"]` and `file_count="multiple"`.
  - `gr.Button` (Index Documents): Triggers the background embedding process.
  - `gr.Button` (Clear All Docs): Clears the vector store for the session.
- **Handlers:** `handle_pdf_upload()`, `clear_docs()`, `doc_chat()`

### 3. Image Studio (`#vision`)
- **Purpose:** Allows users to upload a single image for VQA (Visual Question Answering).
- **Components:**
  - `gr.Image`: Renders the uploaded image.
  - `gr.Button` (Load Image): Caches the image path into session state.
- **Handlers:** `handle_image_upload()`, `img_chat()`

## State Management
Gradio does not use traditional HTTP sessions. State is managed per-user using two mechanisms:
1. **`gr.State`:** Used to store the `session_id` (a UUID generated on page load) and `image_path_state`. These are passed back and forth between the UI and backend handlers.
2. **`contextvars`:** `session_id_var` and `image_path_var` (defined in `core/context.py`) are used to implicitly pass state down to deeply nested Langchain tools (like `describe_image`) without having to manually pipe the arguments through every function signature.

## Rate Limiting & Memory
- **Memory Pruning:** The `chat()` handler implements a sliding window, keeping only the last 10 messages (`history[-10:]`) before passing them to the agent. This prevents context-window exhaustion.
- **Rate Limiting:** An in-memory dictionary (`request_timestamps`) tracks the last request time per `session_id`, enforcing a 3-second cooldown to prevent API abuse.
