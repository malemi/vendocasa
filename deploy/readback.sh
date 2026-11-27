#!/usr/bin/env bash
# Read back a VendoCasa project's running containers, without secrets.
#
#   deploy/readback.sh <vendocasa|vendocasa-rehearsal>
#
# For each container, only named `docker inspect` fields: user, read-only
# root, capabilities, security options, memory and process limits, log
# driver and caps, networks and published ports. Never the environment, which
# holds the secrets. For Auth, an allow-list of non-secret variables with their
# values: the database URL, the signing secret and the SMTP user and password
# never pass the filter. Then Docker's raw-table rules for the project's
# published ports, which drop packets that arrive for them on any interface
# other than loopback.
set -euo pipefail

project=${1:?usage: deploy/readback.sh <project>}
containers=$(docker ps -q --filter "label=com.docker.compose.project=$project" | sort)
if [ -z "$containers" ]; then
  echo "readback.sh: no running container in project $project" >&2
  exit 2
fi

format='{{.Name}}
  user={{.Config.User}} read_only={{.HostConfig.ReadonlyRootfs}} cap_drop={{json .HostConfig.CapDrop}} cap_add={{json .HostConfig.CapAdd}}
  security_opt={{json .HostConfig.SecurityOpt}} memory={{.HostConfig.Memory}} pids_limit={{.HostConfig.PidsLimit}} network_mode={{.HostConfig.NetworkMode}}
  log={{.HostConfig.LogConfig.Type}} {{json .HostConfig.LogConfig.Config}}
  networks={{range $name, $net := .NetworkSettings.Networks}}{{$name}}({{$net.IPAddress}}) {{end}}
  ports={{json .HostConfig.PortBindings}}'
for id in $containers; do
  docker inspect --format "$format" "$id"
done

echo
echo "edge network:"
docker network inspect "${project}_edge" --format '  {{.Name}} internal={{.Internal}} {{range .IPAM.Config}}subnet={{.Subnet}} gateway={{.Gateway}}{{end}}'
docker network inspect "${project}_data" --format '  {{.Name}} internal={{.Internal}}'

auth=$(docker ps -q --filter "label=com.docker.compose.project=$project" --filter "label=com.docker.compose.service=auth")
if [ -n "$auth" ]; then
  echo
  echo "auth settings (allow-listed, non-secret):"
  allow='^(API_EXTERNAL_URL|GOTRUE_(SITE_URL|URI_ALLOW_LIST|JWT_ISSUER|JWT_EXP|JWT_AUD|JWT_VALID_METHODS|JWT_ADMIN_ROLES|DISABLE_SIGNUP|EXTERNAL_[A-Z0-9_]+_ENABLED|MAILER_AUTOCONFIRM|MAILER_SECURE_EMAIL_CHANGE_ENABLED|MAILER_OTP_LENGTH|MAILER_OTP_EXP|MAILER_URLPATHS_[A-Z_]+|RATE_LIMIT_[A-Z_]+|SMTP_HOST|SMTP_PORT|SMTP_ADMIN_EMAIL|SMTP_SENDER_NAME|SMTP_MAX_FREQUENCY|SMS_AUTOCONFIRM|MFA_[A-Z_]+|HOOK_BEFORE_USER_CREATED_ENABLED|HOOK_BEFORE_USER_CREATED_URI|SECURITY_REFRESH_TOKEN_ROTATION_ENABLED|SECURITY_REFRESH_TOKEN_REUSE_INTERVAL|SECURITY_MANUAL_LINKING_ENABLED))='
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$auth" | grep -E "$allow" | sort | sed 's/^/  /'
fi

echo
echo "raw-table rules for published loopback ports:"
ports=$(for id in $containers; do docker port "$id"; done | sed -n 's/.*127\.0\.0\.1:\([0-9]*\)$/\1/p' | sort -u)
if [ -n "$ports" ]; then
  pattern=$(echo "$ports" | paste -sd'|')
  sudo -n iptables -t raw -S PREROUTING | grep -E -- "--dport ($pattern)( |$)" | sed 's/^/  /' || echo "  none found"
fi
echo
echo "published ports:"
for id in $containers; do docker port "$id" | sed "s|^|  $(docker inspect --format '{{.Name}}' "$id") |"; done
