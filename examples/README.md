# Examples

All examples expect:

```bash
export ARGOLINK_API_KEY='your-key'
```

They use `https://api.argolink.io` unless `ARGOLINK_BASE_URL` is set. Install `jq` first. A submit prints a `request_id`; pass that ID to `poll-and-download.sh`.

- `submit-text.sh`: prompt-only generation.
- `submit-reference.sh`: image/video/audio references from HTTPS URLs.
- `upload-and-submit.sh`: upload one local asset, then submit it as a reference.
- `poll-and-download.sh`: bounded polling followed by atomic download.

The scripts do not retry submit requests. This prevents an uncertain network response from creating a duplicate job. They also avoid printing bearer tokens and signed upload URLs.
