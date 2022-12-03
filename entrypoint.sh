#!/usr/bin/env sh

set -eu

if [ -n "${RULES_FILE:-}" ] && [ -e "$RULES_FILE" ]
then
    rules="$(cat "$RULES_FILE")"
elif [ -n "${RULES:-}" ]
then
    rules="$RULES"
else
    echo "No rules given! Use either RULES_FILE or RULES env vars." >&2
    exit 1
fi

if [ -n "${UPSTREAM_DNS:-}" ]
then
    upstream_dns="$UPSTREAM_DNS"
else
    resolvconf_servers="$(grep '^nameserver' /etc/resolv.conf | cut -d' ' -f2)"
    if [ -n "$resolvconf_servers" ]
    then
        upstream_dns="$(echo "$resolvconf_servers" | paste -sd ' ')"
    else
        echo "No upstream DNS servers detected! Use UPSTREAM_DNS or make sure /etc/resolv.conf contains nameserver entries."
        exit 2
    fi

fi
healthcheck_domain="${HEALTHCHECK_DOMAIN:-.}"
ttl="${OVERRIDE_TTL:-5}"

transformer='map("    rewrite continue {\n        ttl regex " + .from + " " + strenv(TTL) + "\n    }\n    rewrite stop {\n        name regex " + .from + " " + .to + "\n        answer auto\n    }") | .[]'
#transformer='to_entries | map("    rewrite stop name regex " + .key + " " + .value + " answer auto") | .[]'
coredns_rules="$(echo "$rules" | TTL="$ttl" yq -r "$transformer")"
corefile="/Corefile"
catchall_domain='localhost'

cat <<EOF > "$corefile"
.:53 {
    log
    health
$coredns_rules
    rewrite stop name regex .* $catchall_domain
    forward . $upstream_dns {
        except $catchall_domain
        health_check 30s domain $healthcheck_domain
    }
}
EOF

cat "$corefile"
exec coredns -conf "$corefile"