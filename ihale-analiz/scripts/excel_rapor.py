#!/usr/bin/env python3
"""Bir ihale klasöründeki analiz çıktılarını Excel şablonuna doldurur.

Kullanım: python3 excel_rapor.py <İhaleler/ihale-kodu> [--tur birim-fiyat|anahtar-teslim] [--sablon dosya.xlsx]

Şablon seçimi: --sablon verilmişse o; yoksa teklif türüne göre (01-ozet.md içindeki
"Teklif türü" ya da --tur) önce .sistem/sablonlar/, sonra skill'in templates/excel/
klasöründeki birim-fiyat.xlsx veya anahtar-teslim.xlsx.

Şablona sadık kalır: yalnızca şablonun gizli "_harita" sayfasında tanımlı sütunlara,
formül içermeyen hücrelere yazar; sayfa, sütun, formül ya da biçim eklemez veya silmez.
Yazar: <ihale-kodu> Analiz.xlsx (ihale klasörünün içine). Gerektirir: openpyxl.
"""
import argparse
import csv
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

BAS, HEADER_ROW = 5, 4
SKILL_SABLON = Path(__file__).resolve().parent.parent / "templates" / "excel"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s).replace("ı", "i").replace("İ", "i")).lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s)


def md_tablo(text: str) -> list[dict]:
    satirlar = [l.strip() for l in text.splitlines() if l.strip().startswith("|") and l.strip().endswith("|")]
    satirlar = [[c.strip() for c in l.strip("|").split("|")] for l in satirlar]
    satirlar = [s for s in satirlar if not all(re.fullmatch(r":?-+:?", c) for c in s if c)]
    if not satirlar:
        return []
    bas = satirlar[0]
    return [{norm(b): v for b, v in zip(bas, s)} for s in satirlar[1:]]


def md_alanlar(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        m = re.match(r"\s*-\s*([^:]{1,80}):\s*(.*)", line)
        if m and m.group(2).strip():
            out[norm(m.group(1))] = m.group(2).strip()
    return out


def karar(ihale: Path) -> dict:
    out = {norm("tarih"): date.today()}
    for f in ihale.glob("*Rapor.md"):
        m = re.search(r"\*\*Karar:\*\*\s*([^.\n]+)\.?\s*(.*)", f.read_text(encoding="utf-8"))
        if m:
            out[norm("karar")] = m.group(1).strip()
            out[norm("gerekce")] = m.group(2).strip()
    return out


def yaz(hucre, v, puan=False):
    """Değeri hücreye yazar; yalnızca şablonda sayı/tarih biçimli hücrelerde dönüştürür.
    puan: kaynak değer yüzde puanı (55 = %55) olarak verilmiştir."""
    if hucre.number_format == "General" or isinstance(v, (int, float, date)):
        hucre.value = v
        return
    s = str(v).strip()
    m = re.fullmatch(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", s)
    if m and ("d" in hucre.number_format or "y" in hucre.number_format):
        hucre.value = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        return
    hucre.value = sayi(s, "%" in hucre.number_format, puan)


def sayi(s: str, yuzde=False, puan=False):
    ham = s.replace("%", "").replace("TL", "").replace("₺", "").strip()
    if re.fullmatch(r"[+-]?\d{1,3}(\.\d{3})+(,\d+)?|[+-]?\d+,\d+", ham):
        ham = ham.replace(".", "").replace(",", ".")
    if not re.fullmatch(r"[+-]?\d+(\.\d+)?", ham):
        return s
    n = float(ham)
    if "%" in s or puan or (yuzde and n > 1):     # "%3", puan "3" ve oran hücresine "3" -> 0.03
        return n / 100
    return int(n) if n.is_integer() and not yuzde else n


def kaynak_oku(calisma: Path, ihale: Path, kaynak: str):
    tip, _, ad = kaynak.partition(":")
    if tip == "karar":
        return karar(ihale)
    f = calisma / ad
    if not f.exists():
        return None
    if tip == "csv":
        with open(f, encoding="utf-8-sig", newline="") as fh:
            return [{norm(k): v for k, v in r.items() if k} for r in csv.DictReader(fh)]
    text = f.read_text(encoding="utf-8")
    return md_tablo(text) if tip == "tablo" else md_alanlar(text)


def deger(kayit: dict, alan: str):
    for a in alan.split("|"):
        v = kayit.get(norm(a.rstrip("%")))
        if v not in (None, ""):
            return v
    return None


def tur_bul(calisma: Path, verilen: str | None) -> str:
    if verilen:
        return verilen
    f = calisma / "01-ozet.md"
    t = norm(md_alanlar(f.read_text(encoding="utf-8")).get(norm("Teklif türü"), "")) if f.exists() else ""
    return "anahtar-teslim" if ("anahtar" in t or "goturu" in t) else "birim-fiyat"


def sablon_bul(ihale: Path, tur: str) -> Path:
    for parent in ihale.resolve().parents:
        cand = parent / ".sistem" / "sablonlar" / f"{tur}.xlsx"
        if cand.exists():
            return cand
    return SKILL_SABLON / f"{tur}.xlsx"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ihale", type=Path)
    p.add_argument("--tur", choices=["birim-fiyat", "anahtar-teslim"])
    p.add_argument("--sablon", type=Path)
    a = p.parse_args()

    ihale, calisma = a.ihale, a.ihale / "calisma"
    tur = tur_bul(calisma, a.tur)
    sablon = a.sablon or sablon_bul(ihale, tur)
    if not sablon.exists():
        sys.exit(f"Şablon bulunamadı: {sablon}")
    wb = load_workbook(sablon)
    if "_harita" not in wb.sheetnames:
        sys.exit(f"{sablon} bir ihale-analiz şablonu değil (_harita sayfası yok)")

    gruplar: dict[tuple, list] = {}
    for sayfa, kaynak, baslik, alan in wb["_harita"].iter_rows(min_row=3, values_only=True):
        if sayfa:
            gruplar.setdefault((sayfa, kaynak), []).append((baslik, alan))

    rapor = []
    for (sayfa, kaynak), eslesmeler in gruplar.items():
        veri = kaynak_oku(calisma, ihale, kaynak)
        if not veri or sayfa not in wb.sheetnames:
            continue
        ws = wb[sayfa]
        if isinstance(veri, dict):            # Özet: A sütunundaki etikete göre B'ye yaz
            etiket = {norm(ws.cell(r, 1).value): r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value}
            for baslik, alan in eslesmeler:
                r = etiket.get(norm(baslik))
                v = deger(veri, alan)
                if r and v is not None and not str(ws.cell(r, 2).value or "").startswith("="):
                    yaz(ws.cell(r, 2), v, alan.endswith("%"))
            rapor.append(f"{sayfa}: alanlar")
            continue
        sutun = {norm(ws.cell(HEADER_ROW, c).value): c for c in range(1, ws.max_column + 1) if ws.cell(HEADER_ROW, c).value}
        kapasite = sum(1 for r in range(BAS, ws.max_row + 1))
        for i, kayit in enumerate(veri):
            if i >= kapasite:
                print(f"UYARI: {sayfa} sayfası {kapasite} satırla sınırlı, {len(veri) - kapasite} satır yazılmadı")
                break
            r = BAS + i
            for baslik, alan in eslesmeler:
                c = sutun.get(norm(baslik))
                if not c or str(ws.cell(r, c).value or "").startswith("="):
                    continue
                v = i + 1 if alan == "#sira" else deger(kayit, alan)
                if v is not None:
                    yaz(ws.cell(r, c), v, alan.endswith("%"))
        rapor.append(f"{sayfa}: {min(len(veri), kapasite)} satır")

    # yazdırma alanını dolu satırlarla sınırla (boş şablon satırları basılmasın)
    for ws in wb.worksheets:
        if ws.title in ("Özet", "_harita") or ws.cell(HEADER_ROW, 1).value is None:
            continue
        son = HEADER_ROW
        for r in range(BAS, ws.max_row + 1):
            if any(ws.cell(r, c).value not in (None, "") and not str(ws.cell(r, c).value).startswith("=")
                   for c in range(1, ws.max_column + 1)):
                son = r
        ws.print_area = f"A1:{get_column_letter(ws.max_column)}{son}"

    out = ihale / f"{ihale.name} Analiz.xlsx"
    wb.save(out)
    print(f"Şablon: {sablon.name} ({tur})")
    print("\n".join(rapor))
    print(f"Excel raporu: {out}")


if __name__ == "__main__":
    main()
