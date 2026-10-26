#!/usr/bin/env python3
"""Create or update a Confluence page from a folder made by tools/html2confluence.py
(page_storage.xhtml, attachments/, title.txt) and upload its attachments.

Works with Confluence Cloud and Data Center/Server (REST API v1 content endpoints).

Cloud (email + API token, https://id.atlassian.com/manage-profile/security/api-tokens):
    export CONFLUENCE_EMAIL=you@gbrx.co.uk
    export CONFLUENCE_API_TOKEN=xxxxxxxx
    python tools/publish_to_confluence.py docs/confluence/technical_document \
        --base-url https://YOURSITE.atlassian.net/wiki --space RAIL [--parent-id 123456]

Data Center/Server (personal access token):
    export CONFLUENCE_PAT=xxxxxxxx
    python tools/publish_to_confluence.py docs/confluence/technical_document --base-url https://confluence.yourorg.com --space RAIL

Re-running with the same title updates the page (new version) and replaces attachments.
Use --dry-run to see what would happen without calling the API.
Requires: pip install requests
"""
import argparse
import json
import mimetypes
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def session(args):
    import requests
    s = requests.Session()
    if os.environ.get("CONFLUENCE_PAT"):
        s.headers["Authorization"] = "Bearer " + os.environ["CONFLUENCE_PAT"]
    elif os.environ.get("CONFLUENCE_EMAIL") and os.environ.get("CONFLUENCE_API_TOKEN"):
        s.auth = (os.environ["CONFLUENCE_EMAIL"], os.environ["CONFLUENCE_API_TOKEN"])
    elif not args.dry_run:
        sys.exit("Set CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN (Cloud) or CONFLUENCE_PAT (Data Center).")
    s.headers["Accept"] = "application/json"
    return s


def check(r, what):
    if r.status_code >= 400:
        sys.exit(f"{what} failed: HTTP {r.status_code}\n{r.text[:1500]}")
    return r.json() if r.text else {}


def find_page(s, api, space, title):
    r = s.get(f"{api}/content", params={"spaceKey": space, "title": title, "type": "page", "expand": "version"})
    res = check(r, "Page lookup").get("results", [])
    return res[0] if res else None


def upsert_page(s, api, args, body):
    page = find_page(s, api, args.space, args.title)
    data = {"type": "page", "title": args.title, "space": {"key": args.space},
            "body": {"storage": {"value": body, "representation": "storage"}}}
    if args.parent_id:
        data["ancestors"] = [{"id": str(args.parent_id)}]
    if page:
        data["version"] = {"number": page["version"]["number"] + 1, "message": "Updated by publish_to_confluence.py"}
        r = s.put(f"{api}/content/{page['id']}", json=data, headers={"Content-Type": "application/json"})
        page = check(r, "Page update")
        print(f"Updated page {page['id']} (version {page['version']['number']})")
    else:
        r = s.post(f"{api}/content", json=data, headers={"Content-Type": "application/json"})
        page = check(r, "Page create")
        print(f"Created page {page['id']}")
    return page["id"]


def upload(s, api, page_id, path):
    hdr = {"X-Atlassian-Token": "no-check"}
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    r = s.get(f"{api}/content/{page_id}/child/attachment", params={"filename": path.name})
    existing = check(r, f"Attachment lookup {path.name}").get("results", [])
    with open(path, "rb") as fh:
        files = {"file": (path.name, fh, ctype)}
        if existing:
            url = f"{api}/content/{page_id}/child/attachment/{existing[0]['id']}/data"
        else:
            url = f"{api}/content/{page_id}/child/attachment"
        r = s.post(url, files=files, data={"minorEdit": "true"}, headers=hdr)
    check(r, f"Upload {path.name}")
    print(f"  {'replaced' if existing else 'attached'} {path.name}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page_dir", help="folder with page_storage.xhtml, attachments/ and title.txt")
    ap.add_argument("--base-url", required=True, help="Cloud: https://SITE.atlassian.net/wiki ; DC: https://confluence.example.com")
    ap.add_argument("--space", required=True, help="space key, e.g. SWR")
    ap.add_argument("--title", help="page title (default: title.txt in the page folder)")
    ap.add_argument("--parent-id", help="optional parent page id")

    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    api = args.base_url.rstrip("/") + "/rest/api"
    pdir = Path(args.page_dir)
    if not args.title:
        args.title = (pdir / "title.txt").read_text(encoding="utf-8").strip()
    body = (pdir / "page_storage.xhtml").read_text(encoding="utf-8")
    att = pdir / "attachments"
    files = sorted(p for p in att.iterdir() if p.is_file()) if att.exists() else []
    if args.dry_run:
        print(json.dumps({"api": api, "space": args.space, "title": args.title, "parent": args.parent_id,
                          "body_chars": len(body), "attachments": [p.name for p in files]}, indent=1))
        return
    s = session(args)
    page_id = upsert_page(s, api, args, body)
    for p in files:
        upload(s, api, page_id, p)
    print(f"Done: {args.base_url.rstrip('/')}/pages/viewpage.action?pageId={page_id}")


if __name__ == "__main__":
    main()
