# Executive Summary

## Overview
**Multimodal Q&A Pro** is an elite, hybrid AI agent built to intelligently process and answer questions across multiple modalities: local documents (PDFs), images (Vision), and the live internet (Web Search). 

## Purpose
The primary purpose of this application is to serve as a high-performance, enterprise-grade AI assistant capable of performing **Retrieval-Augmented Generation (RAG)** on uploaded PDFs, executing **Visual Question Answering (VQA)** on uploaded images, and conducting real-time internet research, all orchestrated by a single autonomous agent.

## Business Requirements
- **Intelligent Routing:** The system must automatically determine the best tool (or combination of tools) to answer a user's question.
- **Multimodal Support:** The system must support text, PDF, and image inputs.
- **Production Readiness:** The system must handle concurrent users, large file uploads, rate limits, and malicious prompt injections.

## Functional Requirements
- **PDF Upload:** Users can upload up to 15MB of PDF documents per session.
- **Image Upload:** Users can upload a single image for analysis.
- **Hybrid Chat:** A conversational interface that maintains a sliding-window memory of the last 10 interactions.
- **Reasoning Trace:** The system must transparently display the agent's internal "thought process" and tool observations.

## Architecture Highlights
- **Framework:** LangGraph (Stateful Agent orchestration)
- **UI:** Gradio (Web Interface)
- **LLM:** Groq (Llama-3-70b-versatile with Llama-3-8b-8192 fallbacks)
- **Vision:** Groq (Llama-3.2-11b-vision-preview)
- **Vector Database:** Pinecone (Cloud) with ChromaDB (Local Fallback)
- **Embeddings:** HuggingFace (`all-MiniLM-L6-v2`)

## Related Documents
- [System Overview](architecture/overview.md)
- [Installation Guide](setup/installation.md)
