# Releasing

## Version policy

The single source of truth is `term_mcp_deepseek/_version.py`. The CLI, `/health`, `/mcp/info`, wheel metadata, tag, and release title must all match it.

Use semantic versioning:

- patch: compatible fixes and documentation;
- minor: compatible tools, policy, UI, or protocol capabilities;
- major: incompatible CLI, receipt, policy, or protocol behavior.

## Pre-release checklist

1. Update `_version.py` and `CHANGELOG.md`.
2. Run `./local_ci.sh`.
3. Run `./scripts/release_check.sh` from a clean worktree.
4. Confirm the wheel contains static UI and receipt schema assets.
5. Test the generated wheel, not the current editable checkout.
6. Build and health-check the Docker image.
7. Confirm the MCP compatibility document has current dates and versions.
8. Commit and push `main`; wait for CI and security workflows to pass.

## Tag and publish

```bash
VERSION="$(python3 -c 'from term_mcp_deepseek._version import VERSION; print(VERSION)')"
git tag -s "v${VERSION}" -m "term-mcp-deepseek ${VERSION}"
git push origin "v${VERSION}"
```

The release workflow fails if tag, package, and CLI versions differ. It rebuilds from the tag, validates artifacts with Twine, installs the wheel in a clean environment, generates checksums and provenance, and creates the GitHub release. Uploads are bounded and file-by-file; a failed draft can be resumed with the manual workflow input for the same tag. Rerunning a complete public release verifies its required assets without replacing them.

Publishing to PyPI is intentionally separate and requires a protected trusted-publisher environment. A GitHub release or local dry-run is not evidence of a PyPI publication.

## Rollback

1. Do not move or overwrite the published tag.
2. Mark the affected GitHub release clearly and describe the impact.
3. Reinstall the previous wheel or image digest.
4. Publish a new patch version containing the fix or revert.
5. Keep historical receipts and schemas unchanged.

Never delete a release merely to hide a regression; preserve evidence and provide an explicit superseding version.
