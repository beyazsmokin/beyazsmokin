#!/usr/bin/env python3
"""DWG çeviricisini bulur; yoksa kullanıcıya neden gerektiğini ve diğer yolu açıklar.

Kullanım: python3 dwg_cevirici.py        # durumu ve açıklamayı yazar

Aranan programlar (ikisi de ücretsiz):
- ODA File Converter (önerilen; Windows, macOS, Linux)
- LibreDWG `dwg2dxf`
"""
import glob
import shutil
import sys
from pathlib import Path

ODA_URL = "https://www.opendesign.com/guestfiles/oda_file_converter"
LIBREDWG_URL = "https://www.gnu.org/software/libredwg/"

ACIKLAMA = f"""\
DWG çevirici bulunamadı.

Neden gerekli?
  DWG, AutoCAD'in kapalı dosya biçimidir; skill'in metraj betikleri onu
  doğrudan okuyamaz. Çizimden katman, uzunluk, alan ve blok (kapı, pencere
  vb.) sayılarını ölçebilmek için DWG önce açık biçim olan DXF'e çevrilir.
  Bu çeviriyi bilgisayarınızdaki ücretsiz bir program yapar.

Kurarsanız:
  İhale projelerindeki DWG dosyaları otomatik olarak DXF'e çevrilir ve
  metraj doğrudan çizimden ölçülür. Sizden bir şey istenmez.

Kurmazsanız:
  Her DWG çizimi için sizden DXF ya da PDF halini isteriz:
  - AutoCAD'de: Farklı Kaydet > dosya türü DXF
  - Ya da çizimi PDF'e yazdırın (vektörel PDF)
  DXF ile ölçüm aynı doğrulukta yapılır. PDF'te ölçek paftadan okunur;
  taranmış PDF ve görsellerden okunan ölçüler TAHMİN etiketi alır.
  Diğer formatlardaki çizimlerle analiz devam eder; DWG'den ölçü uydurulmaz.

Önerilen: ODA File Converter (ücretsiz)
  {ODA_URL}
  Kurduktan sonra ek ayar gerekmez; skill programı kendisi bulur.
"""


def bul() -> tuple[str, str] | None:
    """(tür, yol) döndürür: tür 'dwg2dxf' ya da 'oda'; bulunamazsa None."""
    if p := shutil.which("dwg2dxf"):
        return "dwg2dxf", p
    if p := shutil.which("ODAFileConverter"):
        return "oda", p
    adaylar = []
    if sys.platform == "win32":
        for kok in ("C:/Program Files", "C:/Program Files (x86)"):
            adaylar += glob.glob(f"{kok}/ODA/ODAFileConverter*/ODAFileConverter.exe")
    elif sys.platform == "darwin":
        adaylar += glob.glob("/Applications/ODAFileConverter*.app/Contents/MacOS/ODAFileConverter")
    else:
        adaylar += ["/usr/bin/ODAFileConverter", "/usr/local/bin/ODAFileConverter"]
        adaylar += glob.glob("/opt/ODAFileConverter*/ODAFileConverter")
    for a in sorted(adaylar, reverse=True):  # en yeni sürüm önce
        if Path(a).exists():
            return "oda", a
    return None


def durum_metni() -> str:
    c = bul()
    if c:
        return f"DWG çevirici bulundu ({'ODA File Converter' if c[0] == 'oda' else 'LibreDWG'}): {c[1]}"
    return ACIKLAMA


if __name__ == "__main__":
    print(durum_metni())
