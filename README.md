# ⚰️ Bug Graveyard

> *Every bug deserves a proper burial.*

A GitHub Pages site where Claude AI automatically writes humorous epitaphs for every closed issue, rendered as gothic gravestones in an atmospheric dark-green cemetery.

**Live site:** `https://<your-username>.github.io/bug-graveyard/`

---

## How it works

1. An issue is closed in a repository.
2. The `epitaph.yml` workflow fires, sends the issue details to Claude claude-haiku-4-5-20251001.
3. Claude writes a creative Chinese-language epitaph with a poetic alias, dates, body text, and a closing maxim.
4. The bot prepends the result to `epitaphs/epitaphs.json` and commits it.
5. GitHub Pages re-deploys; the new gravestone appears on the site.

---

## Setup — standalone (issues in *this* repo)

1. **Fork or use this repo** as your graveyard repository.
2. Add your Anthropic API key as a repository secret:
   - `Settings → Secrets and variables → Actions → New repository secret`
   - Name: `ANTHROPIC_API_KEY`
3. Enable GitHub Pages:
   - `Settings → Pages → Source: Deploy from a branch → Branch: main / root`
4. The workflow is already at `.github/workflows/epitaph.yml`. Close any issue to test.

---

## Setup — cross-repo (bury bugs from your *other* repos)

To have bugs from another repository trigger epitaphs here, use a **repository dispatch** or a workflow in the source repo that calls this one.

### Option A — workflow in the source repo

Add `.github/workflows/notify-graveyard.yml` to any other repo:

```yaml
name: Notify Bug Graveyard on issue close

on:
  issues:
    types: [closed]

jobs:
  dispatch:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger graveyard workflow
        uses: peter-evans/repository-dispatch@v3
        with:
          token: ${{ secrets.GRAVEYARD_PAT }}
          repository: YOUR_USERNAME/bug-graveyard
          event-type: external-issue-closed
          client-payload: |
            {
              "title":      "${{ github.event.issue.title }}",
              "body":       "${{ github.event.issue.body }}",
              "number":     "${{ github.event.issue.number }}",
              "url":        "${{ github.event.issue.html_url }}",
              "labels":     "${{ join(github.event.issue.labels.*.name, ',') }}",
              "created_at": "${{ github.event.issue.created_at }}",
              "closed_at":  "${{ github.event.issue.closed_at }}"
            }
```

Then add a `repository_dispatch` trigger to `epitaph.yml` and read from `github.event.client_payload`.

> **Required secret:** `GRAVEYARD_PAT` — a Personal Access Token with `repo` scope, added to the *source* repo's secrets.

### Option B — GitHub App webhook

Point a GitHub App webhook at a small relay server (e.g., a free Vercel function) that calls the `workflow_dispatch` endpoint of this repo via the GitHub API whenever an issue is closed in any subscribed repo.

---

## Testing with `workflow_dispatch`

The workflow supports manual runs with custom inputs so you can test without closing a real issue:

1. Go to `Actions → Write Bug Epitaph → Run workflow`.
2. Fill in **Issue title**, **Issue body**, **Issue number**, **Labels**.
3. Watch the epitaph appear on the graveyard page within a minute.

---

## Configuration

| File | Purpose |
|------|---------|
| `.github/workflows/epitaph.yml` | Workflow — triggers, Claude call, JSON update, commit |
| `epitaphs/epitaphs.json` | Persistent store of all epitaphs (max 100) |
| `index.html` | The graveyard page — self-contained, no build step |
| `.nojekyll` | Tells GitHub Pages to skip Jekyll processing |

**Model:** `claude-haiku-4-5-20251001` (fast and cheap; swap to `claude-sonnet-4-5` for more elaborate prose).

**Max stored epitaphs:** 100 (oldest are dropped). Change the slice in the workflow Python script.

---

## Local preview

```bash
python3 -m http.server 8080
# open http://localhost:8080
```

No build step, no Node.js. Pure HTML/CSS/JS.

---

*"In the long run, every bug is mortal."*
