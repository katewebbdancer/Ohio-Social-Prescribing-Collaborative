#!/usr/bin/env python3
"""
Pulls new asset-map listings from the OSPC backend Google Sheet and appends a
standardized resource-card to the matching category section of index.html.

This does NOT touch or reformat any existing card — every card already on the
site was hand-written/curated, and this script only ever *adds* a new card for
an organization name it doesn't already find inside that category's section.
A human (the asset-map lead) should still review and polish new cards before
merging — that's why this runs via a pull request, not a direct push to main.

Env vars required:
  GOOGLE_CREDENTIALS_JSON  - full JSON (as a string) for a Google service
                             account that has been given view access to the
                             spreadsheet below.
  GOOGLE_SHEET_ID          - defaults to OSPC's backend data map if unset.
"""
import html
import json
import os
import re
import sys

from google.oauth2 import service_account
from googleapiclient.discovery import build

SHEET_ID = os.environ.get(
    "GOOGLE_SHEET_ID", "1byn6F2Ktq-jdjUAV6RDp1LRMI73U5RxrNyY9v92jCcE"
)
INDEX_HTML = os.path.join(os.path.dirname(__file__), "..", "index.html")

# Statewide category tab -> cat-section id in index.html.
# (The "cat-yo-*" sections are Youngstown-region-specific and intentionally
# left alone here.)
CATEGORY_TO_SECTION_ID = {
    "Arts & Culture": "cat-arts",
    "Movement": "cat-movement",
    "Nature & Green Space": "cat-nature",
    "Social Connection": "cat-belonging",
    "Essential Services": "cat-sdoh",
    "Volunteering": "cat-service",
    "Active Arts Prescribing": "cat-active-arts",
    "SP-Adjacent Healthcare": "cat-healthcare",
}

COLUMNS = [
    "org_name", "category", "region", "in_referral_guide", "description",
    "populations", "register", "cost", "accessibility", "transportation",
    "website", "address",
]


def get_sheets_service():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        print("GOOGLE_CREDENTIALS_JSON is not set — nothing to do.", file=sys.stderr)
        sys.exit(0)
    info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    return build("sheets", "v4", credentials=creds)


def read_tab(service, tab_name):
    resp = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=SHEET_ID, range=f"'{tab_name}'!A2:L")
        .execute()
    )
    rows = resp.get("values", [])
    out = []
    for row in rows:
        row = row + [""] * (len(COLUMNS) - len(row))
        out.append(dict(zip(COLUMNS, row)))
    return out


def esc(text):
    return html.escape(text or "", quote=False)


def build_card(row):
    name = esc(row["org_name"])
    desc = esc(row["description"])
    details = []
    if row["populations"]:
        details.append(f"<strong>Populations Served:</strong> {esc(row['populations'])}")
    if row["address"]:
        details.append(f"<strong>Address:</strong> {esc(row['address'])}")
    if row["cost"]:
        details.append(f"<strong>Cost:</strong> {esc(row['cost'])}")
    if row["transportation"] and row["transportation"].lower() not in ("not specified", "not applicable"):
        details.append(f"<strong>Transportation:</strong> {esc(row['transportation'])}")
    if row["accessibility"] and row["accessibility"].lower() not in ("not specified", "not applicable"):
        details.append(f"<strong>Accessibility:</strong> {esc(row['accessibility'])}")
    if row["register"]:
        details.append(f"<strong>How to Register:</strong> {esc(row['register'])}")
    details_html = "<br>\n          ".join(details)

    link_html = ""
    if row["website"] and row["website"].lower().startswith("http"):
        site_label = esc(row["website"].replace("https://", "").replace("http://", "").rstrip("/"))
        link_html = (
            f'\n        <a href="{esc(row["website"])}" target="_blank" '
            f'style="margin-top:0.75rem;display:inline-block;color:var(--accent);'
            f'font-weight:600;font-size:0.9rem">Visit {site_label}</a>'
        )

    return (
        '<div class="resource-card" style="margin-bottom:1.25rem">\n'
        f"        <h3>{name}</h3>\n"
        f"        <p>{desc}</p>\n"
        '        <p style="margin-top:0.75rem;font-size:0.88rem;color:var(--mid)">\n'
        f"          {details_html}\n"
        "        </p>"
        f"{link_html}\n"
        "      </div>\n"
    )


def section_bounds(html_text, section_id):
    """Return (start, end) character offsets spanning one cat-section div's
    inner content, up to (not including) the next cat-section div or end of
    the directory block."""
    start_match = re.search(
        rf'<div class="cat-section" id="{re.escape(section_id)}">', html_text
    )
    if not start_match:
        return None
    start = start_match.end()
    next_section = re.search(r'<div class="cat-section" id="', html_text[start:])
    end = start + next_section.start() if next_section else len(html_text)
    return start, end


def main():
    service = get_sheets_service()
    html_text = open(INDEX_HTML, encoding="utf-8").read()
    added = []

    for category, section_id in CATEGORY_TO_SECTION_ID.items():
        rows = read_tab(service, category)
        bounds = section_bounds(html_text, section_id)
        if not bounds:
            print(f"WARNING: section id {section_id} not found, skipping {category}", file=sys.stderr)
            continue
        start, end = bounds
        section_text = html_text[start:end]

        new_cards = ""
        for row in rows:
            name = (row["org_name"] or "").strip()
            if not name:
                continue
            if name.lower() in section_text.lower():
                continue  # already represented somewhere in this category
            new_cards += build_card(row)
            added.append(f"{category}: {name}")

        if new_cards:
            # Insert right before the section's closing </div>, i.e. at `end`.
            html_text = html_text[:end] + new_cards + html_text[end:]
            # Recompute offsets for subsequent sections since text length changed.
            bounds_shift = len(new_cards)
            # (next loop iteration re-searches html_text fresh, so no manual
            # offset bookkeeping needed beyond re-slicing from updated html_text)

    if not added:
        print("No new listings to add — index.html left unchanged.")
        return

    with open(INDEX_HTML, "w", encoding="utf-8") as f:
        f.write(html_text)

    print("Added the following new cards:")
    for a in added:
        print(f"  - {a}")

    # Surface the list for the GitHub Action step that opens the PR.
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("### New asset map listings added\n")
            for a in added:
                f.write(f"- {a}\n")
    added_path = os.environ.get("NEW_LISTINGS_FILE")
    if added_path:
        with open(added_path, "w", encoding="utf-8") as f:
            f.write("\n".join(f"- {a}" for a in added))


if __name__ == "__main__":
    main()
