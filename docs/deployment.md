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
| `DJANGO_HTTPS` | `True` |
| `DJANGO_TLS_DOMAIN` | Exact existing Beanstalk hostname |

This mode exposes Derah's landing page at `/`, plus `/health/` and `/ready/`.
It deliberately excludes admin and account routes while the authentication
backend is being integrated. The login/sign-up templates are present, but their
views are not implemented yet; `/login/` and `/register/` return 404 for now.
The landing page's event board and testimonials are frontend sample content,
not live events or verified user reviews. SQLite is only
for infrastructure verification, not real user data; instance replacement can
lose this data. `/ready/` validates SQLite, not PostgreSQL or RDS.

For real application testing, keep `DJANGO_HTTPS=True`, set
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
5. Wait for Ready/Green and confirm `/`, `/health/`, `/ready/` return 200 over HTTPS.
   Confirm the landing page and its hashed CSS, JS and images load. Confirm
   `/admin/`, `/login/`, `/register/` and `/accounts/login/` return 404 in check mode.

`Procfile` starts Gunicorn on port 8000. `.ebextensions/django.config` runs
migrations and collects static files, served by WhiteNoise. Health middleware
permits internal Host headers only on `/health/`; other URLs keep host checks.

The manual procedure remains available for recovery. Normal updates to the
central `develop` branch now use the workflow described below.

## Automatic develop deployment

`.github/workflows/deploy-develop.yml` runs on pushes and PRs targeting `develop`.
Every run checks dependencies, Django configuration and migrations, application
tests, infrastructure safety tests and shell hook syntax. Only a successful
**push to the central develop branch** can obtain AWS credentials and deploy.
Forks, feature branches, `main`, and unmerged PRs cannot publish to this environment.

AWS authentication uses GitHub OIDC and the `nyc-active-github-deploy` role.
There are no long-lived AWS keys in GitHub. The trust policy uses the immutable
organization/repository IDs reported by this repository's OIDC settings, plus
the exact `refs/heads/develop` subject and `sts.amazonaws.com` audience.
The policy/trust documents are in `infra/github-deploy-*.json`. Only the existing
team environment, its application versions, a dedicated prefix in the existing
source bucket, and read-only cost/pause checks are permitted. The separate
personal assignment is excluded. No account/admin credentials are passed to CI.

The deploy job is serialized and an active release is never cancelled by a new
push. An older queued commit skips deployment if develop has already advanced.
The script publishes an exact git archive as `gha-<run id>-<commit>`, excluding
workflow files, infrastructure tooling, local databases and credentials.
It changes only the existing environment's version label, retaining AllAtOnce
deployment on one instance and the existing environment variables.

Before publishing and throughout the deployment wait, the script checks the
project's $15 pre-credit budget, the distribution's enabled state, the expected
environment identity and its unpaused single-instance Auto Scaling group.
Missing cost data, a reached threshold, a disabled distribution or suspended
scaling stops publication. The workflow cannot intentionally resume the budget
guard's paused group or re-enable CloudFront. Billing remains delayed; these
checks do not turn the budget into an exact cap.

A successful run waits for Ready/Green, then checks the HTTPS homepage, its
referenced local static assets, `/health/` and `/ready/`. If release verification
fails and the environment is Ready and still passes the budget/pause checks,
the script attempts to restore the preceding application version. Database
migrations are not reversed by this operation; review backwards compatibility
when introducing schema changes. If the environment is busy or budget-stopped,
the workflow fails without forcing recovery.

Find progress and failures under GitHub **Actions → Test and deploy develop**.
After fixing a transient problem, use **Re-run jobs** on the existing run;
outdated commits are skipped. Fix failed tests through a new PR. If publication
must be suspended, disable this workflow in GitHub Actions; this does not stop
the currently running site or its usage charges. Automatic deployment does not
enable the still-unimplemented login/registration backend or provision a database.

## HTTPS test entry point

- URL: https://dgaeptdmd25z5.cloudfront.net/
- CloudFront distribution: `E1YOQE0SL33H2U`
- Origin: the same Beanstalk environment above; no additional EC2 or database
- Configuration template: `infra/cloudfront.json` (excluded from the app ZIP)

CloudFront uses its default trusted certificate for the assigned hostname and
redirects browser HTTP requests to HTTPS. The existing Beanstalk hostname also
supports direct HTTPS with its own trusted certificate. The CloudFront hostname
remains the shared frontend URL.

The managed CachingDisabled policy prevents stale deployment pages and health
checks. AllViewerExceptHostHeader forwards viewer query strings and cookies,
while setting Host to the Beanstalk origin hostname so Django's explicit host
allowlist remains valid. No WAF, access logs, Lambda@Edge, or paid subscription
was added.

Both network legs use HTTPS: browser to CloudFront, and CloudFront to the
Beanstalk instance. The CloudFront origin protocol is `https-only`, restricted
to TLS 1.2. The instance's Nginx accepts TLS 1.2/1.3 and overwrites
X-Forwarded-Proto with `https` before forwarding to Gunicorn on loopback port
8000. Django redirects ordinary HTTP application requests to HTTPS; internal
health probes and ACME HTTP-01 validation remain available on port 80.

The prebuild hook obtains a free Let's Encrypt certificate for DJANGO_TLS_DOMAIN
using HTTP-01. Keys stay in `/etc/letsencrypt/` on the instance; they are never
committed or uploaded in the application ZIP. The postdeploy hook installs a
systemd timer that checks renewal twice daily and reloads Nginx after renewal.
If no TLS domain is configured, these hooks do nothing. Instance replacement
will need fresh certificate issuance, subject to the certificate authority's
availability and limits. Maintain the same hostname and public DNS routing.

Keep the restricted deployment-check mode enabled while publishing the landing
page, until the team's authentication features and PostgreSQL database are ready.
The application's CSRF trusted origins must
include its chosen HTTPS frontend URL. HTTPS does not make the temporary SQLite
database suitable for real user data.

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
