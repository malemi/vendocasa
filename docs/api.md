# API Reference

## Base URL

- Local development: `http://localhost:8000`
- Production: the Railway backend URL, which the frontend reads from `VITE_API_URL`.

## Authentication

Every route under `/api/` except `GET /api/health` requires a signed-in account:

```
Authorization: Bearer <Supabase Auth access token>
```

The frontend obtains the token through Supabase Auth email sign-in links (`@supabase/supabase-js`). The backend verifies it before reading the request body (`backend/app/auth.py`):
- signature, expiry, issuer `<SUPABASE_URL>/auth/v1` and audience `authenticated`;
- the algorithm from `SUPABASE_JWT_ALGORITHM`, never from the token header, using the project's JWKS or the HS256 secret;
- not an anonymous user;
- an email whose domain is not on the disposable-domain list.

Cookies, CORS and forwarding headers grant nothing.

The **owner** is the account whose token subject equals `OWNER_USER_ID`. Only the owner may write transaction records and use the `/api/admin/` routes.

## CORS

Configured through `CORS_ORIGINS` (comma-separated origins). Credentials (cookies) are not used. Refusals carry CORS headers, so the browser can read them.

## Refusals

A refused request returns:

```json
{"detail": {"error": "<code>", "message": "<Italian message for the user>"}}
```

The codes and messages are in `backend/app/refusals.py`. The frontend shows `message`.

The other errors send `detail` as a plain string:
- **In Italian.** Six input checks answer `400`:
  - in `POST /api/chat`: a message longer than `AGENT_MAX_MESSAGE_CHARS`, more than 4 documents in one message, and attachments over `AGENT_MAX_ATTACHMENT_BYTES`;
  - in `POST /api/documents/upload`: an unsupported file type, a file that is not a valid PDF, and an empty or corrupt image.
- **In English.** These answer in English:
  - an invalid `bbox` (`400`);
  - an owner's transaction update with no fields (`400`);
  - every `404`: an address, zone, semester or transaction that is not found.

The frontend shows a plain-string detail as it is.

| Code | Status | When |
|------|--------|------|
| `not_authenticated` | 401 | No bearer token |
| `session_expired` | 401 | The token has expired |
| `invalid_token` | 401 | Bad signature, issuer, audience or claims, or an anonymous user |
| `disposable_email` | 403 | The account's email domain is a disposable-address domain |
| `auth_unavailable` | 503 | Identity configuration or the domain list is unavailable |
| `owner_only` | 403 | An owner-only route called by another account |
| `rate_limited` | 429 | A per-account or per-IP request limit; `Retry-After` gives the seconds to wait |
| `daily_limit` | 503 | The service-wide daily model-call ceiling |
| `account_limit` | 429 | The account's monthly allowance is used up |
| `global_limit` | 503 | The service's monthly allowance is used up |
| `paused` | 503 | The owner has turned paid calls off |
| `assistant_unavailable` | 503 | The spending ledger or the model provider failed |
| `concurrent` | 429 | The account already has an active chat stream |
| `too_large` | 413 | The request body or the file is over its limit |
| `account_uploads_full` | 429 | The account's stored uploads are at their byte cap |
| `uploads_full` | 503 | All stored uploads are at the total byte cap |
| `document_expired` | 400 | A referenced document is missing, expired or not the account's own; the three cases look the same |
| `history_limit` | 400 | The conversation is over `AGENT_MAX_HISTORY_MESSAGES` messages |
| `model_refusal` | — | Sent as an SSE `error` event when the model declines |

Request bodies are limited before parsing (`backend/app/middleware.py`): 1 MiB for `/api/chat`, 6 MiB for `/api/documents/upload`, 64 KiB elsewhere. Validation errors keep FastAPI's `422` format. A refused non-finite number (`NaN`, `Infinity`) is echoed in `input` as a string, because it is not valid JSON.

## Spending caps

Every paid provider call is charged to the requesting account, in a PostgreSQL ledger (`backend/app/services/spending.py`). Paid calls are model calls, and Google geocoding when its key is configured.

- **Caps.** Each account may spend `ACCOUNT_MONTHLY_CAP_USD`, default $1, and the whole service `GLOBAL_MONTHLY_CAP_USD`, default $100, per calendar month in UTC.
- **Reserve.** Before each call its maximum cost is reserved against both caps. A call that would exceed either cap is refused before it starts.
- **Settle.** The actual cost is recorded afterwards. If the outcome is unknown (error, timeout, cancellation), the full reservation is charged.
- **Switch.** Paid calls start switched off. The owner turns them on through `PUT /api/admin/paid-calls`.
- **Overrun.** If a call's actual cost exceeds its reservation, the price table or the token count is wrong. The cost is still recorded in full, and paid calls are switched off until the owner turns them on again. If switching them off fails, the error is logged and paid calls stay on.

## Endpoints

### POST /api/chat

The conversational valuation agent, streamed as Server-Sent Events. The backend runs Claude (`ANTHROPIC_MODEL`, default `claude-sonnet-5-5`) with server-side tool calls.

**Request body:**
```json
{
  "messages": [
    {"role": "user", "content": "Valuta Via Sottocorno 17, Milano, 62mq", "document_ids": ["<uuid>"]}
  ]
}
```

- **Roles and history.** Roles are `user` or `assistant`; anything else is refused with `422`. Send the full conversation each time, because the backend is stateless.
- **Bounds.** The history holds at most `AGENT_MAX_HISTORY_MESSAGES` messages, default 50. Each message holds at most `AGENT_MAX_MESSAGE_CHARS` characters, default 4000.
- **Documents.** `document_ids` refers to the account's own uploads, and the total size of attachments in one request is at most `AGENT_MAX_ATTACHMENT_BYTES`, default 15 MB.
- **Limits.** The route applies per-account and per-IP request limits, the global daily model-call ceiling, the monthly spending caps and the paid-call switch. One active stream per account.

**Response:** `text/event-stream`

```
event: text_delta
data: {"text": "Ciao! Cerco subito "}

event: tool_result
data: {"tool": "valuate_property", "result": {"zone": {...}, "location": {...}, "estimate": {...}}}

event: done
data: {}
```

| Event | Data | Purpose |
|-------|------|---------|
| `text_delta` | `{"text": "..."}` | Streamed text |
| `tool_result` | `{"tool": "...", "result": {...}}` | Structured valuation data, rendered as inline cards |
| `error` | `{"error": "<code>", "message": "..."}` | A refusal or failure during the stream, for example `account_limit`, `daily_limit`, `model_refusal` or `assistant_unavailable` |
| `done` | `{}` | Stream complete |

Provider error details never reach the client.

### POST /api/documents/upload

Uploads a PDF or image (JPEG, PNG, WEBP, GIF) for use in chat and returns its ID.

- **Size and lifetime.** At most 5 MB. The file stays in the backend's memory for 30 minutes, and a restart deletes it.
- **Ownership.** The document belongs to the uploading account, and no other account can use it.
- **Caps.** Stored uploads are capped at 20 MiB per account and 200 MiB in total.
- **Limits.** The route shares the chat route's request limits.

**Response:** `{"doc_id": "...", "filename": "...", "size": 1234, "media_type": "application/pdf"}`

### GET /api/valuate

Geocodes an address, finds its OMI zone and returns price data. The route applies the chat-level request limits, because it reaches the public geocoders.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| address | string | yes | | Italian address |
| property_type | int | no | 20 | Property type code (20 = Abitazioni civili) |
| surface_m2 | float | no | | Surface; when given, the total estimate is computed. Finite, above 0 and at most 100,000, or `422` |
| semester | string | no | latest complete | A semester recorded complete, e.g. "2024_S2" |

**Response:**
```json
{
  "address": "Via Roma 1, Milano",
  "coordinates": {"lat": 45.464, "lng": 9.190},
  "location": {"precision": "exact", "source": "photon", "matched_address": "...", "zone_distance_m": null, "approximate": false},
  "zone": {"link_zona": "MI00000290", "zone_code": "B01", "fascia": "B", "municipality": "MILANO", "description": "CENTRO STORICO", "distance_m": null},
  "semester": "2024_S2",
  "quotations": [{"conservation_state": "NORMALE", "is_prevalent": true, "price_min": 3800.0, "price_max": 5200.0, "surface_type_sale": "L", "...": "..."}],
  "estimate": {"min": 304000.0, "max": 416000.0, "mid": 360000.0, "eur_per_m2_range": [3800.0, 5200.0]},
  "comparables": []
}
```

- **Location.** `location.approximate` is true when the geocoder did not report a building-level match, or when the nearest zone within 200 m replaced an exact zone match.
- **No data.** When the zone has no usable quotation range (missing, non-positive, reversed or NaN), `estimate` is null and `no_data` explains it: `{"reason": "no_usable_quotation", "message": "..."}`.
- **Comparables.** They are transaction records with the zone's exact `link_zona`.
- **Errors.** `404` when the address, the zone or the semester is not found.

### POST /api/valuate/enhanced

Applies correction coefficients to the OMI range of the selected conservation state, and compares the result with comparables. The request body is unchanged:
- `address`, `surface_m2` (finite, above 0 and at most 100,000, or `422`), `property_type` and `semester`;
- `details` with `conservation_state`, `renovation`, `floor`, `exposure`, `noise`, `elevator`, `common_areas`, `building_facade` and `energy_class`.

The response has the following parts:
- `location`, `zone` and `semester`;
- `quotations_by_state`;
- `adjusted_estimate`, which holds the base and adjusted EUR/m2 values, the totals, `total_coefficient`, `breakdown` and `benchmark_comparison`;
- `comparables`.

All amounts are rounded to cents. When no usable range exists, the response carries `no_data` and no `adjusted_estimate`. The route applies the same request limits as `GET /api/valuate`.

### GET /api/coefficients

All correction coefficient factors and options. The list is static, so the route has the per-account route quota, not the chat-level limits.

### GET /api/zones/geojson

Zone polygons as a GeoJSON FeatureCollection. `bbox` (`min_lng,min_lat,max_lng,max_lat`) is required. At most 500 zones are returned, ordered by `link_zona`. `semester` defaults to the latest complete one.

### GET /api/zones/by-coordinates

The zone at a point (`lat`, `lng`, optional `semester`).

### GET /api/quotations

Quotations for a zone (`link_zona`, optional `semester`), at most 200 rows.

### GET /api/transactions

Transaction records, newest first, one page at a time: `limit` (default 50, at most 100) and `offset`. Optional filters: `link_zona` and `municipality`.

### POST /api/transactions, PUT /api/transactions/{id}, DELETE /api/transactions/{id}

Create, update and delete transaction records. **Owner only.** The create body:

```json
{
  "transaction_date": "2024-06-01",
  "transaction_type": "Residenziale",
  "declared_price": 250000.00,
  "municipality": "MILANO",
  "omi_zone": "B01",
  "link_zona": "MI00000290",
  "cadastral_category": "A/2",
  "cadastral_vani": 5.0,
  "cadastral_mq": null,
  "cadastral_mc": null,
  "notes": "Appartamento piano 3, buone condizioni"
}
```

Records without a `link_zona` are never used as comparables.

### GET /api/semesters

The semesters whose import is recorded complete, newest first: `{"semesters": [...], "latest": "2024_S2"}`.

### GET /api/admin/spending

**Owner only.** The current month's spending in US dollars: the global total, each account's spending and reservations, the caps and the paid-call switch.

### PUT /api/admin/paid-calls

**Owner only.** Body `{"enabled": true}`. Turns paid provider calls on or off; the rest of the site keeps working.

### GET /api/health

Public liveness check: `{"status": "ok"}`.

## Geocoding

The geocoder tries the following, in order:
1. Photon, the primary.
2. Nominatim.
3. Google Geocoding, only when `GOOGLE_GEOCODING_API_KEY` is set. Each Google request is reserved and charged to the requesting account at its price, whatever the result.

A result is `exact` only for a building-level match. Results are not cached.
