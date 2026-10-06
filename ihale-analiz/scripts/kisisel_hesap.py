#!/usr/bin/env python3
"""Kullanıcının kişisel hesap kurallarını metraja uygular, sistem tahminiyle yan yana koyar.

Kullanım: python3 kisisel_hesap.py <metraj.csv> [--vt ihale.db]

Girdi CSV: poz_no,tanim,birim,miktar,birim_fiyat
Kurallar: vt.py kural-ekle ile kaydedilen aktif kurallar.
Yazar (CSV ile aynı klasöre): kisisel-hesap.csv ve 07-kisisel-hesap.md

Sistem tahmini hiçbir zaman değişmez (kurallar.md). Birim fiyatı olmayan
kalemler hesaba katılmaz ve ayrıca listelenir (K-4.6).
"""
import argparse
import csv
from pathlib import Path

import vt


def kucuk(s: str) -> str:
    return (s or "").replace("İ", "i").replace("I", "ı").lower()


def eslesir(kural, satir) -> bool:
    k = (kural["kapsam"] or "").strip()
    if not k:
        return True
    return satir["poz_no"].startswith(k) or kucuk(k) in kucuk(satir.get("tanim"))


def tl(x: float) -> str:
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " ₺"


def hesapla(satirlar, kurallar):
    kalemler, fiyatsiz, sabitler = [], [], []
    for r in satirlar:
        miktar, bf = vt.num(r.get("miktar")), vt.num(r.get("birim_fiyat"))
        if miktar is None or bf is None:
            fiyatsiz.append(r)
            continue
        sistem = miktar * bf
        kisisel_bf, carpan, uygulanan = bf, 1.0, []
        for k in kurallar:
            if not eslesir(k, r):
                continue
            if k["islem"] == "birim_fiyat":
                kisisel_bf = k["deger"]
            elif k["islem"] == "yuzde_ekle":
                carpan *= 1 + k["deger"] / 100
            elif k["islem"] == "yuzde_cikar":
                carpan *= 1 - k["deger"] / 100
            else:
                continue
            uygulanan.append(k["ad"])
        kalemler.append({**r, "sistem": sistem, "kisisel": miktar * kisisel_bf * carpan,
                         "kurallar": ", ".join(uygulanan)})
    for k in kurallar:
        if k["islem"] == "tutar_ekle" and any(eslesir(k, r) for r in satirlar):
            sabitler.append((k["ad"], k["deger"]))
    return kalemler, fiyatsiz, sabitler


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv", type=Path)
    p.add_argument("--vt", type=Path, default=None)
    a = p.parse_args()

    con = vt.connect(a.vt or vt.default_db())
    kurallar = con.execute("SELECT * FROM hesap_kurallari WHERE aktif=1 ORDER BY id").fetchall()
    with open(a.csv, encoding="utf-8-sig", newline="") as f:
        satirlar = list(csv.DictReader(f))

    kalemler, fiyatsiz, sabitler = hesapla(satirlar, kurallar)
    sistem = sum(k["sistem"] for k in kalemler)
    kisisel = sum(k["kisisel"] for k in kalemler) + sum(d for _, d in sabitler)

    out_csv = a.csv.parent / "kisisel-hesap.csv"
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["poz_no", "tanim", "birim", "miktar", "birim_fiyat", "sistem_tutar",
                    "kisisel_tutar", "uygulanan_kurallar"])
        for k in kalemler:
            w.writerow([k["poz_no"], k.get("tanim"), k.get("birim"), k.get("miktar"), k.get("birim_fiyat"),
                        round(k["sistem"], 2), round(k["kisisel"], 2), k["kurallar"]])

    satir = f"Sistem tahmini: {tl(sistem)} · Sizin yönteminizle: {tl(kisisel)}"
    md = [f"# Kişisel hesap\n", f"**{satir}**\n",
          "- Sistem tahmini etiketi: dayandığı birim fiyatın etiketi (BELGE / RESMİ / ARŞİV)",
          "- Kişisel tutar etiketi: TAHMİN (kullanıcı kuralı)\n",
          "| Kural | Kapsam | İşlem | Değer |", "|---|---|---|---|"]
    md += [f"| {k['ad']} | {k['kapsam'] or 'hepsi'} | {k['islem']} | {k['deger']} |" for k in kurallar]
    if not kurallar:
        md.append("| (kural yok) | | | |")
    fark = [k for k in kalemler if k["kurallar"]]
    if fark:
        md += ["\n| Poz | Tanım | Sistem tutarı | Kişisel tutar | Kurallar |", "|---|---|---|---|---|"]
        md += [f"| {k['poz_no']} | {k.get('tanim') or ''} | {tl(k['sistem'])} | {tl(k['kisisel'])} | {k['kurallar']} |"
               for k in fark]
    for ad, d in sabitler:
        md.append(f"\n- Sabit ek ({ad}): {tl(d)}")
    if fiyatsiz:
        md.append(f"\n- Birim fiyatı ya da miktarı olmadığı için hesaba katılmayan kalem: {len(fiyatsiz)} "
                  f"({', '.join(r['poz_no'] for r in fiyatsiz[:10])})")
    (a.csv.parent / "07-kisisel-hesap.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(satir)


if __name__ == "__main__":
    main()
