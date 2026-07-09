# Authentication & Session Management

## Overview
The Multimodal Q&A Pro application implements secure user authentication via **Google OAuth 2.0**. This allows users to seamlessly log into the application using their Google accounts without the need to manage custom passwords.

## OAuth Flow
1. **Initiation:** The user clicks "Login with Google" on the React frontend.
2. **Redirect:** The frontend redirects the user to the FastAPI backend endpoint `GET /login/google`.
3. **Google Prompt:** The backend redirects the user to Google's OAuth consent screen.
4. **Callback:** After successful authentication, Google redirects back to `GET /auth` with an authorization `code`.
5. **Token Exchange:** The backend exchanges the `code` for an access token via a synchronous HTTPS POST request to `https://oauth2.googleapis.com/token`.
6. **User Profile Retrieval:** Using the access token, the backend fetches the user's profile information (Email, Name).
7. **Database Sync:** The user is either created or retrieved from the SQLite database.
8. **Session Establishment:** The user's internal Database ID and Email are saved into an encrypted Starlette Session Cookie.
9. **Final Redirect:** The backend redirects the browser back to the React frontend `http://localhost:5173/`.

## Session Middleware
Session state is maintained across requests via `Starlette SessionMiddleware`.
- **Secret Key:** Driven by the `SECRET_KEY` environment variable.
- **Cookies:** State is stored in a secure, signed cookie (`lax` same-site policy) sent automatically by the browser on subsequent requests to the `/api` endpoints.

## API Endpoint Protection
Currently, core endpoints verify the active session:
- `GET /api/me`: Returns 401 Unauthorized if no valid session cookie exists. Otherwise, it returns the user's details for frontend rendering.
- *Note:* In future iterations, `/api/chat` and `/api/upload` can be strictly protected to ensure only authenticated users can access the Agent.
