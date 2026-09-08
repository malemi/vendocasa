# API Reference

## Base URL

- Local development: `http://localhost:8000`
- Production: `https://vendocasa-backend.railway.app` (or configured domain)

## CORS

Configured via `CORS_ORIGINS` environment variable (comma-separated origins).

## Endpoints

### POST /api/chat

AI conversational agent via Server-Sent Events (SSE). The backend orchestrates Claude Sonnet 4 with programmatic tool calling to perform valuations through natural conversation.

**Request Body:**
```json
{
  "messages": [
    {"role": "user", "content": "Valuta Via Sottocorno 17, Milano, 62mq"}
  ]
}
```

Messages follow the standard `role`/`content` format. Send the full conversation history with each request (the backend is stateless). The history is capped at `AGENT_MAX_HISTORY_MESSAGES` messages (default 20) of up to `AGENT_MAX_MESSAGE_CHARS` characters each (default 4000); a request exceeding either returns `400`.

The endpoint is rate-limited per identity (the `vendocasa_uid` cookie and
the client IP, checked independently) and by a global daily ceiling on
Anthropic model calls -- see **Errors** below and `docs/deployment.md` for
the environment variables and defaults.

**Response:** `text/event-stream` (SSE)

```
event: text_delta
data: {"text": "Ciao! Cerco subito "}

event: text_delta
data: {"text": "informazioni sulla zona..."}

event: tool_result
data: {"tool": "valuate_property", "result": {"zone": {...}, "estimate": {...}, "coordinates": {...}}}

event: map_update
data: {"lat": 45.464, "lng": 9.190}

event: text_delta
data: {"text": "L'immobile si trova in zona C20..."}

event: done
data: {}
```

**SSE Event Types:**

| Event | Data | Purpose |
|-------|------|---------|
| `text_delta` | `{"text": "..."}` | Streamed text token |
| `tool_result` | `{"tool": "...", "result": {...}}` | Structured valuation data (rendered as inline cards in the chat) |
| `map_update` | `{"lat": ..., "lng": ...}` | Coordinates for map flyTo |
| `done` | `{}` | Stream complete |
| `error` | `{"message": "..."}` | Error occurred |

**Errors:**
- `400` -- conversation history or a single message exceeds the configured cap
- `400` -- total attachment bytes across the request exceed `AGENT_MAX_ATTACHMENT_BYTES`
- `429` -- per-identity rate limit exceeded (per-minute or per-day). Body:
  `{"detail": {"error": "rate_limited", "message": "..."}}`, with a
  `Retry-After` header giving the number of seconds to wait
- `503` -- the service-wide daily model-call ceiling has been reached. Body:
  `{"detail": {"error": "service_unavailable", "message": "..."}}`

A missing `ANTHROPIC_API_KEY` is a startup failure, not a per-request
error -- the backend does not accept traffic without one configured.

---

### GET /api/valuate

Main valuation endpoint. Geocodes an address, finds its OMI zone, and returns price data.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| address | string | yes | | Italian address to valuate |
| property_type | int | no | 20 | Property type code (20=Abitazioni civili) |
| surface_m2 | float | no | null | Surface area; if provided, calculates total estimate |
| semester | string | no | latest | Semester to query (e.g. "2024_S2") |

**Response:**
```json
{
  "address": "Via Roma 1, Milano",
  "coordinates": {"lat": 45.464, "lng": 9.190},
  "zone": {
    "link_zona": "MI00000290",
    "zone_code": "B01",
    "fascia": "B",
    "municipality": "MILANO",
    "description": "CENTRO STORICO"
  },
  "semester": "2024_S2",
  "quotations": [
    {
      "property_type_desc": "Abitazioni civili",
      "conservation_state": "NORMALE",
      "is_prevalent": true,
      "price_min": 3800.0,
      "price_max": 5200.0,
      "surface_type_sale": "L",
      "rent_min": 14.0,
      "rent_max": 21.0,
      "surface_type_rent": "L"
    }
  ],
  "estimate": {
    "min": 304000.0,
    "max": 416000.0,
    "mid": 360000.0,
    "eur_per_m2_range": [3800.0, 5200.0]
  },
  "comparables": []
}
```

**Errors:**
- `404` -- address not found by geocoder
- `404` -- no OMI zone found for location (not even within 200m fallback)

---

### POST /api/valuate/enhanced

Enhanced valuation with correction coefficients. Takes property-specific details and applies Italian appraisal methodology adjustments to the OMI base range.

**Request Body:**
```json
{
  "address": "Via Sottocorno 17, Milano",
  "surface_m2": 62,
  "property_type": 20,
  "semester": null,
  "details": {
    "conservation_state": "OTTIMO",
    "renovation": "premium_post_2015",
    "floor": "third_fourth",
    "exposure": "south_dual",
    "noise": "very_silent",
    "elevator": "present",
    "common_areas": "needs_maintenance",
    "facade": "good",
    "energy_class": "c_d"
  }
}
```

**Response:**
```json
{
  "base_estimate": {
    "min": 403000,
    "max": 551800,
    "mid": 477400,
    "eur_per_m2_range": [6500, 8900]
  },
  "adjusted_estimate": {
    "min": 487630,
    "max": 667678,
    "mid": 577654,
    "eur_per_m2_range": [7865, 10769]
  },
  "total_coefficient": 0.21,
  "coefficients_applied": [
    {"factor": "renovation", "option": "premium_post_2015", "value": 0.10},
    {"factor": "floor", "option": "third_fourth", "value": 0.05},
    {"factor": "exposure", "option": "south_dual", "value": 0.05},
    {"factor": "noise", "option": "very_silent", "value": 0.03},
    {"factor": "common_areas", "option": "needs_maintenance", "value": -0.02}
  ],
  "zone": { "..." },
  "coordinates": {"lat": 45.464, "lng": 9.190}
}
```

---

### GET /api/coefficients

Returns all available correction coefficient factors and options. Used by the frontend to dynamically build the property details form.

**Response:**
```json
{
  "factors": {
    "renovation": {
      "label": "Ristrutturazione",
      "label_en": "Renovation",
      "options": [
        {"key": "premium_post_2015", "label": "Ristrutturazione integrale post-2015", "label_en": "Premium renovation post-2015", "pct": 0.10},
        {"key": "standard_recent", "label": "Ristrutturazione parziale/recente", "label_en": "Standard/recent renovation", "pct": 0.05},
        {"key": "none", "label": "Nessuna ristrutturazione", "label_en": "No renovation", "pct": 0.0},
        {"key": "needs_work", "label": "Da ristrutturare", "label_en": "Needs renovation", "pct": -0.10}
      ]
    },
    ...
  }
}
```

---

### GET /api/zones/geojson

Returns zone polygons as GeoJSON for map display.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| bbox | string | no | | Bounding box: "min_lng,min_lat,max_lng,max_lat" |
| semester | string | no | latest | Semester |

**Response:** GeoJSON FeatureCollection with zone properties and average price data.

---

### GET /api/zones/by-coordinates

Look up zone info for a specific point.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| lat | float | yes | Latitude |
| lng | float | yes | Longitude |
| semester | string | no | Semester (defaults to latest) |

---

### GET /api/quotations

Quotations for a specific zone.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| link_zona | string | yes | Zone identifier |
| semester | string | no | Defaults to latest |

---

### POST /api/transactions

Create a manually entered transaction record.

**Request Body:**
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

---

### GET /api/transactions

List transactions, optionally filtered.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| link_zona | string | no | Filter by zone |
| municipality | string | no | Filter by municipality |

---

### PUT /api/transactions/{id}

Update a transaction record.

---

### DELETE /api/transactions/{id}

Delete a transaction record.

---

### GET /api/semesters

List all available data periods.

**Response:**
```json
{
  "semesters": ["2024_S2", "2024_S1", "2023_S2", "..."],
  "latest": "2024_S2"
}
```

---

### GET /api/health

Health check endpoint (used by Railway for deployment monitoring).

**Response:**
```json
{"status": "ok"}
```

---

## Geocoding Strategy

1. **Nominatim** -- free, 1 request/second rate limit, results cacheable permanently (ODbL)
2. **Google Geocoding API** -- fallback, 10k free requests/month, requires API key

Note: There is currently **no database cache table** (`omi.geocode_cache` does not exist). Geocoding results are not persisted between requests.

---

## Error Responses

All errors follow the format:
```json
{
  "detail": "Human-readable error message"
}
```

Common error codes:
- `404` -- resource not found (address, zone, transaction)
- `422` -- validation error (invalid parameters)
- `429` -- rate limit exceeded on `/api/chat` or `/api/documents/upload` (`detail.error: "rate_limited"`, `Retry-After` header) -- both share the same per-identity budget
- `500` -- internal server error
- `503` -- `/api/chat` global daily model-call ceiling reached (`detail.error: "service_unavailable"`)
