# Week 6: Ship Your Portfolio App — Polish & Deployment

Welcome to the **Week 6** (Final) project of the GenAI Track. You've built a powerful, multi-modal Hybrid Agent in Week 5. However, a local script isn't a portfolio piece. 

This week focuses on **Software Engineering Polish**. We take the Hybrid Agent and make it robust, user-friendly, and production-ready by implementing progress bars, universal error handling, advanced UI layouts, and finally deploying it to the internet via Hugging Face Spaces.

---

## 🧠 Core Concepts & Theory (with Real-World Examples)

### 1. Robust Error Handling (`@safe_call`)
In early iterations, if an LLM API timed out or if you forgot your API key, the app would crash, spewing a terrifying raw Python stack trace into the user's UI. 
For production, we intercept these exceptions. By wrapping our Gradio event handlers in a Python Decorator (`@safe_call`), we catch all errors (like `RateLimitError` or `GraphRecursionError`) and raise them as native `gr.Error("Friendly message")`. This shows a beautiful, red toast notification to the user without crashing the server.
> **🏢 Modern Example:** Think about **Netflix**. If a movie fails to load because of a server timeout, it doesn't crash the entire Netflix app or show you a wall of Python code. It elegantly catches the error and shows a polite message: "We're having trouble playing this title right now." This is called "Graceful Degradation," and `@safe_call` implements it for your LLM app.

### 2. Streaming Progress (`gr.Progress`)
When an agent is thinking for 15 seconds, the user might think the app is frozen. We inject `gr.Progress()` into our backend functions. As the LangGraph agent loops through its tools, we emit progress updates (e.g., `progress(0.5, desc="Calling DuckDuckGo...")`). Gradio automatically renders a smooth loading bar over the UI.
> **🏢 Modern Example:** When you use a search engine like **Perplexity AI** or **Gemini**, you don't just stare at a blank screen while it searches. You see progressive updates like "Searching 5 sources..." -> "Reading articles..." -> "Synthesizing answer." This reduces user anxiety and dramatically improves perceived performance.

### 3. Advanced UI Layouts (`gr.Tabs`)
Cramming a PDF uploader, an Image uploader, a Chatbot, and a Reasoning Trace into a single column is horrible UX. We use `gr.Tabs()` to separate contexts logically:
- **Tab 1: Hybrid Chat** (Main conversational interface)
- **Tab 2: Document QA** (PDF upload and indexing status)
- **Tab 3: Image Studio** (Visual analysis sandbox)
> **🏢 Modern Example:** Look at professional AI dashboards like **Midjourney's web interface** or **Anthropic's Console**. They compartmentalize different workflows (Prompts, Model Settings, Output History) into separate tabs and modal windows rather than overwhelming the user with every option at once.

### 4. Cloud Deployment & Secret Management
Running locally is great for development, but a portfolio piece needs a public URL. Hugging Face Spaces provides free hosting for Gradio apps. The critical engineering concept here is **Secret Management**. You *never* commit your `.env` file or API keys to a public GitHub repository. Instead, you inject them securely into the cloud provider's environment via "Repository Secrets".
> **🏢 Modern Example:** Every major tech company uses secret managers (like AWS Secrets Manager, HashiCorp Vault, or GitHub Secrets). If an engineer accidentally commits a database password to a public repository, bots can scrape it in milliseconds and compromise the company's entire infrastructure. 

---

## 🛠️ Key Code & Functions

### The Error Handling Decorator
A decorator allows you to wrap functions cleanly without writing `try/except` a hundred times.
```python
import functools
import gradio as gr
import groq

def safe_call(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except groq.RateLimitError:
            raise gr.Error("⏱️ Rate limit hit. Please wait a few seconds.")
        except Exception as e:
            raise gr.Error(f"❌ Something went wrong: {e}")
    return wrapper

# Applied cleanly to our UI handlers:
@safe_call
def handle_chat(message, history, session_id):
    # ...
```

### Emitting Progress
```python
def index_pdf(filepath: str, progress=gr.Progress()) -> int:
    progress(0.1, desc="Loading PDF...")
    loader = PyPDFLoader(filepath)
    # ...
    progress(0.9, desc="Writing to ChromaDB...")
```

---

## 🚀 Setup & Deployment

### Local Testing
1. Navigate to the directory:
   ```bash
   cd week6-portfolio
   ```
2. Activate your virtual environment and install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your API key in `.env` and run:
   ```bash
   python app.py
   ```

### Deploying to Hugging Face Spaces
1. Create a free account at [huggingface.co](https://huggingface.co/).
2. Click **New Space**, select **Gradio** as the Space SDK.
3. Once the Space is created, go to **Settings > Variables and secrets**. Add a New Secret:
   - Name: `GROQ_API_KEY`
   - Value: `your_actual_api_key_here`
4. Push the contents of the `week6-portfolio` directory directly to the Space's Git repository (do **not** push `.env` or `chroma_store/`).
5. Wait for the build process to finish. Your app is now live and shareable on your resume!

---

## 🎯 Learning Outcomes
By completing this final week, you should understand:
1. How to use Python decorators to build robust, application-wide error handling.
2. How to improve UX during long-running LLM inferences using Progress streams.
3. How to design clean, multi-tabbed web applications using Gradio.
4. How to securely deploy GenAI applications to the cloud using environment variables and secrets management.
