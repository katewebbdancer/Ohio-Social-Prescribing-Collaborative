# Automating the Programs Directory

This repo now has a GitHub Action (`.github/workflows/update-directory.yml`)
that checks the [backend spreadsheet](https://docs.google.com/spreadsheets/d/1byn6F2Ktq-jdjUAV6RDp1LRMI73U5RxrNyY9v92jCcE/edit)
weekly (Mondays 9am ET) — and on demand via the Actions tab — for organizations
not yet on the live Programs Directory, and opens a **pull request** adding a
standardized card for each one.

**It opens a PR, not a direct push to main.** The existing cards on the site
are hand-written and curated — this script never touches them, and new cards
it drafts are deliberately simple so the asset-map lead can review, polish the
language, and merge (or edit first) rather than having auto-generated copy go
live unreviewed.

## One-time setup (you'll need to do this once)

1. **Create a Google Cloud service account** with read access to Google Sheets:
   - Go to [console.cloud.google.com](https://console.cloud.google.com), create
     (or reuse) a project, enable the **Google Sheets API**.
   - Under IAM & Admin → Service Accounts, create a new service account and
     generate a **JSON key** for it (downloads a `.json` file).
2. **Share the spreadsheet** with that service account's email address
   (looks like `something@your-project.iam.gserviceaccount.com`) — Viewer
   access is enough.
3. **Add two repo secrets** (Settings → Secrets and variables → Actions → New
   repository secret) on `katewebbdancer/ohio-social-prescribing-collaborative`:
   - `GOOGLE_CREDENTIALS_JSON` — paste the **entire contents** of the JSON key
     file downloaded in step 1.
   - `GOOGLE_SHEET_ID` — `1byn6F2Ktq-jdjUAV6RDp1LRMI73U5RxrNyY9v92jCcE` (already
     defaults to this if you skip the secret, but setting it explicitly is
     clearer).

Once those secrets exist, the workflow will run automatically on its weekly
schedule, or you can trigger it any time from the **Actions** tab → "Pull new
asset map listings into Programs Directory" → **Run workflow**.

## What it does and doesn't do

- ✅ Finds organizations in the 8 category tabs that aren't already mentioned
  anywhere in that category's section of `index.html`.
- ✅ Drafts a simple card (name, description, populations served, address,
  cost, transportation, accessibility, registration, website link) from the
  spreadsheet's columns.
- ✅ Opens a PR so nothing reaches the live site without a human looking at it
  first — GitHub Pages only redeploys when the PR is merged.
- ❌ Does not edit, reformat, or remove any existing card.
- ❌ Does not match the editorial voice/tags of hand-written cards — treat its
  drafts as a starting point, not final copy.
- ❌ Does not currently cover the Youngstown-specific sections (`cat-yo-*`) or
  the city-specific Referral Guide grid — those would need their own mapping
  if you want them automated too.
