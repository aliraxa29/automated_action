<div align="center">

# Automated Actions

**No-code workflow automation for the [Frappe Framework](https://frappeframework.com)**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Frappe](https://img.shields.io/badge/Frappe-v15-blue.svg)](https://frappeframework.com)

</div>

---

## Overview

**Automated Actions** lets you create powerful automation rules that trigger when documents are created, updated, deleted, or at scheduled intervals — all without writing code.

Define conditions, pick an action, and let the app handle the rest.

### Key Features

- **Event-driven triggers** — Fire rules on Create, Update, Delete, or any combination
- **Time-based triggers** — Schedule actions relative to a date field (e.g., 7 days after creation)
- **Conditional execution** — Filter on before/after document state using Frappe-style JSON filters
- **Field-level tracking** — Trigger only when specific fields change
- **Six built-in actions:**
  - Update Record — Set field values on the current document
  - Create Record — Auto-create linked documents
  - Execute Python Code — Run sandboxed Python with Jinja2 templating
  - Send Email — Send templated emails to document owner or custom fields
  - Create ToDo — Generate tasks and assign to users
  - Add Comment — Post audit-trail comments
- **Test Run** — Preview matching documents before enabling a rule
- **Security** — Sandboxed Python execution with blocked dangerous patterns, recursion prevention

## Requirements

- Python 3.10+
- [Frappe Framework](https://frappeframework.com) v15+

## Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/kodlyft/automated_action --branch version-15
bench --site your-site.localhost install-app automated_actions
```

## Usage

1. Navigate to **Automated Action** list in the Frappe desk
2. Click **+ Add Automated Action**
3. Select a **Document Type** (e.g., Sales Order, ToDo, etc.)
4. Choose a **Trigger** — when should this rule fire?
5. Define **Conditions** (optional) — JSON filters on old/new document values
6. Pick an **Action Type** and configure it
7. Save and enable the rule

### Example: Auto-close stale tasks

| Setting | Value |
|---|---|
| Document Type | `ToDo` |
| Trigger | `Based on Time Condition` |
| Trigger Date Field | `creation` |
| Delay | `30 Days` |
| Condition | `[["status", "=", "Open"]]` |
| Action Type | `Update Record` |
| Field Update | `status` → `Closed` |

### Condition Syntax

Conditions use Frappe-style JSON filter arrays:

```json
[["status", "=", "Open"], ["grand_total", ">", 1000], ["customer_name", "like", "%Corp%"]]
```

Supported operators: `=`, `!=`, `>`, `<`, `>=`, `<=`, `like`, `not like`, `in`, `not in`, `is`

### Template Variables

Field values support Jinja2 templates:

| Variable | Description |
|---|---|
| `{doc.fieldname}` | Any field on the current document |
| `{today}` | Current date |
| `{now}` | Current datetime |

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- Setting up a development environment
- Code style and linting
- Submitting pull requests
- Reporting bugs

## Development Setup

1. Set up a Frappe bench (see [Frappe docs](https://frappeframework.com/docs/user/en/installation))
2. Install the app in development mode:
   ```bash
   bench get-app https://github.com/kodlyft/automated_action --branch version-15
   bench --site your-site.localhost install-app automated_actions
   ```
3. Enable pre-commit hooks:
   ```bash
   cd apps/automated_actions
   pre-commit install
   ```

### Code Quality Tools

This project uses the following tools (enforced via pre-commit):

| Tool | Purpose |
|---|---|
| [ruff](https://github.com/astral-sh/ruff) | Python linting & formatting |
| [eslint](https://eslint.org/) | JavaScript linting |
| [prettier](https://prettier.io/) | JavaScript/JSON formatting |
| [pyupgrade](https://github.com/asottile/pyupgrade) | Python syntax modernization |

### Running Tests

```bash
cd $PATH_TO_YOUR_BENCH
bench --site your-site.localhost run-tests --app automated_actions
```

## CI/CD

GitHub Actions workflows are configured:

| Workflow | Trigger | Description |
|---|---|---|
| **Server Tests** | Push to `develop` and `version-15`, PRs | Installs app, runs unit tests (MariaDB, Redis, Python 3.10, Node 18) |
| **Pre-commit** | Pull requests | Runs repository formatting and lint hooks exactly as contributors run them locally |
| **Linters** | Pull requests | [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) |
| **Semantic Commits** | Pull requests | Validates commit messages for release automation |
| **Generate Semantic Release** | Push to `version-15` | Publishes releases using semantic-release |

## Security

If you discover a security vulnerability, please report it responsibly. See [SECURITY.md](SECURITY.md) for details.

## License

This project is licensed under the [MIT License](license.txt).

Copyright © 2026 Kodlyft
