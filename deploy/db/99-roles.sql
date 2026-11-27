-- Passwords of the two database roles that log in over the network.
--
-- Mounted as /etc/postgresql.schema.sql, which the Supabase Postgres image's
-- init (docker-entrypoint-initdb.d/migrate.sh) runs once, as supabase_admin,
-- after its own init scripts and migrations, on an empty data directory. The
-- Supabase CLI sets passwords the same way.
--
-- postgres: the backend and the migrations (POSTGRES_PASSWORD, which the image
--           also gives supabase_admin).
-- supabase_auth_admin: Auth (AUTH_DB_PASSWORD).
-- Every other built-in role keeps no password, so it cannot log in over the
-- network. Both values come from the db service's environment file
-- (deploy/make_secrets.py); they never appear in this file.

\set pgpass `echo "$POSTGRES_PASSWORD"`
\set authpass `echo "$AUTH_DB_PASSWORD"`

ALTER USER postgres WITH PASSWORD :'pgpass';
ALTER USER supabase_auth_admin WITH PASSWORD :'authpass';
