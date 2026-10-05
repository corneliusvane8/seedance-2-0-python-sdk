# Validation checklist

Before publishing a change, run the checks from the repository root:

```bash
python -m py_compile seedance_api.py mcp_server.py
python -m unittest discover -s tests -v
bash -n examples/submit-text.sh examples/submit-reference.sh examples/upload-and-submit.sh examples/poll-and-download.sh
```

Then perform a public-boundary scan. Keep any retired-brand denylist outside the public repository:

```bash
rg -n 'Bearer [^$`{[:space:]]|ARGOLINK_API_KEY=[^$`{[:space:]]|sk-[A-Za-z0-9]' . --glob '!SECURITY.md'
```

The scan should find only variable names and explanatory security text, never a real credential. A live smoke test should use a disposable key and a short prompt; it is intentionally not part of the offline test suite.
