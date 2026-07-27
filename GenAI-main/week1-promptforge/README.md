# Week 1: PromptForge — Multi-Mode AI Assistant

Welcome to the **Week 1** project of the GenAI Track. This project focuses entirely on the foundational layer of Generative AI: **Prompt Engineering** and direct **LLM API integration**. 

In this week, we don't use heavy frameworks like LangChain or LangGraph. Instead, we use the raw Groq API to understand exactly how messages are sent, formatted, and parsed by a Large Language Model.

---

## 🧠 Core Concepts & Theory (with Real-World Examples)

### 1. The Chat Completion API
Modern LLMs operate on a conversation history structure rather than a single string of text. A prompt is usually constructed as a list of dictionaries with specific `role`s:
- **`system`**: Sets the behavior, persona, and strict constraints. The AI treats this as its absolute truth.
- **`user`**: The actual query or input from the human.
- **`assistant`**: The AI's previous responses (used for conversational memory).

> **🏢 Modern Example:** When you use **ChatGPT's "Custom Instructions"**, you are silently modifying the `system` role behind the scenes. In the enterprise world, companies like **Shopify** use strict system prompts to create customer service bots that are legally bound to only talk about return policies and are explicitly forbidden from offering unauthorized discounts.

### 2. Prompt Engineering Techniques Used
* **Persona Adoption**: By deeply defining a persona in the system prompt (e.g., "You are an elite ESport Coach for Valorant"), the LLM changes its vocabulary, tone, and the structure of its advice.
* **Few-Shot Prompting**: Sometimes telling an LLM what to do isn't enough; you have to *show* it. Few-shot prompting involves injecting dummy `user`/`assistant` message pairs into the history *before* the actual user query. This forces the LLM to recognize and mimic a specific output format.
  > **🏢 Modern Example:** Imagine building an **automated accounting tool**. You use few-shot prompting to show the AI five examples of messy, unstructured vendor emails and the exact clean JSON format you expect back (extracting Invoice Number, Date, and Total Amount).
* **Temperature**: A parameter controlling randomness. A temperature of `0.0` makes the model deterministic and analytical (perfect for the Code Reviewer mode), while `0.7` allows for more creativity and conversational flow (good for the Teacher mode).

### 3. Structured Outputs (JSON Mode)
When building applications, you often don't want raw text; you want data you can parse (like a dictionary). By instructing the LLM to output pure JSON and setting the `response_format` API flag to `{"type": "json_object"}`, we ensure the model's output can be directly deserialized by Python's `json.loads()` and rendered into a beautiful UI.
> **🏢 Modern Example:** Apps like **Duolingo** or **Quizlet** might use an LLM in JSON mode in the background. The user asks for a quiz on French verbs, and the LLM returns `{"question": "...", "options": [...], "answer": "..."}` so the app can render interactive buttons, rather than just printing raw text to the screen.

### 4. Streaming Response
Waiting 10 seconds for a large response ruins UX. Using `stream=True` in the API call allows the server to yield chunks (tokens) as they are generated, giving the user a real-time typing effect.
> **🏢 Modern Example:** This is the exact typing effect you see when using **Claude**, **ChatGPT**, or **Gemini**. Without streaming, the page would just freeze with a loading spinner until the entire paragraph was finished computing.

---

## 🛠️ Key Code & Functions

### `client.chat.completions.create(...)`
This is the workhorse function from the `groq` library.
```python
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain gravity."}
    ],
    temperature=0.7,
    stream=True
)
```

### Yielding Tokens for UI
To achieve the streaming effect in Gradio, the backend function must be a generator:
```python
partial_message = ""
for chunk in response:
    if chunk.choices[0].delta.content is not None:
        partial_message += chunk.choices[0].delta.content
        yield partial_message # Gradio immediately updates the UI with each yield
```

---

## 🚀 Setup & Execution

### Prerequisites
- Python 3.10+
- Groq API Key (from [console.groq.com](https://console.groq.com/))

### Installation
1. Navigate to the directory:
   ```bash
   cd week1-promptforge
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your environment variables:
   ```bash
   cp .env.example .env
   # Open .env and add your GROQ_API_KEY
   ```

### Running the App
```bash
python app.py
```
Open `http://127.0.0.1:7860` in your browser. Try switching between the different modes (Coding Teacher, ESport Coach, Doctor, Code Reviewer) to see how the system prompt drastically alters the LLM's behavior!

---

## 🎯 Learning Outcomes
By completing this week, you should understand:
1. How to structure `messages` for a Chat API.
2. How to write a robust system prompt to constrain AI behavior.
3. How to stream tokens to a frontend for better UX.
4. How to force an LLM to generate parseable JSON for application logic.
