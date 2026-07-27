# Authentication & Session Management

## Overview

NexusIQ uses **Google OAuth 2.0** for user authentication and **stateless JWT tokens** for session management. After login, the browser stores the JWT and sends it as a `Bearer` token with every API request.

## OAuth + JWT Flow

```mermaid
sequenceDiagram
    participant Browser
    participant Frontend
    participant FastAPI
    participant Google

    Frontend->>Browser: redirect to /login/google
    Browser->>FastAPI: GET /login/google
    FastAPI->>FastAPI: Check GOOGLE_CLIENT_ID is set
    FastAPI->>Google: authorize_redirect(request, redirect_uri)
    Browser->>Google: Google consent screen
    Google->>FastAPI: GET /auth?code=4%2F0AX...&state=...
    FastAPI->>Google: POST https://oauth2.googleapis.com/token (code exchange)
    Note right of FastAPI: redirect_uri = str(request.url_for('auth'))\n(must exactly match the URI sent in step 3)
    Google-->>FastAPI: { access_token: "..." }
    FastAPI->>Google: GET /oauth2/v2/userinfo (Bearer access_token)
    Google-->>FastAPI: { email, name }
    FastAPI->>FastAPI: Upsert User in SQLite database
    FastAPI->>FastAPI: jwt.encode({ sub: user_id, email, exp: +7 days })
    FastAPI-->>Browser: 302 Redirect → FRONTEND_URL/?token=<jwt>
    Browser->>Frontend: Frontend stores token in localStorage
    Frontend->>FastAPI: GET /api/me (Authorization: Bearer <jwt>)
    FastAPI->>FastAPI: jwt.decode(token, JWT_SECRET_KEY)
    FastAPI-->>Frontend: { id, name, email }
```

## Endpoint Reference

### `GET /login/google`
Initiates the OAuth flow. Redirects the browser to Google's consent screen.

Returns `500 HTML` if `GOOGLE_CLIENT_ID` is not configured.

### `GET /auth`
OAuth callback. Exchanges the authorization code with Google, fetches user info, upserts the user in SQLite, and issues a signed JWT.

```
Redirect → FRONTEND_URL/?token=<signed_jwt>
```

> **Important:** The `redirect_uri` used during token exchange is dynamically derived from the incoming request using `request.url_for('auth')`. This must exactly match the **Authorized redirect URI** registered in the Google Cloud Console (`http://localhost:7860/auth`).

### `GET /api/me`
Validates the JWT from the `Authorization: Bearer <token>` header and returns the authenticated user's profile.

**Request:**
```http
GET /api/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200):**
```json
{
  "id": 1,
  "name": "Meet Virugama",
  "email": "meet@example.com"
}
```

**Error responses:**
- `401` — Missing or expired token
- `401` — User not found in database

### `GET /logout`
Clears the Starlette session cookie and redirects to `http://localhost:5173/`.

## JWT Token Properties

| Property | Value |
|---|---|
| **Algorithm** | HS256 |
| **Signing Key** | `JWT_SECRET_KEY` env var (falls back to `SECRET_KEY`) |
| **Expiry** | 7 days (`JWT_EXPIRATION_MINUTES = 60 * 24 * 7`) |
| **Payload** | `{ sub: user_id, email: string, exp: timestamp }` |

## Endpoint Protection

All `/api/*` endpoints call `get_current_user()` via FastAPI `Depends()`. This dependency:
1. Reads the `Authorization: Bearer <token>` header.
2. Decodes the JWT using `JWT_SECRET_KEY`.
3. Returns the `user_id` (int) or `None` if unauthenticated.

`/api/chat` and `/api/upload` accept unauthenticated requests (returning `user_id=None`) but will not persist messages to Redis memory in that case.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_CLIENT_ID` | Yes (for login) | OAuth 2.0 client ID |
| `GOOGLE_CLIENT_SECRET` | Yes (for login) | OAuth 2.0 client secret |
| `SECRET_KEY` | Yes | Session middleware key |
| `JWT_SECRET_KEY` | No | JWT signing key (defaults to `SECRET_KEY`) |
| `FRONTEND_URL` | Yes | Post-login redirect destination |
