# The web gateway: the built frontend served by Caddy (deploy/gateway.Caddyfile).
# Build context: the repository root.
#
# The frontend calls /api and /auth/v1 on its own origin, so VITE_API_URL stays
# empty. VITE_SUPABASE_URL is the public origin and VITE_SUPABASE_ANON_KEY the
# public client key, which grants nothing (no Data API exists); both are build
# arguments because Vite reads them at build time.

FROM node:22-alpine@sha256:1314fb30ec37592d5845e5a160d522c0e680972aa534549940b8d73bde88481a AS build
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ENV VITE_API_URL="" VITE_SUPABASE_URL=$VITE_SUPABASE_URL VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY
RUN test -n "$VITE_SUPABASE_URL" && test -n "$VITE_SUPABASE_ANON_KEY" && npm run build

# caddy:2.10.0-alpine, the image nql8r's gateway uses.
FROM caddy@sha256:ae4458638da8e1a91aafffb231c5f8778e964bca650c8a8cb23a7e8ac557aa3c
# The listeners use unprivileged ports, so the binary needs no file capability.
# Without it, Caddy runs as UID 1001 with an empty capability set.
RUN setcap -r /usr/bin/caddy
COPY deploy/gateway.Caddyfile /etc/caddy/Caddyfile
COPY --from=build /src/dist /srv
USER 1001:1001
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
