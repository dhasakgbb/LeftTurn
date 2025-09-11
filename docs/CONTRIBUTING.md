# Contributing & Commit Messages

GitHub shows the last commit message next to each folder. To keep the repo’s folder “descriptions” readable, prefer small, scoped commits that touch a single top‑level folder with a descriptive message.

## Commit message style

Format: `<scope>: <concise description>`

Examples:
- `infra: add RLS template and notes`
- `fabric/sql: seed contract tables and views`
- `notebooks: DI extractor writes RateCard/Surcharge`
- `src/agents: evidence-first citations include file/page`

Keep messages to <72 chars; use body for details if needed.

## Helper: split commits by folder

If you modified multiple folders but want clean folder descriptions on GitHub, you can split commits per folder using the helper below.

```bash
bash tools/commit_folder_descriptions.sh \
  \
  "docs: update integration guide" \
  "fabric/sql: add RLS policy" \
  "infra: tweak bicep outputs" \
  "src: refine orchestrator citations"
```

The script commits each folder with the provided message, in order, if there are staged changes within that folder. Review the script before use; it only runs `git add`/`git commit`.

