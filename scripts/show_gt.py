"""Overlay ground-truth annotations on a PDF and open the result in the browser.

Usage
-----
    python scripts/show_gt.py doc.pdf ann_p1.json ann_p2.json
    python scripts/show_gt.py doc.pdf ann_p1.json -o /tmp/review.html

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
from pathlib import Path
from typing import Any

# --- colour map -----------------------------------------------------------

_COLORS = {
    "title": "#8b5cf6",
    "text": "#3b82f6",
    "table": "#ef4444",
    "figure": "#10b981",
    "image": "#10b981",
    "caption": "#ec4899",
    "list": "#06b6d4",
    "list_item": "#06b6d4",
    "header": "#a3a3a3",
    "footer": "#a3a3a3",
    "page_number": "#a3a3a3",
    "equation": "#f59e0b",
}
_DEFAULT_COLOR = "#9ca3af"


def _color(cat: str) -> str:
    return _COLORS.get(cat.lower(), _DEFAULT_COLOR)


# --- PDF rendering --------------------------------------------------------

def render_pdf(pdf_path: Path, dpi: int = 144) -> tuple[list[str], list[tuple[float, float]]]:
    """Return (base64_pngs, (width_px, height_px)) for every page."""
    import pypdfium2 as pdfium

    scale = dpi / 72.0
    imgs, sizes = [], []
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        for i in range(len(pdf)):
            page = pdf[i]
            w, h = page.get_size()
            pil = page.render(scale=scale).to_pil().convert("RGB")
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            imgs.append(base64.b64encode(buf.getvalue()).decode("ascii"))
            sizes.append((w * scale, h * scale))
    finally:
        pdf.close()
    return imgs, sizes


# --- annotation helpers ---------------------------------------------------

def load_page_annotations(json_path: Path) -> dict[str, Any]:
    with open(json_path) as f:
        return json.load(f)


def sorted_dets(page: dict[str, Any]) -> list[dict[str, Any]]:
    dets = page.get("layout_dets", [])
    return sorted(dets, key=lambda d: float("inf") if d.get("order") is None else d["order"])


def norm_poly(poly: list[float], w: float, h: float) -> tuple[float, float, float, float] | None:
    if not poly or len(poly) < 4 or not w or not h:
        return None
    x0, y0, x1, y1 = poly[0] / w, poly[1] / h, poly[2] / w, poly[3] / h
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
<header>{title} — ground-truth annotations</header>
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
    imgs, _ = render_pdf(pdf_path, dpi)

    # index annotation files by 1-based page_no
    pages: dict[int, dict[str, Any]] = {}
    for p in json_paths:
        page = load_page_annotations(p)
        pages[page.get("page_info", {}).get("page_no", 0)] = page

    seen_cats: set[str] = set()
    img_parts, txt_parts = [], []

    for idx, img_b64 in enumerate(imgs):
        page_no = idx + 1
        page = pages.get(page_no)

        # boxes on image
        boxes = ""
        if page:
            pi = page.get("page_info", {})
            pw, ph = float(pi.get("width", 1)), float(pi.get("height", 1))
            for det in sorted_dets(page):
                bbox = norm_poly(det.get("poly", []), pw, ph)
                if not bbox:
                    continue
                x0, y0, x1, y1 = bbox
                eid = f"a{det.get('anno_id', idx)}"
                c = _color(det.get("category_type", ""))
                seen_cats.add(det.get("category_type", "unknown"))
                boxes += (
                    f'<div class="box" data-id="{eid}" style="'
                    f"left:{x0*100:.2f}%;top:{y0*100:.2f}%;"
                    f"width:{(x1-x0)*100:.2f}%;height:{(y1-y0)*100:.2f}%;"
                    f'border-color:{c};background:{c}22"></div>'
                )

        img_parts.append(
            f'<div class="page">'
            f'<img src="data:image/png;base64,{img_b64}" alt="page {page_no}">'
            f"{boxes}</div>"
        )

        # annotation list
        txt_parts.append(f'<div class="plabel">page {page_no}</div>')
        if page:
            pi = page.get("page_info", {})
            pw, ph = float(pi.get("width", 1)), float(pi.get("height", 1))
            for det in sorted_dets(page):
                bbox = norm_poly(det.get("poly", []), pw, ph)
                eid = f"a{det.get('anno_id', idx)}"
                cat = det.get("category_type", "unknown")
                c = _color(cat)
                nogeo = "" if bbox else " nogeo"
                txt_parts.append(
                    f'<div class="ann{nogeo}" data-id="{eid}" style="border-left-color:{c}">'
                    f'<span class="cat">{html.escape(cat)}</span>'
                    f'<span class="meta">#{det.get("order","")} · id {det.get("anno_id","")}</span>'
                    f'<div class="txt">{html.escape(det.get("text","") or "")}</div></div>'
                )
        else:
            txt_parts.append('<div class="ann nogeo" style="border-left-color:#9ca3af">'
                             '<span class="cat">no annotation for this page</span></div>')

    legend = "".join(
        f'<span class="lchip" style="background:{_color(c)}">{html.escape(c)}</span>'
        for c in sorted(seen_cats)
    )

    return _TEMPLATE.format(
        title=html.escape(pdf_path.name),
        legend=legend,
        img_col="".join(img_parts),
        txt_col="".join(txt_parts),
    )


# --- CLI ------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate a ground-truth overlay HTML from a PDF and annotation JSON(s)."
    )
    ap.add_argument("pdf", help="PDF file to render")
    ap.add_argument("annotations", nargs="+", metavar="JSON", help="per-page annotation JSON file(s)")
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
