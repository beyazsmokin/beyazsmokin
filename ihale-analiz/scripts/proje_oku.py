#!/usr/bin/env python3
"""Proje dosyalarını tarar ve metraj için okunabilen bilgiyi Markdown olarak yazar.

Kullanım: python3 proje_oku.py <dosya-veya-klasor> [...]

İsteğe bağlı kütüphaneler: ezdxf (DXF), pdfplumber (PDF), Pillow (görseller).
Eksik olan kütüphanenin formatı "görsel inceleme gerekli" olarak raporlanır.
DWG için sistemde dwg2dxf (LibreDWG) veya ODAFileConverter aranır.
"""
import math
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".bmp"}
INSUNITS = {0: "birimsiz", 1: "inç", 2: "feet", 4: "mm", 5: "cm", 6: "m"}


def dxf_report(path: Path) -> list[str]:
    try:
        import ezdxf
    except ImportError:
        return ["- ezdxf kurulu değil: `pip install ezdxf`"]
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    unit = INSUNITS.get(doc.header.get("$INSUNITS", 0), "bilinmiyor")
    length = defaultdict(float)
    area = defaultdict(float)
    count = defaultdict(int)
    blocks = defaultdict(int)
    texts = []
    for e in msp:
        layer = e.dxf.layer
        kind = e.dxftype()
        count[layer] += 1
        if kind == "LINE":
            length[layer] += math.dist(e.dxf.start, e.dxf.end)
        elif kind == "LWPOLYLINE":
            pts = [p[:2] for p in e.get_points()]
            if e.closed:
                pts.append(pts[0])
                area[layer] += abs(sum(
                    x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:])
                )) / 2
            length[layer] += sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        elif kind == "CIRCLE":
            length[layer] += 2 * math.pi * e.dxf.radius
            area[layer] += math.pi * e.dxf.radius ** 2
        elif kind == "INSERT":
            blocks[e.dxf.name] += 1
        elif kind in ("TEXT", "MTEXT"):
            texts.append(e.plain_text() if kind == "MTEXT" else e.dxf.text)

    out = [f"- Çizim birimi: {unit}", "", "| Katman | Nesne | Uzunluk | Kapalı alan |",
           "|--------|-------|---------|-------------|"]
    for layer in sorted(count):
        out.append(f"| {layer} | {count[layer]} | {length[layer]:.2f} | {area[layer]:.2f} |")
    if blocks:
        out += ["", "| Blok | Adet |", "|------|------|"]
        out += [f"| {n} | {c} |" for n, c in sorted(blocks.items())]
    if texts:
        out += ["", f"- Yazılar ({len(texts)}): " + "; ".join(t.strip() for t in texts[:50])]
    return out


def dwg_report(path: Path) -> list[str]:
    tmp = Path(tempfile.mkdtemp())
    if shutil.which("dwg2dxf"):
        dxf = tmp / (path.stem + ".dxf")
        subprocess.run(["dwg2dxf", "-o", str(dxf), str(path)], capture_output=True)
    elif shutil.which("ODAFileConverter"):
        subprocess.run(["ODAFileConverter", str(path.parent), str(tmp), "ACAD2018", "DXF",
                        "0", "1", path.name], capture_output=True)
        dxf = tmp / (path.stem + ".dxf")
    else:
        return ["- DWG çevirici yok (dwg2dxf veya ODAFileConverter). "
                "Kullanıcıdan DXF ya da PDF çıktısı iste."]
    if not dxf.exists():
        return ["- DWG çevrilemedi. Kullanıcıdan DXF ya da PDF çıktısı iste."]
    return ["- DWG, DXF'e çevrildi."] + dxf_report(dxf)


def pdf_report(path: Path) -> list[str]:
    try:
        import pdfplumber
    except ImportError:
        return ["- pdfplumber kurulu değil; PDF görsel olarak incelenmeli."]
    out = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = (page.extract_text() or "").strip()
            vector = len(page.lines) + len(page.rects) + len(page.curves)
            tables = page.extract_tables()
            kind = "vektör" if vector else ("metin" if text else "taranmış, görsel inceleme gerekli")
            out.append(f"- Sayfa {i}: {kind}, {len(text)} karakter yazı, "
                       f"{vector} çizgi/şekil, {len(tables)} tablo")
            for t in tables:
                for row in t[:30]:
                    out.append("  | " + " | ".join(c or "" for c in row) + " |")
    return out


def image_report(path: Path) -> list[str]:
    try:
        from PIL import Image
    except ImportError:
        return ["- Pillow kurulu değil; görsel olarak incelenmeli."]
    with Image.open(path) as im:
        frames = getattr(im, "n_frames", 1)
        dpi = im.info.get("dpi")
        out = [f"- {im.width}x{im.height} piksel, {frames} sayfa/kare"
               + (f", {dpi[0]:.0f} DPI" if dpi else ", DPI bilgisi yok")]
    out.append("- Görsel inceleme gerekli: ölçü yazılarını ve ölçek çubuğunu esas al.")
    return out


def report(path: Path) -> list[str]:
    ext = path.suffix.lower()
    try:
        if ext == ".dxf":
            body = dxf_report(path)
        elif ext == ".dwg":
            body = dwg_report(path)
        elif ext == ".pdf":
            body = pdf_report(path)
        elif ext in IMAGE_EXT:
            body = image_report(path)
        else:
            return []
    except Exception as exc:  # okunamayan dosya raporda görünmeli, betik durmamalı
        body = [f"- Okunamadı: {exc}"]
    return [f"## {path.name}", *body, ""]


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    files = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        files += sorted(f for f in p.rglob("*") if f.is_file()) if p.is_dir() else [p]
    print("# Proje dosyaları\n")
    for f in files:
        print("\n".join(report(f)))


if __name__ == "__main__":
    main()
