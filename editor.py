"""Core logic: replace text in a PDF while keeping font, size, colour and position."""
import re
import pymupdf


def detect_enrollment(doc):
    """Return the first number found after 'ENROLLMENT NO.:' in the document."""
    for page in doc:
        m = re.search(r"ENROLL?MENT\s*NO\.?\s*:?\s*(\d+)", page.get_text(), re.I)
        if m:
            return m.group(1)
        # fallback (e.g. previously edited PDFs): first number on the same line as the label
        for r in page.search_for("ENROLLMENT NO"):
            for w in page.get_text("words"):
                if w[0] >= r.x1 - 1 and abs((w[1] + w[3]) / 2 - (r.y0 + r.y1) / 2) < r.height / 2:
                    m = re.search(r"\d{4,}", w[4])
                    if m:
                        return m.group(0)
    return None


def _font_for(doc, page, font_name, text):
    """Try to reuse the PDF's embedded font; fall back to Helvetica."""
    for xref, _ext, _type, name, *_ in page.get_fonts():
        if name.split("+")[-1] == font_name.split("+")[-1]:
            try:
                _n, ext, _t, buf = doc.extract_font(xref)
                if buf and ext in ("ttf", "otf", "cff"):
                    f = pymupdf.Font(fontbuffer=buf)
                    if all(f.has_glyph(ord(c)) for c in text):
                        return f
            except Exception:
                pass
    return pymupdf.Font("helv")


def replace_text(src_bytes, old, new):
    """Replace every occurrence of `old` with `new`. Returns (pdf_bytes, count)."""
    doc = pymupdf.open(stream=src_bytes, filetype="pdf")
    total = 0
    for page in doc:
        hits = page.search_for(old)
        if not hits:
            continue
        spans = [s for b in page.get_text("dict")["blocks"] for l in b.get("lines", [])
                 for s in l["spans"]]
        jobs = []
        for r in hits:
            span = next((s for s in spans if pymupdf.Rect(s["bbox"]).intersects(r)), None)
            if span:
                jobs.append((r, span))
        for r, _ in jobs:
            page.add_redact_annot(r, fill=(1, 1, 1))
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE,
                              graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
        for r, span in jobs:
            c = span["color"]
            color = ((c >> 16 & 255) / 255, (c >> 8 & 255) / 255, (c & 255) / 255)
            font = _font_for(doc, page, span["font"], new)
            tw = pymupdf.TextWriter(page.rect)
            tw.append((r.x0, span["origin"][1]), new, font=font, fontsize=span["size"])
            tw.write_text(page, color=color)
            total += 1
    out = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return out, total
