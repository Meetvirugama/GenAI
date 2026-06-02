# PromptForge — Multi-Mode AI Assistant

Welcome to **PromptForge**, the mini-project for **Week 1 of the MSTC GenAI Track 2026**. 

PromptForge is a responsive, elegantly styled Gradio web application that lets you interact with a Large Language Model (specifically `llama-3.3-70b-versatile` via the Groq API) across four distinct, pre-configured personas. 

It highlights essential prompt engineering concepts including:
- **System Prompt Customization:** Fine-tuning the LLM's role, rules, and constraints.
- **Few-Shot Prompt Injection:** Injecting prompt-response examples to guarantee formatting.
- **Temperature Control:** Changing response randomness.
- **Structured JSON Parsing:** Generating pure JSON outputs and styling them in clean Markdown.
- **Streaming Response Processing:** Real-time token delivery to the client interface.

---

## 🎨 Persona Modes

1. **Coding Teacher:** Friendly and interactive programming instructor who explains concepts with clean code blocks, provides customized learning roadmaps, and challenges you with practical coding quiz questions.
2. **ESport Coach:** Elite esports consultant analyzing tactical compositions, physical mechanics, mental composure, and fight execution for competitive titles like Valorant, League of Legends, BGMI, and Free Fire.
3. **Doctor:** Empathetic virtual health consultant providing scientific symptom reviews and follow-up discussion points for your doctor (always prefaced with a clear medical disclaimer).
4. **Code Reviewer:** Evaluates code snippets. Prompted to return structured JSON (Issues, Suggestions, Severity), which the frontend parses and styles as a readable report.

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.10 or higher
- A Groq API Key (obtain one for free at [console.groq.com](https://console.groq.com/))

### 1. Clone & Navigate
Ensure you are in the `week1-promptforge` directory:
```bash
cd week1-promptforge
```

### 2. Configure Virtual Environment
Create and activate a sandbox Python environment:
```bash
# On macOS/Linux:
python -m venv venv
source venv/bin/activate

# On Windows:
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
Install all required packages from `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Setup API Keys
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Open `.env` in your editor and replace the value with your actual Groq API key:
```env
GROQ_API_KEY=gsk_abc123...
```

---

## 🖥️ Running the Application

To start the server, run:
```bash
python app.py
```

The application will spin up a local server. Open your browser and navigate to:
```
http://127.0.0.1:7860
```

---

## 🧪 How to Test Modes

- **Coding Teacher:** Choose the mode, type `Explain lists in Python` or `How do async functions work?`. Observe the clear explanation, step-by-step roadmap, and coding challenge at the end.
- **ESport Coach:** Ask `How do I improve my rotation and fight execution in BGMI?` or `What is the meta strategy for Valorant?`. Observe the structured guide covering mechanics, tactics, and mental composure.
- **Doctor:** Ask `What causes mild fatigue and head pressure?`. Verify that the AI displays a bold medical disclaimer first, followed by clinical factors and talking points for your doctor.
- **Code Reviewer:** Paste a bugged or unoptimized block of code:
  ```python
  def calculate(x, y):
      return x/y
  ```
  Watch the raw JSON generation stream, then watch it transform into a polished review table outlining the severity, issues (e.g., division by zero, missing types), and recommendations.
- **System Prompt Inspector:** Toggle the **📜 Active System Prompt** accordion at the bottom of the sidebar to inspect the exact prompt structure sent to the LLM.
