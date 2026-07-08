# Multimodal Q&A Pro

A hybrid AI Agent powered by LangGraph, Groq, ChromaDB, and Gradio. This agent can intelligently route queries between PDF document search, live web search, and image analysis.

## Features
- **Local RAG:** Upload PDFs and semantic search using ChromaDB and HuggingFace embeddings.
- **Vision Studio:** Upload images and analyze them using Groq Vision (`llama-3.2-11b-vision-preview`).
- **Web Search:** Fetch live internet data via DuckDuckGo.
- **Agentic Routing:** Automatically decides which tools to use for any given query.
- **Multi-user Ready:** Built with session isolation and context variables for thread safety.

## Setup
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add your Groq API Key.
4. Run the app: `python main.py`

## HuggingFace Spaces Deployment
This project is ready to be deployed to HuggingFace Spaces as a Gradio app. 
Make sure to add your `GROQ_API_KEY` to the Space Secrets.
