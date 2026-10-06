#!/usr/bin/env python3
"""Takip edilen ihaleler, ajanda ve analiz süreci (panelin ve ajanların ortak veri katmanı).

Panel (`panel.py`) ve ajanlar aynı SQLite veritabanını (`.sistem/veritabani/ihale.db`)
kullanır. Kullanıcı panelden "hesaplanacak" ihale ekler; ajanlar kuyruğu buradan okur,
her adımı `adim` komutuyla `calisma/durum.json` dosyasına yazar, panel süreci canlı gösterir.

Kullanım:
  takip.py liste
  takip.py ekle --kod 2026/123456 --ad "Okul onarımı" [--idare I --il IL --tur birim_fiyat
                --yaklasik 2500000 --ihale-tarihi "2026-10-20 10:30" --durum takipte]
  takip.py guncelle --kod K [--ihale-tarihi ... --idare ... --yaklasik ... --tur ...]
  takip.py kuyruk                         # panelden "Analizi başlat" denmiş ihaleler
  takip.py durum --kod K --durum analizde # takipte|hesaplanacak|analizde|rapor_hazir|teklif_verildi|...
  takip.py adim --kod K --adim 2a --durum basladi|bitti|hata [--mesaj "..."]
  takip.py etkinlik-ekle --kod K --tarih 2026-10-15 [--saat 14:00] --tur yer_gorme --baslik "Yer görme"
                [--kaynak ajan]           # şartnameden okunan tarihler ajandaya böyle girer (BELGE)
  takip.py ajanda [--gun 30]              # yaklaşan ihale günleri, etkinlikler ve hatırlatmalar

İhale tarihi bir etkinlik olarak ayrıca yazılmaz; ajanda onu ve `config.yaml` içindeki
`panel.hatirlatma_gun` hatırlatmalarını kendisi üretir.
"""
import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import vt

DURUMLAR = {
    "takipte": "Takipte",
    "hesaplanacak": "Hesaplanacak",
    "analizde": "Analizde",
    "rapor_hazir": "Rapor hazır",
    "teklif_verildi": "Teklif verildi",
    "kazanildi": "Kazanıldı",
    "kaybedildi": "Kaybedildi",
    "katilinmadi": "Katılınmadı",
    "iptal": "İptal",
}
KAPALI = {"kazanildi", "kaybedildi", "katilinmadi", "iptal"}

ETKINLIK_TURLERI = {
    "ihale": "İhale günü",
    "yer_gorme": "Yer görme",
    "aciklama_talebi": "Açıklama talebi son günü",
    "dokuman": "Doküman / e-imza",
    "teminat": "Teminat",
    "sozlesme": "Sözleşme",
    "hatirlatma": "Hatırlatma",
    "diger": "Diğer",
}

# SKILL.md §2 iş akışı. Dosya: durum.json yoksa adımın bittiğini gösteren çıktı.
ADIMLAR = [
    ("0", "Hazırlık ve geçmiş bağlam", "koordinator", ["calisma/00-baglam.md"]),
    ("1", "Doküman okuma", "dokuman-okuyucu", ["calisma/01-ozet.md"]),
    ("2a", "İdari analiz", "idari-analist", ["calisma/02-idari.md"]),
    ("2b", "Teknik analiz", "teknik-analist", ["calisma/03-teknik.md"]),
    ("2c", "Mali analiz", "mali-analist", ["calisma/04-mali.md"]),
    ("2d", "Metraj", "metraj-analist", ["calisma/06-metraj.md"]),
    ("3", "Risk denetimi", "risk-denetci", ["calisma/05-riskler.md"]),
    ("4", "Rapor (Markdown, HTML, PDF, Excel)", "rapor-yazari", ["* Rapor.md"]),
    ("5", "Öğrenme kaydı", "koordinator", []),
]
# Ön inceleme: ihale dosyası inmeden, takip sitesinin ilan bilgisi ve öğrenen veritabanıyla
# yapılan hızlı değerlendirme (motor.py --tur on). Çıktı: "<kod> Ön İnceleme Rapor.md".
ON_ADIMLAR = [
    ("o1", "İlan bilgisi", "tarayici", []),
    ("o2", "Geçmiş, rakip ve tenzilat", "koordinator", []),
    ("o3", "Uygunluk puanı", "tarayici", []),
    ("o4", "Ön değerlendirme", "koordinator", []),
    ("o5", "Ön inceleme raporu", "rapor-yazari", ["* Ön İnceleme Rapor.md"]),
]
ON_EK = "Ön İnceleme Rapor"

SCHEMA = """
CREATE TABLE IF NOT EXISTS takip (
  kod TEXT PRIMARY KEY, ikn TEXT, ad TEXT, idare TEXT, il TEXT, tur TEXT, yaklasik REAL,
  ihale_tarihi TEXT, durum TEXT DEFAULT 'takipte', oncelik INTEGER DEFAULT 2, notlar TEXT,
  kaynak_url TEXT, teklif REAL, kazanan_teklif REAL, eklenme TEXT, guncelleme TEXT
);
CREATE TABLE IF NOT EXISTS etkinlikler (
  id INTEGER PRIMARY KEY AUTOINCREMENT, kod TEXT, tarih TEXT, saat TEXT, tur TEXT,
  baslik TEXT, aciklama TEXT, tamam INTEGER DEFAULT 0, kaynak TEXT DEFAULT 'kullanici'
);
CREATE INDEX IF NOT EXISTS ix_etkinlik_tarih ON etkinlikler(tarih);
"""
ALANLAR = ("ikn", "ad", "idare", "il", "tur", "yaklasik", "ihale_tarihi", "durum", "oncelik",
           "notlar", "kaynak_url", "teklif", "kazanan_teklif")


# --- Yollar ------------------------------------------------------------------

def alan_dir() -> Path:
    """Çalışma alanı kökü: .sistem/skill/scripts/ içinden çalışıyorsa üç üst klasör."""
    scripts = Path(__file__).resolve().parent
    if scripts.parents[1].name == ".sistem":
        return scripts.parents[2]
    import os
    if os.environ.get("IHALE_ALAN"):
        return Path(os.environ["IHALE_ALAN"])
    from init_workspace import FOLDER_NAME, desktop_dir
    return desktop_dir() / FOLDER_NAME


def baglan(alan: Path):
    con = vt.connect(alan / ".sistem" / "veritabani" / "ihale.db")
    con.executescript(SCHEMA)
    return con


def klasor_adi(kod: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", kod).strip(" .") or "ihale"


def ihale_klasoru(alan: Path, kod: str) -> Path:
    return alan / "İhaleler" / kod


def simdi() -> str:
    return datetime.now().isoformat(timespec="seconds")


def tarih_norm(v: str | None) -> str | None:
    """'20.10.2026 10:30', '2026-10-20T10:30' ya da '2026-10-20' -> '2026-10-20T10:30' / '2026-10-20'."""
    if not v:
        return None
    v = v.strip().replace("T", " ")
    for f in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(v, f).strftime("%Y-%m-%dT%H:%M")
        except ValueError:
            pass
    for f in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(v, f).strftime("%Y-%m-%d")
        except ValueError:
            pass
    raise ValueError(f"Tarih anlaşılamadı: {v} (ör. 2026-10-20 10:30)")


# --- İhaleler ----------------------------------------------------------------

def ekle(con, alan: Path, veri: dict) -> str:
    ham = (veri.get("kod") or veri.get("ikn") or "").strip()
    if not ham:
        ham = f"{veri.get('idare') or 'ihale'}-{veri.get('ad') or ''}-{date.today():%Y%m%d}"
    kod = klasor_adi(ham)
    if con.execute("SELECT 1 FROM takip WHERE kod=?", (kod,)).fetchone():
        raise ValueError(f"Bu kodla bir ihale zaten takipte: {kod}")
    klasor = ihale_klasoru(alan, kod)
    (klasor / "kaynak").mkdir(parents=True, exist_ok=True)
    (klasor / "calisma").mkdir(exist_ok=True)
    (klasor / "calisma" / ".takip-disi").unlink(missing_ok=True)
    temiz = alanlari_temizle(veri)
    temiz.setdefault("ikn", ham if re.fullmatch(r"\d{4}/\d+", ham) else None)
    temiz.setdefault("durum", "takipte")
    kolon = ["kod", "eklenme", "guncelleme", *temiz]
    con.execute(f"INSERT INTO takip ({','.join(kolon)}) VALUES ({','.join('?' * len(kolon))})",
                (kod, simdi(), simdi(), *temiz.values()))
    if temiz["durum"] in KAPALI:
        sonucu_ogren(con, kod)
    return kod


def tutar(v) -> float:
    """'2.500.000', '2.500.000,50', '2500000.5' ve '2 500 000 ₺' biçimlerini okur."""
    s = re.sub(r"[\s₺]|TL", "", str(v))
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return vt.num(s)
    except ValueError:
        raise ValueError(f"Tutar anlaşılamadı: {v}")


def alanlari_temizle(veri: dict) -> dict:
    temiz = {}
    for k in ALANLAR:
        if k not in veri:
            continue
        v = veri[k]
        if isinstance(v, str):
            v = v.strip() or None
        if k in ("yaklasik", "teklif", "kazanan_teklif") and v is not None:
            v = tutar(v)
        if k == "oncelik" and v is not None:
            v = max(1, min(3, int(v)))
        if k == "ihale_tarihi":
            v = tarih_norm(v)
        if k == "durum" and v not in DURUMLAR:
            raise ValueError(f"Geçersiz durum: {v}")
        temiz[k] = v
    return temiz


def guncelle(con, kod: str, veri: dict) -> None:
    temiz = alanlari_temizle(veri)
    if not temiz:
        return
    cur = con.execute(
        f"UPDATE takip SET {', '.join(f'{k}=?' for k in temiz)}, guncelleme=? WHERE kod=?",
        (*temiz.values(), simdi(), kod))
    if not cur.rowcount:
        raise KeyError(kod)
    if temiz.get("durum") in KAPALI:
        sonucu_ogren(con, kod)


def sonucu_ogren(con, kod: str) -> None:
    """Kapanan ihalenin sonucunu öğrenen veritabanına (ihaleler tablosu) yazar."""
    t = con.execute("SELECT * FROM takip WHERE kod=?", (kod,)).fetchone()
    con.execute(
        """INSERT INTO ihaleler (kod, tarih, idare, konu, tur, yaklasik_maliyet, sonuc, teklif,
                                 kazanan_teklif, kayit_tarihi) VALUES (?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(kod) DO UPDATE SET sonuc=excluded.sonuc,
             teklif=COALESCE(excluded.teklif, ihaleler.teklif),
             kazanan_teklif=COALESCE(excluded.kazanan_teklif, ihaleler.kazanan_teklif),
             idare=COALESCE(ihaleler.idare, excluded.idare), konu=COALESCE(ihaleler.konu, excluded.konu),
             tur=COALESCE(ihaleler.tur, excluded.tur),
             yaklasik_maliyet=COALESCE(ihaleler.yaklasik_maliyet, excluded.yaklasik_maliyet)""",
        (kod, (t["ihale_tarihi"] or "")[:10] or vt.today(), t["idare"], t["ad"], t["tur"], t["yaklasik"],
         t["durum"], t["teklif"], t["kazanan_teklif"], vt.today()))


def esitle(con, alan: Path) -> None:
    """İhaleler/ altındaki klasörleri takibe alır, analiz durumunu dosyalardan günceller.

    Sohbetten başlatılan analizler de böylece panelde görünür."""
    kok = alan / "İhaleler"
    if not kok.is_dir():
        return
    var = {r["kod"]: r["durum"] for r in con.execute("SELECT kod, durum FROM takip")}
    for d in sorted(p for p in kok.iterdir() if p.is_dir() and not p.name.startswith(".")
                    and not (p / "calisma" / ".takip-disi").exists()):
        s = surec(d)
        if d.name not in var:
            i = con.execute("SELECT * FROM ihaleler WHERE kod=?", (d.name,)).fetchone()
            durum = "rapor_hazir" if s["rapor"] else "analizde" if s["basladi"] else "takipte"
            con.execute(
                """INSERT INTO takip (kod, ad, idare, tur, yaklasik, durum, eklenme, guncelleme)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (d.name, i and i["konu"], i and i["idare"], i and i["tur"], i and i["yaklasik_maliyet"],
                 durum, simdi(), simdi()))
        elif var[d.name] in ("takipte", "analizde") or (var[d.name] == "hesaplanacak" and s["calisiyor"]):
            # kuyruktaki ihale ajan başlayana dek kuyrukta kalır (eski raporu olsa bile)
            # bitmiş bir ön inceleme ihaleyi "analizde"ye çekmez
            # yarıda kesilen motor analizi ihaleyi "analizde" bırakmaz, yeniden başlatılabilir
            yeni = "analizde" if s["calisiyor"] else "rapor_hazir" if s["rapor"] else \
                "takipte" if var[d.name] == "analizde" and s["motor"] else var[d.name]
            if yeni != var[d.name]:
                con.execute("UPDATE takip SET durum=?, guncelleme=? WHERE kod=?", (yeni, simdi(), d.name))


def liste(con) -> list[dict]:
    return [dict(r) for r in con.execute(
        """SELECT * FROM takip ORDER BY
             CASE WHEN durum IN ('kazanildi','kaybedildi','katilinmadi','iptal') THEN 1 ELSE 0 END,
             COALESCE(ihale_tarihi, '9999'), oncelik""")]


# --- Analiz süreci -----------------------------------------------------------

def durum_dosyasi(klasor: Path) -> Path:
    return klasor / "calisma" / "durum.json"


def motor_calisiyor(klasor: Path, kayit: dict) -> bool:
    """Panelin başlattığı analiz (motor.py) sürüyor mu: başlangıç var, bitiş yok ve motorun kilidi
    duruyor (süreç yeni başlatıldıysa kilit birkaç saniye sonra gelir)."""
    if not kayit.get("baslangic") or kayit.get("bitis"):
        return False
    try:
        gecen = datetime.now() - datetime.fromisoformat(kayit["baslangic"])
    except ValueError:
        return False
    return gecen < timedelta(minutes=2) or ((klasor / "calisma" / ".motor.kilit").exists()
                                            and gecen < timedelta(hours=3))


def surec_bitir(klasor: Path) -> None:
    p = durum_dosyasi(klasor)
    try:
        veri = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    veri["bitis"] = simdi()
    gecici = p.with_suffix(".tmp")
    gecici.write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")
    gecici.replace(p)


def surec_baslat(klasor: Path, tur: str) -> None:
    """Yeni analiz için durum.json'u sıfırlar; tur 'on' (ön inceleme) ya da 'detay'."""
    p = durum_dosyasi(klasor)
    p.parent.mkdir(parents=True, exist_ok=True)
    gecici = p.with_suffix(".tmp")
    gecici.write_text(json.dumps({"tur": tur, "baslangic": simdi(), "adimlar": {}, "gunluk": []},
                                 ensure_ascii=False, indent=1), encoding="utf-8")
    gecici.replace(p)


def adim_yaz(klasor: Path, adim: str, durum: str, mesaj: str | None = None) -> None:
    if adim not in {a[0] for a in ADIMLAR + ON_ADIMLAR}:
        raise ValueError(f"Geçersiz adım: {adim}")
    if durum not in ("basladi", "bitti", "hata"):
        raise ValueError("--durum basladi, bitti ya da hata olmalı")
    p = durum_dosyasi(klasor)
    p.parent.mkdir(parents=True, exist_ok=True)
    veri = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"adimlar": {}, "gunluk": []}
    tur = "on" if adim in {a[0] for a in ON_ADIMLAR} else "detay"
    if (veri.get("tur") or "detay") != tur:  # ön incelemeden sonra başlayan analiz yeni süreçtir
        veri = {"tur": tur, "adimlar": {}, "gunluk": []}
    veri["adimlar"][adim] = {"durum": durum, "zaman": simdi(), "mesaj": mesaj}
    veri["gunluk"].append({"zaman": simdi(), "adim": adim, "durum": durum, "mesaj": mesaj})
    veri["gunluk"] = veri["gunluk"][-200:]
    gecici = p.with_suffix(".tmp")
    gecici.write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")
    gecici.replace(p)


def _var(klasor: Path, desen: str) -> Path | None:
    bulunan = sorted(klasor.glob(desen))
    if desen == "* Rapor.md":  # ön inceleme raporu ana rapor sayılmaz
        bulunan = [f for f in bulunan if not f.stem.endswith(ON_EK)]
    return next(iter(bulunan), None)


def surec(klasor: Path) -> dict:
    """Her adımın durumu: durum.json'dan, yoksa çıktı dosyalarından çıkarılır."""
    p = durum_dosyasi(klasor)
    try:
        kayit = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except (json.JSONDecodeError, OSError):
        kayit = {}
    adimlar = []
    tur = kayit.get("tur") or "detay"
    for kimlik, ad, ajan, dosyalar in (ON_ADIMLAR if tur == "on" else ADIMLAR):
        k = kayit.get("adimlar", {}).get(kimlik)
        cikti = [f for f in (_var(klasor, d) for d in dosyalar) if f]
        if k:
            durum = {"basladi": "calisiyor", "bitti": "bitti", "hata": "hata"}[k["durum"]]
            zaman, mesaj = k.get("zaman"), k.get("mesaj")
        elif dosyalar and len(cikti) == len(dosyalar):
            durum = "bitti"
            zaman = datetime.fromtimestamp(cikti[0].stat().st_mtime).isoformat(timespec="seconds")
            mesaj = None
        else:
            durum, zaman, mesaj = "bekliyor", None, None
        adimlar.append({"adim": kimlik, "ad": ad, "ajan": ajan, "durum": durum, "zaman": zaman,
                        "mesaj": mesaj, "cikti": [str(f.relative_to(klasor)).replace("\\", "/") for f in cikti]})
    biten = sum(a["durum"] == "bitti" for a in adimlar)
    return {
        "adimlar": adimlar,
        "yuzde": round(100 * biten / len(adimlar)),
        "basladi": any(a["durum"] != "bekliyor" for a in adimlar),
        "calisiyor": any(a["durum"] == "calisiyor" for a in adimlar) or motor_calisiyor(klasor, kayit),
        "motor": bool(kayit.get("baslangic")),
        "tur": tur,
        "rapor": bool(_var(klasor, "* Rapor.md")),
        "gunluk": kayit.get("gunluk", [])[-50:],
    }


def dosyalar(klasor: Path) -> dict:
    def bilgi(f: Path) -> dict:
        st = f.stat()
        return {"yol": str(f.relative_to(klasor)).replace("\\", "/"), "ad": f.name, "boyut": st.st_size,
                "zaman": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")}
    kaynak = klasor / "kaynak"
    return {
        "kaynak": [bilgi(f) for f in sorted(kaynak.rglob("*")) if f.is_file()] if kaynak.is_dir() else [],
        "raporlar": [bilgi(f) for f in sorted(klasor.glob("*"))
                     if f.is_file() and f.suffix.lower() in (".md", ".html", ".pdf", ".xlsx")],
    }


# --- Ajanda ------------------------------------------------------------------

def hatirlatma_gunleri(alan: Path) -> list[int]:
    cfg = alan / ".sistem" / "config.yaml"
    if cfg.exists():
        m = re.search(r"^\s*hatirlatma_gun:\s*\[([^\]]*)\]", cfg.read_text(encoding="utf-8"), re.M)
        if m:
            return [int(x) for x in re.findall(r"\d+", m.group(1))]
    return [7, 3, 1]


def ajanda(con, alan: Path, bas: date, son: date) -> list[dict]:
    """Aralıktaki ihale günleri, etkinlikler ve ihale tarihinden üretilen hatırlatmalar."""
    olaylar = []
    gunler = hatirlatma_gunleri(alan)
    for t in con.execute("SELECT * FROM takip WHERE ihale_tarihi IS NOT NULL"):
        gun = date.fromisoformat(t["ihale_tarihi"][:10])
        saat = t["ihale_tarihi"][11:16] or None
        ad = t["ad"] or t["kod"]
        kapali = t["durum"] in KAPALI
        if bas <= gun <= son:
            olaylar.append({"id": f"ihale-{t['kod']}", "kod": t["kod"], "tarih": gun.isoformat(), "saat": saat,
                            "tur": "ihale", "baslik": f"İhale: {ad}", "aciklama": t["idare"],
                            "tamam": kapali, "kaynak": "otomatik", "durum": t["durum"]})
        if kapali or t["durum"] == "teklif_verildi":
            continue
        for g in gunler:
            h = gun - timedelta(days=g)
            if bas <= h <= son:
                olaylar.append({"id": f"hat-{t['kod']}-{g}", "kod": t["kod"], "tarih": h.isoformat(),
                                "saat": None, "tur": "hatirlatma",
                                "baslik": f"{g} gün kaldı: {ad}", "aciklama": "Teklif hazırlığını kontrol edin",
                                "tamam": False, "kaynak": "otomatik", "durum": t["durum"]})
    for e in con.execute(
            """SELECT e.*, t.ad ihale_ad, t.durum FROM etkinlikler e LEFT JOIN takip t ON t.kod = e.kod
               WHERE e.tarih BETWEEN ? AND ? AND (e.kod IS NULL OR t.kod IS NOT NULL)""",
            (bas.isoformat(), son.isoformat())):  # takipten çıkan ihalenin kaydı ajandada kalmaz
        d = dict(e)
        d["tamam"] = bool(d["tamam"])
        olaylar.append(d)
    return sorted(olaylar, key=lambda o: (o["tarih"], o["saat"] or "99"))


def etkinlik_ekle(con, veri: dict) -> int:
    tur = veri.get("tur") or "diger"
    if tur not in ETKINLIK_TURLERI or tur == "ihale":
        raise ValueError(f"Geçersiz etkinlik türü: {tur} (ihale günü ihalenin tarihinden gelir)")
    tarih = tarih_norm(veri.get("tarih"))
    if not tarih:
        raise ValueError("Tarih gerekli")
    saat = veri.get("saat") or (tarih[11:16] if "T" in tarih else None)
    baslik = (veri.get("baslik") or "").strip() or ETKINLIK_TURLERI[tur]
    cur = con.execute(
        "INSERT INTO etkinlikler (kod, tarih, saat, tur, baslik, aciklama, kaynak) VALUES (?,?,?,?,?,?,?)",
        (veri.get("kod") or None, tarih[:10], saat, tur, baslik, veri.get("aciklama"),
         veri.get("kaynak") or "kullanici"))
    return cur.lastrowid


def ics(olaylar: list[dict]) -> str:
    def kac(s):
        return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    satir = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ihale-analiz//panel//TR", "CALSCALE:GREGORIAN",
             "X-WR-CALNAME:İhale Ajandası"]
    damga = datetime.now().strftime("%Y%m%dT%H%M%S")
    for o in olaylar:
        g = o["tarih"].replace("-", "")
        satir += ["BEGIN:VEVENT", f"UID:{o['id']}@ihale-analiz", f"DTSTAMP:{damga}"]
        if o.get("saat"):
            bas = datetime.strptime(f"{o['tarih']} {o['saat']}", "%Y-%m-%d %H:%M")
            satir += [f"DTSTART:{bas:%Y%m%dT%H%M%S}", f"DTEND:{bas + timedelta(hours=1):%Y%m%dT%H%M%S}"]
        else:
            ertesi = date.fromisoformat(o["tarih"]) + timedelta(days=1)
            satir += [f"DTSTART;VALUE=DATE:{g}", f"DTEND;VALUE=DATE:{ertesi:%Y%m%d}"]
        satir += [f"SUMMARY:{kac(o['baslik'])}", f"DESCRIPTION:{kac(o.get('aciklama'))}"]
        if o["tur"] == "ihale":
            satir += ["BEGIN:VALARM", "TRIGGER:-PT2H", "ACTION:DISPLAY", f"DESCRIPTION:{kac(o['baslik'])}",
                      "END:VALARM"]
        satir.append("END:VEVENT")
    satir.append("END:VCALENDAR")
    return "\r\n".join(satir) + "\r\n"


# --- Komut satırı --------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--alan", type=Path, help="çalışma alanı (varsayılan: Masaüstü/İhale Analiz)")
    sub = p.add_subparsers(dest="komut", required=True)
    sub.add_parser("liste")
    sub.add_parser("kuyruk")
    s = sub.add_parser("ekle")
    s.add_argument("--kod")
    for f in ("ad", "idare", "il", "tur", "yaklasik", "ihale-tarihi", "durum", "notlar", "kaynak-url"):
        s.add_argument(f"--{f}")
    s = sub.add_parser("guncelle")
    s.add_argument("--kod", required=True)
    for f in ("ad", "idare", "il", "tur", "yaklasik", "ihale-tarihi", "notlar", "kaynak-url"):
        s.add_argument(f"--{f}")
    s = sub.add_parser("durum")
    s.add_argument("--kod", required=True)
    s.add_argument("--durum", required=True, choices=list(DURUMLAR))
    s = sub.add_parser("adim")
    s.add_argument("--kod", required=True)
    s.add_argument("--adim", required=True, choices=[a[0] for a in ADIMLAR + ON_ADIMLAR])
    s.add_argument("--durum", required=True, choices=["basladi", "bitti", "hata"])
    s.add_argument("--mesaj")
    s = sub.add_parser("etkinlik-ekle")
    s.add_argument("--kod")
    s.add_argument("--tarih", required=True)
    s.add_argument("--saat")
    s.add_argument("--tur", default="diger", choices=[k for k in ETKINLIK_TURLERI if k != "ihale"])
    s.add_argument("--baslik")
    s.add_argument("--aciklama")
    s.add_argument("--kaynak", default="ajan")
    s = sub.add_parser("ajanda")
    s.add_argument("--gun", type=int, default=30)
    a = p.parse_args()

    alan = a.alan or alan_dir()
    con = baglan(alan)
    try:
        with con:
            esitle(con, alan)
            if a.komut == "liste":
                for t in liste(con):
                    print(f"{t['kod']} | {DURUMLAR.get(t['durum'], t['durum'])} | {t['ad'] or '-'} | "
                          f"{t['idare'] or '-'} | ihale: {(t['ihale_tarihi'] or '-').replace('T', ' ')}")
            elif a.komut == "kuyruk":
                rows = con.execute("SELECT * FROM takip WHERE durum='hesaplanacak' ORDER BY oncelik, eklenme")
                n = 0
                for t in rows:
                    n += 1
                    print(f"{t['kod']} | {t['ad'] or '-'} | {ihale_klasoru(alan, t['kod'])}")
                if not n:
                    print("Kuyrukta ihale yok")
            elif a.komut == "ekle":
                veri = {k.replace("-", "_"): v for k, v in vars(a).items() if v is not None}
                print(f"Takibe alındı: {ekle(con, alan, veri)}")
            elif a.komut == "guncelle":
                veri = {k.replace("-", "_"): v for k, v in vars(a).items()
                        if v is not None and k not in ("kod", "komut", "alan")}
                guncelle(con, klasor_adi(a.kod), veri)
                print(f"Güncellendi: {klasor_adi(a.kod)}")
            elif a.komut == "durum":
                guncelle(con, klasor_adi(a.kod), {"durum": a.durum})
                print(f"{a.kod}: {DURUMLAR[a.durum]}")
            elif a.komut == "adim":
                kod = klasor_adi(a.kod)
                adim_yaz(ihale_klasoru(alan, kod), a.adim, a.durum, a.mesaj)
                if a.durum == "basladi":
                    con.execute("UPDATE takip SET durum='analizde', guncelleme=? WHERE kod=? AND "
                                "durum IN ('takipte','hesaplanacak')", (simdi(), kod))
                print(f"{kod} adım {a.adim}: {a.durum}")
            elif a.komut == "etkinlik-ekle":
                veri = vars(a).copy()
                veri["kod"] = klasor_adi(a.kod) if a.kod else None
                print(f"Ajandaya eklendi (#{etkinlik_ekle(con, veri)})")
            elif a.komut == "ajanda":
                bugun = date.today()
                olaylar = ajanda(con, alan, bugun, bugun + timedelta(days=a.gun))
                for o in olaylar:
                    print(f"{o['tarih']} {o['saat'] or '     '} | {ETKINLIK_TURLERI.get(o['tur'], o['tur'])} | "
                          f"{o['baslik']}" + (" (tamam)" if o["tamam"] else ""))
                if not olaylar:
                    print(f"Önümüzdeki {a.gun} günde kayıt yok")
    except KeyError as e:
        sys.exit(f"Hata: takipte böyle bir ihale yok: {e}. Önce `takip.py ekle`.")
    except ValueError as e:
        sys.exit(f"Hata: {e}")


if __name__ == "__main__":
    main()
