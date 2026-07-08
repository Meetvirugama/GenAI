# User Interface (React Frontend)

## Overview
The application uses a **React + Vite** frontend as the primary User Interface. This provides a fast, dynamic, and state-of-the-art Single Page Application (SPA) experience.

*Note: There is a legacy Gradio implementation located in `multimodal_qa/ui/` which was used for initial prototyping, but the primary interactions now flow through the React application.*

## Layout & Components
The interface is centered around a modern sidebar layout and a main chat arena.

### 1. Global Header
- Displays the application branding.
- Features dynamic user authentication controls (e.g. Login with Google / Logout).

### 2. Sidebar 
- Used for navigating between different chat sessions (History).
- Contains the "New Chat" functionality to clear the current active session state.

### 3. Main Chat Interface
- **Message List:** Displays user messages and AI responses, parsing Markdown syntax for rich formatting.
- **Thinking Accordion:** Provides a dropdown trace of the agent's thought process, tool invocations, and raw observations.
- **Input Area:** 
  - Text input for chatting.
  - Image attachment button for VQA (Visual Question Answering).
  - Document attachment button for RAG (Retrieval-Augmented Generation).

## State Management
The frontend manages state using standard React `useState` and `useEffect` hooks. 
- Authentication state is verified by calling the `/api/me` endpoint.
- If authenticated, the React app stores the user's profile information.
- The `session_id` is maintained client-side and sent with every chat/upload request to ensure the backend maps the requests to the correct vector store and conversation history.

## API Integration
The React app communicates with the FastAPI backend via Axios HTTP requests:
- `POST /api/chat`: Sends message, image, and session ID.
- `POST /api/upload`: Sends PDF files via FormData.
- `GET /login/google`: Initiates the OAuth flow.
- `GET /api/me`: Returns the currently authenticated user's profile.
