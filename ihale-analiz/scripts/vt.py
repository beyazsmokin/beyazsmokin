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

    ozet = con.execute(
        "SELECT COUNT(*) n, SUM(sonuc='kazanildi') k FROM ihaleler").fetchone()
    print(f"\n## Genel\n- Toplam analiz: {ozet['n']}, kazanılan: {ozet['k'] or 0}")


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

    a = p.parse_args()
    con = connect(a.vt or default_db())
    with con:
        a.fn(con, a)


if __name__ == "__main__":
    main()
