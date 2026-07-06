# Generative AI Development Track (2026)

Welcome to the central repository for the **MSTC GenAI Track 2026**. This repository contains a progressive series of projects designed to take you from foundational Prompt Engineering to building multi-modal, agentic AI applications deployed to production.

## 📚 Curriculum Overview

This track is divided into weekly hands-on projects, each introducing critical Generative AI concepts using modern tools like LangChain, LangGraph, Groq, ChromaDB, and Gradio.

### [Week 1: PromptForge](./week1-promptforge)
**Topic:** Foundations of Prompt Engineering & LLM APIs
* **Concepts:** System Prompts, Persona crafting, Few-Shot Prompting, Temperature manipulation, Structured JSON Outputs.
* **Stack:** Groq API (`llama-3.3-70b-versatile`), Gradio.
* **App:** A multi-mode chatbot featuring a Coding Teacher, ESport Coach, Doctor, and JSON Code Reviewer.

### [Week 2: DocBuddy](./week2-docbuddy)
**Topic:** Retrieval-Augmented Generation (RAG)
* **Concepts:** Document Ingestion, Text Splitting, Vector Embeddings (`all-MiniLM-L6-v2`), Vector Databases (ChromaDB), Semantic Search, Source Citations.
* **Stack:** LangChain, ChromaDB, PyPDFLoader.
* **App:** A Q&A engine that answers questions strictly based on uploaded PDFs and cites the exact page numbers to prevent hallucination.

### [Week 3: AgentX](./week3-agentx)
**Topic:** Autonomous ReAct Agents & Tool Calling
* **Concepts:** The ReAct (Reason + Act) loop, Tool definitions, State manipulation, Conversation Memory, Dynamic Routing.
* **Stack:** LangGraph (`create_react_agent`), DuckDuckGo Search, Wikipedia API.
* **App:** A research agent that can decide when to browse the live web vs. when to look up encyclopedic history, displaying its reasoning trace step-by-step.

### *(Week 4: Reading/Conceptual Week)*
*(No dedicated codebase for this week. Focuses on theoretical architectures and evaluation.)*

### [Week 5: HybridSight](./week5-hybridsight)
**Topic:** Multimodal & Hybrid Agents
* **Concepts:** Vision APIs (`llama-3.2-11b-vision-preview`), combining RAG as a tool alongside Web Search and Vision, Complex Routing Rules.
* **Stack:** Groq Vision API, LangGraph, ChromaDB.
* **App:** A unified agent capable of reading PDFs, searching the internet, and analyzing uploaded images all in the same conversation thread.

### [Week 6: Portfolio & Deployment](./week6-portfolio)
**Topic:** Polish, Error Handling & Shipping
* **Concepts:** Production-ready UI, Exception Handling (`@safe_call`), Streaming Progress UI, Secret Management, Deployment to Hugging Face Spaces.
* **Stack:** Gradio (`gr.Tabs`, `gr.Progress`), Hugging Face.
* **App:** The fully polished, recruiter-ready version of HybridSight.

---

## 🚀 Getting Started

To run any of these projects locally:

1. Obtain a free API key from [Groq Console](https://console.groq.com/).
2. Navigate into the specific week's folder.
3. Install the requirements (`pip install -r requirements.txt`).
4. Set up your `.env` file with `GROQ_API_KEY`.
5. Run the app (`python app.py`).

Dive into the specific folders for detailed technical notes, architecture diagrams, and specific implementation details for that week's stack!
