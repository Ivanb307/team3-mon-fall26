# AWS deployment

This deployment extends Rae's Django project from the team `develop` branch.
It does not introduce a second Django project or a separate core app.

## Existing test environment

- Region: `us-east-1`
- Elastic Beanstalk application: `nyc-active`
- Environment: `nyc-active-demo-287872994760`
- Platform: Amazon Linux 2023, Python 3.12
- One `t3.micro` instance, 8 GiB gp3 root disk
- No load balancer, RDS instance, or NAT gateway for this check

The running instance uses standard CPU credits to avoid surplus CPU charges.
Recheck that setting if Elastic Beanstalk replaces the instance. Compute,
storage, and public IPv4 still consume AWS credits while running.

## Environment variables

Configure these through AWS environment properties, never committed files:

| Variable | Temporary deployment check |
| --- | --- |
| `DJANGO_SETTINGS_MODULE` | `config.production` |
| `DJANGO_SECRET_KEY` | Random private value stored in AWS |
| `DJANGO_ALLOWED_HOSTS` | Exact environment hostname, optionally localhost |
| `DJANGO_DEPLOYMENT_CHECK_ONLY` | `True` |
| `DJANGO_DATABASE_PATH` | `/var/app/data/db.sqlite3` |
| `DJANGO_HTTPS` | `False` |

This mode exposes only `/`, `/health/`, and `/ready/`. It deliberately excludes
admin and account routes while the environment has only HTTP. SQLite is only
for infrastructure verification, not real user data; instance replacement can
lose this data. `/ready/` validates SQLite, not PostgreSQL or RDS.

For real application testing, configure HTTPS, set `DJANGO_HTTPS=True` and
`DJANGO_DEPLOYMENT_CHECK_ONLY=False`, and provide `DB_HOST`, `DB_NAME`,
`DB_USER`, `DB_PASSWORD`, optionally `DB_PORT` (default 5432).
PostgreSQL connections require TLS. Set `DJANGO_CSRF_TRUSTED_ORIGINS` to any
needed HTTPS origins, comma separated. Missing database configuration fails
startup rather than silently using SQLite.

## Manual release

1. Test the intended commit: `python manage.py test` and `python manage.py check`.
2. Commit changes. Create a `dist` directory if necessary, then package that
   exact commit with `git archive --format=zip --output=dist/nyc-active.zip HEAD`.
3. Create an Elastic Beanstalk application version using the ZIP. Project files
   must be at the archive root. Do not include `.env`, virtual environments,
   local databases, or credentials.
4. Deploy that version to the **existing** test environment. When moving from
   the old skeleton, update `DJANGO_SETTINGS_MODULE` from
   `config.settings.production` to `config.production` in the same update.
5. Wait for Ready/Green and confirm `/`, `/health/`, `/ready/` return HTTP 200.
   Confirm `/admin/` and `/accounts/login/` return 404 in check mode.

`Procfile` starts Gunicorn on port 8000. `.ebextensions/django.config` runs
migrations and collects static files, served by WhiteNoise. Health middleware
permits internal Host headers only on `/health/`; other URLs keep host checks.

No GitHub Actions or CodePipeline auto-deployment is configured. GitHub changes
do not alter the running version until explicitly deployed. A release can later
come from `develop` after review, using these same deployment settings.

## HTTPS test entry point

- URL: https://dgaeptdmd25z5.cloudfront.net/
- CloudFront distribution: `E1YOQE0SL33H2U`
- Origin: the same Beanstalk environment above; no additional EC2 or database
- Configuration template: `infra/cloudfront.json` (excluded from the app ZIP)

CloudFront uses its default trusted certificate for the assigned hostname and
redirects browser HTTP requests to HTTPS. The original `elasticbeanstalk.com`
hostname is still HTTP-only; adding `https://` to that hostname does not select
the CloudFront distribution.

The managed CachingDisabled policy prevents stale deployment pages and health
checks. AllViewerExceptHostHeader forwards viewer query strings and cookies,
while setting Host to the Beanstalk origin hostname so Django's explicit host
allowlist remains valid. No WAF, access logs, Lambda@Edge, or paid subscription
was added.

This check encrypts **browser to CloudFront** traffic. **CloudFront to Beanstalk
still uses HTTP**, so this is not end-to-end TLS. Keep deployment-check mode
enabled and do not expose account routes or real user data until origin HTTPS
and trusted proxy forwarding are configured. Do not just set DJANGO_HTTPS=True
behind the current HTTP origin; that can cause redirect loops. The future
application's CSRF trusted origins must include its chosen HTTPS frontend URL.

The distribution uses pay-as-you-go pricing with CloudFront's applicable free
usage allowance; it is not subscribed to a flat-rate plan. AWS Free Tier accounts
are not eligible for CloudFront flat-rate plans. Existing EC2, disk and IPv4
charges continue. Relevant official documentation:

- https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-https-viewers-to-cloudfront.html
- https://aws.amazon.com/cloudfront/pricing/pay-as-you-go/
- https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/flat-rate-pricing-plan.html

For recreation, copy the JSON template outside the source tree, replace the
origin placeholder with the existing environment hostname, and choose a unique
CallerReference. Review the account and existing distributions before calling
`aws cloudfront create-distribution --distribution-config file://<file>`.
Updating the existing distribution uses its current ETag and
`aws cloudfront update-distribution`, not a second distribution.
