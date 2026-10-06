#!/usr/bin/env python3
"""Gelen Dosyalar klasöründeki dosyaları yeni bir ihale klasörüne taşır.

Kullanım: python3 yeni_ihale.py <calisma-alani> <ihale-kodu> [dosya ...]

Dosya adı verilmezse "Gelen Dosyalar" içindeki her şey (BENİ OKU hariç)
taşınır. Zip arşivleri kaynak/ altına açılır.
Oluşan yapı: İhaleler/<ihale-kodu>/{kaynak,calisma}/
"""
import re
import shutil
import sys
import zipfile
from pathlib import Path

KEEP = {"BENİ OKU.txt"}


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    root, kod = Path(sys.argv[1]), re.sub(r'[<>:"/\\|?*]', "-", sys.argv[2]).strip()
    gelen = root / "Gelen Dosyalar"
    hedef = root / "İhaleler" / kod
    kaynak = hedef / "kaynak"
    kaynak.mkdir(parents=True, exist_ok=True)
    (hedef / "calisma").mkdir(exist_ok=True)

    files = [gelen / n for n in sys.argv[3:]] if len(sys.argv) > 3 else [
        p for p in gelen.iterdir() if p.name not in KEEP]
    for f in files:
        dst = kaynak / f.name
        if f.suffix.lower() == ".zip":
            with zipfile.ZipFile(f) as z:
                z.extractall(kaynak / f.stem)
        shutil.move(str(f), dst)
        print(f"taşındı: {f.name}")
    print(f"İhale klasörü: {hedef}")


if __name__ == "__main__":
    main()
