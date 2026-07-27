# Week 5: HybridSight — Multimodal Agents

Welcome to the **Week 5** project of the GenAI Track. After exploring Prompt Engineering, RAG, and Agents, we now bring all these domains together into a single, unified architecture: **The Hybrid Agent**. 

In this week, we introduce a new modality: **Vision**. Our agent will no longer be limited to text inputs; it will be able to analyze and understand uploaded images alongside searching the web and reading PDFs.

---

## 🧠 Core Concepts & Theory (with Real-World Examples)

### 1. Vision APIs & Multimodality
Modern APIs (like `llama-3.2-11b-vision-preview`) process both text and images in the same request. Instead of passing a single string as the `content` of a user message, we pass a list of dictionaries containing text parts and image parts (encoded in base64).
> **🏢 Modern Example:** When you use **ChatGPT Plus** to take a picture of the inside of your fridge and ask "What can I cook with this?", you are using Multimodality. The model processes the visual pixels and the text query simultaneously to generate a recipe.

### 2. RAG as a Tool
In Week 2, RAG was the entire application. In Week 5, RAG is reduced to just a single tool in the agent's toolbox. 
We take our ChromaDB retreiver and wrap it in a `@tool` decorator (`search_documents`). This allows the LangGraph agent to dynamically decide when to read your PDFs (e.g., when you say "according to the notes") and when to ignore them in favor of web search.
> **🏢 Modern Example:** In a corporate setting, an employee might ask an HR bot: "What is the holiday schedule, and what is the current weather in the London office?" The bot uses its RAG tool to read the internal HR PDF for the holiday schedule, and then uses a live Weather API tool for the London weather, combining both into one response.

### 3. Vision as a Tool
Instead of forcing the Vision model to run every time, we wrap the image analysis call in a `@tool` (`describe_image`). When a user uploads an image, the Gradio frontend encodes it in base64 and attaches the URI to the prompt. The router agent sees this, triggers the `describe_image` tool, reads the visual description returned by the tool, and synthesizes it with its other knowledge.
> **🏢 Modern Example:** Modern **AI Medical Assistants** use Vision as a tool. A doctor uploads an X-Ray. The agent uses a Vision tool to analyze the scan, then uses a RAG tool to cross-reference the patient's past medical history in their electronic health record (EHR) database, delivering a comprehensive diagnostic suggestion.

### 4. Advanced Agent Routing
As the number of tools grows, the agent requires much stricter supervision. The System Prompt becomes a detailed routing manifest:
```text
ROUTING RULES — follow these in order:
1. If the user asks about uploaded documents, use search_documents.
2. If the user uploads an image, use describe_image FIRST.
3. If the user asks about current events, use DuckDuckGo.
4. If the user asks general knowledge, use Wikipedia.
```
Without these explicit instructions, the agent might hallucinate which tool to use.
> **🏢 Modern Example:** Virtual assistants like **Apple Intelligence (Siri)** or **Google Gemini** have hundreds of tools. They rely on incredibly complex, heavily engineered routing rules to ensure that asking to "Play Taylor Swift" triggers the Apple Music tool, but asking "Who is Taylor Swift?" triggers the Wikipedia/Web Search tool.

---

## 🛠️ Key Code & Functions

### Base64 Encoding Images
Vision APIs require images to be passed as data URIs.
```python
import base64

def image_to_data_uri(filepath: str) -> str:
    with open(filepath, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"
```

### Vision API Request Structure
Notice how `content` is a list, not a string.
```python
response = client.chat.completions.create(
    model="llama-3.2-11b-vision-preview",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe this image."},
            {"type": "image_url", "image_url": {"url": data_uri}},
        ],
    }],
)
```

### Increasing Recursion Limits
Because a query might require looking at an image, taking that description, and then searching the web for it, the agent takes more steps. We must increase LangGraph's recursion limit to prevent crashes during deep reasoning:
```python
DEFAULT_CONFIG_EXTRA = {"recursion_limit": 12}
```

---

## 🚀 Setup & Execution

### Prerequisites
- Python 3.10+
- Groq API Key

### Installation
1. Navigate to the directory:
   ```bash
   cd week5-hybridsight
   ```
2. Activate your virtual environment:
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your environment variables:
   ```bash
   cp .env.example .env
   # Add your GROQ_API_KEY
   ```

### Running the App
```bash
python app.py
```
Open `http://127.0.0.1:7860`.
Try the following test cases to watch the router agent at work:
1. Ask "Who won the superbowl this year?" -> Watch it use DuckDuckGo.
2. Upload a PDF and ask a question about it -> Watch it use `search_documents`.
3. Upload an image and ask "What is in this picture?" -> Watch it use `describe_image`.

---

## 🎯 Learning Outcomes
By completing this week, you should understand:
1. How to format and send requests to Multimodal Vision LLMs.
2. How to wrap complex pipelines (like RAG and Vision APIs) into atomic Agent tools.
3. How to engineer a robust system prompt to manage multi-tool routing logic.
4. How a single unified agent architecture can handle vast, multi-modal workflows seamlessly.
