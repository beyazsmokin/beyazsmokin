#!/usr/bin/env python3
"""İdarenin metrajı ile hesaplanan metrajı poz numarasına göre kıyaslar.

Kullanım: python3 metraj_kiyas.py idare.csv hesap.csv [tolerans_yuzde] [--csv metraj-kiyas.csv]

CSV sütunları: poz_no, tanim, birim, miktar[, birim_fiyat] (ondalık ayırıcı nokta veya virgül).
--csv verilirse Excel şablonunun "BFTC Kıyas" sayfasını besleyen dosyayı da yazar
(poz_no, tanim, birim, idare, hesap, birim_fiyat).
"""
import csv
import sys


def num(v):
    s = str(v or "").strip()
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return float(s)


def load(path: str) -> dict[str, dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = {}
        for r in csv.DictReader(f):
            r["miktar"] = num(r["miktar"])
            r["birim_fiyat"] = num(r.get("birim_fiyat"))
            rows[r["poz_no"].strip()] = r
        return rows


def main() -> None:
    args = sys.argv[1:]
    out_csv = None
    if "--csv" in args:
        i = args.index("--csv")
        out_csv = args[i + 1]
        del args[i:i + 2]
    if len(args) < 2:
        sys.exit(__doc__)
    idare, hesap = load(args[0]), load(args[1])
    tol = float(args[2]) if len(args) > 2 else 5.0

    rows = []
    print("| Poz | Tanım | Birim | İdare | Hesap | Fark % | Not |")
    print("|-----|-------|-------|-------|-------|--------|-----|")
    for poz in sorted(idare.keys() | hesap.keys()):
        a, b = idare.get(poz), hesap.get(poz)
        ref = a or b
        ia = a["miktar"] if a else None
        hb = b["miktar"] if b else None
        if a and b:
            diff = (hb - ia) / ia * 100 if ia else float("inf")
            note = "cetvelde eksik" if diff > tol else "cetvelde fazla" if diff < -tol else ""
            print(f"| {poz} | {ref['tanim']} | {ref['birim']} | {ia:.2f} | {hb:.2f} | {diff:+.1f} | {note} |")
        elif a:
            print(f"| {poz} | {ref['tanim']} | {ref['birim']} | {ia:.2f} | - | - | projede bulunamadı |")
        else:
            print(f"| {poz} | {ref['tanim']} | {ref['birim']} | - | {hb:.2f} | - | cetvelde yok |")
        fiyat = (a or {}).get("birim_fiyat") or (b or {}).get("birim_fiyat")
        rows.append({"poz_no": poz, "tanim": ref["tanim"], "birim": ref["birim"],
                     "idare": "" if ia is None else ia, "hesap": "" if hb is None else hb,
                     "birim_fiyat": "" if fiyat is None else fiyat})

    if out_csv:
        with open(out_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["poz_no", "tanim", "birim", "idare", "hesap", "birim_fiyat"])
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
