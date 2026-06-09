# Contributing to Automated Actions

Thank you for contributing. This app follows standard Frappe development practices so it is easy to review, test, and maintain.

## Before You Start

- Search existing issues and pull requests before opening a new one
- Keep each issue focused on one bug, feature, or documentation change
- For questions or implementation discussions, prefer the relevant GitHub issue before opening a large pull request

## Development Setup

1. Create or use an existing Frappe Bench with Frappe v15.
2. Get the app into your bench:

```bash
cd /path/to/frappe-bench
bench get-app https://github.com/kodlyft/automated_action --branch version-15
bench --site your-site.localhost install-app automated_actions
```

3. Install development hooks:

```bash
cd apps/automated_actions
pre-commit install
```

## Project Standards

- Follow existing Frappe and ERPNext coding patterns where possible
- Keep changes small and focused
- Put business logic on the server side
- Avoid unrelated refactors in feature or bug-fix pull requests
- Update documentation when behavior or setup changes

## Code Quality

Pre-commit is configured for repository checks. Run it before pushing:

```bash
cd apps/automated_actions
pre-commit run --all-files
```

This repository uses:

- Ruff for Python linting and formatting
- ESLint for JavaScript linting
- Prettier for frontend formatting
- Standard Frappe CI workflows for validation

## Tests

Run automated tests from the bench root:

```bash
cd /path/to/frappe-bench
bench --site your-site.localhost run-tests --app automated_actions
```

If your change affects document events, scheduler logic, or automation execution, include or update tests accordingly.

## Pull Request Guidelines

- Target the active maintenance branch, typically `version-15`
- Use a clear title describing the change
- Explain the problem being solved and the chosen approach
- Include screenshots or recordings for UI changes
- Mention any migration, scheduler, or configuration impact
- Link the related issue using `Closes #123` when applicable
- Make sure CI passes before requesting review

## Reporting Bugs

Good bug reports include:

- Steps to reproduce
- Expected behavior
- Actual behavior
- Relevant error logs or tracebacks
- Output of `bench version`
- Whether the issue is reproducible on a clean site

## Suggesting Features

When proposing a feature, describe:

- The problem or workflow gap
- The expected user behavior
- Any alternative approaches considered
- Whether the change is specific to this app or should follow broader Frappe patterns

## Security Issues

Please do not report security vulnerabilities through public issues. Follow the process in SECURITY.md.