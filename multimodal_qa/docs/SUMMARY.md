# Executive Summary

## Overview
**Multimodal Q&A Pro** is an elite, hybrid AI agent built to intelligently process and answer questions across multiple modalities: local documents (PDFs), images (Vision), and the live internet (Web Search). 

## Purpose
The primary purpose of this application is to serve as a high-performance, enterprise-grade AI assistant capable of performing **Retrieval-Augmented Generation (RAG)** on uploaded PDFs, executing **Visual Question Answering (VQA)** on uploaded images, and conducting real-time internet research, all orchestrated by a single autonomous agent.

## Business Requirements
- **Intelligent Routing:** The system must automatically determine the best tool (or combination of tools) to answer a user's question.
- **Multimodal Support:** The system must support text, PDF, and image inputs.
- **Production Readiness:** The system must handle concurrent users, robust sessions via Google OAuth, and secure SQLite profile storage.

## Functional Requirements
- **Authentication:** Users must securely log in via Google OAuth.
- **PDF Upload:** Users can upload PDFs which are immediately embedded into the vector store.
- **Image Upload:** Users can upload a single image for analysis directly in the chat interface.
- **Hybrid Chat:** A conversational interface built in React that maintains a conversational history.
- **Reasoning Trace:** The system must transparently display the agent's internal "thought process" and tool observations via the UI.

## Architecture Highlights
- **Backend:** FastAPI (Python)
- **Frontend:** React + Vite + TypeScript (Modern UI)
- **Framework:** LangGraph (Stateful Agent orchestration)
- **LLM:** Groq (Llama-3-70b-versatile with fallback support)
- **Vision:** Groq (Llama-3.2-11b-vision-preview)
- **Vector Database:** ChromaDB (Local embeddings)
- **SQL Database:** SQLite (User accounts & Session mapping)
- **Embeddings:** HuggingFace (`all-MiniLM-L6-v2`)

## Related Documents
- [System Overview](architecture/overview.md)
- [Installation Guide](setup/installation.md)
