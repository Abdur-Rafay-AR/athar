# Security Policy

## Local-First Security & Privacy Model

Athar is engineered from the ground up as a **local-first** developer tool:

- **Zero Cloud Egress**: Athar does not send prompts, model completions, tool arguments, or trace data to any external server or cloud service.
- **Local SQLite Persistence**: All traces are stored locally on your filesystem (default: `agent_traces.db`) under your control.
- **No Telemetry**: Athar does not collect analytics, usage metrics, or system fingerprints.
- **Bound to Localhost by Default**: The Athar UI server binds exclusively to `127.0.0.1` unless explicitly instructed via `--host 0.0.0.0`.

---

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.3.x   | :white_check_mark: |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

---

## Reporting a Vulnerability

If you discover a security vulnerability in Athar, please do **NOT** open a public issue.

Instead, please report security concerns responsibly by contacting the maintainer via:
- **Email**: `abdurrafay.ar.dev@gmail.com` (or through the GitHub Security Advisories tab on the repository).

Please include:
1. A description of the issue and potential impact.
2. Steps to reproduce or a minimal proof-of-concept.
3. Any suggested mitigation.

We will acknowledge receipt within 48 hours and work with you on a coordinated disclosure and fix.
