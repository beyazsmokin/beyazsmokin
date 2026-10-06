#!/usr/bin/env python3
"""Bir ihale klasöründeki analiz çıktılarından Excel raporu üretir.

Kullanım: python3 excel_rapor.py <İhaleler/ihale-kodu> [sablon.xlsx]

Okur: calisma/*.md (Markdown tabloları ve "- Alan: değer" satırları), calisma/*.csv
Yazar: <ihale-kodu> Analiz.xlsx (ihale klasörünün içine)

Şablon verilirse (ya da .sistem/sablonlar/analiz.xlsx varsa) o kopyalanır:
şablonda aynı adlı sayfa varsa veriler o sayfanın ilk boş satırından itibaren
yazılır, yoksa yeni sayfa eklenir. Gerektirir: openpyxl.
"""
import csv
import re
import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

SHEETS = [  # (sayfa adı, kaynak dosya)
    ("Özet", "01-ozet.md"),
    ("Yeterlilik", "02-idari.md"),
    ("Teknik", "03-teknik.md"),
    ("Mali", "04-mali.md"),
    ("Riskler", "05-riskler.md"),
    ("Metraj", "06-metraj.md"),
]
HEADER_FILL = PatternFill("solid", fgColor="163460")
HEADER_FONT = Font(bold=True, color="FFFFFF")
RISK_FILL = {"yüksek": "F4C7C3", "orta": "FCE8B2", "düşük": "D9EAD3"}


def md_tables(text: str) -> list[list[list[str]]]:
    tables, cur = [], []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", c) for c in cells if c):
                cur.append(cells)
        elif cur:
            tables.append(cur)
            cur = []
    if cur:
        tables.append(cur)
    return tables


def md_fields(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        m = re.match(r"\s*-\s*([^:]{1,60}):\s*(.*)", line)
        if m:
            rows.append([m.group(1).strip(), m.group(2).strip()])
    return rows


def to_number(v: str):
    s = v.replace("%", "").strip()
    if re.fullmatch(r"[+-]?\d{1,3}(\.\d{3})*(,\d+)?", s) and ("," in s or "." in s):
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s) if re.fullmatch(r"[+-]?\d+(\.\d+)?", s) else v
    except ValueError:
        return v


def write_block(ws, rows: list[list[str]], header: bool = True) -> None:
    start = ws.max_row + 2 if ws.max_row > 1 or ws["A1"].value else 1
    for i, row in enumerate(rows):
        for j, val in enumerate(row, 1):
            c = ws.cell(row=start + i, column=j, value=val if i == 0 and header else to_number(val))
            c.alignment = Alignment(wrap_text=True, vertical="top")
            if i == 0 and header:
                c.fill, c.font = HEADER_FILL, HEADER_FONT
        level = next((k for k in RISK_FILL if any(k in str(v).lower() for v in row)), None)
        if level and i > 0:
            for j in range(1, len(row) + 1):
                ws.cell(row=start + i, column=j).fill = PatternFill("solid", fgColor=RISK_FILL[level])


def autosize(ws) -> None:
    for col in ws.columns:
        width = max((len(str(c.value)) for c in col if c.value is not None), default=8)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max(width + 2, 10), 60)
    ws.freeze_panes = "A2"


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ihale = Path(sys.argv[1])
    calisma = ihale / "calisma"
    kod = ihale.name

    sablon = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    if sablon is None:
        for parent in ihale.resolve().parents:
            cand = parent / ".sistem" / "sablonlar" / "analiz.xlsx"
            if cand.exists():
                sablon = cand
                break
    if sablon and sablon.exists():
        wb = load_workbook(sablon)
    else:
        wb = Workbook()
        wb.remove(wb.active)

    def sheet(name):
        return wb[name] if name in wb.sheetnames else wb.create_sheet(name[:31])

    for name, fname in SHEETS:
        f = calisma / fname
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        ws = sheet(name)
        fields = md_fields(text)
        if fields:
            write_block(ws, [["Alan", "Değer"], *fields])
        for t in md_tables(text):
            write_block(ws, t)
        autosize(ws)

    for f in sorted(calisma.glob("*.csv")):
        with open(f, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))
        if rows:
            ws = sheet(f.stem.replace("-", " ").title())
            write_block(ws, rows)
            autosize(ws)

    if not wb.sheetnames:
        sys.exit(f"{calisma} içinde rapora alınacak çıktı yok")
    out = ihale / f"{kod} Analiz.xlsx"
    wb.save(out)
    print(f"Excel raporu: {out}")


if __name__ == "__main__":
    main()
