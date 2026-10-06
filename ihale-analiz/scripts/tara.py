#!/usr/bin/env python3
"""İhale listesini firma profiline ve kullanıcının beğen/reddet geçmişine göre skorlar.

Kullanım:
  python3 tara.py liste.csv --cikti "Taramalar/2026-10-06.md" \
      [--iller "Ankara,Konya"] [--kelimeler "okul,bina,onarım"] \
      [--butce-min 1000000] [--butce-max 50000000] [--vt ihale.db]

Girdi CSV: ikn,idare,il,konu,tur,yaklasik[,son_tarih]
Filtre değerleri .sistem/config.yaml içindeki `tarama:` bölümünden alınır.

Skor (aritmetik betikte, K-4.2.1):
  il eşleşmesi +2, her anahtar kelime +2 (en fazla +4),
  bütçe aralıkta +2, aralık dışında -3,
  tercih ağırlığı (vt.py tercih-ozet) her eşleşen idare / il / tür için ağırlık x 3.
"""
import argparse
import csv
from pathlib import Path

import vt
from kisisel_hesap import kucuk


def liste(deger: str | None) -> list[str]:
    return [kucuk(x.strip()) for x in (deger or "").split(",") if x.strip()]


def skorla(r: dict, a, iller, kelimeler, agirlik) -> tuple[float, list[str]]:
    puan, neden = 0.0, []
    if iller and kucuk(r.get("il")) in iller:
        puan += 2
        neden.append("il")
    hit = [k for k in kelimeler if k in kucuk(r.get("konu"))]
    if hit:
        puan += min(2 * len(hit), 4)
        neden.append("kelime: " + ", ".join(hit))
    y = vt.num(r.get("yaklasik"))
    if y is not None and (a.butce_min or a.butce_max):
        if (a.butce_min or 0) <= y <= (a.butce_max or float("inf")):
            puan += 2
            neden.append("bütçe uygun")
        else:
            puan -= 3
            neden.append("bütçe dışı")
    for alan, _ in vt.TERCIH_ALANLARI:
        w = agirlik.get((alan, r.get(alan)))
        if w:
            puan += 3 * w[2]
            neden.append(f"tercih {alan} {w[2]:+.2f}")
    return round(puan, 2), neden


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv", type=Path)
    p.add_argument("--cikti", type=Path, required=True)
    p.add_argument("--iller")
    p.add_argument("--kelimeler")
    p.add_argument("--butce-min", type=vt.num)
    p.add_argument("--butce-max", type=vt.num)
    p.add_argument("--vt", type=Path, default=None)
    a = p.parse_args()

    con = vt.connect(a.vt or vt.default_db())
    agirlik = vt.tercih_agirliklari(con)
    with open(a.csv, encoding="utf-8-sig", newline="") as f:
        satirlar = list(csv.DictReader(f))
    iller, kelimeler = liste(a.iller), liste(a.kelimeler)

    sonuc = sorted(((*skorla(r, a, iller, kelimeler, agirlik), r) for r in satirlar),
                   key=lambda x: -x[0])
    md = [f"# Tarama: {a.cikti.stem}\n", f"{len(sonuc)} ihale skorlandı. "
          "Beğendiğin ya da ilgilenmediğin ihaleyi söylersen sonraki taramalar buna göre sıralanır.\n",
          "| Skor | İKN | İdare | İl | Konu | Tür | Yaklaşık maliyet | Son tarih | Neden |",
          "|---|---|---|---|---|---|---|---|---|"]
    for puan, neden, r in sonuc:
        md.append(f"| {puan} | {r.get('ikn', '')} | {r.get('idare', '')} | {r.get('il', '')} | "
                  f"{r.get('konu', '')} | {r.get('tur', '')} | {r.get('yaklasik', '')} | "
                  f"{r.get('son_tarih', '')} | {'; '.join(neden)} |")
    a.cikti.parent.mkdir(parents=True, exist_ok=True)
    a.cikti.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Tarama: {a.cikti} ({len(sonuc)} ihale)")


if __name__ == "__main__":
    main()
