-- Local stack only. The backend's Alembic migrations own these schemas
-- (backend/migrations). They exist before the first migration only so that
-- the local Data API, which exposes them for the client-role tests
-- (supabase/config.toml), can load its schema cache and start.
CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS omi;
