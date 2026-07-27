# NexusIQ — Frontend

This is the React + Vite frontend for the NexusIQ Multimodal AI platform. It provides a clean, responsive, and modern user interface for interacting with the LangGraph AI agent, uploading PDFs, and analyzing images.

## Technologies Used
- **React 18**
- **Vite** (for fast development and bundling)
- **TypeScript**
- **Axios** (for API communication)
- **Tailwind / CSS Modules** (for styling)
- **Lucide React** (for icons)

## Getting Started

### Prerequisites
- Node.js (v18+)
- Ensure the FastAPI backend is running on `http://127.0.0.1:7860` (see `../multimodal_qa/README.md`).

### Installation
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install the dependencies:
   ```bash
   npm install
   ```

### Running the Development Server
Start the Vite development server:
```bash
npm run dev
```
The application will be available at `http://localhost:5173` (or `5174` if `5173` is busy).

## Features
- **Google OAuth Login:** Authenticates users via the backend and securely stores stateless JWT tokens in localStorage.
- **Chat Interface:** Real-time multi-modal chat using Server-Sent Events (SSE) for token-by-token streaming.
- **File Uploads:** Supports uploading PDF/DOCX documents and images directly from the chat interface to a Celery background worker.
- **Agent Trace:** Displays the hidden reasoning steps (tool calls, observations) from the LangGraph agent in an expandable accordion.
- **Responsive UI:** A dynamic and modern sidebar layout that adapts to different screen sizes.

## API Integration
The frontend is configured to communicate with the backend API located at `http://localhost:7860`. The core integrations include:
- `POST /api/chat/stream`: Sends chat messages and receives real-time SSE chunks.
- `POST /api/upload`: Handles multipart form data uploads.
- `GET /api/me`: Fetches the authenticated user profile using the stored JWT (`Authorization: Bearer <token>`).
- `GET /login/google`: Redirect endpoint for initiating the OAuth flow.
