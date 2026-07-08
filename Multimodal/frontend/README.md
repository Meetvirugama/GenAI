# Multimodal Q&A Pro - Frontend

This is the React + Vite frontend for the Multimodal Q&A Pro application. It provides a clean, responsive, and modern user interface for interacting with the LangGraph AI agent, uploading PDFs, and analyzing images.

## Technologies Used
- **React 18**
- **Vite** (for fast development and bundling)
- **TypeScript**
- **Axios** (for API communication)
- **CSS Modules** (for styling)
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
The application will be available at `http://localhost:5173`.

## Features
- **Google OAuth Login:** Seamlessly authenticates users with the backend session middleware.
- **Chat Interface:** Real-time multi-modal chat with the AI agent.
- **File Uploads:** Supports uploading PDF documents and images directly from the chat interface.
- **Responsive UI:** A dynamic and modern sidebar layout that adapts to different screen sizes.

## API Integration
The frontend is configured to communicate with the backend API located at `http://localhost:7860/api`. This includes endpoints for chat (`/chat`), document uploads (`/upload`), and fetching user profiles (`/me`).
