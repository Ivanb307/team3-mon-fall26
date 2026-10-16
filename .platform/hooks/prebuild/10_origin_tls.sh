#!/bin/bash
set -euo pipefail

tls_domain="$(/opt/elasticbeanstalk/bin/get-config environment -k DJANGO_TLS_DOMAIN 2>/dev/null || true)"
if [ -z "$tls_domain" ]; then
    exit 0
fi
if ! [[ "$tls_domain" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]+$ ]]; then
    echo "DJANGO_TLS_DOMAIN must be a DNS hostname" >&2
    exit 1
fi

install -d -m 755 /var/www/nyc-active-acme
if [ ! -x /opt/nyc-active-certbot/bin/certbot ]; then
    python3.12 -m venv /opt/nyc-active-certbot
    /opt/nyc-active-certbot/bin/python -m pip install --disable-pip-version-check certbot==5.8.0
fi

if systemctl is-active --quiet nginx; then
    # Enable HTTP-01 on the currently running server before the new proxy deploys.
    install -m 644 .platform/nginx/conf.d/elasticbeanstalk/05_acme.conf /etc/nginx/conf.d/elasticbeanstalk/05_acme.conf
    nginx -t
    systemctl reload nginx
    authenticator=(--webroot --webroot-path /var/www/nyc-active-acme)
else
    authenticator=(--standalone)
fi
/opt/nyc-active-certbot/bin/certbot certonly "${authenticator[@]}" \
    --domain "$tls_domain" --cert-name nyc-active-origin --non-interactive \
    --agree-tos --register-unsafely-without-email --keep-until-expiring

install -d -m 755 .platform/nginx/conf.d
sed "s/__TLS_DOMAIN__/$tls_domain/g" .platform/nginx/https.conf.template > .platform/nginx/conf.d/https.conf
