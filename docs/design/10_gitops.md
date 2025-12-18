# GitOps workflow

## Storage format

Use simple, reviewable files:

- `parts/<name>.yaml` (metadata + template text)
- `plays/<name>.yaml` (metadata + ordered steps)
- `providers/<name>.yaml` (metadata + secret references, not secret values)

## Import (Git → Nautobot)

- Pull repo
- Validate schemas
- Upsert Tasks/Workflows/ProviderConfigs
- Record last commit imported and errors

## Export (Nautobot → Git)

- Serialize current Part/Play definitions to files
- Commit with meaningful message
- Optional: open a PR (future)

Key requirement: **secrets never exported**; only references to Nautobot SecretsGroup/Secrets are exported.
