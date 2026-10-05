# Security policy

## Credentials

Use `ARGOLINK_API_KEY` through the process environment or a local ignored secret manager. Never place a key in source, examples, issue reports, MCP arguments, CI logs, or a committed `.env` file.

Signed upload URLs and generated media URLs are bearer capabilities. Treat them as secrets, do not log them, and delete temporary files after processing.

## Reporting

If you find a credential leak or a request-signing problem, stop using the affected key, rotate it in Argolink, and open a private security report with the smallest reproducible description. Do not include the key or private response bodies.

## Scope

This repository contains a client and documentation. It does not store customer data, proxy credentials, production configuration, or server-side secrets.
