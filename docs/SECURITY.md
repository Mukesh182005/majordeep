# Security

## Authentication

- **JWT-based authentication** using HS256 signing with configurable secret key.
- Passwords hashed with bcrypt via passlib.
- Token expiry is configurable (default: 24 hours).
- Registration requires a valid email address format.

## Production Safety

The application **refuses to start** in production mode if:

- `JWT_SECRET_KEY` is still the default placeholder value.
- `JWT_SECRET_KEY` is shorter than 32 characters.
- `DEBUG` mode is enabled.
- `CORS_ORIGINS` contains a wildcard (`*`).

This prevents accidental deployment with insecure defaults.

## Upload Security

- **File type validation:** Uploads are validated by MIME type and file extension.
- **Size limits:** Configurable maximum upload size (default: 100 MB).
- **Rate limiting:** Per-user and per-IP upload rate limits (configurable).
- **SHA-256 hashing:** Every uploaded file is cryptographically hashed at ingestion for integrity verification.

## Request Security

- **Request IDs:** Every API request receives a unique request ID for audit trail correlation.
- **Security headers:** Production mode enables HSTS, X-Content-Type-Options, X-Frame-Options, and Referrer-Policy headers.
- **CORS:** Origins are explicitly configured; wildcard is rejected in production.
- **Error handling:** Internal errors return opaque messages with request IDs. Stack traces are logged server-side only and never exposed to clients.
- **Content-Length enforcement:** Oversized uploads are rejected before the body is read.

## Report Integrity

- Generated PDF reports are SHA-256 hashed.
- Report hashes are stored in the database and exposed via the `X-Report-SHA256` response header.
- A verification endpoint (`/api/reports/{ref}/verify`) allows independent integrity checking.

## Data Isolation

- Users can only access their own analysis history.
- Job results are scoped to the job owner or guest session.
- Upload audit events are recorded with user ID and client IP.

## Secrets Management

- `.env` files are excluded from version control via `.gitignore`.
- `.env.example` contains only placeholder values and documentation.
- No API keys, passwords, or tokens are hardcoded in source code.

## Known Security Considerations

- **JWT tokens are stored in localStorage** in the frontend. For deployments handling sensitive case material, migration to httpOnly cookies is recommended to prevent token theft via XSS.
- **SQLite (development)** does not support concurrent writes well. Production deployments should use PostgreSQL.
- **Guest uploads** (without authentication) are rate-limited but allowed by default. Disable by setting `GUEST_RATE_LIMIT_PER_HOUR=0`.
