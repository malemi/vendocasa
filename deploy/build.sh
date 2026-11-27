#!/usr/bin/env bash
# Build a project's images on Docker's default builder, or reuse the backend
# image that was built and rehearsed from the same backend inputs.
#
#   deploy/build.sh <vendocasa|vendocasa-rehearsal> backend [--rebuild]
#   deploy/build.sh <vendocasa|vendocasa-rehearsal> web
#
# backend: tagged vendocasa-backend:<commit>, the commit it was built from.
#   When the worktree is clean and an existing clean image's commit has the
#   same backend inputs as HEAD (`git diff --quiet`), that image is reused and
#   nothing is built: production then runs the bytes the rehearsal ran, whose
#   Debian packages are not pinned. --rebuild builds anyway, after removing the
#   superseded backend images that no container uses. A tag gains "-dirty" when
#   the worktree has changes, and such an image is never reused.
# web: tagged vendocasa-web:<project>-<commit>; it carries the project's public
#   URL and client key, so it belongs to one project.
#
# Records the commit, `git status --porcelain`, the free disk and the cache of
# the builder selected on this server (xplat, another project's) before and
# after, and writes the tag into the project's compose.env. A build refuses
# below BUILD_FLOOR_GB (5) GiB of free disk, counted in bytes.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/.." && pwd)
project=${1:?usage: deploy/build.sh <project> backend [--rebuild] | web}
target=${2:?usage: deploy/build.sh <project> backend [--rebuild] | web}
rebuild=${3:-}
settings="$HOME/.config/vendocasa/$project/compose.env"
floor_gb=${BUILD_FLOOR_GB:-5}
backend_inputs=(Dockerfile .dockerignore backend/app backend/migrations backend/scripts backend/sql
  backend/data backend/alembic.ini backend/requirements.lock)

free_bytes() { df -B1 --output=avail / | tail -1 | tr -dc '0-9'; }
gib() { awk -v b="$1" 'BEGIN { printf "%.2f GiB", b / 1073741824 }'; }
xplat_cache() { docker buildx du --builder xplat 2>/dev/null | awk '/^Total:/ {print $2}'; }

set_tag() {
  local key=$1 tag=$2 tmp
  tmp=$(mktemp "$settings.XXXXXX")
  grep -v "^$key=" "$settings" > "$tmp" || true
  echo "$key='$tag'" >> "$tmp"
  chmod 600 "$tmp"
  mv "$tmp" "$settings"
}

commit=$(git -C "$repo" rev-parse --short=12 HEAD)
porcelain=$(git -C "$repo" status --porcelain)
echo "build.sh: project=$project target=$target commit=$commit"
if [ -n "$porcelain" ]; then
  echo "build.sh: worktree has changes:"
  echo "$porcelain"
  suffix=-dirty
else
  echo "build.sh: worktree clean"
  suffix=
fi

case "$target" in
  backend)
    key=BACKEND_TAG
    tag="$commit$suffix"
    if [ -z "$suffix" ] && [ "$rebuild" != --rebuild ]; then
      for existing in $(docker images vendocasa-backend --format '{{.Tag}}' | grep -v -- '-dirty$' || true); do
        if git -C "$repo" cat-file -e "$existing^{commit}" 2>/dev/null &&
          git -C "$repo" diff --quiet "$existing" HEAD -- "${backend_inputs[@]}"; then
          set_tag "$key" "$existing"
          echo "build.sh: reusing vendocasa-backend:$existing: its backend inputs equal HEAD's"
          exit 0
        fi
      done
    fi
    if [ "$rebuild" = --rebuild ]; then
      for existing in $(docker images vendocasa-backend --format '{{.Tag}}'); do
        [ "$existing" = "$tag" ] && continue
        if docker image rm "vendocasa-backend:$existing" > /dev/null 2>&1; then
          echo "build.sh: removed superseded vendocasa-backend:$existing"
        else
          echo "build.sh: kept vendocasa-backend:$existing, which a container uses"
        fi
      done
    fi
    ;;
  web) key=WEB_TAG; tag="$project-$commit$suffix" ;;
  *) echo "build.sh: unknown target $target" >&2; exit 2 ;;
esac

free=$(free_bytes)
echo "build.sh: free disk before: $(gib "$free"); xplat cache before: $(xplat_cache)"
if [ "$free" -lt $((floor_gb * 1073741824)) ]; then
  echo "build.sh: refusing to build below ${floor_gb} GiB free" >&2
  exit 3
fi

set_tag "$key" "$tag"
VENDOCASA_BUILD=1 "$here/compose.sh" "$project" build "$target"

echo "build.sh: built $key=$tag"
echo "build.sh: free disk after: $(gib "$(free_bytes)"); xplat cache after: $(xplat_cache)"
