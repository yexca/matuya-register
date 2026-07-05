# Documentation Overview

Matuya Register is a Flask-based admin tool for authorized registration workflow
testing. It separates the web UI, account persistence, target-site automation,
and mail retrieval so each part can be tested or replaced independently.

Use these documents as the maintained reference:

- [Getting Started](getting-started.md): local and Docker startup.
- [Configuration](configuration.md): environment variables and mail providers.
- [Architecture](architecture.md): modules, data flow, and task lifecycle.
- [API Reference](api-reference.md): admin JSON endpoints.
- [Development Guide](development-guide.md): code conventions and extension points.
- [Operations](operations.md): deployment, backups, and troubleshooting.

## Safety Boundary

This project must only be used in environments where you have explicit
authorization. Do not use real service URLs, credentials, personal accounts, or
production data in examples, tests, issues, commits, or documentation.

All examples in this documentation are intentionally fake.
