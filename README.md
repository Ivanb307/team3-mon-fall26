# NYC Active

The team's Django project. Feature branches should start from `develop` and
return through a pull request. `main` is the stable branch.

## Local development

Use Python 3.12. Create a virtual environment, activate it, then install and run:

```sh
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/. `config/settings.py` remains the local development
configuration. The temporary home page only verifies the application runs;
the frontend team can replace it. `/health/` checks the process, and `/ready/`
checks database connectivity. Run `python manage.py test` for deployment tests.

## AWS

The existing single-instance Elastic Beanstalk test environment uses
`config.production`, which extends the team's settings. See
[deployment instructions](docs/deployment.md) for environment variables,
packaging, and the limitations of the temporary HTTP check.

Deployment is manual. Pushing or merging GitHub branches does not update AWS.
This project uses Django 5.2 LTS because Django 4.2 support ended in April 2026.

The HTTPS deployment-check URL is https://dgaeptdmd25z5.cloudfront.net/.
CloudFront supplies the browser-facing certificate and redirects HTTP to HTTPS.
Its connection to the existing Beanstalk instance currently uses HTTP; the
check still exposes no account routes. See the deployment guide before adding
real user data or authentication.
