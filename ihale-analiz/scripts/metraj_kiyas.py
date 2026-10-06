#!/usr/bin/env python3
"""İdarenin metrajı ile hesaplanan metrajı poz numarasına göre kıyaslar.

Kullanım: python3 metraj_kiyas.py idare.csv hesap.csv [tolerans_yuzde]

CSV sütunları: poz_no, tanim, birim, miktar (ondalık ayırıcı nokta veya virgül).
"""
import csv
import sys


def load(path: str) -> dict[str, dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = {}
        for r in csv.DictReader(f):
            r["miktar"] = float(str(r["miktar"]).replace(".", "").replace(",", ".")
                                if "," in str(r["miktar"]) else r["miktar"])
            rows[r["poz_no"].strip()] = r
        return rows


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    idare, hesap = load(sys.argv[1]), load(sys.argv[2])
    tol = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0

    print("| Poz | Tanım | Birim | İdare | Hesap | Fark % | Not |")
    print("|-----|-------|-------|-------|-------|--------|-----|")
    for poz in sorted(idare.keys() | hesap.keys()):
        a, b = idare.get(poz), hesap.get(poz)
        ref = a or b
        if a and b:
            diff = (b["miktar"] - a["miktar"]) / a["miktar"] * 100 if a["miktar"] else float("inf")
            note = "cetvelde eksik" if diff > tol else "cetvelde fazla" if diff < -tol else ""
            print(f"| {poz} | {ref['tanim']} | {ref['birim']} | {a['miktar']:.2f} | "
                  f"{b['miktar']:.2f} | {diff:+.1f} | {note} |")
        elif a:
            print(f"| {poz} | {ref['tanim']} | {ref['birim']} | {a['miktar']:.2f} | - | - | projede bulunamadı |")
        else:
            print(f"| {poz} | {ref['tanim']} | {ref['birim']} | - | {b['miktar']:.2f} | - | cetvelde yok |")


if __name__ == "__main__":
    main()
