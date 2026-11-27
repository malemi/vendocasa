#!/usr/bin/env bash
# Build a project's images on Docker's default builder.
#
#   deploy/build.sh <vendocasa|vendocasa-rehearsal> backend|web
#
# backend: tagged vendocasa-backend:<commit>, the commit it was built from.
#   The tag gains "-dirty" when the worktree has changes, and such an image is
#   never reused in production (docs/deployment.md, "Images and builds").
# web: tagged vendocasa-web:<project>-<commit>; it carries the project's
#   public URL and client key, so it belongs to one project.
#
# Records the commit, `git status --porcelain`, the free disk and the cache of
# the builder selected on this server (xplat, another project's) before and
# after, and writes the tag into the project's compose.env. Refuses below
# BUILD_FLOOR_GB (5) of free disk.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/.." && pwd)
project=${1:?usage: deploy/build.sh <project> backend|web}
target=${2:?usage: deploy/build.sh <project> backend|web}
settings="$HOME/.config/vendocasa/$project/compose.env"
floor_gb=${BUILD_FLOOR_GB:-5}

free_gb() { df -BG --output=avail / | tail -1 | tr -dc '0-9'; }
xplat_cache() { docker buildx du --builder xplat 2>/dev/null | awk '/^Total:/ {print $2}'; }

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

free=$(free_gb)
echo "build.sh: free disk before: ${free} GB; xplat cache before: $(xplat_cache)"
if [ "$free" -lt "$floor_gb" ]; then
  echo "build.sh: refusing to build below ${floor_gb} GB free" >&2
  exit 3
fi

case "$target" in
  backend) key=BACKEND_TAG; tag="$commit$suffix" ;;
  web) key=WEB_TAG; tag="$project-$commit$suffix" ;;
  *) echo "build.sh: unknown target $target" >&2; exit 2 ;;
esac

# Record the tag first: compose reads it from compose.env.
tmp=$(mktemp "$settings.XXXXXX")
grep -v "^$key=" "$settings" > "$tmp" || true
echo "$key=$tag" >> "$tmp"
chmod 600 "$tmp"
mv "$tmp" "$settings"

"$here/compose.sh" "$project" build "$target"

echo "build.sh: built $key=$tag"
echo "build.sh: free disk after: $(free_gb) GB; xplat cache after: $(xplat_cache)"
