import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

from .io import digest


def normalize(text):
    """Normalize typography while retaining case and word boundaries."""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(str.maketrans({"‐": "-", "‑": "-", "–": "-", "−": "-", "’": "'"}))
    return re.sub(r"\s+", " ", text).strip()


def element_text(element):
    if element is None:
        return ""
    # A space between every itertext fragment would split inline gene names.
    return normalize("".join(element.itertext()))


def parse_article(path, include_references=False):
    path = Path(path)
    raw = path.read_bytes()
    root = ET.fromstring(raw)
    for node in root.iter():
        node.tag = node.tag.rsplit("}", 1)[-1]
    meta = root.find("./front/article-meta")
    if meta is None:
        raise ValueError("Expected JATS article-meta")
    ids = {node.get("pub-id-type"): element_text(node) for node in meta.findall("article-id")}
    paper_id = ids.get("pmcid", path.stem)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", paper_id):
        raise ValueError("Unsafe or malformed article identifier")
    if ids.get("pmid") and not re.fullmatch(r"[0-9]{1,12}", ids["pmid"]):
        raise ValueError("Malformed PMID")
    title = element_text(meta.find("./title-group/article-title"))
    blocks = []

    def add(node, section, kind, section_id=""):
        if node is None:
            return
        text = element_text(node)
        if text:
            blocks.append({"block_id": f"b{len(blocks) + 1:04d}", "xml_id": node.get("id", ""),
                           "section": section, "section_id": section_id, "content_type": kind,
                           "text": text})

    title_node = meta.find("./title-group/article-title")
    add(title_node, "Title", "title")

    def walk(node, section, section_id=""):
        for child in node:
            tag = child.tag
            if tag == "sec":
                heading = element_text(child.find("title"))
                new_section = f"{section} / {heading}" if heading else section
                new_id = child.get("id", section_id)
                add(child.find("title"), new_section, "section_heading", new_id)
                walk(child, new_section, new_id)
            elif tag in ("p", "list", "disp-quote", "statement"):
                # Floating objects in paragraphs need their own table/caption representation.
                if any(n.tag in ("table-wrap", "fig") for n in child.iter()):
                    copy = ET.fromstring(ET.tostring(child))
                    for parent in copy.iter():
                        for nested in list(parent):
                            if nested.tag in ("table-wrap", "fig"):
                                # The float's tail belongs to the surrounding paragraph.
                                siblings = list(parent)
                                index = siblings.index(nested)
                                if nested.tail:
                                    if index:
                                        previous = siblings[index - 1]
                                        previous.tail = (previous.tail or "") + nested.tail
                                    else:
                                        parent.text = (parent.text or "") + nested.tail
                                parent.remove(nested)
                    add(copy, section, "paragraph", section_id)
                    for nested in child.iter():
                        if nested.tag in ("table-wrap", "fig"):
                            floating(nested, section, section_id)
                else:
                    add(child, section, "paragraph", section_id)
            elif tag in ("table-wrap", "fig"):
                floating(child, section, section_id)
            elif tag == "ref-list":
                if include_references:
                    for reference in child.findall("ref"):
                        add(reference, "References", "reference", section_id)
            elif tag not in ("title", "label", "permissions", "contrib-group"):
                walk(child, section, section_id)

    def floating(node, section, section_id):
        label = element_text(node.find("label"))
        caption = node.find("caption")
        if caption is not None:
            add(caption, f"{section} / {label}", "caption", section_id)
        if node.tag == "table-wrap":
            for row in node.findall(".//tr"):
                cells = [element_text(cell) for cell in row if cell.tag in ("td", "th")]
                if cells:
                    row_node = ET.Element("row")
                    row_node.text = " | ".join(cells)
                    add(row_node, f"{section} / {label}", "table_row", section_id)
            foot = node.find("table-wrap-foot")
            if foot is not None:
                add(foot, f"{section} / {label}", "table_note", section_id)

    for abstract in meta.findall("abstract"):
        walk(abstract, "Abstract")
    body = root.find("body")
    if body is not None:
        walk(body, "Body")
    back = root.find("back")
    if back is not None:
        walk(back, "Back matter")
    floats = root.find("floats-group")
    if floats is not None:
        walk(floats, "Floating objects")
    warnings = []
    article_type = root.get("article-type", "unknown")
    if article_type == "abstract" and re.search(r"proceedings|congress|conference", title, re.I):
        warnings.append("Possible multi-study proceedings: candidate pairs may cross independent abstracts")
    if body is None:
        warnings.append("missing_body")
    graphics = sum(1 for _ in root.iter("graphic"))
    supplements = sum(1 for _ in root.iter("supplementary-material"))
    if graphics:
        warnings.append(f"{graphics} linked graphics: captions read; image pixels not analyzed")
    if supplements:
        warnings.append(f"{supplements} supplement references: external supplements not downloaded")
    return {"paper_id": paper_id, "pmid": ids.get("pmid", ""), "doi": ids.get("doi", ""),
            "article_type": article_type,
            "title": title, "source_file": str(path.resolve()), "source_sha256": digest(raw),
            "blocks": blocks, "warnings": warnings, "include_references": include_references}
