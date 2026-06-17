"""Overlay annotations on every page of a PDF and open the result in the browser.

Usage
-----
    python show_gt.py doc.pdf ann.json
    python show_gt.py doc.pdf gt_p1.json gt_p2.json -o /tmp/review.html

Renders **all pages** (two-pane viewer: page image on the left, annotation list
on the right, hover-linked). Accepts either format:

  * GT / OmniDocBench  — ``{"page_info", "layout_dets":[{"poly", ...}]}`` (poly in
    page pixels). One file per page; pass one file per page to cover the document.
  * MinerU / doc_bench — ``{"pages", "elements":[{"bbox", ...}]}`` (single file,
    all pages).

Coordinate space is auto-detected per file *and per page*, so the three
conventions in this repo all overlay correctly:

  * page pixels / PDF points  (GT, MinerU pipeline) — coords match the page size.
  * per-mille 0..1000         (MinerU2.5-Pro / doc_bench bbox) — divided by 1000.
  * normalized 0..1           — used as-is.

The output HTML is self-contained (base64 PNG pages + CSS + JS, no server needed).
"""

from __future__ import annotations

import argparse
import base64
import html
import io
import json
import sys
import webbrowser
from collections import defaultdict
from pathlib import Path
from typing import Any

# --- colour map -----------------------------------------------------------

_COLORS = {
    # GT / OmniDocBench category names
    "title": "#8b5cf6",
    "text": "#3b82f6",
    "list": "#06b6d4",
    # doc_bench / MinerU element types
    "heading": "#8b5cf6",
    "paragraph": "#3b82f6",
    "list_item": "#06b6d4",
    "table": "#ef4444",
    "figure": "#10b981",
    "image": "#10b981",
    "caption": "#ec4899",
    "equation": "#f59e0b",
    "header": "#a3a3a3",
    "footer": "#a3a3a3",
    "page_number": "#a3a3a3",
}
_DEFAULT_COLOR = "#9ca3af"


def _color(cat: str) -> str:
    return _COLORS.get(cat.lower(), _DEFAULT_COLOR)


# --- PDF rendering --------------------------------------------------------

def render_pdf(pdf_path: Path, dpi: int = 144) -> list[str]:
    """Return the base64-encoded PNG of every page."""
    import pypdfium2 as pdfium

    scale = dpi / 72.0
    imgs: list[str] = []
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        for i in range(len(pdf)):
            pil = pdf[i].render(scale=scale).to_pil().convert("RGB")
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            imgs.append(base64.b64encode(buf.getvalue()).decode("ascii"))
    finally:
        pdf.close()
    return imgs


# --- annotation helpers ---------------------------------------------------

# Normalised element shape used internally by the HTML builder:
#   page_no — 1-based page number
#   eid     — unique element id string (used for hover linking)
#   cat     — category / type label
#   text    — display text
#   meta    — short metadata string shown in the list pane
#   poly    — [x0, y0, x1, y1] in the coordinate space of the source
#   pw,ph   — page width / height in the same coordinate space
#   nbox    — poly normalized to [0, 1] (filled in once the scale is detected)


def _detect_scale(polys: list[list[float]], pw: float, ph: float) -> tuple[float, float]:
    """Infer the (x, y) divisors that map a page's polys into [0, 1].

    Auto-detects across the three conventions used in the repo:
      * coords that fit the page size  -> divide by (pw, ph)   [pixels / points]
      * coords up to ~1000             -> divide by (1000, 1000) [per-mille]
      * coords up to ~1                -> divide by (1, 1)        [already normalized]
    """
    polys = [p for p in polys if p and len(p) >= 4]
    if not polys:
        return (pw or 1.0, ph or 1.0)

    max_x = max(max(p[0], p[2]) for p in polys)
    max_y = max(max(p[1], p[3]) for p in polys)

    # If the coordinates fit inside the declared page size, they're in page
    # space (pixels or points) — divide by the page dims. (pw/ph > 1.5 guards
    # against a normalized file that happens to declare a 1x1 page.)
    if pw > 1.5 and ph > 1.5 and max_x <= pw * 1.05 and max_y <= ph * 1.05:
        return (pw, ph)

    def scale_of(m: float) -> float:
        if m <= 1.5:
            return 1.0           # already normalized 0..1
        if m <= 1050.0:
            return 1000.0        # per-mille 0..1000
        return m or 1.0          # fallback: shrink to fit

    return (scale_of(max_x), scale_of(max_y))


def _load_elements(json_path: Path) -> list[dict[str, Any]]:
    """Load a GT (layout_dets) or MinerU (elements) JSON for all pages.

    The returned dicts carry an ``nbox`` field already normalized to [0, 1]
    using the coordinate scale detected per file and per page.
    """
    with open(json_path) as f:
        data = json.load(f)

    raw: list[dict[str, Any]] = []

    # MinerU / ParserOutput / doc_bench format — single file, all pages.
    if "elements" in data and "pages" in data:
        dims = {p["page_index"]: (float(p["width"]), float(p["height"]))
                for p in data.get("pages", [])}
        for el in data.get("elements", []):
            pidx = el.get("page_index", 0)
            pw, ph = dims.get(pidx, (1.0, 1.0))
            b = el.get("bbox") or {}
            raw.append({
                "page_no": pidx + 1,
                "eid": str(el.get("element_id", "")),
                "cat": el.get("type", "unknown"),
                "text": el.get("text", "") or "",
                "meta": str(el.get("element_id", ""))[:12],
                "poly": [b.get("x0", 0), b.get("y0", 0), b.get("x1", 0), b.get("y1", 0)],
                "pw": pw, "ph": ph,
            })
    else:
        # GT / layout_dets format — one file per page.
        pi = data.get("page_info", {})
        pw, ph = float(pi.get("width", 1)), float(pi.get("height", 1))
        page_no = int(pi.get("page_no", 1))
        dets = sorted(data.get("layout_dets", []),
                      key=lambda d: float("inf") if d.get("order") is None else float(d["order"]))
        for det in dets:
            raw.append({
                "page_no": page_no,
                "eid": f"a{det.get('anno_id', '')}",
                "cat": det.get("category_type", "unknown"),
                "text": det.get("text", "") or "",
                "meta": f"#{det.get('order', '')} · id {det.get('anno_id', '')}",
                "poly": det.get("poly", []),
                "pw": pw, "ph": ph,
            })

    # Detect the coordinate scale once per page (page dims can differ per page),
    # then normalize every box on that page with it.
    by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for el in raw:
        by_page[el["page_no"]].append(el)
    for page_els in by_page.values():
        pw, ph = page_els[0]["pw"], page_els[0]["ph"]
        sx, sy = _detect_scale([e["poly"] for e in page_els], pw, ph)
        for el in page_els:
            el["nbox"] = norm_poly(el["poly"], sx, sy)
    return raw


def norm_poly(poly: list[float], sx: float, sy: float) -> tuple[float, float, float, float] | None:
    """Normalize a [x0,y0,x1,y1] poly to [0,1] using the given divisors."""
    if not poly or len(poly) < 4 or not sx or not sy:
        return None
    x0, y0, x1, y1 = poly[0] / sx, poly[1] / sy, poly[2] / sx, poly[3] / sy
    x0, x1 = sorted((max(0.0, x0), min(1.0, x1)))
    y0, y1 = sorted((max(0.0, y0), min(1.0, y1)))
    return None if x1 - x0 < 1e-4 or y1 - y0 < 1e-4 else (x0, y0, x1, y1)


# --- HTML builder ---------------------------------------------------------

_TEMPLATE = """\
<!doctype html><html><head><meta charset="utf-8"><title>{title}</title><style>
*{{box-sizing:border-box}}
html,body{{margin:0;height:100%;font:14px/1.5 system-ui,sans-serif;background:#f6f7f9;color:#111}}
body{{display:flex;flex-direction:column;overflow:hidden}}
header{{flex-shrink:0;padding:10px 16px;background:#111;color:#fff;font-weight:600}}
.legend{{flex-shrink:0;display:flex;flex-wrap:wrap;gap:8px;padding:6px 16px;background:#1f2937}}
.lchip{{font-size:11px;padding:2px 8px;border-radius:10px;color:#fff}}
.pane{{display:grid;grid-template-columns:1fr 1fr;flex:1;min-height:0}}
.imgcol,.txtcol{{overflow-y:auto;overflow-x:hidden;padding:16px}}
.imgcol{{background:#e5e7eb}}.txtcol{{background:#fff;border-left:1px solid #ddd}}
.page{{position:relative;display:block;width:100%;margin:0 0 20px;box-shadow:0 1px 6px #0003}}
.page img{{display:block;width:100%;height:auto}}
.box{{position:absolute;border:2px solid;border-radius:2px;cursor:pointer;transition:.08s}}
.box.hl{{box-shadow:0 0 0 3px #facc15;background:#facc1555!important;z-index:5}}
.plabel{{font-weight:700;color:#6b7280;margin:14px 0 6px;font-size:11px;text-transform:uppercase}}
.ann{{border-left:4px solid;padding:5px 10px;margin:3px 0;border-radius:0 6px 6px 0;
  background:#fafafa;cursor:pointer}}
.ann.hl{{background:#fef9c3;box-shadow:0 0 0 2px #facc15}}
.ann.nogeo{{opacity:.6;cursor:default}}
.cat{{font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:.04em}}
.meta{{font-size:10px;color:#9ca3af;margin-left:4px}}
.txt{{white-space:pre-wrap;margin-top:2px}}
</style></head><body>
<header>{title} — {pages} pages · {count} annotations</header>
<div class="legend">{legend}</div>
<div class="pane">
  <div class="imgcol">{img_col}</div>
  <div class="txtcol">{txt_col}</div>
</div>
<script>
const clear=()=>document.querySelectorAll('.hl').forEach(e=>e.classList.remove('hl'));
const mark=id=>document.querySelectorAll('[data-id="'+id+'"]').forEach(e=>e.classList.add('hl'));
document.querySelectorAll('[data-id]').forEach(el=>{{
  el.addEventListener('mouseenter',()=>mark(el.dataset.id));
  el.addEventListener('mouseleave',clear);
  el.addEventListener('click',()=>{{clear();mark(el.dataset.id);
    const b=document.querySelector('.box[data-id="'+el.dataset.id+'"]');
    if(b)b.scrollIntoView({{behavior:'smooth',block:'center'}});
  }});
}});
</script></body></html>"""


def build_html(pdf_path: Path, json_paths: list[Path], dpi: int = 144) -> str:
    imgs = render_pdf(pdf_path, dpi)

    # Flatten elements from every input file, grouped by 1-based page_no.
    by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
    total = 0
    for p in json_paths:
        for el in _load_elements(p):
            by_page[el["page_no"]].append(el)
            total += 1

    seen_cats: set[str] = set()
    img_parts, txt_parts = [], []

    for idx, img_b64 in enumerate(imgs):
        page_no = idx + 1
        elements = by_page.get(page_no, [])

        boxes = ""
        for el in elements:
            seen_cats.add(el["cat"])
            nbox = el["nbox"]
            if not nbox:
                continue
            x0, y0, x1, y1 = nbox
            c = _color(el["cat"])
            boxes += (
                f'<div class="box" data-id="{html.escape(el["eid"])}" style="'
                f"left:{x0*100:.2f}%;top:{y0*100:.2f}%;"
                f"width:{(x1-x0)*100:.2f}%;height:{(y1-y0)*100:.2f}%;"
                f'border-color:{c};background:{c}22"></div>'
            )

        img_parts.append(
            f'<div class="page">'
            f'<img src="data:image/png;base64,{img_b64}" alt="page {page_no}">'
            f"{boxes}</div>"
        )

        txt_parts.append(f'<div class="plabel">page {page_no}</div>')
        if elements:
            for el in elements:
                c = _color(el["cat"])
                nogeo = "" if el["nbox"] else " nogeo"
                txt_parts.append(
                    f'<div class="ann{nogeo}" data-id="{html.escape(el["eid"])}" style="border-left-color:{c}">'
                    f'<span class="cat">{html.escape(el["cat"])}</span>'
                    f'<span class="meta">{html.escape(el["meta"])}</span>'
                    f'<div class="txt">{html.escape(el["text"])}</div></div>'
                )
        else:
            txt_parts.append('<div class="ann nogeo" style="border-left-color:#9ca3af">'
                             '<span class="cat">no annotations for this page</span></div>')

    legend = "".join(
        f'<span class="lchip" style="background:{_color(c)}">{html.escape(c)}</span>'
        for c in sorted(seen_cats)
    )

    return _TEMPLATE.format(
        title=html.escape(pdf_path.name),
        pages=len(imgs),
        count=total,
        legend=legend,
        img_col="".join(img_parts),
        txt_col="".join(txt_parts),
    )


# --- CLI ------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Overlay annotation JSON(s) on all pages of a PDF as a self-contained HTML."
    )
    ap.add_argument("pdf", help="PDF file to render")
    ap.add_argument("annotations", nargs="+", metavar="JSON", help="annotation JSON file(s)")
    ap.add_argument("-o", "--out", help="output HTML path (default: <pdf_stem>.gt_report.html)")
    ap.add_argument("--dpi", type=int, default=144, help="render resolution (default 144)")
    ap.add_argument("--no-open", action="store_true", help="do not open in browser after generating")
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    json_paths = [Path(j) for j in args.annotations]
    out_path = Path(args.out) if args.out else pdf_path.with_suffix(".gt_report.html")

    report = build_html(pdf_path, json_paths, dpi=args.dpi)
    out_path.write_text(report, encoding="utf-8")
    print(f"wrote {out_path}")

    if not args.no_open:
        webbrowser.open(out_path.resolve().as_uri())

    return 0


if __name__ == "__main__":
    sys.exit(main())
