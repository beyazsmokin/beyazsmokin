#!/usr/bin/env python3
"""ihale-analiz öğrenen veritabanı (SQLite, ek kurulum gerektirmez).

Ajanlar analizden önce `baglam` ile geçmiş bilgiyi okur, analizden sonra
sonuçları ve öğrendiklerini buraya yazar. Veritabanı her analizle büyür.

Kullanım (veritabanı yolu varsayılan: <çalışma alanı>/.sistem/veritabani/ihale.db):
  vt.py ihale-kaydet --kod K --idare I --konu K --tur birim_fiyat --yaklasik 1500000 --karar katil
  vt.py sonuc --kod K --sonuc kazanildi --teklif 1400000 --kazanan 1380000
  vt.py metraj-yukle --kod K dosya.csv          # poz_no,tanim,birim,miktar[,birim_fiyat]
  vt.py pursantaj-yukle --kod K dosya.csv       # is_grubu,oran
  vt.py ders-ekle --metin "..." [--idare I] [--ajan metraj-analist] [--etiket beton]
  vt.py fiyat 15.150.1001                       # geçmiş birim fiyat istatistiği
  vt.py pursantaj-ort --tur anahtar_teslim      # geçmiş ortalama pursantaj oranları
  vt.py baglam [--idare I] [--konu K] [--ajan A] # ajana verilecek geçmiş bilgi (Markdown)
  vt.py ara KELIME
  vt.py tercih --ikn I --karar begen|reddet [--idare I --il IL --tur T --konu K --yaklasik 2500000 --neden "..."]
  vt.py tercih-ozet                             # beğen/reddet eğilimleri (tarayıcı skoru buradan beslenir)
  vt.py kural-ekle --ad "Beton firesi" --kapsam beton --islem yuzde_ekle --deger 15 --cumle "betona %15 fire eklerim"
  vt.py kural-listele
  vt.py kural-kapat --id 3

İhale sitesinden gelen veri (siteler.py ile giriş yapıldıysa):
  vt.py katilimci-yukle --kod K --idare I --yaklasik 1500000 [--tarih T] [--kaynak ekap] dosya.csv
                                                # firma,teklif[,durum]  durum: kazanan|gecerli|asiri_dusuk|elendi
  vt.py kurum-fiyat-yukle --idare I [--kod K] [--tarih T] [--kaynak ekap] dosya.csv
                                                # poz_no,tanim,birim,birim_fiyat
  vt.py kurum-fiyat 15.150.1001 [--idare I]     # kurumların geçmiş birim fiyatları
  vt.py tenzilat [--idare I] [--tur T]          # kazanan ve ortalama tenzilat, katılımcı sayısı
  vt.py rakip [--firma F] [--idare I]           # firmaların katılım, kazanma, tenzilat eğilimi
"""
import argparse
import csv
import os
import sqlite3
from datetime import date
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS ihaleler (
  kod TEXT PRIMARY KEY, tarih TEXT, idare TEXT, konu TEXT, tur TEXT,
  yaklasik_maliyet REAL, karar TEXT, sonuc TEXT, teklif REAL, kazanan_teklif REAL,
  notlar TEXT, kayit_tarihi TEXT
);
CREATE TABLE IF NOT EXISTS metraj (
  ihale_kod TEXT, poz_no TEXT, tanim TEXT, birim TEXT, miktar REAL, birim_fiyat REAL,
  kayit_tarihi TEXT
);
CREATE TABLE IF NOT EXISTS pursantaj (
  ihale_kod TEXT, is_grubu TEXT, oran REAL
);
CREATE TABLE IF NOT EXISTS dersler (
  id INTEGER PRIMARY KEY AUTOINCREMENT, tarih TEXT, metin TEXT, idare TEXT,
  ajan TEXT, etiket TEXT, ihale_kod TEXT, kullanim INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS tercihler (
  id INTEGER PRIMARY KEY AUTOINCREMENT, tarih TEXT, ikn TEXT, karar TEXT, idare TEXT,
  il TEXT, tur TEXT, konu TEXT, yaklasik_maliyet REAL, neden TEXT
);
CREATE TABLE IF NOT EXISTS hesap_kurallari (
  id INTEGER PRIMARY KEY AUTOINCREMENT, tarih TEXT, ad TEXT, kapsam TEXT, islem TEXT,
  deger REAL, kaynak_cumle TEXT, aktif INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS katilimcilar (
  ihale_kod TEXT, idare TEXT, tarih TEXT, yaklasik_maliyet REAL, firma TEXT, teklif REAL,
  durum TEXT, kaynak TEXT, kayit_tarihi TEXT
);
CREATE TABLE IF NOT EXISTS kurum_fiyatlari (
  idare TEXT, ihale_kod TEXT, tarih TEXT, poz_no TEXT, tanim TEXT, birim TEXT,
  birim_fiyat REAL, kaynak TEXT, kayit_tarihi TEXT
);
CREATE INDEX IF NOT EXISTS ix_katilimci_firma ON katilimcilar(firma);
CREATE INDEX IF NOT EXISTS ix_kurum_fiyat_poz ON kurum_fiyatlari(poz_no);
CREATE INDEX IF NOT EXISTS ix_metraj_poz ON metraj(poz_no);
CREATE INDEX IF NOT EXISTS ix_ihale_idare ON ihaleler(idare);
"""


def default_db() -> Path:
    env = os.environ.get("IHALE_VT")
    if env:
        return Path(env)
    # scripts/ -> skill/ -> .sistem/
    sistem = Path(__file__).resolve().parents[2]
    if sistem.name == ".sistem":
        return sistem / "veritabani" / "ihale.db"
    return Path.cwd() / "ihale.db"


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def num(v):
    if v in (None, ""):
        return None
    s = str(v).strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return float(s)


def today() -> str:
    return date.today().isoformat()


def cmd_ihale_kaydet(con, a):
    con.execute(
        """INSERT INTO ihaleler (kod, tarih, idare, konu, tur, yaklasik_maliyet, karar, notlar, kayit_tarihi)
           VALUES (?,?,?,?,?,?,?,?,?)
           ON CONFLICT(kod) DO UPDATE SET tarih=excluded.tarih, idare=excluded.idare,
             konu=excluded.konu, tur=excluded.tur, yaklasik_maliyet=excluded.yaklasik_maliyet,
             karar=excluded.karar, notlar=excluded.notlar""",
        (a.kod, a.tarih or today(), a.idare, a.konu, a.tur, num(a.yaklasik), a.karar, a.notlar, today()),
    )
    print(f"Kaydedildi: {a.kod}")


def cmd_sonuc(con, a):
    cur = con.execute(
        "UPDATE ihaleler SET sonuc=?, teklif=?, kazanan_teklif=? WHERE kod=?",
        (a.sonuc, num(a.teklif), num(a.kazanan), a.kod),
    )
    print("Güncellendi" if cur.rowcount else f"İhale bulunamadı: {a.kod}")


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def cmd_metraj_yukle(con, a):
    con.execute("DELETE FROM metraj WHERE ihale_kod=?", (a.kod,))
    rows = read_csv(a.dosya)
    con.executemany(
        "INSERT INTO metraj VALUES (?,?,?,?,?,?,?)",
        [(a.kod, r["poz_no"].strip(), r.get("tanim"), r.get("birim"), num(r.get("miktar")),
          num(r.get("birim_fiyat")), today()) for r in rows],
    )
    print(f"{len(rows)} metraj kalemi kaydedildi")


def cmd_pursantaj_yukle(con, a):
    con.execute("DELETE FROM pursantaj WHERE ihale_kod=?", (a.kod,))
    rows = read_csv(a.dosya)
    con.executemany("INSERT INTO pursantaj VALUES (?,?,?)",
                    [(a.kod, r["is_grubu"].strip(), num(r["oran"])) for r in rows])
    print(f"{len(rows)} pursantaj satırı kaydedildi")


def cmd_ders_ekle(con, a):
    # aynı ders (aynı ajan, idare, metin) her analizde yeniden yazılmasın
    if con.execute("SELECT 1 FROM dersler WHERE metin=? AND ajan IS ? AND idare IS ?",
                   (a.metin, a.ajan, a.idare)).fetchone():
        print("Ders zaten kayıtlı")
        return
    con.execute("INSERT INTO dersler (tarih, metin, idare, ajan, etiket, ihale_kod) VALUES (?,?,?,?,?,?)",
                (today(), a.metin, a.idare, a.ajan, a.etiket, a.kod))
    print("Ders kaydedildi")


def cmd_fiyat(con, a):
    r = con.execute(
        """SELECT COUNT(*) n, MIN(birim_fiyat) mn, AVG(birim_fiyat) ort, MAX(birim_fiyat) mx,
                  MAX(m.kayit_tarihi) son, MAX(tanim) tanim, MAX(birim) birim
           FROM metraj m WHERE poz_no=? AND birim_fiyat IS NOT NULL""", (a.poz,)).fetchone()
    if not r["n"]:
        print(f"{a.poz}: geçmiş fiyat yok")
        return
    print(f"{a.poz} {r['tanim']} ({r['birim']}): {r['n']} kayıt, en düşük {r['mn']:.2f}, "
          f"ortalama {r['ort']:.2f}, en yüksek {r['mx']:.2f}, son kayıt {r['son']}")


def gecmis_fiyatlar(con, pozlar, haric_kod=None) -> dict:
    """Pozların başka ihalelerdeki ortalama birim fiyatı (metraj tablosu, ARŞİV)."""
    pozlar = [p for p in pozlar if p]
    if not pozlar:
        return {}
    yer = ",".join("?" * len(pozlar))
    return {r["poz_no"]: round(r["ort"], 2) for r in con.execute(
        f"""SELECT poz_no, AVG(birim_fiyat) ort FROM metraj
            WHERE poz_no IN ({yer}) AND birim_fiyat IS NOT NULL AND (? IS NULL OR ihale_kod <> ?)
            GROUP BY poz_no""", (*pozlar, haric_kod, haric_kod))}


def fiyat_ozeti(con, haric_kod=None, idare=None, limit=150) -> str:
    """Metraj ajanına verilen geçmiş birim fiyat özeti (`vt.py fiyat` ve `kurum-fiyat`un toplu hali)."""
    bizim = con.execute(
        """SELECT poz_no, MAX(tanim) tanim, MAX(birim) birim, COUNT(*) n, MIN(birim_fiyat) mn,
                  AVG(birim_fiyat) ort, MAX(birim_fiyat) mx
           FROM metraj WHERE birim_fiyat IS NOT NULL AND (? IS NULL OR ihale_kod <> ?)
           GROUP BY poz_no ORDER BY n DESC, poz_no LIMIT ?""", (haric_kod, haric_kod, limit)).fetchall()
    kurum = con.execute(
        """SELECT poz_no, MAX(tanim) tanim, MAX(birim) birim, COUNT(*) n, AVG(birim_fiyat) ort,
                  MAX(tarih) son, GROUP_CONCAT(DISTINCT kaynak) kaynak
           FROM kurum_fiyatlari WHERE birim_fiyat IS NOT NULL AND (? IS NULL OR idare LIKE ?)
           GROUP BY poz_no ORDER BY n DESC, poz_no LIMIT ?""",
        (idare, f"%{idare}%" if idare else None, limit)).fetchall()
    out = []
    if bizim:
        out += ["### Geçmiş analizlerdeki birim fiyatlar (ARŞİV)", "| Poz | Tanım | Birim | Kayıt | En düşük | Ortalama | En yüksek |",
                "|---|---|---|---|---|---|---|"]
        out += [f"| {r['poz_no']} | {r['tanim'] or ''} | {r['birim'] or ''} | {r['n']} | {r['mn']:.2f} | {r['ort']:.2f} | "
                f"{r['mx']:.2f} |" for r in bizim]
    if kurum:
        out += ["", f"### Kurum birim fiyatları{' (' + idare + ')' if idare else ''} (ARŞİV, ihale sitesi)",
                "| Poz | Tanım | Birim | Kayıt | Ortalama | Son | Kaynak |", "|---|---|---|---|---|---|---|"]
        out += [f"| {r['poz_no']} | {r['tanim'] or ''} | {r['birim'] or ''} | {r['n']} | {r['ort']:.2f} | {r['son'] or ''} | "
                f"{r['kaynak'] or ''} |" for r in kurum]
    return "\n".join(out) or "Geçmiş birim fiyat yok (ilk analizler; veritabanı her analizle dolar)."


def tutar_oku(v):
    """'1.234.567,89 TL', '1234567.89', '%23,45' gibi site değerlerini sayıya çevirir."""
    import re
    s = re.sub(r"[^\d.,-]", "", str(v or ""))
    if not s:
        return None
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return num(s)
    except ValueError:
        return None


def site_sonuclari_yukle(con, liste, kaynak="ihale sitesi") -> int:
    """Takip sitesinin kesinleşen sonuçlarındaki kazanan ve sözleşme bedelini katılımcı verisine yazar.

    Site yalnızca kazananı verir: katılımcı sayısı bilinmez, `tenzilat` ve `rakip` bunu ayırır.
    Yaklaşık maliyet yoksa sitedeki tenzilat oranından geri hesaplanır."""
    n = 0
    for r in liste or []:
        kod, firma, bedel = r.get("ikn"), (r.get("kazanan") or "").strip(), tutar_oku(r.get("sozlesme_bedeli"))
        if not kod or not firma or not bedel:
            continue
        ym = tutar_oku(r.get("yaklasik"))
        tz = tutar_oku(r.get("tenzilat"))
        if not ym and tz is not None and 0 <= tz < 100:
            ym = round(bedel / (1 - tz / 100), 2)
        con.execute("DELETE FROM katilimcilar WHERE ihale_kod=? AND kaynak=?", (kod, kaynak))
        con.execute("INSERT INTO katilimcilar VALUES (?,?,?,?,?,?,?,?,?)",
                    (kod, r.get("idare"), (r.get("ihale_tarihi") or "")[:10] or today(), ym, firma, bedel,
                     "kazanan", kaynak, today()))
        n += 1
    return n


def cmd_pursantaj_ort(con, a):
    rows = con.execute(
        """SELECT p.is_grubu, AVG(p.oran) ort, COUNT(*) n FROM pursantaj p
           JOIN ihaleler i ON i.kod = p.ihale_kod
           WHERE (? IS NULL OR i.tur = ?) GROUP BY p.is_grubu ORDER BY ort DESC""",
        (a.tur, a.tur)).fetchall()
    if not rows:
        print("Geçmiş pursantaj verisi yok")
    for r in rows:
        print(f"- {r['is_grubu']}: ortalama %{r['ort']:.2f} ({r['n']} ihale)")


def cmd_baglam(con, a):
    print("# Geçmişten öğrenilenler\n")
    like = lambda v: f"%{v}%" if v else None
    dersler = con.execute(
        """SELECT id, tarih, metin, idare, ajan FROM dersler
           WHERE (? IS NULL OR ajan IS NULL OR ajan = ?)
             AND (? IS NULL OR idare IS NULL OR idare LIKE ?)
           ORDER BY tarih DESC LIMIT 30""",
        (a.ajan, a.ajan, a.idare, like(a.idare))).fetchall()
    print("## Dersler")
    for d in dersler:
        etiket = ", ".join(x for x in (d["idare"], d["ajan"]) if x)
        print(f"- {d['tarih']}: {d['metin']}" + (f" ({etiket})" if etiket else ""))
    if not dersler:
        print("- Henüz kayıt yok")
    con.executemany("UPDATE dersler SET kullanim = kullanim + 1 WHERE id=?", [(d["id"],) for d in dersler])

    benzer = con.execute(
        """SELECT * FROM ihaleler WHERE (? IS NOT NULL AND idare LIKE ?) OR (? IS NOT NULL AND konu LIKE ?)
           ORDER BY tarih DESC LIMIT 10""",
        (a.idare, like(a.idare), a.konu, like(a.konu))).fetchall()
    print("\n## Benzer ihaleler")
    for i in benzer:
        print(f"- {i['tarih']} {i['kod']} | {i['idare']} | {i['konu']} | karar: {i['karar']} | "
              f"sonuç: {i['sonuc'] or '-'} | yaklaşık maliyet: {i['yaklasik_maliyet'] or '-'} | "
              f"kazanan teklif: {i['kazanan_teklif'] or '-'}")
    if not benzer:
        print("- Henüz kayıt yok")

    if a.idare:
        tz = tenzilat_satirlari(con, a.idare)
        print("\n## Bu idarenin geçmiş ihaleleri (site verisi)")
        for r in tz[:10]:
            kt = yuzde(r["kazanan"], r["ym"])
            print(f"- {r['tarih']} {r['ihale_kod']}: {str(r['n']) + ' katılımcı' if r['diger'] else 'kazanan'}, kazanan tenzilat "
                  f"{'-' if kt is None else f'%{kt:.2f}'}")
        if not tz:
            print("- Site verisi yok; rakip, katılımcı ve tenzilat analizi sunulamaz")

    ozet = con.execute(
        "SELECT COUNT(*) n, SUM(sonuc='kazanildi') k FROM ihaleler").fetchone()
    print(f"\n## Genel\n- Toplam analiz: {ozet['n']}, kazanılan: {ozet['k'] or 0}")

    agirlik = tercih_agirliklari(con)
    if agirlik:
        etiket = dict(TERCIH_ALANLARI)
        print("\n## Kullanıcı tercihleri")
        for (alan, deger), (b, r, w) in sorted(agirlik.items(), key=lambda x: -abs(x[1][2]))[:10]:
            print(f"- {etiket[alan]} = {deger}: {b} beğeni, {r} ret")


def cmd_ara(con, a):
    q = f"%{a.kelime}%"
    for r in con.execute("SELECT kod, idare, konu FROM ihaleler WHERE kod LIKE ? OR idare LIKE ? OR konu LIKE ?",
                         (q, q, q)):
        print(f"ihale: {r['kod']} | {r['idare']} | {r['konu']}")
    for r in con.execute("SELECT DISTINCT poz_no, tanim FROM metraj WHERE poz_no LIKE ? OR tanim LIKE ? LIMIT 30",
                         (q, q)):
        print(f"poz: {r['poz_no']} | {r['tanim']}")
    for r in con.execute("SELECT tarih, metin FROM dersler WHERE metin LIKE ? OR etiket LIKE ?", (q, q)):
        print(f"ders: {r['tarih']} | {r['metin']}")


def cmd_katilimci_yukle(con, a):
    con.execute("DELETE FROM katilimcilar WHERE ihale_kod=?", (a.kod,))
    rows = read_csv(a.dosya)
    con.executemany(
        "INSERT INTO katilimcilar VALUES (?,?,?,?,?,?,?,?,?)",
        [(a.kod, a.idare, a.tarih or today(), num(a.yaklasik), r["firma"].strip(), num(r.get("teklif")),
          (r.get("durum") or "gecerli").strip(), a.kaynak, today()) for r in rows])
    print(f"{len(rows)} katılımcı kaydedildi")


def cmd_kurum_fiyat_yukle(con, a):
    rows = read_csv(a.dosya)
    if a.kod:
        con.execute("DELETE FROM kurum_fiyatlari WHERE ihale_kod=? AND idare=?", (a.kod, a.idare))
    con.executemany(
        "INSERT INTO kurum_fiyatlari VALUES (?,?,?,?,?,?,?,?,?)",
        [(a.idare, a.kod, a.tarih or today(), r["poz_no"].strip(), r.get("tanim"), r.get("birim"),
          num(r.get("birim_fiyat")), a.kaynak, today()) for r in rows])
    print(f"{len(rows)} kurum birim fiyatı kaydedildi")


def cmd_kurum_fiyat(con, a):
    rows = con.execute(
        """SELECT idare, COUNT(*) n, MIN(birim_fiyat) mn, AVG(birim_fiyat) ort, MAX(birim_fiyat) mx,
                  MAX(tarih) son, MAX(tanim) tanim, MAX(birim) birim
           FROM kurum_fiyatlari WHERE poz_no=? AND birim_fiyat IS NOT NULL
             AND (? IS NULL OR idare LIKE ?) GROUP BY idare ORDER BY son DESC""",
        (a.poz, a.idare, f"%{a.idare}%" if a.idare else None)).fetchall()
    if not rows:
        print(f"{a.poz}: kurum birim fiyatı yok (site girişi yoksa yalnızca rayiç kullanılır)")
    for r in rows:
        print(f"{a.poz} {r['tanim']} ({r['birim']}) | {r['idare']}: {r['n']} kayıt, en düşük {r['mn']:.2f}, "
              f"ortalama {r['ort']:.2f}, en yüksek {r['mx']:.2f}, son {r['son']}")


def tenzilat_satirlari(con, idare=None, tur=None):
    """Her ihale için katılımcı sayısı, kazanan ve ortalama tenzilat (%)."""
    return con.execute(
        """SELECT k.ihale_kod, MAX(k.idare) idare, MAX(k.tarih) tarih, MAX(k.yaklasik_maliyet) ym,
                  COUNT(*) n, SUM(k.durum <> 'kazanan') diger,
                  MAX(CASE WHEN k.durum='kazanan' THEN k.teklif END) kazanan,
                  AVG(k.teklif) ort_teklif
           FROM katilimcilar k LEFT JOIN ihaleler i ON i.kod = k.ihale_kod
           WHERE k.teklif IS NOT NULL AND (? IS NULL OR k.idare LIKE ?) AND (? IS NULL OR i.tur = ?)
           GROUP BY k.ihale_kod HAVING ym > 0 ORDER BY tarih DESC""",
        (idare, f"%{idare}%" if idare else None, tur, tur)).fetchall()


def yuzde(teklif, ym):
    return None if teklif is None or not ym else (1 - teklif / ym) * 100


def cmd_tenzilat(con, a):
    rows = tenzilat_satirlari(con, a.idare, a.tur)
    if not rows:
        print("Tenzilat verisi yok (site girişi yapılmadıysa bu analiz sunulamaz)")
        return
    for r in rows:
        kt = yuzde(r["kazanan"], r["ym"])
        katilim = f"{r['n']} katılımcı" if r["diger"] else "katılımcı sayısı yok (site yalnızca kazananı verir)"
        print(f"- {r['tarih']} {r['ihale_kod']} | {r['idare']} | {katilim} | "
              f"kazanan tenzilat: {'-' if kt is None else f'%{kt:.2f}'} | "
              f"ortalama tenzilat: %{yuzde(r['ort_teklif'], r['ym']):.2f}")
    kaz = [yuzde(r["kazanan"], r["ym"]) for r in rows if r["kazanan"] is not None]
    tam = [r for r in rows if r["diger"]]
    print(f"\nÖzet: {len(rows)} ihale"
          + (f", ortalama katılımcı {sum(r['n'] for r in tam) / len(tam):.1f}" if tam else "")
          + (f", ortalama kazanan tenzilat %{sum(kaz) / len(kaz):.2f}" if kaz else ""))


def cmd_rakip(con, a):
    rows = con.execute(
        """SELECT firma, COUNT(DISTINCT ihale_kod) n, SUM(durum='kazanan') k,
                  AVG(CASE WHEN yaklasik_maliyet > 0 THEN (1 - teklif / yaklasik_maliyet) * 100 END) tz,
                  MAX(tarih) son
           FROM katilimcilar
           WHERE teklif IS NOT NULL AND (? IS NULL OR firma LIKE ?) AND (? IS NULL OR idare LIKE ?)
           GROUP BY firma ORDER BY n DESC, k DESC LIMIT ?""",
        (a.firma, f"%{a.firma}%" if a.firma else None, a.idare, f"%{a.idare}%" if a.idare else None,
         a.limit)).fetchall()
    if not rows:
        print("Rakip verisi yok (site girişi yapılmadıysa bu analiz sunulamaz)")
    for r in rows:
        tz = "-" if r["tz"] is None else f"%{r['tz']:.2f}"
        print(f"- {r['firma']}: {r['n']} ihale, {r['k'] or 0} kazanma, ortalama tenzilat {tz}, son {r['son']}")


ISLEMLER = ("yuzde_ekle", "yuzde_cikar", "tutar_ekle", "birim_fiyat")
TERCIH_ALANLARI = (("idare", "İdare"), ("il", "İl"), ("tur", "Tür"))
ASGARI_KAYIT = 3  # bir özellik bu kadar kararda görülmeden ağırlık almaz


def cmd_tercih(con, a):
    if a.karar not in ("begen", "reddet"):
        raise SystemExit("--karar begen ya da reddet olmalı")
    con.execute(
        """INSERT INTO tercihler (tarih, ikn, karar, idare, il, tur, konu, yaklasik_maliyet, neden)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (today(), a.ikn, a.karar, a.idare, a.il, a.tur, a.konu, num(a.yaklasik), a.neden))
    print(f"Tercih kaydedildi: {a.ikn} -> {a.karar}")


def tercih_agirliklari(con) -> dict:
    """{(alan, değer): (beğeni, ret, ağırlık)}; ağırlık -1..+1, en az ASGARI_KAYIT kararla."""
    sonuc = {}
    for alan, _ in TERCIH_ALANLARI:
        for r in con.execute(
                f"""SELECT {alan} deger, SUM(karar='begen') b, SUM(karar='reddet') r FROM tercihler
                    WHERE {alan} IS NOT NULL AND {alan} != '' GROUP BY {alan}"""):
            n = r["b"] + r["r"]
            if n >= ASGARI_KAYIT:
                sonuc[(alan, r["deger"])] = (r["b"], r["r"], (r["b"] - r["r"]) / n)
    return sonuc


def cmd_tercih_ozet(con, a):
    toplam = con.execute("SELECT COUNT(*) FROM tercihler").fetchone()[0]
    print(f"# Tercih eğilimleri\n\nToplam karar: {toplam}. "
          f"Bir özellik en az {ASGARI_KAYIT} kararda görülmeden ağırlık almaz.\n")
    agirlik = tercih_agirliklari(con)
    if not agirlik:
        print("- Henüz ağırlık alacak kadar karar yok")
        return
    etiket = dict(TERCIH_ALANLARI)
    for (alan, deger), (b, r, w) in sorted(agirlik.items(), key=lambda x: x[1][2]):
        yon = "öne çıkar" if w > 0 else "geri düşer" if w < 0 else "nötr"
        print(f"- {etiket[alan]} = {deger}: {b} beğeni, {r} ret, ağırlık {w:+.2f} ({yon})")


def cmd_kural_ekle(con, a):
    if a.islem not in ISLEMLER:
        raise SystemExit(f"--islem şunlardan biri olmalı: {', '.join(ISLEMLER)}")
    con.execute(
        "INSERT INTO hesap_kurallari (tarih, ad, kapsam, islem, deger, kaynak_cumle) VALUES (?,?,?,?,?,?)",
        (today(), a.ad, a.kapsam, a.islem, num(a.deger), a.cumle))
    print(f"Kural kaydedildi: {a.ad}")


def cmd_kural_listele(con, a):
    rows = con.execute("SELECT * FROM hesap_kurallari ORDER BY id").fetchall()
    if not rows:
        print("Kişisel hesap kuralı yok")
    for r in rows:
        durum = "aktif" if r["aktif"] else "kapalı"
        print(f"{r['id']}. {r['ad']} | kapsam: {r['kapsam'] or 'hepsi'} | {r['islem']} {r['deger']} | "
              f"{durum} | \"{r['kaynak_cumle'] or ''}\"")


def cmd_kural_kapat(con, a):
    cur = con.execute("UPDATE hesap_kurallari SET aktif=0 WHERE id=?", (a.id,))
    print("Kural kapatıldı" if cur.rowcount else f"Kural bulunamadı: {a.id}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--vt", type=Path, default=None, help="veritabanı dosyası")
    sub = p.add_subparsers(dest="komut", required=True)

    s = sub.add_parser("ihale-kaydet")
    for f in ("kod",):
        s.add_argument(f"--{f}", required=True)
    for f in ("tarih", "idare", "konu", "tur", "yaklasik", "karar", "notlar"):
        s.add_argument(f"--{f}")
    s.set_defaults(fn=cmd_ihale_kaydet)

    s = sub.add_parser("sonuc")
    s.add_argument("--kod", required=True)
    s.add_argument("--sonuc", required=True, help="kazanildi | kaybedildi | katilinmadi | iptal")
    s.add_argument("--teklif")
    s.add_argument("--kazanan")
    s.set_defaults(fn=cmd_sonuc)

    for name, fn in (("metraj-yukle", cmd_metraj_yukle), ("pursantaj-yukle", cmd_pursantaj_yukle)):
        s = sub.add_parser(name)
        s.add_argument("--kod", required=True)
        s.add_argument("dosya")
        s.set_defaults(fn=fn)

    s = sub.add_parser("ders-ekle")
    s.add_argument("--metin", required=True)
    for f in ("idare", "ajan", "etiket", "kod"):
        s.add_argument(f"--{f}")
    s.set_defaults(fn=cmd_ders_ekle)

    s = sub.add_parser("fiyat")
    s.add_argument("poz")
    s.set_defaults(fn=cmd_fiyat)

    s = sub.add_parser("pursantaj-ort")
    s.add_argument("--tur")
    s.set_defaults(fn=cmd_pursantaj_ort)

    s = sub.add_parser("baglam")
    for f in ("idare", "konu", "ajan"):
        s.add_argument(f"--{f}")
    s.set_defaults(fn=cmd_baglam)

    s = sub.add_parser("ara")
    s.add_argument("kelime")
    s.set_defaults(fn=cmd_ara)

    s = sub.add_parser("tercih")
    s.add_argument("--ikn", required=True)
    s.add_argument("--karar", required=True, help="begen | reddet")
    for f in ("idare", "il", "tur", "konu", "yaklasik", "neden"):
        s.add_argument(f"--{f}")
    s.set_defaults(fn=cmd_tercih)

    s = sub.add_parser("tercih-ozet")
    s.set_defaults(fn=cmd_tercih_ozet)

    s = sub.add_parser("kural-ekle")
    s.add_argument("--ad", required=True)
    s.add_argument("--kapsam", help="poz öneki (15.150) ya da tanımda geçen kelime (beton); boşsa tüm kalemler")
    s.add_argument("--islem", required=True, help=" | ".join(ISLEMLER))
    s.add_argument("--deger", required=True)
    s.add_argument("--cumle", help="kullanıcının kuralı söylediği cümle")
    s.set_defaults(fn=cmd_kural_ekle)

    s = sub.add_parser("kural-listele")
    s.set_defaults(fn=cmd_kural_listele)

    s = sub.add_parser("kural-kapat")
    s.add_argument("--id", required=True, type=int)
    s.set_defaults(fn=cmd_kural_kapat)

    s = sub.add_parser("katilimci-yukle")
    s.add_argument("--kod", required=True)
    s.add_argument("--idare", required=True)
    s.add_argument("--yaklasik", required=True)
    for f in ("tarih", "kaynak"):
        s.add_argument(f"--{f}")
    s.add_argument("dosya")
    s.set_defaults(fn=cmd_katilimci_yukle)

    s = sub.add_parser("kurum-fiyat-yukle")
    s.add_argument("--idare", required=True)
    for f in ("kod", "tarih", "kaynak"):
        s.add_argument(f"--{f}")
    s.add_argument("dosya")
    s.set_defaults(fn=cmd_kurum_fiyat_yukle)

    s = sub.add_parser("kurum-fiyat")
    s.add_argument("poz")
    s.add_argument("--idare")
    s.set_defaults(fn=cmd_kurum_fiyat)

    s = sub.add_parser("tenzilat")
    s.add_argument("--idare")
    s.add_argument("--tur")
    s.set_defaults(fn=cmd_tenzilat)

    s = sub.add_parser("rakip")
    s.add_argument("--firma")
    s.add_argument("--idare")
    s.add_argument("--limit", type=int, default=20)
    s.set_defaults(fn=cmd_rakip)

    a = p.parse_args()
    con = connect(a.vt or default_db())
    with con:
        a.fn(con, a)


if __name__ == "__main__":
    main()
