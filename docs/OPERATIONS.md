# DPDP Compass: Operations

How to deploy, configure, monitor and maintain the system in production.

## Deploy

1. Put the Gazette PDF of the Act at `data/legal/DPDP_Act_2023.pdf`.
2. Copy `.env.production.example` to `.env.production` and fill it in.
3. Start the stack:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

The web app listens on `WEB_PORT` (default 8080). Put a TLS-terminating proxy or load balancer in front of it; the API is not exposed directly.

## Configuration

| Variable | Purpose |
|---|---|
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` | Any OpenAI-compatible endpoint |
| `LLM_FALLBACK_API_KEYS` | Comma-separated backup keys, used when the main key is rate-limited or rejected |
| `MOCK_LLM=true` | Run with no model: audits use keyword rules, answers quote the provisions |
| `AUTH_REQUIRED` | Default `true`: every `/api/*` call needs a signed-in session (or the service `API_KEY`). Set `false` only for local scripts |
| `API_KEY` | Service key: a request with a valid `X-API-Key` is accepted without a session |
| `RATE_LIMIT_PER_MIN` | Requests per client IP per minute on `POST /api/*` (default 30) |
| `MAX_BODY_BYTES` | Largest accepted request body (default 12 MB) |
| `CORS_ORIGINS` | Allowed browser origins, comma-separated |
| `TRUSTED_HOSTS` | Allowed `Host` headers, comma-separated |
| `ENV=production` | Hides `/docs` and configuration details in `/health` |

Secrets are read from the environment only. Never commit `.env.production`.

## Health and monitoring

| Endpoint | Meaning |
|---|---|
| `GET /health` | The process is up |
| `GET /ready` | The statute knowledge base and its index are built; returns 503 while starting (about 20 to 60 seconds) |
| `GET /api/compass/kb` | Knowledge-base counts: chunks, obligations, graph size |

Every response carries `X-Request-ID`. Access logs are one JSON object per request (`request_id`, `method`, `path`, `status`, `ms`, `ip`) on the `app.access` logger. Query strings and bodies are never logged. Errors are logged with the request id on `app.errors`; clients receive only `{"detail": "internal error", "request_id": ...}`.

Alert on: `/ready` not 200 for more than 2 minutes, a rising share of 5xx or 429 responses, and audit reports whose `evidence.degraded` field is set (the model was unavailable and keyword rules were used).

## What the service does when the model is unavailable

- **Audit:** falls back to the keyword rules and marks the report `degraded`. Findings still carry citations from the knowledge base.
- **Question:** returns the retrieved provisions themselves, marked `degraded`.
- A rate-limited key fails over to the backup keys before either fallback applies.

## Security controls in place

- Accounts: passwords hashed with scrypt and a per-user salt; sessions in an HttpOnly, SameSite=Lax cookie (Secure in production), stored server-side as a hash; five failed sign-ins lock an email for 15 minutes; state-changing requests from other origins are refused
- Each user sees only their own audits and saved work; deleting an account deletes both
- Service API key and per-IP rate limit on write and model endpoints
- Request-size limit, trusted-host check, CORS allowlist
- Security headers on API and web responses (CSP, `X-Frame-Options`, `nosniff`, HSTS behind TLS)
- Containers run as non-root with a read-only filesystem, no added capabilities
- Personal data in questions is redacted before processing and logging
- Policy text is always passed to the model as data; instruction-like content is flagged
- URL ingestion is protected against server-side request forgery

## Known limits

- **One API worker.** The rate limiter and the SQLite audit store are per-process. To scale out, move rate limiting to Redis and audits to PostgreSQL first.
- **Accounts are basic.** Email and password only: no email verification, no password reset by email, no social sign-in. A user who forgets a password cannot recover the account yet.
- **Free-tier model limits.** The Groq free tier allows 200,000 tokens per day per key for the default model; an audit uses about 5,700 tokens.
- **CPU re-ranking** adds about 0.6 seconds per question.
- **Hindi and Marathi PDFs** need a Devanagari font in the image (Noto Sans Devanagari) for the export feature.

## Backup and restore

Accounts (`accounts.db`), saved audits (`analyses.db`) and uploads live in the `compass_storage` volume (`/app/storage`). Back it up with:

```bash
docker run --rm -v compass_storage:/data -v "$PWD":/backup alpine tar czf /backup/compass_storage.tgz -C /data .
```

The knowledge base is rebuilt from the PDF at every start and needs no backup.

## Upgrades

1. Run the tests: `MOCK_LLM=true python -m pytest tests -q` in `backend/`.
2. If dependencies changed, regenerate `backend/requirements.lock`.
3. Rebuild and restart with the deploy command. The frontend waits for the API to report ready.

## Rotating keys

Replace `LLM_API_KEY` (and any fallback keys) in `.env.production` and restart the backend. Rotate immediately if a key has been pasted into a chat, a ticket or a commit.
