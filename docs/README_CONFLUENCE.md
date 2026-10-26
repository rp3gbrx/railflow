# Putting the railflow documents on Confluence

The HTML files in `docs/` are the master copies. `python docs/build_docs.py` converts each into a Confluence pack:

```
docs/confluence/<document>/
  page_storage.xhtml   page body in Confluence storage format (validated as well-formed XHTML)
  attachments/         figures used by the page
  <document>.docx      Word version (A4)
  title.txt            page title
```

Documents: `technical_document` (railflow technical document), `applications` (Using railflow in other projects:
worked examples) and `sources` (railflow sources). Links between the three pages are converted to Confluence
page links by title, so create all three pages in the same space with the titles in `title.txt`.

## Option 1: publish with the REST API (recommended; Cloud and Data Center)

```bash
pip install requests
# Confluence Cloud: email + API token (id.atlassian.com > Security > API tokens)
export CONFLUENCE_EMAIL=you@example.com CONFLUENCE_API_TOKEN=...
# Data Center / Server: a personal access token instead
# export CONFLUENCE_PAT=...

python tools/publish_to_confluence.py docs/confluence/technical_document \
    --base-url https://yourcompany.atlassian.net/wiki --space RAIL --parent-id 123456
python tools/publish_to_confluence.py docs/confluence/applications --base-url ... --space RAIL --parent-id 123456
python tools/publish_to_confluence.py docs/confluence/sources      --base-url ... --space RAIL --parent-id 123456
```

The script creates the page (or updates it if a page with the same title exists in the space), then uploads
the figures as attachments. `--dry-run` shows what it would do. Re-running after `build_docs.py` updates the
pages in place, keeping their history.

## Option 2: import the Word file

- **Data Center / Server:** create a page, then `...` menu > **Import Word Document** and choose `<document>.docx`.
- **Cloud:** open the `.docx` in Word, select all, copy, and paste into a new Confluence page. Figures and tables
  carry across; replace the contents list with the Table of Contents macro if wanted.

## Option 3: paste the storage format

With the "Confluence Source Editor" app (or the built-in source editor where enabled), paste
`page_storage.xhtml` into a new page, then upload everything in `attachments/` to the page.

## On GitHub

The `.md` files next to the HTML render on GitHub with figures, so the repository is readable without Confluence.
