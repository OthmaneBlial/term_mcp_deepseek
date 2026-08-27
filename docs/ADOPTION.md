# Adoption without product telemetry

Term MCP DeepSeek sends no product analytics, command data, workspace data, receipts, or identifiers to the maintainer. DeepSeek traffic exists only when an operator explicitly configures the optional model feature.

The project measures whether it is useful through repository-level evidence:

| Funnel stage | Observable signal | Source | Interpretation |
| --- | --- | --- | --- |
| Visit | Repository views | Maintainer-only GitHub Traffic, reviewed in aggregate | Discovery only; never treated as activation |
| Clone/install | Unique cloners and clean-package CI | GitHub Traffic and the public `Clean wheel and source archive` job | Interest plus a reproducible install path |
| First result | CI health/demo checks and `onboarding` issues | CI and the setup issue template | Whether documented startup works; no silent client event |
| Return | Repeat visitors/cloners, when GitHub exposes them | Maintainer-only GitHub Traffic | Weak retention proxy, not user identity |
| Reuse | `example reuse` issue reports and accepted recipe PRs | Public, opt-in community reports | Concrete evidence that examples transfer to other repositories |
| Contribution | Contributors and merged PRs | GitHub history and generated release notes | Strongest public adoption signal |
| Distribution | Release asset download counts | GitHub Releases API | Package interest; duplicate downloads are possible |

Stars and forks are displayed by GitHub but remain secondary. The success criterion is that a visitor can clone, obtain a bounded first result, return with a real workflow, and contribute a recipe or regression test.

## Public snapshot

Run the read-only snapshot helper from the repository root:

```bash
python3 scripts/adoption_snapshot.py OthmaneBlial/term_mcp_deepseek
```

It reads public GitHub API data and local example counts. `GITHUB_TOKEN` is optional and only increases the API rate limit. The report includes source URLs and uses `null` when a source is unavailable; it never invents a zero. No data is written or transmitted beyond the GitHub API requests needed to read repository facts.

Review the snapshot at each release and mention only changes supported by evidence. Do not publish private Traffic numbers without deciding that aggregate disclosure is appropriate.
