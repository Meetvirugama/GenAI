# Multimodal Q&A Pro - Enterprise AI Agent

**Multimodal Q&A Pro** is an enterprise-grade AI assistant built using the LangGraph ReAct framework. It integrates document retrieval (RAG), live web search, and vision-based image analysis into a unified interface powered by a React frontend and a FastAPI backend.

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Key Features](#key-features)
3. [Technology Stack](#technology-stack)
4. [Architecture Overview](#architecture-overview)
5. [Authentication and Security](#authentication-and-security)
6. [The LangGraph Agent](#the-langgraph-agent)
7. [Retrieval-Augmented Generation (RAG)](#retrieval-augmented-generation-rag)
8. [Frontend Architecture](#frontend-architecture)
9. [Database Architecture](#database-architecture)
10. [Directory Structure](#directory-structure)
11. [Setup and Installation Guide](#setup-and-installation-guide)
12. [Future Roadmap](#future-roadmap)

---

## Executive Summary

The primary purpose of this application is to serve as a high-performance AI assistant. Traditional AI chat interfaces are limited to text and rely entirely on the data they were trained on. **Multimodal Q&A Pro** overcomes these limitations by operating autonomously. 

It decides for itself:
- When to search the internet.
- When to read your uploaded PDF documents.
- When to analyze an uploaded image.

By combining a fast backend server with a modern frontend user interface, this project provides a production-ready template for building sophisticated AI applications.

---

## Key Features

- **Intelligent Tool Selection:** The system does not guess what tool to use. It uses a Large Language Model to evaluate the user's prompt and mathematically determine the best tool to invoke.
- **Local Document Analysis:** Users can upload PDF documents. The system breaks down, embeds, and indexes these documents locally on the server.
- **Vision Integration:** The agent can see and interpret uploaded images. This integrates visual context seamlessly into the conversation.
- **Live Internet Access:** When asked about current events, the agent autonomously triggers a web search to pull real-time data from the internet.
- **Google Authentication:** The application features secure, passwordless login utilizing Google. It uses encrypted session cookies for maximum security.
- **Transparent Reasoning:** The user interface provides a dropdown menu that reveals the agent's internal thought process. Users can see exactly what raw data the agent retrieved before generating the final answer.
- **Session Privacy:** Documents and chat histories are strictly separated per user session. This ensures complete privacy and prevents data leakage.

---

## Technology Stack

### Frontend Components
- **React 18:** Used for rendering the user interface using a component-based approach.
- **Vite:** Next-generation frontend tooling used for fast development and optimized production builds.
- **TypeScript:** Used for strict type-checking to ensure application reliability and prevent runtime errors.
- **CSS Modules:** Used for scoped, clash-free styling. It ensures a premium and modern visual appearance.
- **Axios:** Used as the HTTP client for interacting with the backend API.

### Backend Components
- **FastAPI:** A high-performance web framework used for building the REST APIs.
- **LangGraph:** A framework used for orchestrating the AI agent in a cyclical loop.
- **LangChain:** Provides the core building blocks for wrapping the Large Language Models and external tools.
- **Authlib:** Handles the Google OAuth integration securely.
- **Uvicorn:** Used as the web server implementation to run the Python application.

### Artificial Intelligence and Data Components
- **Groq:** An ultra-fast inference engine that powers the Large Language Models.
- **ChromaDB:** A local vector database used for extremely fast semantic similarity searches on documents.
- **HuggingFace:** Provides the embedding models used to convert text into mathematical vectors.
- **SQLite:** A relational database used for mapping user accounts and storing authentication details.

---

## Architecture Overview

The system is decoupled into a clear Client-Server architecture. The frontend handles user interactions and rendering. The backend handles the heavy computational workloads, including embedding, LLM orchestration, and authentication.

### Request Lifecycle

1. **Authentication Phase**
   - The user clicks the Login button on the React frontend.
   - The frontend calls the backend API.
   - The backend redirects the user to the Google Consent Screen.
   - Google returns an authentication code to the backend.
   - The backend exchanges this code for a secure Access Token.
   - The backend stores the user profile in the SQLite database and sets a secure Session Cookie in the user's browser.

2. **Document Upload Phase**
   - The user uploads a PDF document.
   - The frontend sends the file to the backend API.
   - The backend chunks the text, embeds it using HuggingFace, and stores the vectors in ChromaDB.
   - The backend returns a success response to the frontend.

3. **Chat Interaction Phase**
   - The user sends a question (e.g., "Summarize the PDF").
   - The frontend sends the question to the backend chat API.
   - The backend passes the question to the LangGraph Agent.
   - The LangGraph Agent asks the Groq LLM to determine the next action.
   - The LLM decides to use the Document Search tool.
   - The Agent queries ChromaDB for similar chunks of text.
   - ChromaDB returns the relevant context.
   - The Agent passes the context back to the Groq LLM to synthesize a final answer.
   - The Agent returns the final answer and its internal reasoning trace to the backend API.
   - The backend API sends this data as a JSON payload to the frontend.
   - The React frontend renders the Markdown answer for the user to read.

---

## Authentication and Security

Security is a primary focus in this application. 

### Google Authentication Flow
Instead of managing custom passwords, the system relies on Google as the Identity Provider. 
- The frontend directs the user to the login endpoint.
- The backend constructs a secure URI and redirects the browser to Google.
- Upon user approval, Google redirects back to the backend with an authorization code.
- The backend exchanges this code for an access token via a synchronous HTTPS POST request. This bypasses common network timeout issues on macOS.
- The backend fetches the user's email and name from Google's API.

### Session Management
Once authenticated, the backend creates a user record in the SQLite database. The internal database ID is then encrypted and cryptographically signed into a cookie via Starlette Session Middleware.
- **Secret Key:** This is driven by a secure environment variable.
- **SameSite Policy:** This is configured as Lax to allow seamless navigation while protecting against Cross-Site Request Forgery attacks.

Subsequent requests from the React frontend to the backend automatically include this cookie. The backend reads this cookie and returns the user profile, allowing the frontend to render personalized interface elements.

---

## The LangGraph Agent

The core intelligence of the application is a cyclical agent built with LangGraph. Unlike traditional linear programs that run from start to finish, a LangGraph agent operates in a continuous loop.

### The Agent Loop
1. **Observe:** The agent looks at the user's input and the conversation history.
2. **Decide:** The agent asks itself if it has enough information to answer. If yes, it generates the final answer. If no, it decides which tool should be used to gather more information.
3. **Act:** The agent invokes the chosen tool to gather data.
4. **Repeat:** The agent feeds the tool's output back into the observation step and repeats the cycle.

### Configured Tools
- **Document Search Tool**: Queries the local ChromaDB vector store for semantic matches to the user's prompt.
- **Web Search Tool**: Connects to the DuckDuckGo search engine API to pull live snippets from the internet.
- **Image Description Tool**: If an image is present, this tool sends the image to Groq's specialized Vision model for detailed visual analysis.

### Context Management
To maintain state while ensuring the agent remembers the context, the system employs a combination of client-side unique identifiers and Python context variables. This ensures that even when multiple users are chatting simultaneously, their tool executions and histories remain completely isolated.

---

## Retrieval-Augmented Generation (RAG)

When a user uploads a PDF, the system performs several critical data-processing steps to make the document searchable.

1. **Extraction:** The system parses the binary PDF file into raw text.
2. **Chunking:** The system breaks the massive text into smaller, overlapping chunks. This preserves contextual boundaries like sentences and paragraphs.
3. **Embedding:** The HuggingFace model converts these text chunks into high-dimensional mathematical vectors. This captures the semantic meaning of the text, rather than just the keywords.
4. **Storage:** The vectors, along with the raw text and the session identifier metadata, are stored in a local ChromaDB instance on the hard drive.
5. **Retrieval:** When the agent invokes the document search tool, it converts the user's search query into a vector and performs a similarity search against the database. It filters strictly by the user's session identifier to ensure complete privacy.

---

## Frontend Architecture

The frontend is a completely custom React Single Page Application. 

### Interface Layout
- **Global Header:** Contains the branding and dynamic authentication controls. It updates in real-time based on the user's login status.
- **Sidebar:** Designed for future expansion. It currently features a New Chat button which resets the client-side session identifier, giving the user a blank slate.
- **Chat Arena:** The primary interface where messages are rendered dynamically. AI responses are parsed using a Markdown renderer to support bold text, lists, and code blocks.
- **Trace Accordion:** A specialized component that intercepts the internal trace output from the backend. It renders this data as an expandable dropdown, giving the user visibility into the AI's tool usage.

### Styling Approach
To ensure a premium and modern aesthetic, the frontend avoids utility-class frameworks. It relies on highly customized CSS modules. Features include:
- Glassmorphism effects such as translucent backgrounds with blur.
- Smooth CSS transitions and small animations on hover states.
- A curated dark-mode color palette optimized for reading long-form text.

---

## Database Architecture

The application strictly separates structured relational data from unstructured vector data.

### Relational Database
- **Role:** Acts as the source of truth for user identities and future chat histories.
- **Technology:** SQLite mapping user accounts and authentications via SQLAlchemy.
- **Usage:** Validates OAuth logins and maps email addresses to internal IDs.

### Vector Database
- **Role:** Acts as a high-speed vector search engine.
- **Technology:** ChromaDB storing document embeddings locally on disk.
- **Usage:** Powers the retrieval capabilities, filtering results by the user's unique session context.

---

## Directory Structure

Here is a breakdown of the project files and folders:

### Frontend Directory
- **public:** Contains static assets like favicons.
- **src/assets:** Contains images and SVG icons.
- **src/components:** Contains reusable React components.
- **src/styles:** Contains CSS modules for scoped styling.
- **src/api.ts:** Contains Axios configuration and API wrappers.
- **src/App.tsx:** Contains the main React component and routing logic.
- **src/index.css:** Contains global CSS variables and resets.
- **src/main.tsx:** Contains the React DOM entry point.
- **package.json:** Defines the Node.js dependencies.
- **vite.config.ts:** Contains the Vite bundler configuration.

### Backend Directory
- **agent:** Contains LangGraph state definitions, prompts, and graph logic.
- **api:** Contains FastAPI routers for authentication and endpoints.
- **core:** Contains system configuration, logging, database setup, and context variables.
- **docs:** Contains comprehensive markdown documentation for developers.
- **rag:** Contains vector store initialization and document chunkers.
- **tests:** Contains unit testing scripts.
- **tools:** Contains Agent tool implementations for the Web, Documents, and Vision.
- **vision:** Contains the Groq Vision API wrappers.
- **main.py:** The primary FastAPI application entry point.
- **requirements.txt:** Defines the Python dependencies.
- **.env.example:** A template for required environment variables.

---

## Setup and Installation Guide

Follow these simple steps to run the complete environment on your local machine.

### Prerequisites
- Python 3.9 or higher installed on your system.
- Node.js version 18 or higher installed on your system.
- A Groq API Key, which is free from the Groq console.
- Google OAuth Credentials, including a Client ID and Secret from the Google Cloud Console.

### Backend Setup Instructions
1. Configure your `.env` file with Groq and Gemini API keys.
2. Start the backend: `cd multimodal_qa && python main.py`
3. Start the frontend: `cd frontend && npm run dev`
4. Access the application at `http://localhost:5173`.

### Frontend Setup Instructions
1. Open a new terminal window and navigate to the frontend directory.
2. Install the Node dependencies using the package manager.
3. Start the Vite development server.

### Usage Instructions
- Open your web browser and navigate to `http://localhost:5173`.
- Click the Login button in the top right corner.
- After successful authentication, you can begin uploading PDFs, attaching images, and asking the agent complex questions.

---

## Future Roadmap

While Multimodal Q&A Pro is highly capable today, the architecture is designed to accommodate future expansions easily.

- **Persistent Chat History:** Leverage the SQLite database to save message threads permanently. This will allow users to resume conversations across different devices.
- **Streaming Responses:** Upgrade the integration to stream the response token-by-token. This will provide a more responsive and immediate user experience.
- **Advanced Document Ranking:** Introduce document reranking models to improve retrieval accuracy on massive document uploads.
- **Expanded Toolset:** Integrate specialized tools like SQL database query agents, weather APIs, or internal company wikis directly into the orchestrator.
