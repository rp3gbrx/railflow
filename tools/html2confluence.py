#!/usr/bin/env python3
"""Convert a project HTML document into Confluence-ready formats.

    python tools/html2confluence.py docs/technical_document.html --out docs/confluence/technical_document

Writes into --out:
  page_storage.xhtml   Confluence storage format (for tools/publish_to_confluence.py)
  attachments/         every local image the document uses, plus any extra --attach files
  <name>.docx          Word version (Confluence "Import Word Document", or open and paste)
  ../<name>.md         GitHub-flavoured Markdown, written next to the HTML (readable on GitHub)
  title.txt            suggested page title (the document's <h1>)

HTML conventions understood (all optional):
  <main> ... </main>         the document body; falls back to <body>
  <p class="eyebrow">        dropped (the Confluence page title replaces it)
  <h1>                       becomes the page title
  <nav class="toc">          replaced by the Confluence table of contents macro
  <div class="key">          Info panel (first <h3> inside becomes the panel title)
  <div class="note">         Note panel
  <div class="eq"> / <pre>   code block
  <figure><img><figcaption>  attached image + italic caption
  <div class="tbl"><table>   table (header rows moved into tbody, as Confluence expects)
  <span class="flag">        bold red text
  <a href="other.html">      links to sibling documents become plain text with the file name,
                             unless --link-map maps them to a Confluence page title

Requires: beautifulsoup4, lxml, pandoc (for .docx/.md).
"""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, CData
from lxml import etree

HERE = Path(__file__).resolve().parent


def to_storage(html, link_map, attach_names):
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.body
    new = BeautifulSoup("", "html.parser")

    def macro(name, params=None, rich=None, plain=None):
        m = new.new_tag("ac:structured-macro", attrs={"ac:name": name})
        for k, v in (params or {}).items():
            p = new.new_tag("ac:parameter", attrs={"ac:name": k}); p.string = v; m.append(p)
        if rich is not None:
            b = new.new_tag("ac:rich-text-body"); m.append(b)
            for el in rich:
                b.append(el)
        if plain is not None:
            b = new.new_tag("ac:plain-text-body"); b.append(CData(plain)); m.append(b)
        return m

    def att_link(fn, text):
        link = new.new_tag("ac:link")
        link.append(new.new_tag("ri:attachment", attrs={"ri:filename": fn}))
        body = new.new_tag("ac:plain-text-link-body"); body.append(CData(text)); link.append(body)
        return link

    def page_link(title, text):
        link = new.new_tag("ac:link")
        link.append(new.new_tag("ri:page", attrs={"ri:content-title": title}))
        body = new.new_tag("ac:plain-text-link-body"); body.append(CData(text)); link.append(body)
        return link

    title = main.find("h1").get_text(" ", strip=True) if main.find("h1") else ""
    for el in main.select("p.eyebrow, h1, script, style"):
        el.decompose()
    for a in main.find_all("a", href=True):
        href = a["href"]
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue
        name = Path(href.split("#")[0]).name
        if name in link_map:
            a.replace_with(page_link(link_map[name], a.get_text()))
        elif name in attach_names:
            a.replace_with(att_link(name, a.get_text()))
        else:
            a.replace_with(f"{a.get_text()} ({name})" if a.get_text().strip() != name else name)
    nav = main.find("nav")
    if nav:
        nav.replace_with(macro("toc", {"maxLevel": "2", "minLevel": "2"}))
    for cls, mname in [("key", "info"), ("note", "note")]:
        for box in main.find_all("div", class_=cls):
            h = box.find("h3")
            params = {"title": h.get_text()} if h else {}
            if h:
                h.decompose()
            kids = [c.extract() for c in list(box.children) if not (isinstance(c, NavigableString) and not c.strip())]
            box.replace_with(macro(mname, params, rich=kids))
    for eq in main.find_all("div", class_="eq") + main.find_all("pre"):
        eq.replace_with(macro("code", {"language": "none"}, plain=eq.get_text()))
    images = []
    for fig in main.find_all("figure"):
        img = fig.find("img"); cap = fig.find("figcaption")
        if img is None:
            fig.unwrap(); continue
        images.append(img["src"])
        fn = Path(img["src"]).name
        im = new.new_tag("ac:image", attrs={"ac:align": "center", "ac:width": "760", "ac:alt": img.get("alt", "")})
        im.append(new.new_tag("ri:attachment", attrs={"ri:filename": fn}))
        p1 = new.new_tag("p"); p1.append(im)
        fig.replace_with(p1)
        if cap:
            p2 = new.new_tag("p"); em = new.new_tag("em"); em.string = cap.get_text(" ", strip=True); p2.append(em)
            p1.insert_after(p2)
    for img in main.find_all("img"):          # loose images
        images.append(img["src"])
        im = new.new_tag("ac:image", attrs={"ac:width": "760"})
        im.append(new.new_tag("ri:attachment", attrs={"ri:filename": Path(img["src"]).name}))
        img.replace_with(im)
    for d in main.find_all("div", class_="tbl"):
        d.unwrap()
    for t in main.find_all("table"):
        thead = t.find("thead"); tbody = t.find("tbody")
        if thead and tbody:
            for tr in reversed(thead.find_all("tr")):
                tbody.insert(0, tr.extract())
            thead.decompose()
    for b in main.find_all("b"):
        b.name = "strong"
    for i in main.find_all("i"):
        i.name = "em"
    for s in main.find_all("span"):
        if "flag" in (s.get("class") or []):
            s.name = "strong"; s.attrs = {"style": "color: rgb(191,38,0);"}
        else:
            s.unwrap()
    for d in main.find_all(["div", "section", "header", "footer", "article"]):
        d.unwrap()
    for el in main.find_all(True):
        if el.name.startswith(("ac:", "ri:")):
            continue
        el.attrs = {k: v for k, v in el.attrs.items() if k in ("href", "start", "style", "colspan", "rowspan")}
    out = "".join(str(c) for c in main.contents)
    out = re.sub(r"\n{3,}", "\n\n", out).strip() + "\n"
    wrapped = ('<root xmlns:ac="http://atlassian.com/content" xmlns:ri="http://atlassian.com/resource/identifier">' + out + "</root>")
    etree.fromstring(wrapped.encode("utf-8"))   # raises if not well-formed XHTML
    return out, title, images


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html")
    ap.add_argument("--out", required=True)
    ap.add_argument("--attach", nargs="*", default=[], help="extra files to attach (linked from the page by file name)")
    ap.add_argument("--link-map", default="{}", help='JSON mapping sibling HTML file names to Confluence page titles')
    ap.add_argument("--reference-docx", default=str(HERE / "reference.docx"))
    a = ap.parse_args()
    src = Path(a.html).resolve(); out = Path(a.out); att = out / "attachments"
    if out.exists():
        shutil.rmtree(out)
    att.mkdir(parents=True)
    html = src.read_text(encoding="utf-8")
    extra = [Path(p) for p in a.attach]
    storage, title, images = to_storage(html, json.loads(a.link_map), {p.name for p in extra})
    (out / "page_storage.xhtml").write_text(storage, encoding="utf-8")
    (out / "title.txt").write_text(title + "\n", encoding="utf-8")
    for rel in images:
        shutil.copy(src.parent / rel, att / Path(rel).name)
    for p in extra:
        shutil.copy(p, att / p.name)
    # Word and Markdown versions (pandoc)
    soup = BeautifulSoup(html, "html.parser")
    for el in soup.select("nav, p.eyebrow, script, style"):
        el.decompose()
    md_soup = BeautifulSoup(str(soup), "html.parser")      # Markdown keeps the h1; Word takes it from metadata
    for h1 in soup.find_all("h1"):
        h1.decompose()
    for d in md_soup.find_all(["main", "div", "section"]):
        d.unwrap()
    for link in md_soup.find_all("a", href=True):        # links to sibling documents point at their .md versions
        h = link["href"]
        if not h.startswith(("http://", "https://", "mailto:", "#")) and h.split("#")[0].endswith(".html") and "/" not in h:
            link["href"] = h.replace(".html", ".md", 1)
    tmp = src.parent / f"_{src.stem}_pandoc.html"
    tmp_md = src.parent / f"_{src.stem}_pandoc_md.html"
    tmp.write_text(str(soup), encoding="utf-8"); tmp_md.write_text(str(md_soup), encoding="utf-8")
    try:
        subprocess.run(["pandoc", "-f", "html", str(tmp), "--resource-path", str(src.parent), "--metadata", f"title={title}",
                        "-t", "docx", "-o", str(out / f"{src.stem}.docx"), "--reference-doc", a.reference_docx], check=True)
        md = src.parent / f"{src.stem}.md"     # next to the HTML so image paths work on GitHub
        subprocess.run(["pandoc", "-f", "html", str(tmp_md), "-t", "gfm", "--wrap=none", "-o", str(md)], check=True)
    finally:
        tmp.unlink(missing_ok=True); tmp_md.unlink(missing_ok=True)
    print(f"{src.name}: '{title}' -> {out} ({len(images)} images, {storage.count('<table')} tables, {len(storage)/1e3:.0f} kB storage)")


if __name__ == "__main__":
    main()
