# mdcmd GitHub Action

Run [`mdcmd`](https://github.com/runsascoded/mdcmd) to update Markdown files and verify they are up-to-date in CI.

## Usage

```yaml
- uses: runsascoded/mdcmd@v1
```

### With options

```yaml
- uses: runsascoded/mdcmd@v1
  with:
    version: '0.7.4'        # Pin to specific version
    files: 'README.md docs/API.md'  # Process multiple files
    run-mktoc: true         # Force mktoc (auto-detects by default)
    fail-on-diff: true      # Fail if files changed (default)
```

## Inputs

| Input | Description | Default |
|-------|-------------|---------|
| `version` | mdcmd version to install | latest |
| `files` | Space-separated files to process | `README.md` |
| `run-mktoc` | Run mktoc for TOC generation | auto-detect* |
| `fail-on-diff` | Fail if changes detected | `true` |

\* Auto-detects if files contain `<!-- \`toc\` -->` marker

## Example workflow

```yaml
name: Check README
on: [push, pull_request]

jobs:
  check-readme:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: runsascoded/mdcmd@v1
```

## What it does

1. Installs `mdcmd` via `uv tool install`
2. Runs `mdcmd` on specified files to execute embedded commands
3. Optionally runs `mktoc` if TOC markers are detected
4. Fails if any files were modified (indicating README is out of date)
