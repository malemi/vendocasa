#!/usr/bin/env bash
# Run docker compose for one VendoCasa project, with its files and settings.
#
#   deploy/compose.sh vendocasa <compose arguments...>            production
#   deploy/compose.sh vendocasa-rehearsal <compose arguments...>  loopback rehearsal
#   VENDOCASA_HARNESS=1 deploy/compose.sh vendocasa-rehearsal ...  rehearsal backend
#                                                                  for the browser journeys
#
# The project's settings come from ~/.config/vendocasa/<project>/compose.env,
# written by deploy/make_secrets.py. Builds use Docker's default builder: the
# builder selected on this server belongs to another project.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
project=${1:?usage: deploy/compose.sh <vendocasa|vendocasa-rehearsal> <compose arguments...>}
shift
case "$project" in
  vendocasa | vendocasa-rehearsal) ;;
  *) echo "compose.sh: unknown project $project" >&2; exit 2 ;;
esac

settings="$HOME/.config/vendocasa/$project/compose.env"
if [ ! -f "$settings" ]; then
  echo "compose.sh: $settings is missing; run deploy/make_secrets.py first" >&2
  exit 2
fi

files=(-f "$here/compose.yaml")
if [ "$project" = vendocasa-rehearsal ]; then
  files+=(-f "$here/compose.rehearsal.yaml")
  if [ "${VENDOCASA_HARNESS:-0}" = 1 ]; then
    files+=(-f "$here/compose.harness.yaml")
  fi
elif [ "${VENDOCASA_HARNESS:-0}" = 1 ]; then
  echo "compose.sh: the journeys' harness never runs in production" >&2
  exit 2
fi

export BUILDX_BUILDER=default
exec docker compose -p "$project" --env-file "$settings" "${files[@]}" "$@"
