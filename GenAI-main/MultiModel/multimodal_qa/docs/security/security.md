# Security & Threat Model

The application has been hardened against common AI and Web vulnerabilities as part of an extreme Red-Teaming audit.

## 1. Authentication & JWT Tokens
- **Google OAuth**: Users are authenticated via Google OAuth.
- **Stateless JWT**: Instead of relying on cookie-based sessions, the `/auth` endpoint generates cryptographically signed JSON Web Tokens (JWT) using `PyJWT`.
- **Validation**: All API endpoints enforce a strict `Authorization: Bearer <token>` check to extract the authenticated `user_id`.

## 2. Input Validation & Path Traversal Prevention
- **Strict Session IDs**: The `session_id` parameters sent from the client are validated via a strict regex (`^[a-zA-Z0-9_-]+$`) to prevent Path Traversal attacks (e.g., `../../../etc/passwd`).
- **Endpoint Enforcement**: This regex validation is applied directly at the FastAPI routing layer (`api/routes.py`) to guarantee safety when creating upload directories.

## 3. Malware Scanning & File Validation
- **File Type Restrictions**: The backend strictly enforces valid file extensions and MIME types (`application/pdf` for documents, standard image types for vision), preventing executable uploads.
- **Malware Signatures**: Before saving, uploaded binaries are scanned against a mock malware dictionary (e.g., matching EICAR standard signatures). Malicious payloads immediately return HTTP 403.
- **Upload Size Limits**: Files are strictly bound to a 25MB threshold. Violations return HTTP 413.

## 4. Prompt Injection & Output Defenses
- **Regex Blocking**: A suite of blacklisted prompt engineering regex patterns (like "ignore all instructions", "DAN mode", "jailbreak") immediately intercepts and blocks malicious messages before reaching the LangGraph core.
- **System Prompt Guardrails**: The LangGraph agent's system prompt contains explicit directives to ignore user requests to "ignore previous instructions" or print the prompt.
- **Output Sanitization**: The final AI response is filtered. If dangerous scripts (`<script>`, `os.system`) are detected, the response is sanitized and flagged.

## 5. Rate Limiting (SlowAPI)
- **Chat Endpoints**: Throttled to 30 requests per minute to prevent token exhaustion.
- **Upload Endpoints**: Upload endpoints are strictly throttled to 10 requests per hour to prevent Disk/CPU DoS attacks during embedding ingestion.

## 6. Comprehensive Testing Suite
- Automated Pytest suites (`tests/test_security.py`) validate the integrity of JWT generation, Fuzzing (invalid payloads and large uploads), and Penetration (simulating Path Traversal strings). All tests run natively in the CI pipeline.
