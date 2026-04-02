### b2r_custom

This is a custom ERP for B2R

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch main
bench install-app b2r_custom
```

### Deployment Notes

After pulling the branch into your bench, run:

```bash
bench --site [sitename] migrate
bench --site [sitename] export-fixtures
```

For Docker deployments, the equivalent bench command inside the backend container is:

```bash
docker compose -f pwd.yml exec backend bench --site frontend migrate
```

If you want `billing_mode` to populate an Accounting Dimension field automatically, set `b2r_billing_dimension_field` in `site_config.json` to the target fieldname.

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/b2r_custom
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade
### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit
